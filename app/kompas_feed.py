"""Bacaan otomatis untuk Kompas: ambil dari sumber pilihan, saring, beri skor,
lalu isi daftar 'Hari ini' (maksimal DAILY_LIMIT).

Sengaja hanya memakai pustaka standar untuk mengambil dan membaca feed,
jadi tidak ada paket baru yang perlu dipasang."""
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models.kompas_reading import DAILY_LIMIT, KompasReading, guess_kind

MAX_AGE_HOURS = 48      # hanya yang terbit dalam 2 hari terakhir
MIN_SCORE = 2           # ambang relevansi (lihat relevance())
PER_SOURCE_INSERT = 3   # paling banyak kandidat per sumber
POOL_TARGET = 12        # ukuran kolam kandidat yang belum dipakai
EXPIRE_DAYS = 3         # kandidat yang tidak terpakai hilang setelah ini
TIMEOUT = 15
MAX_BYTES = 2_000_000
UA = "Mozilla/5.0 (compatible; TalateeKompas/1.0)"


def _gn(query: str, lang: str = "id") -> str:
    """Google News RSS berdasarkan kata kunci, dibatasi 2 hari terakhir."""
    tail = "&hl=id&gl=ID&ceid=ID:id" if lang == "id" else "&hl=en-US&gl=US&ceid=US:en"
    return "https://news.google.com/rss/search?q=" + quote_plus(query + " when:2d") + tail


# Daftar sumber. Ubah sesuka hati: hapus yang tidak berguna, tambah yang kamu percaya.
# Jalankan `python scripts/kompas_refresh.py --check` untuk melihat mana yang hidup.
FEEDS = [
    {"name": "Google News - Skincare ID", "url": _gn("skincare OR kosmetik OR BPOM kosmetik")},
    {"name": "Google News - E-commerce ID", "url": _gn("e-commerce Indonesia OR Shopee OR Tokopedia OR TikTok Shop")},
    {"name": "Google News - Data & AI ID", "url": _gn("kecerdasan buatan bisnis OR analitik data OR otomasi bisnis")},
    {"name": "Google News - AI agents", "url": _gn("AI agents OR n8n OR workflow automation", "en")},
    {"name": "Google News - Data engineering", "url": _gn("business intelligence OR data engineering OR PostgreSQL", "en")},
    {"name": "Google News - Ecommerce & skincare", "url": _gn("ecommerce trends OR skincare industry", "en")},
    {"name": "n8n Blog", "url": "https://blog.n8n.io/rss/"},
    {"name": "Simon Willison", "url": "https://simonwillison.net/atom/everything/"},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
    {"name": "Planet PostgreSQL", "url": "https://planet.postgresql.org/rss20.xml"},
    {"name": "DailySocial", "url": "https://dailysocial.id/feed"},
]

# (kata kuat, kata lemah) per topik. Kata kuat di judul = 3 poin, di ringkasan = 1 poin.
# Kata lemah hanya dihitung 1 poin bila ada di judul.
TOPICS = {
    "data": (
        ["business intelligence", "power bi", "data engineering", "data warehouse", "analitik data",
         "analytics", "postgresql", "postgres", "dashboard", "etl", "sql"],
        ["data", "pipeline"],
    ),
    "automation_ai": (
        ["ai agent", "ai agents", "agentic", "n8n", "automation", "otomasi", "otomatisasi", "workflow",
         "llm", "claude", "openai", "chatbot", "kecerdasan buatan", "artificial intelligence", "mcp"],
        ["agent", "api", "ai"],
    ),
    "ecommerce": (
        ["e-commerce", "ecommerce", "shopee", "tokopedia", "tiktok shop", "lazada", "bukalapak",
         "marketplace", "toko online", "penjual online", "umkm"],
        ["retail", "seller", "logistik"],
    ),
    "skincare": (
        ["skincare", "perawatan kulit", "kosmetik", "kecantikan", "somethinc", "sunscreen",
         "tabir surya", "serum", "bpom", "cosmetic", "cosmetics"],
        ["beauty", "kulit"],
    ),
}


