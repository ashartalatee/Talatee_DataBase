// Laci "Tambah data" Panggung: unggah manual (seret atau pilih file), antrean persetujuan, dan status koneksi API.
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
  useEffect(() => { autoRef.current = auto }, [auto])

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
  useEffect(() => { uploadRef.current = upload })

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
