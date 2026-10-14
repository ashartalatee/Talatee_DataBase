// Laci "Kendali demo" Panggung. Tersembunyi secara bawaan: dibuka lewat pegangan di tepi layar atau tombol C.
// Tidak pernah menampilkan key, alamat internal, atau teks galat mentah (layar ini bisa disiarkan).
import { useRef, useState } from 'react'

// Hanya pesan 4xx yang dikurasi backend yang ditampilkan (mis. "Data 30 hari sudah ada."); sisanya umum.
const friendly = (e) => {
  const m = /^4\d\d: (.{1,160})$/.exec((e && e.message) || '')
  return m ? m[1] : 'Aksi gagal. Detailnya ada di konsol.'
}

export default function StageControls({ open, onOpen, onClose, caps, actions, auto, onAuto, siaran, onSiaran, orient, onOrient, follow, onFollow, mode }) {
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const [preview, setPreview] = useState('')
  const [promote, setPromote] = useState(true)
  const fileRef = useRef(null)

  const run = async (fn, okText) => {
    setBusy(true)
    setMsg('')
    try {
      const r = await fn()
      setMsg(typeof r === 'string' ? r : okText)
    } catch (e) {
      console.warn('[panggung]', e)
      setMsg(friendly(e))
    } finally {
      setBusy(false)
      setConfirm(false)
    }
  }
  const soon = (ok) => (ok ? '' : ' (belum tersedia)')
  const startReset = async () => {
    setBusy(true)
    setMsg('')
    try {
      setPreview((caps.resetPreview && (await actions.resetPreview())) || '')
      setConfirm(true)
    } catch (e) {
      console.warn('[panggung]', e)
      setMsg(friendly(e))
    } finally {
      setBusy(false)
    }
  }

  if (!open) {
    if (siaran) return null
    return (
      <button type="button" className="st-handle" onClick={onOpen} aria-label="Buka kendali demo" title="Kendali (tekan C)">‹</button>
    )
  }

  return (
    <aside className="st-drawer" role="dialog" aria-label="Kendali demo">
      <div className="st-dh">
        <b>Kendali demo</b>
        <button type="button" className="st-x" onClick={onClose} aria-label="Tutup">×</button>
      </div>
      <p className="st-dsub">
        {mode === 'mock' ? 'Mode simulasi: semua aksi hanya terjadi di browser ini.' : 'Mode database: aksi hanya menyentuh bisnis demo.'}
      </p>

      <h3>Data</h3>
      <button type="button" className="st-btn primary" disabled={busy || !caps.trigger} onClick={() => run(actions.trigger, 'Transaksi demo dikirim')}>
        Kirim transaksi demo{soon(caps.trigger)}
      </button>
      {caps.auto && (
        <label className="st-chk"><input type="checkbox" checked={auto} onChange={onAuto} /> Otomatis (transaksi datang sendiri)</label>
      )}
      <button type="button" className="st-btn" disabled={busy || !caps.backfill} onClick={() => run(actions.backfill, 'Data 30 hari diisi')}>
        Isi data 30 hari{soon(caps.backfill)}
      </button>
      <input
        ref={fileRef} type="file" accept=".csv,.xlsx,.xls" hidden aria-label="Pilih file untuk diunggah"
        onChange={(e) => {
          const f = e.target.files && e.target.files[0]
          if (f) run(() => actions.upload(f, { promote }), 'File dikirim')
          e.target.value = ''
        }}
      />
      <button type="button" className="st-btn" disabled={busy || !caps.upload} onClick={() => fileRef.current && fileRef.current.click()}>
        Unggah file…{soon(caps.upload)}
      </button>
      <label className="st-chk st-sub"><input type="checkbox" checked={promote} onChange={(e) => setPromote(e.target.checked)} /> Promote otomatis setelah divalidasi</label>
      <button type="button" className="st-btn" disabled>Hubungkan API (segera)</button>

      <h3>Tampilan</h3>
      <label className="st-chk"><input type="checkbox" checked={siaran} onChange={onSiaran} /> Mode siaran (tombol B)</label>
      <label className="st-chk"><input type="checkbox" checked={!!follow} onChange={onFollow} /> Agen memandu halaman (tombol F)</label>
      <div className="st-segrow" role="group" aria-label="Orientasi siaran">
        {[['auto', 'Otomatis'], ['lanskap', 'Lanskap 16:9'], ['potret', 'Potret 9:16']].map(([k, l]) => (
          <button key={k} type="button" className={`st-btn sm${orient === k ? ' on' : ''}`} aria-pressed={orient === k} onClick={() => onOrient(k)}>{l}</button>
        ))}
      </div>

      <h3>Hati-hati</h3>
      {!confirm ? (
        <button type="button" className="st-btn danger" disabled={busy || !caps.reset} onClick={startReset}>
          Reset demo{soon(caps.reset)}
        </button>
      ) : (
        <div className="st-confirm">
          <p>{preview || 'Kosongkan semua data demo?'}</p>
          <button type="button" className="st-btn danger" disabled={busy} onClick={() => run(actions.reset, 'Data demo dikosongkan')}>Ya, reset</button>
          <button type="button" className="st-btn" onClick={() => setConfirm(false)}>Batal</button>
        </div>
      )}

      <p className="st-msg" aria-live="polite">{msg}</p>
      <p className="st-hint">Tombol C membuka atau menutup laci ini. V orientasi, 1/2 halaman. Esc menutup.</p>
    </aside>
  )
}
