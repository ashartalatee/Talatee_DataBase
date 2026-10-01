import { useState } from "react";
import { SPEC, EX, MC } from "./arahData.js";
import { api } from "../../api/client";
import "./arah.css";

const P = {
  term: '<polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>',
  db: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14a9 3 0 0 0 18 0V5M3 12a9 3 0 0 0 18 0"/>',
  zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  box: '<path d="M21 8l-9-5-9 5v8l9 5 9-5zM3 8l9 5 9-5M12 13v9"/>',
  layout: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>',
  flow: '<circle cx="6" cy="12" r="3"/><circle cx="18" cy="6" r="3"/><circle cx="18" cy="18" r="3"/><path d="M9 11l6-4M9 13l6 4"/>',
  bot: '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 8V4M9 14h.01M15 14h.01"/>',
  brief: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2 20c0-3.5 3-6 7-6s7 2.5 7 6M17 4a3.5 3.5 0 0 1 0 7M22 20c0-3-2-5-5-5.5"/>',
  video: '<rect x="3" y="6" width="13" height="12" rx="2"/><path d="M16 10l5-3v10l-5-3"/>',
  repeat: '<path d="M17 2l4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>',
  wallet: '<path d="M3 7a2 2 0 0 1 2-2h13v4"/><path d="M3 7v11a2 2 0 0 0 2 2h15V9H5a2 2 0 0 1-2-2z"/><circle cx="16" cy="14" r="1"/>',
  shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
};

const Icon = ({ n }) => (
  <span className="a-ico">
    <svg viewBox="0 0 24 24" dangerouslySetInnerHTML={{ __html: P[n] }} />
  </span>
);
const Dots = ({ v }) => (
  <span className="a-dots">{[1, 2, 3, 4, 5].map((i) => <i key={i} className={i <= v ? "on" : ""} />)}</span>
);

const OPEN_KEY = "arah-open";
const FUN_KEY = "kompas-funnel";
const read = (k) => { try { return JSON.parse(localStorage.getItem(k) || "{}"); } catch { return {}; } };
const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* abaikan */ } };

// Status buka/tutup tiap lipatan diingat per browser.
function useFold(id, def) {
  const [open, setOpen] = useState(() => { const s = read(OPEN_KEY); return id in s ? !!s[id] : def; });
  const set = (v) => { setOpen(v); const s = read(OPEN_KEY); s[id] = v; write(OPEN_KEY, s); };
  return [open, set];
}

function Fold({ id, def = false, icon, title, hint, level = "s", children }) {
  const [open, set] = useFold(id, def);
  return (
    <details className={`a-fold a-${level}`} open={open}
      onToggle={(e) => { if (e.currentTarget.open !== open) set(e.currentTarget.open); }}>
      <summary>
        {icon && <Icon n={icon} />}
        <span className="a-ft">{title}</span>
        {hint && <span className="a-fh">{hint}</span>}
        <svg className="a-chev" viewBox="0 0 24 24" aria-hidden="true"><polyline points="6 9 12 15 18 9" /></svg>
      </summary>
      <div className="a-fb">{children}</div>
    </details>
  );
}

// Memarkir ide ke database lewat API yang sama dengan kartu Parkir ide,
// lalu memberi tahu kartu itu lewat event agar daftarnya langsung bertambah.
const parkToDb = async (text) => {
  const created = await api.createKompasParked(text, "");
  window.dispatchEvent(new CustomEvent("kompas:parked", { detail: created }));
};

