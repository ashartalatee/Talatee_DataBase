import { useParams, Link } from 'react-router-dom'
import { Download, FileText } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import StatusBadge from '../components/StatusBadge'
import { formatDateTime, formatBytes } from '../lib/format'

export default function JobDetail() {
  const { id } = useParams()
  const { data, loading, error } = useFetch(() => api.getBatch(id), [id])

  if (loading) return <LoadingState label="Memuat job" />
  if (error) return <ErrorState message={error} />

  return (
    <div className="space-y-6">
      <div>
        <Link to="/jobs" className="text-xs text-text-muted hover:text-accent">
          &larr; Jobs
        </Link>
        <h1 className="font-display text-lg text-text-primary mt-1 break-all">{data.id}</h1>
        <div className="mt-2">
          <StatusBadge status={data.status} />
        </div>
      </div>

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
