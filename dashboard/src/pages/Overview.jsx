import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { Link } from 'react-router-dom'
import {
  CheckCircle2,
  Bot,
  Send,
  ArrowRight,
  Database,
  Cpu,
  LayoutGrid as LayoutGridIcon,
  Radio,
} from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import ProjectsBoard from '../components/ProjectsBoard'
import { LoadingState, ErrorState } from '../components/States'
import { formatBytes, formatNumber, formatRelative, colorForIndex } from '../lib/format'

const CHECKLIST = [
  'Laboratorium Data Pribadi',
  'Pengembangan Proyek',
  'Control Center Client',
  'Monitoring Sistem Real-time',
  'Analisis & Insight AI',
  'Update & Improvement Berkelanjutan',
]

export default function Overview() {
  const { data: stats, loading: statsLoading, error: statsError } = useFetch(
    () => api.getOverview(),
    []
  )
  const { data: businesses, loading: bizLoading } = useFetch(() => api.listBusinesses(), [])

  if (statsLoading) return <LoadingState label="Menghitung ledger" />
  if (statsError) return <ErrorState message={statsError} />

  const {
    total_records,
    total_datasets,
    total_sources,
    total_batches,
    total_storage_bytes,
    data_by_source,
    recent_batches,
  } = stats

  const pieData = data_by_source.map((s) => ({
    name: s.source_name,
    value: s.total_records,
  }))

  return (
    <div className="space-y-8">
      {/* Header brand + visi */}
      <div className="bg-ink-surface border border-ink-border rounded-lg px-6 py-6">
        <div className="max-w-2xl">
          <h1 className="font-display text-2xl text-text-primary">TALATEE</h1>
          <div className="text-accent text-xs font-display tracking-wide mt-1">
            LABORATORIUM PRIBADI + CONTROL CENTER
          </div>
          <p className="text-text-muted text-sm mt-3 leading-relaxed">
            Tempat bereksperimen, menyiapkan proyek, memantau client, dan memahami data
            secara pribadi untuk terus berkembang.
          </p>
          <ul className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5">
            {CHECKLIST.map((item) => (
              <li key={item} className="flex items-center gap-2 text-xs text-text-muted">
                <CheckCircle2 size={13} className="text-accent shrink-0" strokeWidth={1.75} />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Stat cards — semua angka nyata dari ledger, bukan simulasi */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          label="Total Client"
          value={bizLoading ? '…' : formatNumber(businesses.length)}
        />
        <StatCard label="Proyek (Dataset)" value={formatNumber(total_datasets)} />
        <StatCard label="Integrasi (Source)" value={formatNumber(total_sources)} />
        <StatCard label="Data Records" value={formatNumber(total_records)} />
        <StatCard
          label="Storage Used"
          value={formatBytes(total_storage_bytes)}
          sublabel={`${formatNumber(total_batches)} batch tercatat`}
        />
      </div>

      {/* Cuplikan registry Project — versi lengkapnya ada di halaman Proyek */}
      <ProjectsBoard variant="compact" />

      {/* Client termonitor — data nyata, bukan status kesehatan simulasi */}
      <div className="bg-ink-surface border border-ink-border rounded-lg">
        <div className="px-5 py-4 border-b border-ink-border flex items-center justify-between">
          <h2 className="text-sm font-medium text-text-primary">Client Termonitor</h2>
          <Link to="/businesses" className="text-xs text-accent hover:underline">
            Lihat semua
          </Link>
        </div>
        {bizLoading ? (
          <div className="px-5 py-8 text-text-muted text-sm text-center">Memuat…</div>
        ) : businesses.length === 0 ? (
          <div className="px-5 py-8 text-text-muted text-sm text-center">
            Belum ada client. Upload data pertama lewat tombol Upload Data.
          </div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-text-muted text-xs uppercase tracking-wider text-left">
                <th className="px-5 py-2.5 font-normal">Client</th>
                <th className="px-5 py-2.5 font-normal">Kategori</th>
                <th className="px-5 py-2.5 font-normal">Source</th>
                <th className="px-5 py-2.5 font-normal">Dataset</th>
                <th className="px-5 py-2.5 font-normal text-right">Records</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-border">
              {businesses.map((b) => (
                <tr key={b.id} className="hover:bg-ink-elevated/50 transition-colors">
                  <td className="px-5 py-3">
                    <Link to={`/businesses/${b.id}`} className="text-text-primary hover:text-accent">
                      {b.name}
                    </Link>
                  </td>
                  <td className="px-5 py-3 text-text-muted capitalize">{b.category}</td>
                  <td className="px-5 py-3 text-text-muted font-display">{b.total_sources}</td>
                  <td className="px-5 py-3 text-text-muted font-display">{b.total_datasets}</td>
                  <td className="px-5 py-3 text-text-primary font-display text-right">
                    {formatNumber(b.total_records)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        {/* Recently added — ledger style list */}
        <div className="lg:col-span-3 bg-ink-surface border border-ink-border rounded-lg">
          <div className="px-5 py-4 border-b border-ink-border flex items-center justify-between">
            <h2 className="text-sm font-medium text-text-primary">Aktivitas Terbaru</h2>
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

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <AiAnalystPreview />
        <DataFlowDiagram />
      </div>
    </div>
  )
}

function AiAnalystPreview() {
  return (
    <div className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4">
      <div className="flex items-center gap-2 mb-1">
        <Bot size={15} className="text-accent" strokeWidth={1.75} />
        <h2 className="text-sm font-medium text-text-primary">AI Analyst</h2>
      </div>
      <p className="text-text-muted text-xs mb-3">
        Segera hadir — nanti bisa tanya data pakai bahasa natural, misal &ldquo;produk apa
        yang penjualannya naik bulan ini?&rdquo;
      </p>
      <div className="flex items-center gap-2 bg-ink-elevated border border-ink-border rounded-md px-3 py-2 opacity-60">
        <span className="text-text-muted text-xs flex-1">Tanya apa saja tentang data...</span>
        <Send size={13} className="text-text-muted" strokeWidth={1.75} />
      </div>
    </div>
  )
}

function DataFlowDiagram() {
  const steps = [
    { icon: Database, label: 'Sumber Data', detail: 'CSV, Excel, API' },
    { icon: Cpu, label: 'Processing', detail: 'Raw \u2192 Core' },
    { icon: LayoutGridIcon, label: 'Dashboard', detail: 'Insight & laporan' },
    { icon: Radio, label: 'Automation', detail: 'Segera \u2014 belum tersambung' },
  ]
  return (
    <div className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4">
      <h2 className="text-sm font-medium text-text-primary mb-3">Data Flow (Arsitektur)</h2>
      <div className="flex items-center gap-1">
        {steps.map((step, i) => (
          <div key={step.label} className="flex items-center flex-1 min-w-0">
            <div className="flex-1 min-w-0 flex flex-col items-center text-center gap-1.5 px-1">
              <div className="w-9 h-9 rounded-full bg-ink-elevated border border-ink-border flex items-center justify-center">
                <step.icon size={15} className="text-accent" strokeWidth={1.75} />
              </div>
              <div className="text-text-primary text-[11px]">{step.label}</div>
              <div className="text-text-muted text-[10px] leading-snug">{step.detail}</div>
            </div>
            {i < steps.length - 1 && (
              <ArrowRight size={13} className="text-text-muted shrink-0" strokeWidth={1.75} />
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
