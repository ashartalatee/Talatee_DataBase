"""Tahap B: laci "Tambah data" (unggah manual, antrean persetujuan, status API) + data mentah terisi dari database.
Jalankan dari folder talatee-database:  python patch_tahap_b_v1.py
Semua potongan dicek dulu; bila ada yang tidak cocok persis, tidak ada file yang diubah."""
import os
import sys

P = "dashboard/src/pages/"
STAGE = P + "Stage.jsx"
CSS = P + "stage.css"
USE = P + "useStageData.js"
CLIENT = "dashboard/src/api/client.js"
SHOW = "app/api/routes/showcase_control.py"
NEW_INTAKE = P + "StageIntake.jsx"
NEW_DETAIL = P + "useBatchDetail.js"

INTAKE_SRC = r'''// Laci "Tambah data" Panggung: unggah manual (seret atau pilih file), antrean persetujuan, dan status koneksi API.
// Semua unggahan masuk ke bisnis demo (actions.upload). Data baru menunggu "Tandai terpercaya" kecuali dicentang otomatis.
// Saat mode siaran, awalan kunci API disembunyikan. Seret-file ke layar bekerja di mana saja, juga saat siaran.
import { useEffect, useRef, useState } from 'react'
import { ago } from './stageUi'

const MAX_BYTES = 5 * 1024 * 1024
const friendly = (e) => {
  const m = /^4\d\d: (.{1,160})$/.exec((e && e.message) || '')
  return m ? m[1] : 'Gagal. Detailnya ada di konsol.'
}
const hasFiles = (e) => !!(e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files'))

export default function StageIntake({ open, onClose, batches, apiInfo, actions, caps, siaran, now }) {
  const [log, setLog] = useState([])
  const [busy, setBusy] = useState(false)
  const [auto, setAuto] = useState(false)
  const [veil, setVeil] = useState(false)
  const [pmsg, setPmsg] = useState('')
  const [pbusy, setPbusy] = useState(null)
  const fileRef = useRef(null)
  const busyRef = useRef(false)
  const autoRef = useRef(false)
  const uploadRef = useRef(null)
  autoRef.current = auto

  const upload = async (files) => {
    const list = Array.from(files || [])
    if (!list.length || busyRef.current || !caps.upload) return
    busyRef.current = true
    setBusy(true)
    setLog([])
    const out = []
    for (const f of list) {
      let line
      if (!/\.(csv|xlsx)$/i.test(f.name)) line = `${f.name}: hanya file .csv atau .xlsx`
      else if (f.size > MAX_BYTES) line = `${f.name}: terlalu besar (maksimal 5 MB)`
      else {
        try {
          const m = await actions.upload(f, { promote: autoRef.current })
          line = typeof m === 'string' && m ? m : `${f.name}: terkirim`
        } catch (e) {
          console.warn('[panggung]', e)
          line = `${f.name}: ${friendly(e)}`
        }
      }
      out.push(line)
      setLog([...out])
    }
    busyRef.current = false
    setBusy(false)
  }
  uploadRef.current = upload

  // Seret file ke mana saja di layar: lapisan "Lepas file di sini", lalu unggah.
  useEffect(() => {
    if (!caps.upload) return undefined
    let depth = 0
    const over = (e) => { if (hasFiles(e)) e.preventDefault() }
    const enter = (e) => { if (!hasFiles(e)) return; e.preventDefault(); depth += 1; setVeil(true) }
    const leave = (e) => { if (!hasFiles(e)) return; depth = Math.max(0, depth - 1); if (depth === 0) setVeil(false) }
    const drop = (e) => {
      if (!hasFiles(e)) return
      e.preventDefault()
      depth = 0
      setVeil(false)
      uploadRef.current(e.dataTransfer.files)
    }
    window.addEventListener('dragover', over)
    window.addEventListener('dragenter', enter)
    window.addEventListener('dragleave', leave)
    window.addEventListener('drop', drop)
    return () => {
      window.removeEventListener('dragover', over)
      window.removeEventListener('dragenter', enter)
      window.removeEventListener('dragleave', leave)
      window.removeEventListener('drop', drop)
    }
  }, [caps.upload])

  // Hasil unggahan tampil sebagai notifikasi singkat bila laci tertutup.
  useEffect(() => {
    if (open || busy || !log.length) return undefined
    const t = setTimeout(() => setLog([]), 7000)
    return () => clearTimeout(t)
  }, [open, busy, log])

  const promote = async (id) => {
    setPbusy(id)
    setPmsg('')
    try {
      await actions.promote(id)
      setPmsg('Ditandai terpercaya.')
    } catch (e) {
      console.warn('[panggung]', e)
      setPmsg(friendly(e))
    } finally {
      setPbusy(null)
    }
  }

  const waiting = batches.filter((b) => b.trust === 'VALIDATING')
  const held = batches.filter((b) => b.trust === 'NEEDS_REVIEW')

  return (
    <>
      {veil && (
        <div className="st-veil" role="status">
          <div><b>Lepas file di sini</b><span>CSV atau XLSX, masuk ke data demo</span></div>
        </div>
      )}
      {!open && log.length > 0 && (
        <div className="st-toast" role="status">{log.map((l, i) => <span key={i}>{l}</span>)}</div>
      )}
      {open && (
        <aside className="st-drawer st-intake" role="dialog" aria-label="Tambah data">
          <div className="st-dh">
            <b>Tambah data</b>
            <button type="button" className="st-x" onClick={onClose} aria-label="Tutup">&times;</button>
          </div>
          <p className="st-dsub">Semua masuk ke data demo. Data klien sungguhan tidak tersentuh.</p>

          <h3>Unggah manual</h3>
          {caps.upload ? (
            <>
              <input
                ref={fileRef} type="file" multiple accept=".csv,.xlsx" hidden aria-label="Pilih file CSV atau XLSX"
                onChange={(e) => { upload(e.target.files); e.target.value = '' }}
              />
              <button type="button" className="st-dz" disabled={busy} onClick={() => fileRef.current && fileRef.current.click()}>
                <b>{busy ? 'Mengunggah...' : 'Seret file ke mana saja di layar ini'}</b>
                <span>atau klik untuk memilih dari laptop atau HP (.csv, .xlsx, maks. 5 MB)</span>
              </button>
              <label className="st-chk st-sub">
                <input type="checkbox" checked={auto} onChange={(e) => setAuto(e.target.checked)} /> Langsung dianggap terpercaya (lewati persetujuan)
              </label>
              <ul className="st-ulog" aria-live="polite">{log.map((l, i) => <li key={i}>{l}</li>)}</ul>
            </>
          ) : (
            <p className="st-dsub">Unggah belum tersedia di backend ini.</p>
          )}

          <h3>Menunggu persetujuan{waiting.length > 0 ? ` (${waiting.length})` : ''}</h3>
          {waiting.length === 0 ? (
            <p className="st-dsub">Tidak ada file yang menunggu.</p>
          ) : (
            <ul className="st-wl">
              {waiting.map((b) => (
                <li key={b.id}>
                  <span className="st-wn"><b>{b.file}</b><small>{b.channel} &middot; {b.rows} baris &middot; {ago(b.t, now)}</small></span>
                  {caps.promote && (
                    <button type="button" className="st-btn primary sm" disabled={pbusy === b.id} onClick={() => promote(b.id)}>Tandai terpercaya</button>
                  )}
                </li>
              ))}
            </ul>
          )}
          {held.length > 0 && <p className="st-dsub">{held.length} file ditahan karena perlu ditinjau, tidak dihitung ke omzet.</p>}
          {pmsg && <p className="st-msg" aria-live="polite">{pmsg}</p>}

          <h3>Sambungkan API</h3>
          <p className="st-dsub">Sistem lain (n8n, skrip, toko online) mengirim data ke Panggung memakai kunci API bisnis demo.</p>
          {apiInfo && apiInfo.configured ? (
            <div className="st-card">
              <div className="st-row"><span>Status</span><b>{apiInfo.last_used ? `Terakhir menerima ${ago(apiInfo.last_used, now)}` : 'Menunggu data pertama'}</b></div>
              <div className="st-row"><span>Kunci</span><b className="st-mono">{siaran ? 'Disembunyikan saat siaran' : `${apiInfo.key_prefix}...`}</b></div>
            </div>
          ) : (
            <p className="st-dsub">Belum ada kunci API untuk bisnis demo.</p>
          )}
          <p className="st-hint">Kunci lengkap tidak pernah ditampilkan di layar ini. Membuat kunci baru: scripts/create_api_key.py.</p>
          <p className="st-hint">Tombol U membuka atau menutup laci ini. Esc menutup.</p>
        </aside>
      )}
    </>
  )
}
'''

