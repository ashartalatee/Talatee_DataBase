import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState } from '../components/States'
import { formatBytes, formatNumber, colorForIndex } from '../lib/format'

export default function Storage() {
  const overview = useFetch(() => api.getOverview(), [])
  const datasets = useFetch(() => api.listDatasets(), [])

  if (overview.loading || datasets.loading) return <LoadingState label="Menghitung storage" />
  if (overview.error) return <ErrorState message={overview.error} />
  if (datasets.error) return <ErrorState message={datasets.error} />

  const { total_storage_bytes, data_by_source } = overview.data
  const maxRecords = Math.max(...data_by_source.map((s) => s.total_records), 1)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-text-primary">Storage</h1>
        <p className="text-text-muted text-sm mt-1">
          Ruang yang terpakai di MinIO oleh raw file — akumulasi seluruh batch, tidak pernah
          berkurang (append-only).
        </p>
      </div>

      <div className="bg-ink-surface border border-ink-border rounded-lg px-6 py-8 text-center">
        <div className="text-text-muted text-xs uppercase tracking-wider">Total Storage Used</div>
        <div className="font-display text-4xl text-accent mt-2">
          {formatBytes(total_storage_bytes)}
        </div>
      </div>

      <div className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4">
        <h2 className="text-sm font-medium text-text-primary mb-4">Records by Source</h2>
        {data_by_source.length === 0 ? (
          <div className="text-text-muted text-sm text-center py-8">Belum ada data.</div>
        ) : (
          <div className="space-y-3">
            {data_by_source
              .sort((a, b) => b.total_records - a.total_records)
              .map((s, i) => (
                <div key={s.source_id}>
                  <div className="flex items-center justify-between text-xs mb-1">
                    <span className="text-text-primary">{s.source_name}</span>
                    <span className="font-display text-text-muted">
                      {formatNumber(s.total_records)}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-ink-elevated overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${(s.total_records / maxRecords) * 100}%`,
                        background: colorForIndex(i),
                      }}
                    />
                  </div>
                </div>
              ))}
          </div>
        )}
      </div>

      <div className="bg-ink-surface border border-ink-border rounded-lg overflow-hidden">
        <div className="px-5 py-4 border-b border-ink-border">
          <h2 className="text-sm font-medium text-text-primary">Datasets</h2>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-ink-border text-text-muted text-xs uppercase tracking-wider">
              <th className="text-left px-5 py-3 font-medium">Dataset</th>
              <th className="text-right px-5 py-3 font-medium">Batches</th>
              <th className="text-right px-5 py-3 font-medium">Records</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-border">
            {datasets.data.map((d) => (
              <tr key={d.id}>
                <td className="px-5 py-3 text-text-primary">{d.name}</td>
                <td className="px-5 py-3 text-right font-display text-text-muted">
                  {d.total_batches}
                </td>
                <td className="px-5 py-3 text-right font-display text-text-primary tabular-nums">
                  {formatNumber(d.total_records)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
