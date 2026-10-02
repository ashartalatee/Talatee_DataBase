import { useState } from "react";
import { Icon, useFold, read, write } from "./ArahKompas";
import {
  CRITERIA, DAILY_TARGET, DEFAULT_PRODUCTS, EXPORT_STEPS, FEED, GATE, NOTES, QUESTIONS, STAGES,
} from "./risetData.js";
import "./arah.css";
import "./riset.css";

const KEY = "riset-v1";
const blank = () => ({ products: DEFAULT_PRODUCTS, findings: [], scores: {}, chosen: null, checks: {}, accepted: [] });
const iso = (d = new Date()) => new Date(d.getTime() - d.getTimezoneOffset() * 6e4).toISOString().slice(0, 10);
const uid = () => (globalThis.crypto?.randomUUID ? crypto.randomUUID() : String(Date.now() + Math.random()));
const stageName = (k) => STAGES.find((s) => s.k === k)?.n ?? k;
const isUrl = (v) => /^https?:\/\/\S+\.\S+/.test(v.trim());

// Tiga pertanyaan hari ini: berurutan menyusuri tahap hulu ke hilir, jadi seluruh rantai tercakup.
function dailyQuestions(product, day) {
  return [0, 1, 2].map((i) => {
    const n = day * 3 + i;
    const stage = STAGES[n % STAGES.length];
    const list = QUESTIONS[stage.k];
    return { id: `${day}-${i}`, stage: stage.k, text: list[Math.floor(n / STAGES.length) % list.length].replaceAll("{p}", product) };
  });
}

function QCard({ q, onSave }) {
  const [text, setText] = useState("");
  const [source, setSource] = useState("");
  const [err, setErr] = useState("");
  const save = () => {
    if (text.trim().length < 10) return setErr("Tulis temuanmu minimal satu kalimat.");
    if (!isUrl(source)) return setErr("Sumber wajib berupa tautan (diawali http).");
    onSave({ stage: q.stage, text: text.trim(), source: source.trim() });
    setText(""); setSource(""); setErr("");
  };
  return (
    <div className="r-card">
      <div className="r-tag">{stageName(q.stage)}</div>
      <p className="r-q">{q.text}</p>
      <textarea rows={2} value={text} onChange={(e) => setText(e.target.value)} placeholder="Temuanmu, dengan angka kalau ada" aria-label="Temuan" />
      <input value={source} onChange={(e) => setSource(e.target.value)} placeholder="Tautan sumber (BPS, Kemendag, jurnal, berita)" aria-label="Sumber" />
      {err && <p className="a-note mid">{err}</p>}
      <button type="button" className="a-go" onClick={save}>Simpan temuan</button>
    </div>
  );
}

