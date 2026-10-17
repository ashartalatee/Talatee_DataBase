import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import { formatDateTime } from '../lib/format'

export default function Sources() {
  const sources = useFetch(() => api.listSourcesTrusted(), [])
  const businesses = useFetch(() => api.listBusinesses(), [])

  if (sources.loading || businesses.loading) return <LoadingState label="Memuat sources" />
  if (sources.error) return <ErrorState message={sources.error} />
  if (businesses.error) return <ErrorState message={businesses.error} />

  const businessMap = Object.fromEntries(businesses.data.map((b) => [b.id, b.name]))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-text-primary">Sources</h1>
        <p className="text-text-muted text-sm mt-1">
          Asal data yang terdaftar di platform, lintas semua business.
        </p>
      </div>

      {sources.data.length === 0 ? (
        <EmptyState label="Belum ada source terpercaya. Data baru masuk ke Eksperimen dulu; jadikan dataset-nya TRUSTED agar source muncul di sini." />
      ) : (
        <div className="bg-ink-surface border border-ink-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink-border text-text-muted text-xs uppercase tracking-wider">
                <th className="text-left px-5 py-3 font-medium">Name</th>
                <th className="text-left px-5 py-3 font-medium">Business</th>
                <th className="text-left px-5 py-3 font-medium">Type</th>
                <th className="text-left px-5 py-3 font-medium">Status</th>
                <th className="text-left px-5 py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-border">
              {sources.data.map((s) => (
                <tr key={s.id} className="hover:bg-ink-elevated/50 transition-colors">
                  <td className="px-5 py-3">
                    <Link to={`/sources/${s.id}`} className="text-text-primary hover:text-accent">
                      {s.name}
                    </Link>
                  </td>
                  <td className="px-5 py-3">
                    <Link
                      to={`/businesses/${s.business_id}`}
                      className="text-text-muted hover:text-accent"
                    >
                      {businessMap[s.business_id] || '-'}
                    </Link>
                  </td>
                  <td className="px-5 py-3 text-text-muted">{s.type}</td>
                  <td className="px-5 py-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full border ${
                        s.status === 'active'
                          ? 'border-success/40 text-success'
                          : 'border-ink-border text-text-muted'
                      }`}
                    >
                      {s.status}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-text-muted font-display text-xs">
                    {formatDateTime(s.created_at)}
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