function FocusGuard({ onPark }) {
  const [idea, setIdea] = useState("");
  const [on, setOn] = useState([false, false, false]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const n = on.filter(Boolean).length;
  const has = idea.trim().length > 0;
  const tone = !has ? "" : n === 3 ? "ok" : n === 2 ? "mid" : "no";
  const text = !has ? "Isi dulu idenya" : n === 3 ? "Kerjakan. Selaras." : n === 2 ? "Ragu. Ubah dulu atau parkir." : "Parkir. Menjauh dari spesialis.";
  const park = async () => {
    const v = idea.trim();
    if (!v || busy) return;
    setBusy(true); setMsg(null);
    try {
      await onPark(v);
      setIdea(""); setOn([false, false, false]);
      setMsg({ ok: true, t: "Terparkir. Boleh ditinjau lagi setelah 30 hari." });
    } catch {
      setMsg({ ok: false, t: "Gagal memarkir ide. Pastikan backend menyala, lalu coba lagi." });
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="a-guard">
      <input value={idea} onChange={(e) => setIdea(e.target.value)} maxLength={200} placeholder="Mau kerjakan atau pelajari apa hari ini?" aria-label="Ide" />
      <div className="a-qs">
        {SPEC.qs.map((q, i) => (
          <button key={q} type="button" className="a-q" aria-pressed={on[i]}
            onClick={() => setOn((o) => o.map((x, j) => (j === i ? !x : x)))}>
            <span className="a-c">✓</span>{q}
          </button>
        ))}
      </div>
      <div className="a-verdict">
        <strong className={tone}>{text}</strong>
        <button type="button" className="a-go" disabled={!has || busy} onClick={park}>
          {busy ? "Memarkir…" : "Simpan ke Parkir ide"}
        </button>
      </div>
      {msg && <p className={`a-msg ${msg.ok ? "ok" : "mid"}`} role="status">{msg.t}</p>}
      <p className="a-rule"><b>Aturan:</b> {SPEC.rule}</p>
    </div>
  );
}

function MoneyCard({ k, x, c, funnel, bump }) {
  const f = funnel[x] || [0, 0, 0, 0];
  const exs = EX[x] || [];
  return (
    <Fold id={`m${x}`} level="m" icon={k.i} title={`0${x + 1}  ${k.n}`} hint={k.md}>
      <p className="a-ds">{c.desc}</p>
      <div className="a-mt">
        <div>Cepat <Dots v={k.m[0]} /></div><div>Stabil <Dots v={k.m[1]} /></div><div>Skala <Dots v={k.m[2]} /></div>
      </div>
      <Fold id={`m${x}-jobs`} level="n" def title="Contoh pekerjaan" hint={`${c.jobs.length} jenis`}>
        <ul className="a-list">{c.jobs.map((j) => <li key={j}>{j}</li>)}</ul>
      </Fold>
      <Fold id={`m${x}-val`} level="n" def title="Contoh nilai" hint={c.val}>
        <p className="a-vv">{c.val}</p><p className="a-vn">{c.note}</p>
      </Fold>
      <Fold id={`m${x}-buyer`} level="n" title="Pembeli dan tawaran" hint={`${k.offers.length} tawaran`}>
        <div className="a-sb">
          <h4>Siapa yang membayar</h4><p>{k.who}</p>
          <h4>Yang bisa ditawarkan</h4>
          <ul className="a-list">{k.offers.map((o) => <li key={o} dangerouslySetInnerHTML={{ __html: o }} />)}</ul>
          {k.est && <p><small>{k.est}</small></p>}
        </div>
      </Fold>
      <Fold id={`m${x}-plan`} level="n" title="Skill, langkah, risiko">
        <div className="a-sb">
          <h4>Skill yang dipakai</h4>
          <div className="a-chips">{k.skills.map((s) => <span key={s}>{s}</span>)}</div>
          <h4>Tiga langkah pertama</h4>
          <ol className="a-list">{k.first.map((o) => <li key={o}>{o}</li>)}</ol>
          <h4>Risiko</h4><p className="a-risk">{k.risk}</p>
        </div>
      </Fold>
      <Fold id={`m${x}-ex`} level="n" title="Contoh nyata" hint={`${exs.length} cerita ilustrasi`}>
        <p className="a-note">Cerita ilustrasi, bukan klien sungguhan.</p>
        {exs.map((e, i) => (
          <Fold key={e.t} id={`m${x}-ex${i}`} level="n" title={e.t}>
            <dl className="a-dl">
              <dt>Situasi</dt><dd>{e.sit}</dd>
              <dt>Yang dibangun</dt><dd>{e.build}</dd>
              <dt>Alurnya</dt><dd><ol className="a-list">{e.flow.map((s) => <li key={s}>{s}</li>)}</ol></dd>
              <dt>Hasil</dt><dd>{e.hasil}</dd>
              <dt>Uangmu</dt><dd className="a-money">{e.uang}</dd>
              <dt>Waktu</dt><dd>{e.waktu}</dd>
            </dl>
          </Fold>
        ))}
      </Fold>
      <Fold id={`m${x}-fun`} level="n" title="Pelacak" hint={`${f[3]} di tahap akhir`}>
        <div className="a-fun">
          {k.st.map((s, j) => (
            <div key={s}>{s}<b>{f[j]}</b>
              <button type="button" aria-label={`Kurangi ${s}`} onClick={() => bump(x, j, -1)}>−</button>
              <button type="button" aria-label={`Tambah ${s}`} onClick={() => bump(x, j, 1)}>+</button>
            </div>
          ))}
        </div>
      </Fold>
    </Fold>
  );
}

/**
 * Bagian "Arah" untuk halaman Kompas.
 * onPark(teks)          : opsional. Bawaannya memarkir ke database lewat api.createKompasParked.
 * funnel, onFunnelChange: opsional, untuk simpan penghitung ke database.
 */
export default function ArahKompas({ onPark, funnel: funnelProp, onFunnelChange }) {
  const [own, setOwn] = useState(() => read(FUN_KEY));
  const [show, setShow] = useFold("arah-detail", true);
  const funnel = funnelProp ?? own;

  const bump = (x, j, d) => {
    const next = { ...funnel, [x]: [...(funnel[x] || [0, 0, 0, 0])] };
    next[x][j] = Math.max(0, next[x][j] + d);
    setOwn(next); write(FUN_KEY, next); onFunnelChange?.(next);
  };

  const ok = SPEC.skills.filter((s) => s.s === "ok").length;
  const hasil = [0, 1, 2, 3].reduce((a, x) => a + ((funnel[x] || [])[3] || 0), 0);

  return (
    <section className="arah" aria-label="Arah">
      <div className="a-hero">
        <svg className="a-compass" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth=".5" aria-hidden="true">
          <circle cx="12" cy="12" r="10" /><circle cx="12" cy="12" r="7.5" strokeDasharray=".4 1.2" />
          <g className="needle"><polygon points="12 4 14 12 12 20 10 12" fill="currentColor" stroke="none" /></g>
        </svg>
        <div className="a-hmain">
          <div className="a-lbl">{SPEC.who}</div>
          <h2 className="a-title">{SPEC.title}</h2>
          <p className="a-niche">{SPEC.niche}</p>
          <p className="a-goal">{SPEC.goal}</p>
          <div className="a-stats">
            <span><b>{ok}/{SPEC.skills.length}</b> skill terbukti</span>
            <span><b>{SPEC.money.length}</b> jalur uang</span>
            <span><b>{hasil}</b> hasil nyata</span>
          </div>
          {SPEC.focus && <div className="a-focus"><small>Fokus minggu ini</small>{SPEC.focus}</div>}
        </div>
        <button type="button" className="a-toggle" aria-expanded={show} onClick={() => setShow(!show)}>
          {show ? "Sembunyikan detail" : "Tampilkan detail"}
        </button>
      </div>

      {show && (
        <div className="a-secs">
          <Fold id="s-alur" icon="flow" title="Alur berpikir" hint="5 tahap">
            <div className="a-flow">
              {["Business", "Data", "System", "Intelligence", "Automation"].map((t, i, a) => (
                <span key={t} className={i === a.length - 1 ? "last" : ""}>{t}</span>
              ))}
            </div>
          </Fold>

          <Fold id="s-skill" icon="term" title="Skill" hint={`${ok}/${SPEC.skills.length} terbukti`}>
            <div className="a-grid">
              {SPEC.skills.map((k) => (
                <div key={k.n} className={`a-card ${k.s === "ok" ? "done" : ""}`}>
                  <Icon n={k.i} /><h4>{k.n}</h4><p>{k.p}</p>
                  <div className={`a-st ${k.s}`}><i />{k.t}</div>
                </div>
              ))}
            </div>
          </Fold>

          <Fold id="s-uang" icon="wallet" title="Sumber uang" hint={`${SPEC.money.length} jalur`}>
            <p className="a-note">Dari yang tercepat sampai yang paling berskala. Angka adalah perkiraan awal, ubah di arahData.js sesuai pengalamanmu.</p>
            <div className="a-secs">
              {SPEC.money.map((k, x) => <MoneyCard key={k.n} k={k} x={x} c={MC[x]} funnel={funnel} bump={bump} />)}
            </div>
          </Fold>

          <Fold id="s-fokus" icon="shield" title="Penjaga fokus" hint="3 pertanyaan">
            <FocusGuard onPark={onPark ?? parkToDb} />
          </Fold>
        </div>
      )}
    </section>
  );
}
