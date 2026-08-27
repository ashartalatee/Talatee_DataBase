import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import { LoadingState, ErrorState } from '../components/States'
import { formatBytes, formatNumber, formatRelative, colorForIndex } from '../lib/format'

export default function Overview() {
  const { data, loading, error } = useFetch(() => api.getOverview(), [])

  if (loading) return <LoadingState label="Menghitung ledger" />
  if (error) return <ErrorState message={error} />

  const {
    total_records,
    total_datasets,
    total_sources,
    total_batches,
    total_storage_bytes,
    data_by_source,
    recent_batches,
  } = data

  const pieData = data_by_source.map((s) => ({
    name: s.source_name,
    value: s.total_records,
  }))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-text-primary">Overview</h1>
        <p className="text-text-muted text-sm mt-1">
          Ringkasan seluruh data yang tercatat di ledger.
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Records" value={formatNumber(total_records)} />
        <StatCard label="Datasets" value={formatNumber(total_datasets)} />
        <StatCard label="Sources" value={formatNumber(total_sources)} />
        <StatCard
          label="Storage Used"
          value={formatBytes(total_storage_bytes)}
          sublabel={`${formatNumber(total_batches)} batch tercatat`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Recently added — ledger style list */}
        <div className="lg:col-span-3 bg-ink-surface border border-ink-border rounded-lg">
          <div className="px-5 py-4 border-b border-ink-border flex items-center justify-between">
            <h2 className="text-sm font-medium text-text-primary">Recently Added</h2>
            <Link to="/jobs" className="text-xs text-accent hover:underline">
              Lihat semua
            </Link>
          </div>
          {recent_batches.length === 0 ? (
            <div className="px-5 py-8 text-text-muted text-sm text-center">
              Belum ada data masuk.
            </div>
          ) : (
            <ul className="divide-y divide-ink-border">
              {recent_batches.map((b) => (
                <li key={b.id} className="px-5 py-3 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="text-sm text-text-primary truncate">{b.filename}</div>
                    <div className="text-xs text-text-muted mt-0.5">
                      {b.source_name} &middot; {b.dataset_name}
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <StatusBadge status={b.status} />
                    <div className="text-xs text-text-muted mt-0.5 font-display">
                      {formatRelative(b.started_at)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Data by source — pie chart */}
        <div className="lg:col-span-2 bg-ink-surface border border-ink-border rounded-lg px-5 py-4">
          <h2 className="text-sm font-medium text-text-primary mb-2">Data by Source</h2>
          {pieData.length === 0 ? (
            <div className="text-text-muted text-sm text-center py-12">Belum ada data.</div>
          ) : (
            <>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={45}
                      outerRadius={75}
                      paddingAngle={2}
                      stroke="none"
                    >
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={colorForIndex(i)} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: '#1c222b',
                        border: '1px solid #262c36',
                        borderRadius: 6,
                        fontSize: 12,
                      }}
                      itemStyle={{ color: '#e6e8eb' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="space-y-1.5 mt-2">
                {pieData.map((d, i) => (
                  <li key={d.name} className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-2 text-text-muted truncate">
                      <span
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ background: colorForIndex(i) }}
                      />
                      {d.name}
                    </span>
                    <span className="text-text-primary font-display">
                      {formatNumber(d.value)}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
