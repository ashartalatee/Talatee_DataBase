// Panggung (/stage): layar tontonan. Hanya membaca, tanpa tombol kendali.
// Mode siaran: tambahkan ?siaran di URL atau tekan tombol B.
import { useEffect, useState } from 'react'
import { ResponsiveContainer, AreaChart, Area, XAxis, Tooltip, PieChart, Pie } from 'recharts'
import { useStageData } from './useStageData'
import './stage.css'

// Nama publik Panggung. Sengaja tidak memuat kata "Talatee" (sama seperti versi sebelumnya).
const STAGE_NAME = 'Panggung'
const ICON =
  'data:image/svg+xml,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0b0f0c"/><circle cx="16" cy="16" r="6" fill="#22ff66"/></svg>'
  )

// Warna mengikuti token tema dashboard (index.css).
const COLORS = ['#7cfc3c', '#5bb8d4', '#a77bff', '#f5b942', '#8a9484']
const TRUST = [['INGESTED', 'Baru masuk', '#5bb8d4'], ['VALIDATING', 'Divalidasi', '#f5b942'], ['NEEDS_REVIEW', 'Perlu ditinjau', '#ff5c5c'], ['TRUSTED', 'Terpercaya', '#7cfc3c']]
const rp = (v) => (v >= 1e6 ? `Rp ${(v / 1e6).toFixed(2).replace('.', ',')} jt` : `Rp ${Math.round(v / 1000)} rb`)
const fmt = (n) => new Intl.NumberFormat('id-ID').format(n)

function ago(t, now) {
  if (!t) return 'belum ada'
  const s = Math.max(0, ((now - t) / 1000) | 0)
  return s < 5 ? 'baru saja' : s < 60 ? `${s} dtk lalu` : s < 3600 ? `${(s / 60) | 0} mnt lalu` : `${(s / 3600) | 0} jam lalu`
}

function useNow(ms = 1000) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), ms); return () => clearInterval(id) }, [ms])
  return now
}

