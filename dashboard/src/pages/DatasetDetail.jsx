import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import StatusBadge from '../components/StatusBadge'
import { formatDateTime, formatNumber } from '../lib/format'

export default function DatasetDetail() {
  const { id } = useParams()
  const { data, loading, error } = useFetch(() => api.getDataset(id), [id])

  if (loading) return <LoadingState label="Memuat dataset" />
  if (error) return <ErrorState message={error} />

  const columns = data.schema?.columns || []

  return (
    <div className="space-y-6">
      <div>
        <Link to="/datasets" className="text-xs text-text-muted hover:text-accent">
          &larr; Datasets
        </Link>
        <h1 className="font-display text-xl text-text-primary mt-1">{data.name}</h1>
        <p className="text-text-muted text-sm mt-1">
          {data.description || 'Tidak ada deskripsi'} &middot; dibuat{' '}
          {formatDateTime(data.created_at)}
        </p>
      </div>

      {columns.length > 0 && (
        <div className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4">
          <h2 className="text-sm font-medium text-text-primary mb-3">
            Schema <span className="text-text-muted font-normal">(dari batch terakhir)</span>
          </h2>
          <div className="flex flex-wrap gap-2">
            {columns.map((c) => (
              <span
                key={c}
                className="font-display text-xs px-2.5 py-1 rounded border border-ink-border text-text-muted bg-ink-elevated"
              >
                {c}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="bg-ink-surface border border-ink-border rounded-lg">
        <div className="px-5 py-4 border-b border-ink-border">
          <h2 className="text-sm font-medium text-text-primary">
            Riwayat Batch <span className="text-text-muted font-normal">({data.batches.length})</span>
          </h2>
        </div>
        {data.batches.length === 0 ? (
          <EmptyState label="Belum ada batch untuk dataset ini." />
        ) : (
          <ul className="divide-y divide-ink-border">
            {data.batches.map((b) => (
              <li key={b.id} className="px-5 py-3 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <Link
                    to={`/jobs/${b.id}`}
                    className="font-display text-xs text-text-primary hover:text-accent truncate block"
                  >
                    {b.id}
                  </Link>
                  <div className="text-text-muted text-xs mt-0.5 font-display">
                    {formatDateTime(b.started_at)}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <StatusBadge status={b.status} />
                  <div className="text-xs text-text-muted mt-0.5 font-display">
                    {formatNumber(b.records_saved)} records
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
