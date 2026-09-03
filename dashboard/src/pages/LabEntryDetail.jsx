import { useState } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  FlaskConical,
  Lightbulb as TipsIcon,
  CloudDownload,
  Brush,
  ShieldCheck,
  TrendingUp,
  Lightbulb,
  LayoutDashboard,
  SendHorizontal,
  CircleCheckBig,
  CircleX,
  Loader2,
  Play,
  ChevronDown,
  SquareArrowOutUpRight,
  ArrowUpCircle,
} from 'lucide-react'
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { LoadingState, ErrorState } from '../components/States'
import { formatNumber, formatCurrency, formatDateTime } from '../lib/format'

/**
 * Halaman "Pipeline Laboratorium" untuk 1 entri — dipicu dari kartu di
 * Laboratorium.jsx kalau entrinya sudah ditautkan ke Dataset. Tampilan
 * dirancang ulang supaya tiap step kelihatan jelas statusnya: badge nomor +
 * ikon berwarna beda per step, tombol JALANKAN, baris metrik, tombol Detail
 * yang buka/tutup rinciannya, dan panah penghubung ke step berikutnya.
 *
 * Step 1-4 & 6 tersambung ke endpoint NYATA (upload/core_processor/quality/
 * insights yang sudah ada). Step 5 (Insight AI) & 7 (Kirim WA) masih
 * "Segera hadir" karena belum ada integrasi AI atau WhatsApp di Talatee —
 * supaya tidak ada tombol yang pura-pura jalan.
 */

// Warna per step, dipetakan dari palet chart yang sudah dipakai di seluruh
// dashboard (lihat lib/format.js CHART_PALETTE) supaya konsisten, bukan
// warna baru yang asing dari sisa aplikasi.
const STEP_COLORS = {
  ambil: '#7CFC3C', // hijau — sama dengan --color-accent
  bersihkan: '#B08CE0', // ungu
  validasi: '#E8C547', // emas
  analisis: '#5BB8D4', // biru
  insight: '#E8C547', // emas (sama seperti Validasi di rancangan)
  dashboard: '#3DDC97', // teal
  wa: '#3DDC97', // hijau WA — dipakai hijau-teal supaya beda dari step 1
}

export default function LabEntryDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { data: entry, loading, error } = useFetch(() => api.getLabEntry(id), [id])

  if (loading) return <LoadingState label="Memuat entri" />
  if (error) return <ErrorState message={error} />

  if (!entry.dataset_id) {
    return (
      <div className="space-y-4">
        <BackLink />
        <div className="text-text-muted text-sm py-12 text-center border border-dashed border-ink-border rounded-lg">
          Entri ini belum ditautkan ke Dataset — tidak ada data untuk ditest. Kembali ke
          Laboratorium dan edit entrinya untuk memilih dataset.
        </div>
      </div>
    )
  }

  async function handlePromote() {
    if (
      !window.confirm(
        `Promosikan "${entry.name}" jadi Project resmi di Proyek > 01 Laboratorium?`
      )
    ) {
      return
    }
    await api.promoteLabEntry(entry.id)
    navigate('/proyek')
  }

  return (
    <div className="space-y-4">
      <BackLink />

      <LabHero entry={entry} />

      <div className="flex items-center justify-between px-0.5">
        <h2 className="font-display text-xs tracking-wider text-text-muted uppercase">
          Pipeline Laboratorium
        </h2>
        <button className="flex items-center gap-1.5 text-[11px] text-text-muted border border-ink-border rounded-md px-2.5 py-1 hover:text-accent hover:border-accent/40 transition-colors">
          <TipsIcon size={12} />
          Tips
        </button>
      </div>

      <div>
        <StepAmbilData datasetId={entry.dataset_id} isLast={false} />
        <StepBersihkan datasetId={entry.dataset_id} isLast={false} />
        <StepValidasi datasetId={entry.dataset_id} isLast={false} />
        <StepAnalisis datasetId={entry.dataset_id} isLast={false} />
        <StepComingSoon
          number={5}
          icon={Lightbulb}
          color={STEP_COLORS.insight}
          title="Insight"
          description="Temukan insight penting dari hasil analisis secara otomatis"
          note="Butuh integrasi AI/LLM untuk membaca data & menulis kesimpulan — belum dibangun di Talatee."
          isLast={false}
        />
        <StepDashboard datasetId={entry.dataset_id} isLast={false} />
        <StepComingSoon
          number={7}
          icon={SendHorizontal}
          color={STEP_COLORS.wa}
          title="Kirim ke WA"
          description="Kirim laporan / insight / link dashboard langsung ke WhatsApp"
          note="Buku Kas Warung sudah punya bot WA sendiri (WAHA/n8n), tapi Talatee belum tersambung ke WhatsApp sama sekali."
          isLast
        />
      </div>

      <button
        onClick={handlePromote}
        className="w-full flex items-center justify-center gap-2 bg-accent text-ink font-medium text-sm rounded-md py-2.5 glow-accent-sm hover:bg-accent-soft transition-colors"
      >
        <ArrowUpCircle size={15} />
        Data Sudah Benar — Pindahkan ke Proyek Siap Publikasi
      </button>
    </div>
  )
}