function useSiaran() {
  const [on, setOn] = useState(() => new URLSearchParams(window.location.search).has('siaran'))
  useEffect(() => {
    const h = (e) => {
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return
      if (e.key === 'b' || e.key === 'B') setOn((v) => !v)
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [])
  return on
}

function Panel({ title, note, children, className = '' }) {
  return (
    <section className={`st-panel ${className}`}>
      <h2>{title}{note && <span className="st-note">{note}</span>}</h2>
      {children}
    </section>
  )
}

export default function Stage() {
  const { data, error, mode, paused, togglePause } = useStageData()
  const now = useNow()
  const siaran = useSiaran()

  // Tekan P untuk menjeda/melanjutkan simulasi (hanya berlaku di mode mock).
  useEffect(() => {
    const h = (e) => {
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return
      if (e.key === 'p' || e.key === 'P') togglePause()
    }
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  })

  // Judul tab dan ikon diganti selama halaman ini terbuka, lalu dikembalikan.
  // index.html masih bertuliskan "Talatee" sampai React jalan, jadi untuk siaran
  // langsung buka halaman ini sebelum mulai berbagi layar.
  useEffect(() => {
    const prevTitle = document.title
    document.title = STAGE_NAME
    let link = document.querySelector("link[rel~='icon']")
    const created = !link
    if (!link) { link = document.createElement('link'); link.rel = 'icon'; document.head.appendChild(link) }
    const prevHref = link.getAttribute('href')
    link.setAttribute('href', ICON)
    return () => {
      document.title = prevTitle
      if (created) link.remove()
      else if (prevHref) link.setAttribute('href', prevHref)
    }
  }, [])

  if (!data) {
    return <main className="stage"><p className="st-empty">{error || 'Menyambungkan ke data demo…'}</p></main>
  }

  const { flow, trend, categories, channels, low_stock: stok, hermes, feed } = data
  const omzet = trend.reduce((n, x) => n + x.rev, 0)
  const order = trend.reduce((n, x) => n + x.ord, 0)
  const trustTotal = TRUST.reduce((n, t) => n + (flow.trust[t[0]] || 0), 0)
  const trusted = flow.trust.TRUSTED || 0
  const catTotal = categories.reduce((n, c) => n + c.value, 0) || 1
  const chanMax = Math.max(1, ...channels.map((c) => c.value))

  const hermesOn = data.hermes_connected !== false
  const steps = [
    ['File masuk', 'Upload atau bridge', flow.file.count, flow.file.last],
    ['Batch tercatat', 'Postgres + penyimpanan mentah', flow.batch.count, flow.batch.last],
    ['Status kepercayaan', 'Dari baru masuk ke terpercaya', `${trusted}/${trustTotal}`, flow.trust.last],
    ['Hermes bertanya', 'Lewat MCP, hanya baca', hermesOn ? flow.question.count : '–', hermesOn ? flow.question.last : null],
    ['Jawaban + sumbernya', 'Dataset dan batch yang dipakai', hermesOn ? flow.answer.count : '–', hermesOn ? flow.answer.last : null],
  ]
  const kpis = [
    ['Omzet 30 hari', rp(omzet), 'dari batch terpercaya'],
    ['Order', fmt(order), '30 hari terakhir'],
    ['Rata-rata per order', rp(omzet / Math.max(1, order)), 'omzet ÷ order'],
    ['Batch terpercaya', trustTotal ? `${Math.round((trusted / trustTotal) * 100)}%` : '–', `${trusted} dari ${trustTotal} batch`],
  ]

  return (
    <main className={`stage${siaran ? ' siaran' : ''}`}>
      <header className="st-head">
        <div>
          <h1>{STAGE_NAME}</h1>
          <p className="st-sub">Penjualan, stok, dan marketing dari semua channel dalam satu layar. Setiap angka bisa dilacak ke batch dan dataset asalnya.</p>
        </div>
        <div className="st-tags">
          <span className={`st-tag ${error ? 'bad' : 'live'}`}><i className="st-dot" />{error ? 'Terputus' : 'Live'}</span>
          <span className="st-tag">Data demo</span>
          {mode === 'mock' && <span className="st-tag">{paused ? 'Simulasi dijeda' : 'Simulasi lokal'}</span>}
        </div>
      </header>
      {error && <p className="st-err" role="alert">{error}</p>}

      <section className="st-flow" aria-label="Alur data">
        {steps.map(([t, s, n, last]) => (
          <div key={t} className={`st-step${last && now - last < 2500 ? ' pulse' : ''}`}>
            <b>{t}</b><small>{s}</small>
            <div className="st-n">{n}</div>
            <small>{!hermesOn && (t === 'Hermes bertanya' || t === 'Jawaban + sumbernya') ? 'Belum tersambung' : ago(last, now)}</small>
          </div>
        ))}
      </section>

      <section className="st-kpis">
        {kpis.map(([l, v, d]) => (
          <div key={l} className="st-panel st-kpi"><small>{l}</small><div className="st-v">{v}</div><div className="st-d">{d}</div></div>
        ))}
      </section>

      <div className="st-main">
        <div className="st-col">
          <Panel title="Tren penjualan" note="30 hari">
            <div className="st-chart">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trend} margin={{ top: 6, right: 6, left: 6, bottom: 0 }}>
                  <defs><linearGradient id="stg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#7cfc3c" stopOpacity={0.35} /><stop offset="100%" stopColor="#7cfc3c" stopOpacity={0} /></linearGradient></defs>
                  <XAxis dataKey="d" tick={{ fill: '#8a9484', fontSize: 11 }} axisLine={false} tickLine={false} interval={4} />
                  <Tooltip formatter={(v) => rp(v)} labelFormatter={(l) => `Hari ke-${l}`} contentStyle={{ background: '#12160f', border: '1px solid #232b20', borderRadius: 8, color: '#e8ede5' }} />
                  <Area type="monotone" dataKey="rev" name="Omzet" stroke="#7cfc3c" strokeWidth={2} fill="url(#stg)" isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Panel>

          <div className="st-two">
            <Panel title="Penjualan per kategori" note="30 hari">
              {categories.length === 0 && <p className="st-empty">Belum ada penjualan dari dataset terpercaya.</p>}
              {categories.length > 0 && <div className="st-donut">
                <div className="st-pie">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart><Pie data={categories.map((c, i) => ({ ...c, fill: COLORS[i % COLORS.length] }))} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="92%" stroke="none" isAnimationActive={false}>
                    </Pie></PieChart>
                  </ResponsiveContainer>
                </div>
                <ul className="st-leg">
                  {categories.map((c, i) => (
                    <li key={c.name}><i style={{ background: COLORS[i % COLORS.length] }} />{c.name}<b>{Math.round((c.value / catTotal) * 100)}%</b></li>
                  ))}
                </ul>
              </div>}
            </Panel>
            <Panel title="Dari baru masuk ke terpercaya">
              <div className="st-bar">
                {TRUST.map(([k, , c]) => <i key={k} style={{ width: `${trustTotal ? ((flow.trust[k] || 0) / trustTotal) * 100 : 0}%`, background: c }} />)}
              </div>
              <ul className="st-leg">
                {TRUST.map(([k, l, c]) => <li key={k}><i style={{ background: c }} />{l}<b>{flow.trust[k] || 0}</b></li>)}
              </ul>
            </Panel>
          </div>

          <div className="st-two">
            <Panel title="Omzet per channel" note="30 hari">
              {channels.length === 0 && <p className="st-empty">Belum ada data channel.</p>}
              {channels.map((c, i) => (
                <div key={c.name} className="st-rb">
                  <span>{c.name}</span>
                  <div className="st-rt"><i style={{ width: `${(c.value / chanMax) * 100}%`, background: COLORS[i % COLORS.length] }} /></div>
                  <b>{rp(c.value)}</b>
                </div>
              ))}
            </Panel>
            <Panel title="Stok menipis">
              {stok.length === 0 && <p className="st-empty">Belum ada data stok.</p>}
              {stok.map((s) => (
                <div key={s.name} className="st-stat"><span>{s.name}</span><b className={s.stok < 30 ? 'bad' : 'warn'}>{s.stok} unit</b></div>
              ))}
            </Panel>
          </div>
        </div>

        <div className="st-col">
          <Panel title="Hermes menjawab" note="hanya membaca">
            <div className="st-hermes">
              {hermes.length === 0 && <p className="st-empty">{hermesOn ? 'Menunggu pertanyaan masuk.' : 'Log Hermes belum tersambung.'}</p>}
              {hermes.map((m, i) => (
                <div key={`${m.q}-${i}`} className="st-qa">
                  <div className="st-q">{m.q}</div>
                  <div className="st-a">{m.a}</div>
                  <div>{(m.sources || []).map((s) => <span key={s} className="st-chip">{s}</span>)}</div>
                </div>
              ))}
            </div>
          </Panel>
          <Panel title="Aktivitas terbaru" className="st-feedp">
            <ul className="st-feed">
              {feed.map((f, i) => (
                <li key={`${f.t}-${i}`}><time>{ago(f.t, now)}</time><span className={f.tone}>{f.text}</span></li>
              ))}
            </ul>
          </Panel>
        </div>
      </div>

      <p className="st-foot">
        Seluruh isi halaman ini adalah data demo. {mode === 'mock'
          ? 'Angka di halaman ini dibangkitkan di browser untuk menyiapkan tampilan.'
          : 'Angka di halaman ini berasal dari data demo di database, bukan data bisnis nyata.'}
      </p>
    </main>
  )
}