DETAIL_SRC = r'''// Isi mentah + laporan masalah satu batch DEMO (hanya mode API), diambil dari GET /stage/batches/{id}.
// Isi batch tidak berubah setelah masuk, jadi hasilnya disimpan per id.
import { useEffect, useState } from 'react'
import { api } from '../api/client'

const cache = new Map()

export function useBatchDetail(id) {
  const [, bump] = useState(0)
  useEffect(() => {
    if (!id || cache.has(id) || !api.getStageBatch) return undefined
    let alive = true
    api.getStageBatch(id)
      .then((d) => { cache.set(id, d); if (alive) bump((n) => n + 1) })
      .catch((e) => { console.warn('[panggung]', e) })
    return () => { alive = false }
  }, [id])
  return id ? cache.get(id) || null : null
}

// Menggabungkan detail ke batch dari ringkasan, dalam bentuk yang dipahami tabel Data mentah.
export function mergeDetail(batch, d) {
  if (!batch || !d || !d.raw || !d.raw.columns) return batch
  const cols = d.raw.columns
  const issues = (d.issues && d.issues.issues) || []
  const flags = {}
  const dupRows = new Set()
  let fmt = 0
  let empty = 0
  for (const it of issues) {
    const r = it.row - 1
    flags[r] = flags[r] || {}
    if (it.type === 'duplikat') { dupRows.add(r); flags[r]._row = 'dup'; continue }
    const kind = String(it.value || '').trim() === '' ? 'empty' : 'format'
    if (it.column) flags[r][it.column] = kind
    if (kind === 'empty') empty += 1
    else fmt += 1
  }
  const raw = d.raw.rows.map((vals, i) => ({
    c: Object.fromEntries(cols.map((c, j) => [c, vals[j] ?? ''])),
    flags: flags[i] || {},
  }))
  const total = d.raw.total_rows ?? batch.rows
  return { ...batch, cols, raw, rows: total, stats: { kept: Math.max(0, total - dupRows.size), dup: dupRows.size, empty, fmt } }
}
'''