function BackLink() {
  return (
    <Link to="/laboratorium" className="text-xs text-text-muted hover:text-accent">
      &larr; Talatee Laboratorium
    </Link>
  )
}

/* ---------- Hero header ala mockup ---------- */

function LabHero({ entry }) {
  return (
    <div className="bg-ink-surface border border-ink-border rounded-xl px-5 py-5">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-accent/15 text-accent flex items-center justify-center shrink-0">
          <FlaskConical size={20} strokeWidth={1.75} />
        </div>
        <div className="min-w-0">
          <h1 className="font-display text-lg text-text-primary tracking-wide">
            LABORATORIUM
          </h1>
          <div className="text-accent text-xs font-display mt-0.5">
            {entry.name}
          </div>
          <p className="text-text-muted text-xs mt-2 leading-relaxed">
            Bangun, uji, dan pahami data{' '}
            {entry.dataset_name ? (
              <>
                dari <span className="text-text-primary">{entry.dataset_name}</span>
              </>
            ) : null}{' '}
            sampai benar-benar akurat sebelum dipindahkan ke tahap{' '}
            <span className="text-warning">Siap Digunakan</span>.
          </p>
        </div>
      </div>
    </div>
  )
}

/* ---------- Step shell ala mockup: badge + ikon, tombol JALANKAN, metrik, Detail ---------- */

