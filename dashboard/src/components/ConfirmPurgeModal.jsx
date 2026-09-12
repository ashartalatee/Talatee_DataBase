import { useState } from 'react'
import { AlertTriangle, X } from 'lucide-react'

/**
 * Dialog konfirmasi HAPUS PERMANEN — dipakai di Trash.jsx, JobDetail.jsx,
 * DatasetDetail.jsx, SourceDetail.jsx. User WAJIB ketik ulang nama entity
 * persis sama sebelum tombol aktif — mencegah klik-tanpa-sengaja untuk aksi
 * yang tidak bisa dibatalkan. Nama yang dicocokkan di sini juga dicek ulang
 * di backend (lihat PurgeRequest.confirm_name di app/schemas/trash.py).
 */
export default function ConfirmPurgeModal({ entityLabel, entityName, onConfirm, onClose }) {
  const [typed, setTyped] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const matches = typed === entityName

  async function handleConfirm() {
    if (!matches || busy) return
    setBusy(true)
    setError(null)
    try {
      await onConfirm(reason.trim() || null)
    } catch (err) {
      setError(err.message || String(err))
      setBusy(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
      <div className="bg-ink-surface border border-danger/40 rounded-lg max-w-md w-full px-5 py-5 space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} className="text-danger shrink-0" strokeWidth={1.75} />
            <h2 className="text-sm font-medium text-text-primary">Hapus Permanen {entityLabel}</h2>
          </div>
          <button onClick={onClose} className="text-text-muted hover:text-text-primary shrink-0">
            <X size={16} />
          </button>
        </div>

        <p className="text-text-muted text-xs leading-relaxed">
          Tindakan ini <span className="text-danger">tidak bisa dibatalkan</span>. Semua data di
          bawah <span className="text-text-primary">{entityName}</span> — termasuk file mentah,
          data yang sudah diproses, dan riwayat koreksinya — akan hilang permanen. Untuk
          melanjutkan, ketik ulang nama persis di bawah ini.
        </p>

        <div className="bg-ink-elevated border border-ink-border rounded px-3 py-2">
          <span className="font-display text-xs text-text-primary break-all">{entityName}</span>
        </div>

        <input
          autoFocus
          type="text"
          value={typed}
          onChange={(e) => setTyped(e.target.value)}
          placeholder="Ketik nama di atas..."
          className="w-full bg-ink px-3 py-2 rounded border border-ink-border text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-danger/60"
        />

        <input
          type="text"
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Alasan hapus (opsional)"
          className="w-full bg-ink px-3 py-2 rounded border border-ink-border text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/60"
        />

        {error && (
          <div className="text-danger text-xs bg-danger/10 border border-danger/30 rounded px-3 py-2">
            {error}
          </div>
        )}

        <div className="flex items-center gap-2 pt-1">
          <button
            onClick={onClose}
            className="flex-1 text-sm text-text-muted hover:text-text-primary border border-ink-border rounded-md py-2 transition-colors"
          >
            Batal
          </button>
          <button
            onClick={handleConfirm}
            disabled={!matches || busy}
            className="flex-1 text-sm font-medium rounded-md py-2 bg-danger text-ink hover:bg-danger/85 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {busy ? 'Menghapus…' : 'Hapus Permanen'}
          </button>
        </div>
      </div>
    </div>
  )
}