export default function RisetKompas() {
  const [s, setS] = useState(() => ({ ...blank(), ...read(KEY) }));
  const [open, setOpen] = useFold("riset-open", false); // tertutup secara bawaan: ini riset waktu senggang
  const [tab, setTab] = useState("hari");
  const [sel, setSel] = useState(() => (s.products[0] || DEFAULT_PRODUCTS[0]));
  const [stageSel, setStageSel] = useState(null);
  const [newP, setNewP] = useState("");
  const commit = (next) => { setS(next); write(KEY, next); };

  const today = iso();
  const day = Math.floor(new Date(today).getTime() / 864e5);
  const todays = s.findings.filter((f) => f.date === today);
  const mine = s.findings.filter((f) => f.product === sel);
  const byStage = Object.fromEntries(STAGES.map((st) => [st.k, mine.filter((f) => f.stage === st.k)]));
  const filled = STAGES.filter((st) => byStage[st.k].length > 0).length;

  const counts = {};
  s.findings.forEach((f) => { counts[f.date] = (counts[f.date] || 0) + 1; });
  let streak = 0;
  for (let d = new Date(today); ; d.setDate(d.getDate() - 1)) {
    const c = counts[iso(d)] || 0;
    if (c >= DAILY_TARGET) streak++;
    else if (iso(d) !== today) break;
  }

  const add = (f) => commit({ ...s, findings: [{ id: uid(), date: today, product: sel, ...f }, ...s.findings] });
  const del = (id) => commit({ ...s, findings: s.findings.filter((f) => f.id !== id) });
  const accept = (item) => {
    commit({ ...s, findings: [{ id: uid(), date: today, product: item.product, stage: item.stage, text: item.text, source: item.url }, ...s.findings], accepted: [...s.accepted, item.id] });
  };
  const addProduct = () => {
    const v = newP.trim();
    if (!v || s.products.includes(v)) return;
    commit({ ...s, products: [...s.products, v] }); setSel(v); setNewP("");
  };
  const setScore = (p, k, v) => commit({ ...s, scores: { ...s.scores, [p]: { ...(s.scores[p] || {}), [k]: v } } });
  const total = (p) => CRITERIA.reduce((a, c) => a + ((s.scores[p] || {})[c.k] || 0), 0);
  const scored = (p) => CRITERIA.every((c) => ((s.scores[p] || {})[c.k] || 0) > 0);

  const ready = [
    { ok: mine.length >= GATE.minFindings, t: `Temuan ${mine.length}/${GATE.minFindings}` },
    { ok: STAGES.every((st) => byStage[st.k].length >= GATE.perStage), t: `Tiap tahap minimal ${GATE.perStage} temuan` },
    { ok: scored(sel), t: "Keenam kriteria sudah dinilai" },
  ];
  const canChoose = ready.every((r) => r.ok);
  const feed = FEED.filter((f) => f.product === sel);
  const shown = stageSel ? mine.filter((f) => f.stage === stageSel) : mine;
  const ranking = [...s.products].sort((a, b) => total(b) - total(a));
  const doneSteps = EXPORT_STEPS.filter((_, i) => s.checks[i]).length;

  const TABS = [["hari", "Hari ini"], ["peta", "Peta"], ["skor", "Skor"], ["ekspor", "Ekspor"]];

  return (
    <section className="arah riset r-one" aria-label="Riset">
      <button type="button" className="r-head" aria-expanded={open} onClick={() => setOpen(!open)}>
        <span className="r-title"><Icon n="search" />Riset komoditas</span>
        <span className="r-hint">
          <span className={todays.length >= DAILY_TARGET ? "ok" : ""}>{Math.min(todays.length, DAILY_TARGET)}/{DAILY_TARGET} hari ini</span>
          {streak > 0 ? ` · ${streak} hari berturut` : ""}{s.chosen ? ` · Fokus: ${s.chosen.product}` : ""}
        </span>
        <svg className={`a-chev ${open ? "up" : ""}`} viewBox="0 0 24 24" aria-hidden="true"><polyline points="6 9 12 15 18 9" /></svg>
      </button>

      {open && (
        <div className="r-body">
          <p className="a-note">Tiga temuan per hari, lengkap dengan sumber, sampai satu produk terpilih untuk diekspor.</p>
          <div className="r-chips" role="group" aria-label="Pilih produk">
            {s.products.map((p) => (
              <button key={p} type="button" className="r-chip" aria-pressed={p === sel} onClick={() => { setSel(p); setStageSel(null); }}>{p}</button>
            ))}
            <span className="r-add">
              <input value={newP} onChange={(e) => setNewP(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addProduct()} placeholder="Tambah produk" aria-label="Tambah produk" />
              <button type="button" className="r-chip" onClick={addProduct} aria-label="Tambah">+</button>
            </span>
          </div>

          <div className="r-tabs" role="tablist">
            {TABS.map(([k, n]) => (
              <button key={k} type="button" role="tab" className="r-tab" aria-selected={tab === k} onClick={() => setTab(k)}>
                {n}{k === "peta" ? ` ${filled}/${STAGES.length}` : ""}
              </button>
            ))}
          </div>

          {tab === "hari" && (
            <div role="tabpanel">
              {feed.length > 0 && <h4 className="r-h">Kiriman hari ini</h4>}
              {feed.map((f) => (
                <div className="r-card" key={f.id}>
                  <div className="r-tag">{stageName(f.stage)} · perlu diverifikasi</div>
                  <p className="r-q">{f.text}</p>
                  <p className="a-note"><a href={f.url} target="_blank" rel="noreferrer">{f.source}</a></p>
                  <button type="button" className="a-go" disabled={s.accepted.includes(f.id)} onClick={() => accept(f)}>
                    {s.accepted.includes(f.id) ? "Sudah disimpan" : "Simpan ke temuan"}
                  </button>
                </div>
              ))}
              {NOTES[sel] && <p className="a-note r-hyp">{NOTES[sel]}</p>}
              <h4 className="r-h">Tiga pertanyaan hari ini</h4>
              {dailyQuestions(sel, day).map((q) => <QCard key={q.id + sel} q={q} onSave={add} />)}
            </div>
          )}

          {tab === "peta" && (
            <div role="tabpanel">
              <div className="r-map">
                {STAGES.map((st, i) => (
                  <button key={st.k} type="button" aria-pressed={stageSel === st.k}
                    className={`r-node ${byStage[st.k].length ? "" : "empty"}`}
                    onClick={() => setStageSel(stageSel === st.k ? null : st.k)}>
                    <small>{i + 1}</small><b>{byStage[st.k].length}</b><span>{st.n}</span><em>{st.d}</em>
                  </button>
                ))}
              </div>
              <p className="a-note">Angka merah berarti tahap itu belum punya temuan. Ketuk satu tahap untuk menyaring daftar.</p>
              {shown.length === 0 && <p className="a-note">Belum ada temuan untuk {sel}.</p>}
              {shown.map((f) => (
                <div className="r-find" key={f.id}>
                  <div className="r-tag">{stageName(f.stage)} · {f.date}</div>
                  <p>{f.text}</p>
                  <p className="a-note"><a href={f.source} target="_blank" rel="noreferrer">{f.source}</a>{" "}
                    <button type="button" className="r-del" onClick={() => del(f.id)} aria-label="Hapus temuan">Hapus</button></p>
                </div>
              ))}
            </div>
          )}

          {tab === "skor" && (
            <div role="tabpanel">
              <p className="a-note">Nilai {sel} dari 1 (lemah) sampai 5 (kuat). Isi berdasarkan temuanmu, bukan kesan.</p>
              {CRITERIA.map((c) => {
                const v = (s.scores[sel] || {})[c.k] || 0;
                return (
                  <div className="r-score" key={c.k}>
                    <div><b>{c.n}</b><div className="a-note">{c.h}</div></div>
                    <input type="range" min="0" max="5" step="1" value={v} onChange={(e) => setScore(sel, c.k, +e.target.value)} aria-label={c.n} />
                    <span className="mono">{v || "-"}</span>
                  </div>
                );
              })}
              <h4 className="r-h">Perbandingan produk</h4>
              <table className="r-table"><thead><tr><th>Produk</th><th>Skor</th><th>Temuan</th></tr></thead><tbody>
                {ranking.map((p) => (
                  <tr key={p}><td>{p}{s.chosen?.product === p ? " ✓" : ""}</td><td>{scored(p) ? `${total(p)}/${CRITERIA.length * 5}` : "belum lengkap"}</td><td>{s.findings.filter((f) => f.product === p).length}</td></tr>
                ))}
              </tbody></table>
              <h4 className="r-h">Syarat memilih {sel} sebagai fokus</h4>
              {ready.map((r) => <div key={r.t} className={`r-gate ${r.ok ? "ok" : ""}`}>{r.ok ? "✓" : "○"} {r.t}</div>)}
              <p className="a-note">Hanya satu produk yang boleh menjadi fokus. Syarat ini mencegah memilih karena rasa, bukan bukti.</p>
              {s.chosen?.product === sel ? (
                <button type="button" className="a-toggle" onClick={() => commit({ ...s, chosen: null })}>Batalkan pilihan</button>
              ) : (
                <button type="button" className="a-go" disabled={!canChoose || !!s.chosen} onClick={() => commit({ ...s, chosen: { product: sel, date: today } })}>
                  {s.chosen ? `Fokus sudah ${s.chosen.product}` : `Pilih ${sel} sebagai fokus`}
                </button>
              )}
            </div>
          )}

          {tab === "ekspor" && (
            <div role="tabpanel">
              {!s.chosen && <p className="a-note">Terkunci. Terbuka setelah satu produk dipilih sebagai fokus di tab Skor.</p>}
              {s.chosen && (
                <>
                  <p className="a-note">Kerangka umum untuk <b>{s.chosen.product}</b> ({doneSteps}/{EXPORT_STEPS.length}). Verifikasi ke Kemendag, Bea Cukai, dan eksportir berpengalaman.</p>
                  {EXPORT_STEPS.map((t, i) => (
                    <label className="r-step" key={t}>
                      <input type="checkbox" checked={!!s.checks[i]} onChange={() => commit({ ...s, checks: { ...s.checks, [i]: !s.checks[i] } })} /> <span>{t}</span>
                    </label>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
