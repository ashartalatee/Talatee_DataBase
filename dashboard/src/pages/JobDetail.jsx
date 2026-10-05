import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Download, FileText, Trash2, RotateCcw } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import StatusBadge from '../components/StatusBadge'
import ConfirmPurgeModal from '../components/ConfirmPurgeModal'
import BatchRawTable from '../components/BatchRawTable'
import BatchCleanView from '../components/BatchCleanView'
import { formatDateTime, formatBytes } from '../lib/format'

export default function JobDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data, loading, error, reload } = useFetch(() => api.getBatch(id), [id])
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState(null)
  const [showPurge, setShowPurge] = useState(false)

  if (loading) return <LoadingState label="Memuat job" />
  if (error) return <ErrorState message={error} />

  async function handleTrash() {
    setBusy(true)
    setActionError(null)
    try {
      await api.trashBatch(id)
      await reload()
    } catch (err) {
      setActionError(err.message || String(err))
    } finally {
      setBusy(false)
    }
  }

  async function handleRestore() {
    setBusy(true)
    setActionError(null)
    try {
      await api.restoreBatch(id)
      await reload()
    } catch (err) {
      setActionError(err.message || String(err))
    } finally {
      setBusy(false)
    }
  }

  async function handlePurgeConfirm(reason) {
    const confirmName = data.files[0]?.filename || `Batch ${new Date(data.started_at).toISOString()}`
    await api.purgeBatch(id, confirmName, reason)
    navigate('/jobs')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link to="/jobs" className="text-xs text-text-muted hover:text-accent">
            &larr; Jobs
          </Link>
          <h1 className="font-display text-lg text-text-primary mt-1 break-all">{data.id}</h1>
          <div className="mt-2 flex items-center gap-3">
            <StatusBadge status={data.status} />
            {data.deleted_at && (
              <span className="text-xs text-danger">Di Sampah sejak {formatDateTime(data.deleted_at)}</span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {data.deleted_at ? (
            <button
              onClick={handleRestore}
              disabled={busy}
              className="flex items-center gap-1.5 text-xs text-accent hover:underline disabled:opacity-50"
            >
              <RotateCcw size={13} strokeWidth={1.75} />
              Pulihkan
            </button>
          ) : (
            <button
              onClick={handleTrash}
              disabled={busy}
              className="flex items-center gap-1.5 text-xs text-text-muted hover:text-danger disabled:opacity-50"
            >
              <Trash2 size={13} strokeWidth={1.75} />
              Pindah ke Sampah
            </button>
          )}
          {data.deleted_at && (
            <button
              onClick={() => setShowPurge(true)}
              className="flex items-center gap-1.5 text-xs text-danger hover:underline"
            >
              Hapus Permanen
            </button>
          )}
        </div>
      </div>

      {actionError && (
        <div className="text-danger text-xs bg-danger/10 border border-danger/30 rounded px-3 py-2">
          {actionError}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <InfoCell label="Started" value={formatDateTime(data.started_at)} mono />
        <InfoCell label="Finished" value={formatDateTime(data.finished_at)} mono />
        <InfoCell label="Records Received" value={data.records_received} />
        <InfoCell label="Records Saved" value={data.records_saved} />
      </div>

      {data.error_message && (
        <div className="bg-danger/10 border border-danger/30 rounded-lg px-5 py-4">
          <div className="text-danger text-xs uppercase tracking-wider mb-1">Error</div>
          <div className="text-text-primary text-sm">{data.error_message}</div>
        </div>
      )}

      <div className="bg-ink-surface border border-ink-border rounded-lg">
        <div className="px-5 py-4 border-b border-ink-border">
          <h2 className="text-sm font-medium text-text-primary">
            Files <span className="text-text-muted font-normal">({data.files.length})</span>
          </h2>
        </div>
        {data.files.length === 0 ? (
          <EmptyState label="Tidak ada file untuk batch ini." />
        ) : (
          <ul className="divide-y divide-ink-border">
            {data.files.map((f) => (
              <li key={f.id} className="px-5 py-3 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                  <FileText size={16} className="text-text-muted shrink-0" strokeWidth={1.75} />
                  <div className="min-w-0">
                    <div className="text-sm text-text-primary truncate">{f.filename}</div>
                    <div className="text-xs text-text-muted mt-0.5 font-display truncate">
                      {f.storage_path}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4 shrink-0">
                  <span className="text-xs text-text-muted font-display">
                    {formatBytes(f.file_size)}
                  </span>
                  <a
                    href={api.fileDownloadUrl(f.id)}
                    className="flex items-center gap-1.5 text-xs text-accent hover:underline"
                  >
                    <Download size={13} strokeWidth={1.75} />
                    Download
                  </a>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      <BatchRawTable batchId={id} />

      <BatchCleanView batchId={id} />

      {showPurge && (
        <ConfirmPurgeModal
          entityLabel="Batch"
          entityName={data.files[0]?.filename || `Batch ${new Date(data.started_at).toISOString()}`}
          onConfirm={handlePurgeConfirm}
          onClose={() => setShowPurge(false)}
        />
      )}
    </div>
  )
}

function InfoCell({ label, value, mono }) {
  return (
    <div className="bg-ink-surface border border-ink-border rounded-lg px-4 py-3">
      <div className="text-text-muted text-[11px] uppercase tracking-wider">{label}</div>
      <div className={`text-text-primary text-sm mt-1 ${mono ? 'font-display text-xs' : ''}`}>
        {value ?? '-'}
      </div>
    </div>
  )
}
