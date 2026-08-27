import { useParams, Link } from 'react-router-dom'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import { formatDateTime, formatNumber } from '../lib/format'

export default function SourceDetail() {
  const { id } = useParams()
  const source = useFetch(() => api.getSource(id), [id])
  const datasets = useFetch(() => api.listDatasets(), [id])
  const business = useFetch(
    () => (source.data ? api.getBusiness(source.data.business_id) : Promise.resolve(null)),
    [source.data?.business_id]
  )

  if (source.loading || datasets.loading) return <LoadingState label="Memuat source" />
  if (source.error) return <ErrorState message={source.error} />
  if (datasets.error) return <ErrorState message={datasets.error} />

  const related = datasets.data.filter((d) => d.source_id === id)

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-1.5 text-xs text-text-muted">
          <Link to="/businesses" className="hover:text-accent">
            Businesses
          </Link>
          {business.data && (
            <>
              <span>/</span>
              <Link to={`/businesses/${business.data.id}`} className="hover:text-accent">
                {business.data.name}
              </Link>
            </>
          )}
          <span>/</span>
          <Link to="/sources" className="hover:text-accent">
            Sources
          </Link>
        </div>
        <h1 className="font-display text-xl text-text-primary mt-1">{source.data.name}</h1>
        <p className="text-text-muted text-sm mt-1">
          {source.data.type} &middot; terdaftar {formatDateTime(source.data.created_at)}
        </p>
      </div>

      <div className="bg-ink-surface border border-ink-border rounded-lg">
        <div className="px-5 py-4 border-b border-ink-border">
          <h2 className="text-sm font-medium text-text-primary">Datasets dari source ini</h2>
        </div>
        {related.length === 0 ? (
          <EmptyState label="Belum ada dataset dari source ini." />
        ) : (
          <ul className="divide-y divide-ink-border">
            {related.map((d) => (
              <li key={d.id} className="px-5 py-3 flex items-center justify-between">
                <Link to={`/datasets/${d.id}`} className="text-text-primary hover:text-accent text-sm">
                  {d.name}
                </Link>
                <span className="text-xs text-text-muted font-display">
                  {formatNumber(d.total_records)} records &middot; {d.total_batches} batch
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