CSS_ADD = r'''
/* ---- laci Tambah data: unggah manual, antrean persetujuan, status API ---- */
.stage button.st-add{display:inline-flex;align-items:center;gap:7px;cursor:pointer;font:inherit;color:var(--g);background:transparent;border:1px solid color-mix(in srgb,var(--g) 45%,var(--line));border-radius:99px;padding:3px 12px}
.stage button.st-add:hover{background:color-mix(in srgb,var(--g) 12%,transparent)}
.stage .st-add em{font-style:normal;font-size:.8em;font-weight:700;color:#1a1300;background:#f5b942;border-radius:99px;padding:0 7px}
.stage .st-dz{display:grid;gap:4px;width:100%;text-align:center;cursor:pointer;color:var(--tx);font:inherit;background:radial-gradient(260px 80px at 50% 0,color-mix(in srgb,var(--g) 12%,transparent),transparent 70%),var(--bg);border:1.5px dashed color-mix(in srgb,var(--g) 45%,var(--line));border-radius:var(--rad);padding:20px 14px;transition:border-color .2s}
.stage .st-dz:hover:not(:disabled){border-color:var(--g)}
.stage .st-dz:disabled{opacity:.6;cursor:progress}
.stage .st-dz span{color:var(--mut);font-size:.85em}
.stage .st-ulog{list-style:none;margin:8px 0 0;padding:0;font-size:.85em;display:grid;gap:4px;color:var(--mut)}
.stage .st-wl{list-style:none;margin:0;padding:0;display:grid;gap:8px}
.stage .st-wl li{display:flex;justify-content:space-between;align-items:center;gap:10px;border:1px solid var(--line);border-radius:10px;padding:8px 10px;background:var(--bg)}
.stage .st-wn{display:grid;min-width:0}
.stage .st-wn b{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.stage .st-wn small{color:var(--mut)}
.stage .st-card{border:1px solid var(--line);border-radius:10px;padding:8px 10px;background:var(--bg);display:grid;gap:4px}
.stage .st-row{display:flex;justify-content:space-between;gap:10px;font-size:.88em}
.stage .st-row span{color:var(--mut)}
.stage .st-mono{font-family:var(--font-display,ui-monospace,monospace)}
.stage .st-veil{position:fixed;inset:0;z-index:90;display:grid;place-items:center;background:color-mix(in srgb,var(--bg) 82%,transparent);backdrop-filter:blur(3px);border:3px dashed var(--g);margin:14px;border-radius:20px;pointer-events:none}
.stage .st-veil div{display:grid;gap:6px;text-align:center;font-size:1.4em}
.stage .st-veil span{color:var(--mut);font-size:.6em}
.stage .st-toast{position:fixed;left:24px;bottom:24px;z-index:80;max-width:420px;display:grid;gap:4px;background:var(--panel);border:1px solid var(--g);border-radius:12px;padding:10px 14px;font-size:.9em;box-shadow:0 14px 40px #000a}
'''

