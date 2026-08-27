import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import StatusBadge from '../components/StatusBadge'
import { formatDateTime, formatNumber } from '../lib/format'

export default function Jobs() {
  const { data, loading, error } = useFetch(() => api.listBatches(), [])

  if (loading) return <LoadingState label="Memuat jobs" />
  if (error) return <ErrorState message={error} />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-text-primary">Jobs</h1>
        <p className="text-text-muted text-sm mt-1">
          Setiap baris adalah satu batch ingestion — tercatat permanen, tidak pernah ditimpa.
        </p>
      </div>

      {data.length === 0 ? (
        <EmptyState label="Belum ada job." />
      ) : (
        <div className="bg-ink-surface border border-ink-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink-border text-text-muted text-xs uppercase tracking-wider">
                <th className="text-left px-5 py-3 font-medium">Batch ID</th>
                <th className="text-left px-5 py-3 font-medium">Started</th>
                <th className="text-left px-5 py-3 font-medium">Status</th>
                <th className="text-right px-5 py-3 font-medium">Records</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-border">
              {data.map((b) => (
                <tr key={b.id} className="hover:bg-ink-elevated/50 transition-colors">
                  <td className="px-5 py-3">
                    <Link
                      to={`/jobs/${b.id}`}
                      className="font-display text-xs text-text-primary hover:text-accent"
                    >
                      {b.id}
                    </Link>
                  </td>
                  <td className="px-5 py-3 text-text-muted font-display text-xs">
                    {formatDateTime(b.started_at)}
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={b.status} />
                  </td>
                  <td className="px-5 py-3 text-right font-display text-text-primary tabular-nums">
                    {formatNumber(b.records_saved)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
