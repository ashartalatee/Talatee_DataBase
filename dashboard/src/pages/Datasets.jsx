import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import TrustPill from '../components/TrustPill'
import { formatDateTime, formatNumber } from '../lib/format'

export default function Datasets() {
  const { data, loading, error } = useFetch(() => api.listDatasets(), [])
  const [filter, setFilter] = useState(null)

  if (loading) return <LoadingState label="Memuat datasets" />
  if (error) return <ErrorState message={error} />

  // Filter hanya aktif kalau API memang mengirim trust_status; kalau tidak,
  // tampilkan semua supaya data tidak tersembunyi diam-diam.
  const hasTrust = data.some((d) => d.trust_status !== undefined)
  const trusted = data.filter((d) => d.trust_status === 'TRUSTED')
  const mode = filter ?? (hasTrust ? 'trusted' : 'all')
  const shown = mode === 'trusted' ? trusted : data
  const waiting = data.length - trusted.length

  const tabCls = (active) =>
    `px-3 py-1 text-xs rounded-md border transition-colors ${
      active
        ? 'border-accent text-accent bg-accent/10'
        : 'border-ink-border text-text-muted hover:text-text-primary'
    }`

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-xl text-text-primary">Datasets</h1>
          <p className="text-text-muted text-sm mt-1">
            Kumpulan data yang sudah diorganisir dari batch-batch ingestion.
          </p>
        </div>
        {hasTrust && data.length > 0 && (
          <div className="flex items-center gap-2">
            <button onClick={() => setFilter('trusted')} className={tabCls(mode === 'trusted')}>
              Terpercaya ({trusted.length})
            </button>
            <button onClick={() => setFilter('all')} className={tabCls(mode === 'all')}>
              Semua ({data.length})
            </button>
          </div>
        )}
      </div>

      {data.length === 0 ? (
        <EmptyState label="Belum ada dataset." />
      ) : shown.length === 0 ? (
        <div className="bg-ink-surface border border-ink-border rounded-lg px-5 py-6 text-sm">
          <div className="text-text-primary">Belum ada dataset terpercaya.</div>
          <div className="text-text-muted text-xs mt-1">
            {waiting} dataset masih menunggu validasi di Eksperimen. Data hanya muncul di sini
            setelah lolos validasi dan dijadikan TRUSTED.
          </div>
          <div className="flex items-center gap-4 mt-3">
            <Link to="/laboratorium" className="text-accent text-xs hover:underline">
              Buka Eksperimen →
            </Link>
            <button
              onClick={() => setFilter('all')}
              className="text-text-muted text-xs hover:text-text-primary"
            >
              Tampilkan semua
            </button>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {shown.map((d) => (
            <Link
              key={d.id}
              to={`/datasets/${d.id}`}
              className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4 hover:border-accent/50 transition-colors"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="text-text-primary text-sm font-medium truncate">{d.name}</div>
                {d.trust_status && <TrustPill status={d.trust_status} />}
              </div>
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