# Sumber yang isinya kebanyakan siaran pers / laporan pasar otomatis (sinyal rendah).
BLOCKED_SOURCES = (
    "openpr", "ein news", "ein presswire", "einpresswire", "globenewswire",
    "prnewswire", "pr newswire", "business wire", "businesswire", "newsmantra",
)
# Judul bergaya laporan pasar otomatis, dan berita kejadian yang bukan pengetahuan.
_SPAM_TITLE = re.compile(
    r"market (size|report|research|intelligence|analysis|forecast|share|outlook)"
    r"|\bcagr\b|(projected|expected|set) to (grow|reach|surge)|to reach (usd|\$)",
    re.I,
)
_EVENT_TITLE = re.compile(
    r"\b(kebakaran|tewas|meninggal|pembunuhan|gempa|banjir|kecelakaan|tersangka|ditangkap)\b", re.I
)


def is_noise(title: str, source: str) -> bool:
    src = (source or "").lower()
    if any(b in src for b in BLOCKED_SOURCES):
        return True
    return bool(_SPAM_TITLE.search(title) or _EVENT_TITLE.search(title))


def _compile(words):
    return [re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)") for w in words]


_PATTERNS = [(_compile(strong), _compile(weak)) for strong, weak in TOPICS.values()]


# ---------------------------------------------------------------- membaca feed

def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(el, *names) -> str:
    for c in el:
        if _local(c.tag) in names and (c.text or "").strip():
            return c.text.strip()
    return ""