function StepShell({
  number,
  icon: Icon,
  title,
  description,
  color,
  status,
  runLabel = 'JALANKAN',
  onRun,
  running,
  disabled,
  metrics,
  detail,
  isLast,
}) {
  const [detailOpen, setDetailOpen] = useState(false)

  return (
    <div>
      <div className="bg-ink-surface border border-ink-border rounded-xl px-4 py-4 sm:px-5 sm:py-4">
        <div className="flex items-start gap-3">
          <span
            className="w-6 h-6 rounded-full flex items-center justify-center text-[11px] font-display font-bold shrink-0 mt-0.5"
            style={{ background: color, color: '#0a0d0a' }}
          >
            {number}
          </span>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3 flex-wrap sm:flex-nowrap">
              <div className="flex items-start gap-2.5 min-w-0">
                <div
                  className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: `${color}26`, color }}
                >
                  <Icon size={17} strokeWidth={1.75} />
                </div>
                <div className="min-w-0">
                  <h3 className="text-text-primary text-sm font-semibold leading-tight">
                    {title}
                  </h3>
                  <p className="text-text-muted text-xs mt-1 leading-snug">{description}</p>
                </div>
              </div>

              <button
                onClick={onRun}
                disabled={disabled || running}
                className="shrink-0 flex items-center gap-1.5 text-[11px] font-semibold rounded-md px-3 py-1.5 transition disabled:opacity-50 disabled:cursor-not-allowed hover:brightness-110"
                style={{ background: color, color: '#0a0d0a' }}
              >
                {running ? (
                  <Loader2 size={12} className="animate-spin" />
                ) : (
                  <Play size={10} fill="#0a0d0a" strokeWidth={0} />
                )}
                {running ? 'MEMPROSES…' : runLabel}
              </button>
            </div>

            <div className="mt-3.5 pt-3 border-t border-ink-border flex items-end justify-between gap-3 flex-wrap">
              <div className="flex-1 min-w-0">
                {status && <div className="mb-2">{status}</div>}
                {metrics && metrics.length > 0 ? (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-2.5">
                    {metrics.map(({ label, value, tone, link }) => (
                      <div key={label} className="min-w-0">
                        <div className="text-text-muted text-[10px] uppercase tracking-wide truncate">
                          {label}
                        </div>
                        {link ? (
                          <button
                            onClick={link.onClick}
                            className="text-sm font-display mt-0.5 hover:underline"
                            style={{ color }}
                          >
                            {value} &rarr;
                          </button>
                        ) : (
                          <div
                            className={`text-sm font-display mt-0.5 truncate ${
                              tone === 'danger'
                                ? 'text-danger'
                                : tone === 'warn'
                                ? 'text-warning'
                                : tone === 'accent'
                                ? 'text-accent'
                                : 'text-text-primary'
                            }`}
                          >
                            {value}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-text-muted text-xs">Belum dijalankan</div>
                )}
              </div>

              {detail && (
                <button
                  onClick={() => setDetailOpen((v) => !v)}
                  className="shrink-0 flex items-center gap-1.5 text-[11px] text-text-muted border border-ink-border rounded-md px-2.5 py-1.5 hover:text-text-primary hover:border-text-muted/60 transition-colors"
                >
                  <SquareArrowOutUpRight size={11} />
                  Detail
                </button>
              )}
            </div>

            {detail && detailOpen && <div className="mt-3">{detail}</div>}
          </div>
        </div>
      </div>

      {!isLast && (
        <div className="flex justify-center py-1">
          <ChevronDown size={16} className="text-ink-border" strokeWidth={2} />
        </div>
      )}
    </div>
  )
}

function StatusLine({ state, okLabel = 'Berhasil' }) {
  if (state === 'success') {
    return (
      <span className="flex items-center gap-1 text-[11px] text-success font-medium">
        <CircleCheckBig size={12} /> {okLabel}
      </span>
    )
  }
  if (state === 'error') {
    return (
      <span className="flex items-center gap-1 text-[11px] text-danger font-medium">
        <CircleX size={12} /> Ada Masalah
      </span>
    )
  }
  if (state === 'loading') {
    return (
      <span className="flex items-center gap-1 text-[11px] text-text-muted">
        <Loader2 size={12} className="animate-spin" /> Memproses…
      </span>
    )
  }
  return null
}

/* ---------- Step 1: Ambil Data (real — baca metadata dataset & batch) ---------- */

function StepAmbilData({ datasetId, isLast }) {
  const { data, loading, reload } = useFetch(() => api.getDataset(datasetId), [datasetId])
  const totalRecords = data ? data.batches.reduce((sum, b) => sum + (b.records_saved || 0), 0) : 0
  const lastBatch = data?.batches?.[0]

  return (
    <StepShell
      number={1}
      icon={CloudDownload}
      color={STEP_COLORS.ambil}
      title="Ambil Data"
      description="Ambil data dari berbagai sumber (upload CSV/Excel yang sudah masuk ke dataset ini)"
      onRun={reload}
      running={loading}
      runLabel="JALANKAN"
      status={<StatusLine state={data ? 'success' : loading ? 'loading' : 'idle'} />}
      metrics={
        data && [
          { label: 'Sumber', value: data.name },
          { label: 'Records', value: formatNumber(totalRecords) },
          { label: 'Terakhir', value: lastBatch ? formatDateTime(lastBatch.started_at) : '-' },
          { label: 'Status', value: 'Berhasil', tone: 'accent' },
        ]
      }
      detail={
        data && (
          <div className="text-text-muted text-xs bg-ink-elevated border border-ink-border rounded-md px-3 py-2 space-y-1">
            <div>Total batch upload: {formatNumber(data.batches.length)}</div>
            <div>Dataset ID: {data.id}</div>
          </div>
        )
      }
      isLast={isLast}
    />
  )
}

/* ---------- Step 2: Bersihkan Data (real — POST /datasets/{id}/process) ---------- */

function StepBersihkan({ datasetId, isLast }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function run() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.processDataset(datasetId)
      setResult(res)
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <StepShell
      number={2}
      icon={Brush}
      color={STEP_COLORS.bersihkan}
      title="Bersihkan Data"
      description="Hapus duplikat, kosong, format tidak valid, standardisasi data"
      onRun={run}
      running={loading}
      status={
        <>
          {error && <div className="text-danger text-[11px] mb-1">{error}</div>}
          <StatusLine state={loading ? 'loading' : error ? 'error' : result ? 'success' : 'idle'} />
        </>
      }
      metrics={
        result && [
          { label: 'Input', value: formatNumber(result.rows_total) },
          { label: 'Output Clean', value: formatNumber(result.rows_written) },
          {
            label: 'Duplikat',
            value: formatNumber(result.duplicate_count),
            tone: result.duplicate_count > 0 ? 'warn' : undefined,
          },
          {
            label: 'Invalid',
            value: formatNumber(result.invalid_count),
            tone: result.invalid_count > 0 ? 'danger' : undefined,
          },
        ]
      }
      detail={
        result && (
          <div className="text-text-muted text-xs bg-ink-elevated border border-ink-border rounded-md px-3 py-2">
            {formatNumber(result.rows_written)} dari {formatNumber(result.rows_total)} baris lolos
            proses pembersihan ({formatNumber(result.duplicate_count)} duplikat,{' '}
            {formatNumber(result.invalid_count)} invalid dibuang).
          </div>
        )
      }
      isLast={isLast}
    />
  )
}

/* ---------- Step 3: Validasi (real — GET /datasets/{id}/quality) ---------- */

function StepValidasi({ datasetId, isLast }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function run() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getDatasetQuality(datasetId)
      setResult(res)
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  const hasErrors = result?.errors?.length > 0
  const hasWarnings = result?.warnings?.length > 0

  return (
    <StepShell
      number={3}
      icon={ShieldCheck}
      color={STEP_COLORS.validasi}
      title="Validasi"
      description="Cek struktur, tipe data, range, relasi, dan business rules"
      onRun={run}
      running={loading}
      status={
        <>
          {error && <div className="text-danger text-[11px] mb-1">{error}</div>}
          {result && !result.processed && (
            <div className="text-text-muted text-[11px]">
              Belum ada data untuk divalidasi — jalankan step 2 (Bersihkan Data) dulu.
            </div>
          )}
          <StatusLine
            state={loading ? 'loading' : hasErrors ? 'error' : result?.processed ? 'success' : 'idle'}
          />
        </>
      }
      metrics={
        result?.processed && [
          {
            label: 'Data Quality Score',
            value: `${result.quality_score}%`,
            tone: result.quality_score < 70 ? 'danger' : result.quality_score < 90 ? 'warn' : 'accent',
          },
          {
            label: 'Masalah Ditemukan',
            value: formatNumber(result.errors.length + result.warnings.length),
            tone: hasErrors ? 'danger' : hasWarnings ? 'warn' : undefined,
          },
          {
            label: 'Warning',
            value: formatNumber(result.warnings.length),
            tone: hasWarnings ? 'warn' : undefined,
          },
          {
            label: 'Error',
            value: formatNumber(result.errors.length),
            tone: hasErrors ? 'danger' : undefined,
          },
        ]
      }
      detail={
        result?.processed &&
        (hasWarnings || hasErrors) && (
          <ul className="text-xs bg-ink-elevated border border-ink-border rounded-md px-3 py-2 space-y-1">
            {result.errors.map((m, i) => (
              <li key={`e${i}`} className="text-danger">
                &bull; {m}
              </li>
            ))}
            {result.warnings.map((m, i) => (
              <li key={`w${i}`} className="text-warning">
                &bull; {m}
              </li>
            ))}
          </ul>
        )
      }
      isLast={isLast}
    />
  )
}

/* ---------- Step 4: Analisis (real — GET /datasets/{id}/insights) ---------- */

function StepAnalisis({ datasetId, isLast }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function run() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getInsights(datasetId)
      setResult(res)
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <StepShell
      number={4}
      icon={TrendingUp}
      color={STEP_COLORS.analisis}
      title="Analisis"
      description="Hitung metrik, statistik, tren, segmentasi, korelasi"
      onRun={run}
      running={loading}
      status={
        <>
          {error && <div className="text-danger text-[11px] mb-1">{error}</div>}
          {result && !result.processed && (
            <div className="text-text-muted text-[11px]">
              Belum ada data untuk dianalisis — jalankan step 2 (Bersihkan Data) dulu.
            </div>
          )}
          <StatusLine state={loading ? 'loading' : error ? 'error' : result?.processed ? 'success' : 'idle'} />
        </>
      }
      metrics={
        result?.processed && [
          { label: 'Metrik Dihitung', value: formatNumber(result.metrics_computed) },
          { label: 'Tabel Analisis', value: formatNumber(result.tables_computed) },
          { label: 'Waktu Proses', value: `${result.processing_seconds} detik` },
          { label: 'Total Baris', value: formatNumber(result.total_rows) },
        ]
      }
      isLast={isLast}
    />
  )
}

/* ---------- Step 6: Dashboard (real — reuse insights, render chart) ---------- */

function StepDashboard({ datasetId, isLast }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [expanded, setExpanded] = useState(false)

  async function run() {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getInsights(datasetId)
      setResult(res)
      setExpanded(true)
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  const componentCount = result
    ? (result.revenue_by_month.length > 0 ? 1 : 0) +
      (result.top_products.length > 0 ? 1 : 0) +
      (result.status_breakdown.length > 0 ? 1 : 0)
    : 0

  return (
    <StepShell
      number={6}
      icon={LayoutDashboard}
      color={STEP_COLORS.dashboard}
      title="Dashboard"
      description="Visualisasikan data dalam dashboard interaktif"
      onRun={run}
      running={loading}
      status={
        <>
          {error && <div className="text-danger text-[11px] mb-1">{error}</div>}
          {result && !result.processed && (
            <div className="text-text-muted text-[11px]">
              Belum ada data untuk divisualisasikan — jalankan step 2 (Bersihkan Data) dulu.
            </div>
          )}
          <StatusLine state={loading ? 'loading' : error ? 'error' : result?.processed ? 'success' : 'idle'} />
        </>
      }
      metrics={
        result?.processed && [
          { label: 'Dashboard Dibuat', value: '1' },
          { label: 'Komponen', value: formatNumber(componentCount) },
          {
            label: 'Lihat Dashboard',
            value: 'Buka',
            link: { onClick: () => setExpanded((v) => !v) },
          },
        ]
      }
      detail={
        expanded &&
        result?.revenue_by_month?.length > 0 && (
          <div className="h-40 bg-ink-elevated border border-ink-border rounded-md p-2">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={result.revenue_by_month}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-ink-border)" />
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }} />
                <YAxis
                  tick={{ fontSize: 10, fill: 'var(--color-text-muted)' }}
                  tickFormatter={(v) => formatCurrency(v).replace('Rp', '').trim()}
                  width={60}
                />
                <Tooltip
                  formatter={(v) => formatCurrency(v)}
                  contentStyle={{
                    background: 'var(--color-ink-elevated)',
                    border: '1px solid var(--color-ink-border)',
                    borderRadius: 6,
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="revenue" fill={STEP_COLORS.dashboard} radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )
      }
      isLast={isLast}
    />
  )
}

/* ---------- Step placeholder (jujur "Segera hadir") ---------- */

function StepComingSoon({ number, icon: Icon, color, title, description, note, isLast }) {
  return (
    <StepShell
      number={number}
      icon={Icon}
      color={color}
      title={title}
      description={description}
      onRun={undefined}
      disabled
      runLabel="SEGERA"
      status={<span className="text-[11px] text-text-muted">Segera hadir</span>}
      detail={<div className="text-text-muted text-xs bg-ink-elevated border border-ink-border rounded-md px-3 py-2">{note}</div>}
      isLast={isLast}
    />
  )
}