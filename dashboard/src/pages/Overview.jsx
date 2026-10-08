import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { Link, useNavigate } from 'react-router-dom'
import { Bot, ArrowRight } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'
import { LoadingState, ErrorState } from '../components/States'
import { formatBytes, formatNumber, formatCurrency, formatRelative, colorForIndex } from '../lib/format'

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
    total_revenue,
    total_datasets,
    trusted_datasets,
    untrusted_datasets,
    total_sources,
    total_batches,
    total_storage_bytes,
    data_by_source,
    recent_batches,
  } = stats

  // Omzet per channel/source -- hanya baris is_revenue=True yang dihitung
  // (lihat REVENUE_STATUSES di app/models/core_transaction.py), jadi ini
  // benar-benar nilai transaksi yang closing, bukan sekadar jumlah baris.
  const pieData = data_by_source.map((s) => ({
    name: s.source_name,
    value: s.total_revenue,
    records: s.total_records,
  }))

  return (
    <div className="space-y-6">
      {/* Header -- ringkas, cuma identitas + satu kalimat. Checklist fitur
          dibuang: itu daftar marketing, bukan informasi yang berguna
          dilihat tiap hari (hasil diskusi redesign Overview). */}
      <div>
        <h1 className="font-display text-2xl text-text-primary">TALATEE Control Center</h1>
        <p className="text-text-muted text-sm mt-1">
          Ringkasan seluruh client dan data yang dikelola lewat platform ini.
        </p>
      </div>

      {/* Stat cards -- angka pertama yang harus kelihatan, semuanya nyata
          dari ledger, bukan simulasi. */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-4">
        <StatCard
          label="Total Client"
          value={bizLoading ? '…' : formatNumber(businesses.length)}
        />
        <StatCard
          label="Total Omzet"
          value={formatCurrency(total_revenue)}
          sublabel={
            untrusted_datasets == null
              ? undefined
              : untrusted_datasets > 0
                ? `hanya TRUSTED · ${formatNumber(untrusted_datasets)} belum`
                : 'dari dataset TRUSTED'
          }
        />
        <StatCard
          label="Proyek (Dataset)"
          value={formatNumber(total_datasets)}
          sublabel={trusted_datasets == null ? undefined : `${formatNumber(trusted_datasets)} terpercaya`}
        />
        <StatCard label="Integrasi (Source)" value={formatNumber(total_sources)} />
        <StatCard label="Data Records" value={formatNumber(total_records)} />
        <StatCard
          label="Storage Used"
          value={formatBytes(total_storage_bytes)}
          sublabel={`${formatNumber(total_batches)} batch tercatat`}
        />
      </div>

      {/* Insight Otomatis -- dinaikkan & dilebarkan penuh (sebelumnya
          disempitkan berdua sama diagram arsitektur yang sudah dibuang). Ini
          bagian paling "hidup" dari Overview, pantas lebih menonjol. */}
      <AiInsightCard stats={stats} businesses={businesses || []} />

      {/* Client termonitor -- data nyata, bukan status kesehatan simulasi */}
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

        {/* Omzet by source — pie chart */}
        <div className="lg:col-span-2 bg-ink-surface border border-ink-border rounded-lg px-5 py-4">
          <h2 className="text-sm font-medium text-text-primary mb-2">Omzet by Source</h2>
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
                      formatter={(value) => formatCurrency(value)}
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
                    <span className="text-right">
                      <span className="text-text-primary font-display">
                        {formatCurrency(d.value)}
                      </span>
                      <span className="text-text-muted font-display ml-1.5">
                        ({formatNumber(d.records)} rec)
                      </span>
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

function AiInsightCard({ stats, businesses }) {
  const navigate = useNavigate()
  const { data_by_source, recent_batches, total_revenue } = stats

  // Semua dihitung dari data yang SUDAH ke-load di halaman ini -- tidak ada
  // panggilan API baru, apalagi ke Hermes. Bedanya dari AI Analyst penuh:
  // ini "kasih tahu duluan" (proaktif), AI Analyst itu "jawab kalau
  // ditanya" (reaktif) -- dua hal beda, bukan duplikat.
  const failedRecent = recent_batches.filter((b) => b.status === 'Failed').length
  const zeroDataClients = businesses.filter((b) => b.total_records === 0)
  const topSource = data_by_source.length
    ? [...data_by_source].sort((a, b) => b.total_revenue - a.total_revenue)[0]
    : null
  const topSourceShare =
    topSource && total_revenue > 0 ? Math.round((topSource.total_revenue / total_revenue) * 100) : null

  const insights = []
  if (failedRecent > 0) {
    insights.push({
      text: `${failedRecent} dari ${recent_batches.length} batch terakhir berstatus Failed.`,
      cta: 'Cek Logs & Errors',
      to: '/jobs',
    })
  }
  if (topSource && topSourceShare >= 50) {
    insights.push({
      text: `${topSource.source_name} menyumbang ${topSourceShare}% dari total omzet.`,
      cta: 'Lihat Data Explorer',
      to: '/data-explorer',
    })
  }
  if (zeroDataClients.length > 0) {
    insights.push({
      text: `${zeroDataClients.length} client terdaftar belum ada data masuk sama sekali.`,
      cta: 'Lihat Clients',
      to: '/businesses',
    })
  }

  function askMore() {
    const topic = insights[0]?.text ?? 'kondisi data secara keseluruhan'
    try {
      localStorage.setItem('talatee_ai_analyst_draft', `Jelaskan lebih detail soal: ${topic}`)
    } catch {
      // localStorage diblokir -- tetap navigasi, draft-nya cuma tidak ikut
    }
    navigate('/ai-analyst')
  }

  return (
    <div className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4">
      <div className="flex items-center justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <Bot size={15} className="text-accent" strokeWidth={1.75} />
            <h2 className="text-sm font-medium text-text-primary">Insight Otomatis</h2>
          </div>

          {insights.length === 0 ? (
            <p className="text-text-muted text-xs">
              Tidak ada yang perlu diperhatikan khusus saat ini — semua batch terbaru sukses.
            </p>
          ) : (
            <ul className="space-y-1.5">
              {insights.map((ins, i) => (
                <li key={i} className="flex items-center flex-wrap gap-x-3 gap-y-0.5 text-xs">
                  <span className="text-text-primary">{ins.text}</span>
                  <Link to={ins.to} className="text-accent hover:underline whitespace-nowrap">
                    {ins.cta}
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        <button
          onClick={askMore}
          className="shrink-0 flex items-center gap-2 text-xs text-accent border border-ink-border hover:border-accent rounded-md px-3 py-2 transition-colors"
        >
          Tanya lebih lanjut
          <ArrowRight size={12} strokeWidth={1.75} />
        </button>
      </div>
    </div>
  )
}
