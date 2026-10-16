// Panggung (/stage): layar tontonan dengan dua halaman dan satu agen.
//   Halaman 1 "Gudang Data": data masuk apa adanya (mentah).   Halaman 2 "Data Bersih & Insight": hasil kerja agen.
//   Rel "Agen Hermes" selalu terlihat: bekerja sendiri begitu data masuk (baca, bersihkan, validasi, percaya, insight).
// Pintasan: 1/2 atau panah = halaman, F = agen memandu halaman, B = mode siaran, V = orientasi siaran,
//           C = laci kendali, P = jeda simulasi (mock), Esc = tutup laci.
// Mode siaran menggambar kanvas tetap (16:9 = 1920x1080, 9:16 = 1080x1920) yang diskalakan pas ke jendela.
// URL: ?siaran ?potret ?lanskap ?otomatis ?mock ?ikuti
import { useEffect, useRef, useState } from 'react'
import { Upload, Database, ShieldCheck, MessageSquare, FileText, Sparkles } from 'lucide-react'
import { useStageData } from './useStageData'
import StageControls from './StageControls'
import StageIntake from './StageIntake'
import { useBatchDetail, mergeDetail } from './useBatchDetail'
import StageAgent from './StageAgent'
import PipeCanvas from './PipeCanvas'
import StageGudang from './StageGudang'
import StageBersih from './StageBersih'
import { flag, sum, ago } from './stageUi'
import './stage.css'

// Nama publik Panggung. Sengaja tidak memuat kata "Talatee" (sama seperti versi sebelumnya).
const STAGE_NAME = 'Panggung'
const ICON =
  'data:image/svg+xml,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0b0f0c"/><circle cx="16" cy="16" r="6" fill="#22ff66"/></svg>'
  )

const TRUST = [['INGESTED', 'Baru masuk', '#5bb8d4'], ['VALIDATING', 'Divalidasi', '#f5b942'], ['NEEDS_REVIEW', 'Perlu ditinjau', '#ff5c5c'], ['TRUSTED', 'Terpercaya', '#7cfc3c']]
const NODES = [
  { key: 'file', title: 'File masuk', sub: 'Upload atau bridge', Icon: Upload },
  { key: 'batch', title: 'Batch tercatat', sub: 'Postgres + penyimpanan mentah', Icon: Database },
  { key: 'trust', title: 'Status kepercayaan', sub: 'Dari baru masuk ke terpercaya', Icon: ShieldCheck },
  { key: 'question', title: 'Hermes bertanya', sub: 'Lewat MCP, hanya baca', Icon: MessageSquare },
  { key: 'answer', title: 'Jawaban + sumbernya', sub: 'Dataset dan batch yang dipakai', Icon: FileText },
]

function useNow(ms = 1000) {
  const [now, setNow] = useState(Date.now())
  useEffect(() => { const id = setInterval(() => setNow(Date.now()), ms); return () => clearInterval(id) }, [ms])
  return now
}

// Mendeteksi nilai yang berubah (cap waktu "last" dari data) untuk memicu kilatan node dan paket data.
function useTicks(vals) {
  const prev = useRef(null)
  const [ticks, setTicks] = useState(() => vals.map(() => 0))
  const sig = JSON.stringify(vals.map((v) => (v === undefined ? 'u' : v)))
  useEffect(() => {
    const p = prev.current
    if (p && p.some((v) => v !== undefined)) {
      setTicks((t) => t.map((n, i) => (vals[i] !== p[i] ? n + 1 : n)))
    }
    prev.current = vals
  }, [sig]) // eslint-disable-line react-hooks/exhaustive-deps
  return ticks
}