BTN = """            {caps.upload && !siaran && (
              <button type="button" className="st-tag st-add" onClick={() => { setIntake(true); setOpen(false) }}>
                Tambah data{waiting > 0 && <em>{waiting}</em>}
              </button>
            )}"""

INTAKE_TAG = """<StageIntake open={intake} onClose={() => setIntake(false)} batches={batches} apiInfo={data.api} actions={actions} caps={caps} siaran={siaran} now={now} />
      {canControl && ("""

# (berkas, jangkar, pengganti); jangkar harus ada tepat 1x
EDITS = [
    (STAGE, "import StageControls from './StageControls'", "import StageControls from './StageControls'\nimport StageIntake from './StageIntake'\nimport { useBatchDetail, mergeDetail } from './useBatchDetail'"),
    (STAGE, "const [sel, setSel] = useState(null)", "const [sel, setSel] = useState(null)\n  const [intake, setIntake] = useState(false)"),
    (STAGE, "const agentBatch = data && data.agent ? data.agent.batchId : null",
     "const agentBatch = data && data.agent ? data.agent.batchId : null\n  const selBase = data && data.batches ? (data.batches.find((b) => b.id === sel) || data.batches[0] || null) : null\n  const detail = useBatchDetail(mode === 'api' && selBase ? selBase.id : null)"),
    (STAGE, "else if (k === 'c' && canControl) setOpen((v) => !v)",
     "else if (k === 'c' && canControl) { setOpen((v) => !v); setIntake(false) }\n      else if (k === 'u' && caps.upload) { setIntake((v) => !v); setOpen(false) }"),
    (STAGE, "else if (e.key === 'Escape') setOpen(false)", "else if (e.key === 'Escape') { setOpen(false); setIntake(false) }"),
    (STAGE, "const batches = data.batches || []", "const batches = data.batches || []\n  const waiting = batches.filter((b) => b.trust === 'VALIDATING').length"),
    (STAGE, "const selected = batches.find((b) => b.id === sel) || batches[0] || null",
     "const selected = mergeDetail(batches.find((b) => b.id === sel) || batches[0] || null, detail)"),
    (STAGE, '<div className="st-tags">', '<div className="st-tags">\n' + BTN),
    (STAGE, "{canControl && (", INTAKE_TAG),
    (CLIENT, "stageResetPreview: () => request('/showcase/reset/preview'),",
     "stageResetPreview: () => request('/showcase/reset/preview'),\n  getStageBatch: (id) => request(`/stage/batches/${id}`),\n  stagePromote: (id) => request(`/stage/batches/${id}/promote`, { method: 'POST' }),"),
    (USE, "reset: call('reset'), resetPreview }", "reset: call('reset'), promote: call('promote'), resetPreview }"),
    (USE, "resetPreview: true, auto: true }", "resetPreview: true, auto: true, promote: false }"),
    (USE, "resetPreview: !!api.stageResetPreview, auto: false }", "resetPreview: !!api.stageResetPreview, auto: false, promote: !!api.stagePromote }"),
    (SHOW, 'reason="Reset demo Panggung")',
     'reason="Reset demo Panggung")\n        from app.models.lab_entry import LabEntry\n        db.query(LabEntry).filter(LabEntry.business_id == business.id).delete(synchronize_session=False)\n        db.commit()'),
]


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def main():
    print("patch_tahap_b versi 1 (mendukung CRLF)")
    if os.path.exists(NEW_INTAKE):
        print("Sudah dipasang, tidak ada yang diubah.")
        return 0
    for need in ("app/services/stage_batches.py",):
        if not os.path.exists(need):
            print("BATAL: tahap A (patch_stage_batches) belum terpasang.")
            return 1
    raw = {p: read(p) for p in {e[0] for e in EDITS} | {CSS}}
    eols = {p: ("\r\n" if "\r\n" in t else "\n") for p, t in raw.items()}
    texts = {p: t.replace("\r\n", "\n") for p, t in raw.items()}
    for path, anchor, _ in EDITS:
        n = texts[path].count(anchor)
        if n != 1:
            print(f"BATAL: di {path} potongan ditemukan {n}x (harus 1x): {anchor[:70]!r}")
            return 1
    for path, anchor, new in EDITS:
        texts[path] = texts[path].replace(anchor, new, 1)
    texts[CSS] = texts[CSS].rstrip() + "\n" + CSS_ADD
    for path, content in ((NEW_INTAKE, INTAKE_SRC), (NEW_DETAIL, DETAIL_SRC)):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
    for path, text in texts.items():
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(text.replace("\n", eols[path]))
    print("Selesai: laci Tambah data dan penghubung data mentah terpasang.")
    return 0


sys.exit(main())
