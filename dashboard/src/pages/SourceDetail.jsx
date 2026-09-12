import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Trash2 } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import { formatDateTime, formatNumber } from '../lib/format'

export default function SourceDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const source = useFetch(() => api.getSource(id), [id])
  const datasets = useFetch(() => api.listDatasets(), [id])
  const business = useFetch(
    () => (source.data ? api.getBusiness(source.data.business_id) : Promise.resolve(null)),
    [source.data?.business_id]
  )
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState(null)

  if (source.loading || datasets.loading) return <LoadingState label="Memuat source" />
  if (source.error) return <ErrorState message={source.error} />
  if (datasets.error) return <ErrorState message={datasets.error} />

  const related = datasets.data.filter((d) => d.source_id === id)

  async function handleTrashSource() {
    setBusy(true)
    setActionError(null)
    try {
      await api.trashSource(id)
      // Source yang di-trash langsung 404 di GET /sources/{id} (sengaja),
      // jadi pindah ke list, bukan reload di halaman yang sama. Untuk
      // pulihkan / hapus permanen source ini, buka halaman Sampah.
      navigate('/sources')
    } catch (err) {
      setActionError(err.message || String(err))
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
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
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={handleTrashSource}
            disabled={busy}
            className="flex items-center gap-1.5 text-xs text-text-muted hover:text-danger disabled:opacity-50"
          >
            <Trash2 size={13} strokeWidth={1.75} />
            Pindah ke Sampah
          </button>
        </div>
      </div>

      {actionError && (
        <div className="text-danger text-xs bg-danger/10 border border-danger/30 rounded px-3 py-2">
          {actionError}
        </div>
      )}

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