// Ukuran kanvas siaran dan skala supaya pas di jendela (letterbox bila rasionya beda).
function useCanvas(enabled, orient) {
  const [vp, setVp] = useState(() => ({ w: window.innerWidth, h: window.innerHeight }))
  useEffect(() => {
    if (!enabled) return undefined
    const on = () => setVp({ w: window.innerWidth, h: window.innerHeight })
    on()
    window.addEventListener('resize', on)
    return () => window.removeEventListener('resize', on)
  }, [enabled])
  const portrait = orient === 'potret' || (orient === 'auto' && vp.h > vp.w)
  const W = portrait ? 1080 : 1920
  const H = portrait ? 1920 : 1080
  const s = Math.min(vp.w / W, vp.h / H)
  return { portrait, W, H, s, left: (vp.w - W * s) / 2, top: (vp.h - H * s) / 2 }
}

export default function Stage() {
  const { data, error, mode, paused, togglePause, actions, caps } = useStageData()
  const now = useNow()
  const [siaran, setSiaran] = useState(() => flag('siaran') || flag('potret') || flag('lanskap'))
  const [orient, setOrient] = useState(() => (flag('potret') ? 'potret' : flag('lanskap') ? 'lanskap' : 'auto'))
  const [open, setOpen] = useState(false)
  const [range, setRange] = useState(30)
  const [page, setPage] = useState('gudang')
  const [sel, setSel] = useState(null)
  const [intake, setIntake] = useState(false)
  const [follow, setFollow] = useState(() => flag('siaran') || flag('potret') || flag('lanskap') || flag('ikuti'))
  const cv = useCanvas(siaran, orient)
  const canControl = Object.values(caps).some(Boolean)
  const hasPages = !!(data && data.batches)

  const agentStep = data && data.agent && data.agent.status === 'working' ? data.agent.step : null
  const agentBatch = data && data.agent ? data.agent.batchId : null
  const selBase = data && data.batches ? (data.batches.find((b) => b.id === sel) || data.batches[0] || null) : null
  const detail = useBatchDetail(mode === 'api' && selBase ? selBase.id : null)
  const fl = data && data.flow
  const ticks = useTicks([fl ? fl.file.last : undefined, fl ? fl.batch.last : undefined, fl ? fl.trust.last : undefined, fl ? fl.question.last : undefined, fl ? fl.answer.last : undefined])
  const working = { batch: agentStep === 'read' || agentStep === 'clean', trust: agentStep === 'validate' || agentStep === 'trust' }

  // Agen memandu halaman: baca/bersihkan -> Gudang Data; validasi/percaya/insight -> Data Bersih.
  useEffect(() => {
    if (!follow || !agentStep) return
    setSel(agentBatch)
    setPage(hasPages && (agentStep === 'read' || agentStep === 'clean') ? 'gudang' : 'bersih')
  }, [follow, agentStep, agentBatch, hasPages])

  // Bila backend belum menyediakan data gudang (mode API saat ini), mulai dari halaman Data Bersih.
  useEffect(() => { if (data && !data.batches) setPage('bersih') }, [!!data, hasPages]) // eslint-disable-line react-hooks/exhaustive-deps

  const go = (p) => { setFollow(false); setPage(p) }

  // Pintasan keyboard (tidak aktif saat mengetik di kolom isian).
  useEffect(() => {
    const h = (e) => {
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return
      const k = e.key.toLowerCase()
      if (k === 'b') setSiaran((v) => !v)
      else if (k === 'v') setOrient((o) => (o === 'potret' ? 'lanskap' : 'potret'))
      else if (k === 'p') togglePause()
      else if (k === 'f') setFollow((v) => !v)
      else if (k === '1' || e.key === 'ArrowLeft') go('gudang')
      else if (k === '2' || e.key === 'ArrowRight') go('bersih')
      else if (k === 'c' && canControl) { setOpen((v) => !v); setIntake(false) }
      else if (k === 'u' && caps.upload) { setIntake((v) => !v); setOpen(false) }
      else if (e.key === 'Escape') { setOpen(false); setIntake(false) }
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

  const { flow, trend, categories, channels } = data
  const batches = data.batches || []
  const waiting = flow.trust.VALIDATING || 0
  const insights = data.insights || []
  const agent = data.agent || { status: 'idle', step: null, label: '', lastDone: false }
  // Tanpa data agen dari backend, garis waktu diisi dari aktivitas (feed) supaya tetap hidup.
  const events = data.events || (data.feed || []).map((f) => ({ t: f.t, kind: 'info', text: f.text, tone: f.tone }))
  const selected = mergeDetail(batches.find((b) => b.id === sel) || batches[0] || null, detail)

  const omzet = sum(trend, 'rev')
  const order = sum(trend, 'ord')
  const last7 = sum(trend.slice(-7), 'rev')
  // Pembanding memakai hari-hari PENUH (tanpa hari ini yang baru sebagian), supaya tidak terbaca "turun" hanya karena hari ini belum selesai.
  const fullLast7 = sum(trend.slice(-8, -1), 'rev')
  const fullPrev7 = sum(trend.slice(-15, -8), 'rev')
  const delta = fullPrev7 > 0 ? (fullLast7 - fullPrev7) / fullPrev7 : null
  const today = trend[trend.length - 1] || { ord: 0 }
  const trustTotal = TRUST.reduce((n, t) => n + (flow.trust[t[0]] || 0), 0)
  const trusted = flow.trust.TRUSTED || 0
  const hermesOn = data.hermes_connected !== false
  const metrics = {
    omzet, order, last7, today: today.ord, trusted, trustTotal,
    deltaTxt: delta === null ? 'belum ada pembanding' : `${delta < 0 ? '▼' : '▲'} ${Math.abs(delta * 100).toFixed(1).replace('.', ',')}% vs minggu lalu`,
    deltaTone: delta === null ? '' : delta < 0 ? 'down' : 'up',
  }
  const nodeVal = {
    file: [flow.file.count, flow.file.last],
    batch: [flow.batch.count, flow.batch.last],
    trust: [`${trusted}/${trustTotal}`, flow.trust.last],
    question: [hermesOn ? flow.question.count : '–', hermesOn ? flow.question.last : null],
    answer: [hermesOn ? flow.answer.count : '–', hermesOn ? flow.answer.last : null],
  }
  const canvasClass = siaran ? (cv.portrait ? 'cv-port' : 'cv-land') : 'cv-flow'
  const canvasStyle = siaran ? { width: cv.W, height: cv.H, transform: `scale(${cv.s})`, left: cv.left, top: cv.top } : undefined
  const compact = siaran && cv.portrait
  const select = (id) => { setFollow(false); setSel(id) }
  const goClean = (id) => { setFollow(false); setSel(id); setPage('bersih') }
  const goRaw = (id) => { setFollow(false); setSel(id); setPage('gudang') }
  const pick = (e) => { if (e.batchId) { setFollow(false); setSel(e.batchId); setPage(e.kind === 'file' || e.kind === 'read' || e.kind === 'clean' ? 'gudang' : 'bersih') } }

  return (
    <main className={`stage${siaran ? ' siaran' : ''}`}>
      <div className={`st-canvas ${canvasClass}`} style={canvasStyle}>
        <header className="st-head">
          <div className="st-headl">
            <h1>{STAGE_NAME}</h1>
            <nav className="st-tabs" role="tablist" aria-label="Halaman Panggung">
              <button type="button" role="tab" aria-selected={page === 'gudang'} className={page === 'gudang' ? 'on' : ''} onClick={() => go('gudang')}>
                <Database size={17} strokeWidth={1.9} />Gudang Data{hasPages && <em>{flow.batch.count}</em>}
              </button>
              <button type="button" role="tab" aria-selected={page === 'bersih'} className={page === 'bersih' ? 'on' : ''} onClick={() => go('bersih')}>
                <Sparkles size={17} strokeWidth={1.9} />Data Bersih &amp; Insight{insights.length > 0 && <em>{insights.length}</em>}
              </button>
            </nav>
          </div>
          <div className="st-tags">
            {caps.upload && !siaran && (
              <button type="button" className="st-tag st-add" onClick={() => { setIntake(true); setOpen(false) }}>
                Tambah data{waiting > 0 && <em>{waiting}</em>}
              </button>
            )}
            {follow && <span className="st-tag follow"><i className="st-dot" />Agen memandu</span>}
            <span className={`st-tag ${error ? 'bad' : 'live'}`}><i className="st-dot" />{error ? 'Terputus' : 'Live'}</span>
            <span className="st-tag">Data demo</span>
            {mode === 'mock' && <span className="st-tag">{paused ? 'Simulasi lokal' : 'Simulasi lokal, otomatis'}</span>}
          </div>
        </header>
        {error && <p className="st-err" role="alert">{error}</p>}

        <PipeCanvas val={nodeVal} ticks={ticks} working={working} now={now} hermesOn={hermesOn} ago={ago} trustParts={TRUST.map(([k, , c]) => ({ c, n: flow.trust[k] || 0 }))} />
        <section className="st-pipe old" aria-label="Alur data">
          {NODES.map(({ key, title, sub, Icon }, idx) => {
            const [val, last] = nodeVal[key]
            const off = !hermesOn && (key === 'question' || key === 'answer')
            return (
              <div key={key} className={`st-node${last && now - last < 2500 ? ' pulse' : ''}${working[key] ? ' work' : ''}`}>
                <span className="st-ic"><Icon size={20} strokeWidth={1.75} /></span>
                {ticks[idx] > 0 && <span key={ticks[idx]} className="st-flash" aria-hidden="true" />}
                {idx < NODES.length - 1 && <i className="st-edge" aria-hidden="true">{ticks[idx + 1] > 0 && <b key={ticks[idx + 1]} className="st-packet" />}</i>}
                <b className="st-nt">{title}</b>
                <div className="st-n">{val}</div>
                <small className="st-nsub">{sub}</small>
                <small className="st-nago">{off ? 'Belum tersambung' : ago(last, now)}</small>
                {key === 'trust' && (
                  <div className="st-mini">
                    <div className="st-bar">
                      {TRUST.map(([k, , c]) => <i key={k} style={{ width: `${trustTotal ? ((flow.trust[k] || 0) / trustTotal) * 100 : 0}%`, background: c }} />)}
                    </div>
                    <div className="st-minileg">
                      {TRUST.map(([k, l, c], i) => <span key={k} title={l}><i style={{ background: c }} />{flow.trust[k] || 0}<em>{['baru', 'valid', 'tinjau', 'terpercaya'][i]}</em></span>)}
                    </div>
                  </div>
                )}
              </div>
            )
          })}
        </section>

        <div className="st-body">
          <div className="st-pagewrap" key={page}>
            {page === 'gudang' ? (
              <StageGudang batches={batches} selected={selected} selectedId={selected && selected.id} onSelect={select} onGoClean={goClean} now={now} compact={compact} />
            ) : (
              <StageBersih
                metrics={metrics} trendView={trend.slice(-range)} range={range} setRange={setRange} insights={insights}
                categories={categories} channels={channels} batches={batches} selected={selected} onSelect={goClean} onGoRaw={goRaw} compact={compact}
              />
            )}
          </div>
          <aside className="st-rail">
            <StageAgent agent={agent} events={events} now={now} onPick={pick} limit={compact ? 3 : 7} hermesOn={hermesOn} />
          </aside>
        </div>

        <p className="st-foot">
          Seluruh isi halaman ini adalah data demo. {mode === 'mock'
            ? 'Angka di halaman ini dibangkitkan di browser untuk menyiapkan tampilan.'
            : 'Angka di halaman ini berasal dari data demo di database, bukan data bisnis nyata.'}
        </p>
      </div>

      <StageIntake open={intake} onClose={() => setIntake(false)} batches={batches} waitingTotal={waiting} apiInfo={data.api} actions={actions} caps={caps} siaran={siaran} now={now} />
      {canControl && (
        <StageControls
          open={open} onOpen={() => setOpen(true)} onClose={() => setOpen(false)}
          caps={caps} actions={actions} mode={mode}
          auto={!paused} onAuto={togglePause}
          siaran={siaran} onSiaran={() => setSiaran((v) => !v)}
          orient={orient} onOrient={setOrient}
          follow={follow} onFollow={() => setFollow((v) => !v)}
        />
      )}
    </main>
  )
}
