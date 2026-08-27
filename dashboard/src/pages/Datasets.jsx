import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import { formatDateTime, formatNumber } from '../lib/format'

export default function Datasets() {
  const { data, loading, error } = useFetch(() => api.listDatasets(), [])

  if (loading) return <LoadingState label="Memuat datasets" />
  if (error) return <ErrorState message={error} />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-text-primary">Datasets</h1>
        <p className="text-text-muted text-sm mt-1">
          Kumpulan data yang sudah diorganisir dari batch-batch ingestion.
        </p>
      </div>

      {data.length === 0 ? (
        <EmptyState label="Belum ada dataset." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.map((d) => (
            <Link
              key={d.id}
              to={`/datasets/${d.id}`}
              className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4 hover:border-accent/50 transition-colors"
            >
              <div className="text-text-primary text-sm font-medium truncate">{d.name}</div>
              <div className="text-text-muted text-xs mt-1">
                {d.description || 'Tidak ada deskripsi'}
              </div>
              <div className="flex items-center justify-between mt-4 pt-3 border-t border-ink-border">
                <div>
                  <div className="font-display text-lg text-text-primary tabular-nums">
                    {formatNumber(d.total_records)}
                  </div>
                  <div className="text-text-muted text-[11px]">records</div>
                </div>
                <div className="text-right">
                  <div className="font-display text-lg text-text-primary tabular-nums">
                    {d.total_batches}
                  </div>
                  <div className="text-text-muted text-[11px]">batches</div>
                </div>
              </div>
              <div className="text-text-muted text-[11px] font-display mt-3">
                Updated {formatDateTime(d.updated_at)}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
