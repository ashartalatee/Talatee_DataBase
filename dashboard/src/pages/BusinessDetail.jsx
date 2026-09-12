import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { Trash2 } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import { CATEGORY_META } from './Businesses'
import { formatDateTime } from '../lib/format'

export default function BusinessDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const business = useFetch(() => api.getBusiness(id), [id])
  const sources = useFetch(() => api.getBusinessSources(id), [id])
  const [busy, setBusy] = useState(false)
  const [busySourceId, setBusySourceId] = useState(null)
  const [actionError, setActionError] = useState(null)

  if (business.loading || sources.loading) return <LoadingState label="Memuat business" />
  if (business.error) return <ErrorState message={business.error} />
  if (sources.error) return <ErrorState message={sources.error} />

  const meta = CATEGORY_META[business.data.category] || CATEGORY_META.lainnya
  const Icon = meta.icon

  async function handleTrashBusiness() {
    setBusy(true)
    setActionError(null)
    try {
      await api.trashBusiness(id)
      // Business yang di-trash langsung 404 di GET /businesses/{id}
      // (sengaja), jadi pindah ke list. Untuk pulihkan / hapus permanen,
      // buka halaman Sampah.
      navigate('/businesses')
    } catch (err) {
      setActionError(err.message || String(err))
      setBusy(false)
    }
  }

  async function handleTrashSource(sourceId) {
    setBusySourceId(sourceId)
    setActionError(null)
    try {
      await api.trashSource(sourceId)
      await sources.reload()
    } catch (err) {
      setActionError(err.message || String(err))
    } finally {
      setBusySourceId(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link to="/businesses" className="text-xs text-text-muted hover:text-accent">
            &larr; Businesses
          </Link>
          <h1 className="font-display text-xl text-text-primary mt-1">{business.data.name}</h1>
          <div className="flex items-center gap-2 mt-2">
            <span className="inline-flex items-center gap-1.5 text-xs px-2 py-0.5 rounded-full border border-accent/40 text-accent">
              <Icon size={12} strokeWidth={1.75} />
              {meta.label}
            </span>
            <span className="text-text-muted text-xs">
              terdaftar {formatDateTime(business.data.created_at)}
            </span>
          </div>
        </div>
        <button
          onClick={handleTrashBusiness}
          disabled={busy}
          className="flex items-center gap-1.5 text-xs text-text-muted hover:text-danger disabled:opacity-50 shrink-0"
        >
          <Trash2 size={13} strokeWidth={1.75} />
          Pindah ke Sampah
        </button>
      </div>

      {actionError && (
        <div className="text-danger text-xs bg-danger/10 border border-danger/30 rounded px-3 py-2">
          {actionError}
        </div>
      )}

      <div className="bg-ink-surface border border-ink-border rounded-lg">
        <div className="px-5 py-4 border-b border-ink-border flex items-center justify-between">
          <h2 className="text-sm font-medium text-text-primary">
            Sources <span className="text-text-muted font-normal">({sources.data.length})</span>
          </h2>
          <Link to="/trash" className="text-xs text-text-muted hover:text-accent">
            Lihat Sampah
          </Link>
        </div>
        {sources.data.length === 0 ? (
          <EmptyState label="Belum ada source untuk business ini." />
        ) : (
          <ul className="divide-y divide-ink-border">
            {sources.data.map((s) => (
              <li key={s.id} className="px-5 py-3 flex items-center justify-between">
                <Link to={`/sources/${s.id}`} className="text-text-primary hover:text-accent text-sm">
                  {s.name}
                </Link>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-text-muted">{s.type}</span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full border ${
                      s.status === 'active'
                        ? 'border-success/40 text-success'
                        : 'border-ink-border text-text-muted'
                    }`}
                  >
                    {s.status}
                  </span>
                  <button
                    onClick={() => handleTrashSource(s.id)}
                    disabled={busySourceId === s.id}
                    title="Pindah source ini ke Sampah"
                    className="text-text-muted hover:text-danger disabled:opacity-50"
                  >
                    <Trash2 size={14} strokeWidth={1.75} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
