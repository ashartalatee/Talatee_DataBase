import { useState } from 'react'
import { Trash2, RotateCcw, Database, Folder, Package, ScrollText, Building2 } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import ConfirmPurgeModal from '../components/ConfirmPurgeModal'
import { formatDateTime, formatNumber } from '../lib/format'

const LEVEL_META = {
  business: { label: 'Business', icon: Building2, restore: api.restoreBusiness, purge: api.purgeBusiness },
  source: { label: 'Source', icon: Package, restore: api.restoreSource, purge: api.purgeSource },
  dataset: { label: 'Dataset', icon: Folder, restore: api.restoreDataset, purge: api.purgeDataset },
  batch: { label: 'Batch', icon: Database, restore: api.restoreBatch, purge: api.purgeBatch },
}

export default function Trash() {
  const { data, loading, error, reload } = useFetch(() => api.listTrash(), [])
  const log = useFetch(() => api.listDeletionLog(), [])
  const [purgeTarget, setPurgeTarget] = useState(null) // { level, id, name }
  const [restoringId, setRestoringId] = useState(null)
  const [actionError, setActionError] = useState(null)

  async function handleRestore(item) {
    setActionError(null)
    setRestoringId(item.id)
    try {
      await LEVEL_META[item.level].restore(item.id)
      await reload()
    } catch (err) {
      setActionError(err.message || String(err))
    } finally {
      setRestoringId(null)
    }
  }

  async function handlePurgeConfirm(reason) {
    const { level, id } = purgeTarget
    await LEVEL_META[level].purge(id, purgeTarget.name, reason)
    setPurgeTarget(null)
    await Promise.all([reload(), log.reload()])
  }

  if (loading) return <LoadingState label="Memuat Sampah" />
  if (error) return <ErrorState message={error} />

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-text-primary">Sampah</h1>
        <p className="text-text-muted text-sm mt-1">
          Source, dataset, atau batch yang dipindahkan ke sini langsung hilang dari dashboard &
          laporan, tapi datanya masih ada — pulihkan kapan saja sebelum dihapus permanen.
        </p>
      </div>

      {actionError && (
        <div className="text-danger text-xs bg-danger/10 border border-danger/30 rounded px-3 py-2">
          {actionError}
        </div>
      )}

      {data.items.length === 0 ? (
        <EmptyState label="Sampah kosong — belum ada yang dihapus sesaat." />
      ) : (
        <div className="bg-ink-surface border border-ink-border rounded-lg overflow-hidden">
          <ul className="divide-y divide-ink-border">
            {data.items.map((item) => {
              const meta = LEVEL_META[item.level]
              const Icon = meta.icon
              return (
                <li
                  key={`${item.level}-${item.id}`}
                  className="px-5 py-3 flex items-center justify-between gap-4"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <Icon size={16} className="text-text-muted shrink-0" strokeWidth={1.75} />
                    <div className="min-w-0">
                      <div className="text-sm text-text-primary truncate">{item.name}</div>
                      <div className="text-text-muted text-xs mt-0.5">
                        {meta.label}
                        {item.context_path && <> &middot; {item.context_path}</>}
                        {' '}&middot; dihapus {formatDateTime(item.deleted_at)}
                        {item.deleted_by && <> oleh {item.deleted_by}</>}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => handleRestore(item)}
                      disabled={restoringId === item.id}
                      className="flex items-center gap-1.5 text-xs text-accent hover:underline disabled:opacity-50"
                    >
                      <RotateCcw size={13} strokeWidth={1.75} />
                      {restoringId === item.id ? 'Memulihkan…' : 'Pulihkan'}
                    </button>
                    <button
                      onClick={() => setPurgeTarget(item)}
                      className="flex items-center gap-1.5 text-xs text-danger hover:underline"
                    >
                      <Trash2 size={13} strokeWidth={1.75} />
                      Hapus Permanen
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      <div className="bg-ink-surface border border-ink-border rounded-lg">
        <div className="px-5 py-4 border-b border-ink-border flex items-center gap-2">
          <ScrollText size={15} className="text-text-muted" strokeWidth={1.75} />
          <h2 className="text-sm font-medium text-text-primary">Riwayat Hapus Permanen</h2>
        </div>
        {log.loading ? (
          <div className="text-text-muted text-sm py-8 text-center">Memuat riwayat…</div>
        ) : log.error ? (
          <ErrorState message={log.error} />
        ) : log.data.length === 0 ? (
          <EmptyState label="Belum pernah ada yang dihapus permanen." />
        ) : (
          <ul className="divide-y divide-ink-border">
            {log.data.map((l) => (
              <li key={l.id} className="px-5 py-3 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <div className="text-sm text-text-primary truncate">{l.entity_name}</div>
                  <div className="text-text-muted text-xs mt-0.5">
                    {l.level}
                    {l.context_path && <> &middot; {l.context_path}</>}
                    {' '}&middot; oleh {l.deleted_by || '-'} &middot; {formatDateTime(l.deleted_at)}
                    {l.reason && <> &middot; alasan: {l.reason}</>}
                  </div>
                </div>
                <div className="text-xs text-text-muted font-display shrink-0 text-right">
                  {formatNumber(l.batches_deleted)} batch &middot; {formatNumber(l.records_deleted)}{' '}
                  records
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {purgeTarget && (
        <ConfirmPurgeModal
          entityLabel={LEVEL_META[purgeTarget.level].label}
          entityName={purgeTarget.name}
          onConfirm={handlePurgeConfirm}
          onClose={() => setPurgeTarget(null)}
        />
      )}
    </div>
  )
}