def _clean(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _parse_dt(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        dt = parsedate_to_datetime(s)
    except (TypeError, ValueError, IndexError):
        try:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_feed(data: bytes) -> list[dict]:
    """Baca RSS 2.0 atau Atom jadi daftar {title, link, summary, published, source}."""
    root = ET.fromstring(data)
    items = []
    for el in root.iter():
        if _local(el.tag) not in ("item", "entry"):
            continue
        link = ""
        for c in el:
            if _local(c.tag) == "link":
                link = (c.text or "").strip() or (c.get("href") if c.get("rel", "alternate") == "alternate" else "") or ""
                if link:
                    break
        source = _clean(_child_text(el, "source"))
        title = _clean(_child_text(el, "title"))
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3]
        items.append(
            {
                "title": title,
                "link": link,
                "summary": _clean(_child_text(el, "description", "summary", "content")),
                "published": _parse_dt(_child_text(el, "pubDate", "published", "updated", "date")),
                "source": source,
            }
        )
    return items


def fetch(url: str) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*"},
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310 (sumber dari daftar FEEDS sendiri)
        return r.read(MAX_BYTES)


# ------------------------------------------------------------ menyaring & skor

def normalize_url(u: str) -> str:
    p = urlparse(u.strip())
    q = [
        (k, v)
        for k, v in parse_qsl(p.query, keep_blank_values=True)
        if not k.lower().startswith("utm_") and k.lower() not in ("fbclid", "gclid", "ref")
    ]
    return urlunparse((p.scheme.lower(), p.netloc.lower(), p.path, p.params, urlencode(q), ""))


def title_key(t: str) -> str:
    return re.sub(r"\W+", " ", t.lower()).strip()


def relevance(title: str, summary: str) -> int:
    t, s = title.lower(), summary.lower()
    total = 0
    for strong, weak in _PATTERNS:
        best = 0
        for p in strong:
            if p.search(t):
                best = 3
                break
            if p.search(s):
                best = max(best, 1)
        if best < 3:
            for p in weak:
                if p.search(t):
                    best = max(best, 1)
                    break
        total += best
    return total


def process_feed(feed: dict, now: datetime, data: bytes | None = None):
    """Return (jumlah item, kandidat lolos saring terbaik)."""
    items = parse_feed(data if data is not None else fetch(feed["url"]))
    out = []
    for it in items:
        pub = it["published"]
        if pub is None or not it["title"] or not it["link"].startswith(("http://", "https://")):
            continue
        age_h = (now - pub).total_seconds() / 3600
        if age_h > MAX_AGE_HOURS or age_h < -1:
            continue
        if is_noise(it["title"], it["source"] or feed["name"]):
            continue
        rel = relevance(it["title"], it["summary"])
        if rel < MIN_SCORE:
            continue
        recency = max(0, 20 - int(max(age_h, 0) * 20 / MAX_AGE_HOURS))
        out.append(
            {
                "title": it["title"][:300],
                "url": normalize_url(it["link"]),
                "source_name": (it["source"] or feed["name"])[:120],
                "published_at": pub,
                "score": rel * 10 + recency,
            }
        )
    out.sort(key=lambda c: (-c["score"], -c["published_at"].timestamp()))
    return len(items), out[:PER_SOURCE_INSERT]


def collect_candidates(now: datetime | None = None):
    """Ambil semua sumber. Sumber yang gagal dilewati, bukan menghentikan yang lain."""
    now = now or datetime.now(timezone.utc)
    cands, report = [], []
    for feed in FEEDS:
        try:
            total, good = process_feed(feed, now)
            cands.extend(good)
            report.append((feed["name"], "ok", total, len(good), ""))
        except Exception as exc:  # noqa: BLE001
            report.append((feed["name"], "gagal", 0, 0, f"{type(exc).__name__}: {exc}"[:120]))
    return cands, report


# ---------------------------------------------------------------- database

def _live(db: Session, username: str):
    return db.query(KompasReading).filter(
        KompasReading.username == username, KompasReading.dismissed_at.is_(None)
    )


def expire_old(db: Session, username: str, day: date) -> int:
    """Bacaan otomatis yang tidak disentuh hilang sendiri (ditandai dismissed)."""
    now = datetime.now(timezone.utc)
    stale = (
        _live(db, username)
        .filter(
            KompasReading.origin == "auto",
            KompasReading.read_at.is_(None),
            or_(
                and_(KompasReading.planned_for.isnot(None), KompasReading.planned_for < day),
                and_(KompasReading.planned_for.is_(None), KompasReading.expires_on < day),
            ),
        )
        .all()
    )
    for item in stale:
        item.dismissed_at = now
    # Yang sudah lama dibuang tidak perlu disimpan selamanya.
    db.query(KompasReading).filter(
        KompasReading.username == username,
        KompasReading.dismissed_at.isnot(None),
        KompasReading.dismissed_at < now - timedelta(days=45),
    ).delete(synchronize_session=False)
    db.commit()
    return len(stale)


def refresh_candidates(db: Session, username: str, day: date, now: datetime | None = None):
    """Tambahkan kandidat segar ke kolam. Return (jumlah ditambah, laporan sumber)."""
    expire_old(db, username, day)
    cands, report = collect_candidates(now)
    cands.sort(key=lambda c: -c["score"])

    rows = db.query(KompasReading.url, KompasReading.title).filter(KompasReading.username == username).all()
    seen_urls = {normalize_url(u) for u, _ in rows}
    seen_titles = {title_key(t) for _, t in rows}

    pool = _live(db, username).filter(
        KompasReading.origin == "auto",
        KompasReading.planned_for.is_(None),
        KompasReading.read_at.is_(None),
    ).count()
    room = max(0, POOL_TARGET - pool)

    added = 0
    for c in cands:
        if added >= room:
            break
        key = title_key(c["title"])
        if c["url"] in seen_urls or key in seen_titles:
            continue
        seen_urls.add(c["url"])
        seen_titles.add(key)
        db.add(
            KompasReading(
                username=username,
                url=c["url"],
                title=c["title"],
                kind=guess_kind(c["url"]),
                origin="auto",
                source_name=c["source_name"],
                published_at=c["published_at"],
                score=c["score"],
                expires_on=day + timedelta(days=EXPIRE_DAYS),
            )
        )
        added += 1
    db.commit()
    return added, report


def fill_today(db: Session, username: str, day: date) -> int:
    """Isi 'Hari ini' sampai DAILY_LIMIT dari kolam kandidat, utamakan sumber berbeda."""
    have = _live(db, username).filter(KompasReading.planned_for == day).all()
    need = DAILY_LIMIT - len(have)
    if need <= 0:
        return 0

    pool = (
        _live(db, username)
        .filter(
            KompasReading.origin == "auto",
            KompasReading.planned_for.is_(None),
            KompasReading.read_at.is_(None),
            or_(KompasReading.expires_on.is_(None), KompasReading.expires_on >= day),
        )
        .order_by(KompasReading.score.desc(), KompasReading.published_at.desc())
        .all()
    )
    used = {i.source_name for i in have if i.source_name}
    picked = []
    for cand in pool:  # putaran 1: sumber yang belum muncul hari ini
        if len(picked) >= need:
            break
        if cand.source_name not in used:
            picked.append(cand)
            used.add(cand.source_name)
    for cand in pool:  # putaran 2: sisa, sumber boleh berulang
        if len(picked) >= need:
            break
        if cand not in picked:
            picked.append(cand)
    for cand in picked:
        cand.planned_for = day
    if picked:
        db.commit()
    return len(picked)
