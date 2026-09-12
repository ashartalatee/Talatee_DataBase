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
  ShieldAlert,
  ShieldQuestion,
  ScrollText,
  Scale,
  X,
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
  const [trustRefreshKey, setTrustRefreshKey] = useState(0)
  const bumpTrust = () => setTrustRefreshKey((k) => k + 1)

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

      <DatasetTrustBadge datasetId={entry.dataset_id} refreshKey={trustRefreshKey} />

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
        <StepValidasi datasetId={entry.dataset_id} isLast={false} onTrustChanged={bumpTrust} />
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

      <DataTrustPanel datasetId={entry.dataset_id} />

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

/* ---------- Trust status badge — ringkasan Data Trust Spec section 7/12:
   status ini TERPISAH dari "step berhasil/belum", dan TRUSTED cuma bisa
   dicapai lewat promote eksplisit di Step 3, tidak pernah otomatis. ---------- */

const TRUST_META = {
  INGESTED: {
    label: 'INGESTED',
    desc: 'Data masuk, belum divalidasi',
    cls: 'text-text-muted border-ink-border',
    icon: ShieldQuestion,
  },
  VALIDATING: {
    label: 'VALIDATING',
    desc: 'Lolos quality check, belum di-promote',
    cls: 'text-warning border-warning/40',
    icon: ShieldAlert,
  },
  NEEDS_REVIEW: {
    label: 'NEEDS REVIEW',
    desc: 'Ada error — perlu ditinjau sebelum dipercaya',
    cls: 'text-danger border-danger/40',
    icon: ShieldAlert,
  },
  TRUSTED: {
    label: 'TRUSTED',
    desc: 'Sudah di-promote, aman untuk Analisis',
    cls: 'text-success border-success/40',
    icon: ShieldCheck,
  },
}

function TrustPill({ status }) {
  const cfg = TRUST_META[status] || TRUST_META.INGESTED
  const Icon = cfg.icon
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wide border rounded-full px-2 py-0.5 shrink-0 ${cfg.cls}`}
    >
      <Icon size={10} /> {cfg.label}
    </span>
  )
}

function DatasetTrustBadge({ datasetId, refreshKey }) {
  const { data } = useFetch(() => api.getDataset(datasetId), [datasetId, refreshKey])
  if (!data) return null
  const cfg = TRUST_META[data.trust_status] || TRUST_META.INGESTED
  return (
    <div className="bg-ink-surface border border-ink-border rounded-xl px-4 py-2.5 flex items-center justify-between gap-3 flex-wrap">
      <span className="text-text-muted text-[11px]">Status kepercayaan data saat ini</span>
      <div className="flex items-center gap-2">
        <TrustPill status={data.trust_status} />
        <span className="text-text-muted text-[11px]">{cfg.desc}</span>
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

function StepValidasi({ datasetId, isLast, onTrustChanged }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [promoting, setPromoting] = useState(false)
  const [promoteError, setPromoteError] = useState(null)
  const [correctingOrderId, setCorrectingOrderId] = useState(null)
  const [correctionValue, setCorrectionValue] = useState('')
  const [correctionReason, setCorrectionReason] = useState('')
  const [correctionSaving, setCorrectionSaving] = useState(false)
  const [correctionMsg, setCorrectionMsg] = useState(null)

  async function run() {
    setLoading(true)
    setError(null)
    setPromoteError(null)
    try {
      const res = await api.getDatasetQuality(datasetId)
      setResult(res)
      onTrustChanged?.()
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  async function promote() {
    setPromoting(true)
    setPromoteError(null)
    try {
      const res = await api.promoteDataset(datasetId)
      setResult((prev) => (prev ? { ...prev, trust_status: res.trust_status } : prev))
      onTrustChanged?.()
    } catch (err) {
      setPromoteError(err.message || String(err))
    } finally {
      setPromoting(false)
    }
  }

  async function submitCorrection(orderId) {
    if (!correctionValue.trim() || !correctionReason.trim()) return
    setCorrectionSaving(true)
    setCorrectionMsg(null)
    try {
      await api.createCorrection(datasetId, {
        order_id: orderId,
        field_name: 'subtotal',
        corrected_value: correctionValue.trim(),
        reason: correctionReason.trim(),
      })
      setCorrectionMsg({
        type: 'success',
        text: 'Correction tersimpan. Jalankan ulang Bersihkan Data (Step 2) supaya nilai barunya dipakai.',
      })
      setCorrectingOrderId(null)
      setCorrectionValue('')
      setCorrectionReason('')
    } catch (err) {
      setCorrectionMsg({ type: 'error', text: err.message || String(err) })
    } finally {
      setCorrectionSaving(false)
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

          {result?.processed && (
            <div className="mt-2 flex items-center gap-2 flex-wrap">
              <TrustPill status={result.trust_status} />

              {result.trust_status === 'VALIDATING' && (
                <button
                  onClick={promote}
                  disabled={promoting}
                  className="flex items-center gap-1 text-[11px] font-semibold text-ink bg-success rounded-md px-2.5 py-1 hover:brightness-110 disabled:opacity-50 transition"
                >
                  {promoting ? (
                    <Loader2 size={11} className="animate-spin" />
                  ) : (
                    <ShieldCheck size={11} />
                  )}
                  {promoting ? 'Mempromosikan…' : 'Promote ke TRUSTED'}
                </button>
              )}

              {result.trust_status === 'NEEDS_REVIEW' && (
                <span className="text-[11px] text-warning">
                  Perbaiki error di bawah dulu sebelum bisa di-promote.
                </span>
              )}

              {result.trust_status === 'TRUSTED' && (
                <span className="text-[11px] text-success">
                  Data ini boleh dipakai di step Analisis.
                </span>
              )}
            </div>
          )}
          {promoteError && <div className="text-danger text-[11px] mt-1">{promoteError}</div>}
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
          <div className="space-y-2">
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

            {result.subtotal_mismatch_examples?.length > 0 && (
              <div className="text-xs bg-ink-elevated border border-danger/30 rounded-md px-3 py-2">
                <div className="text-text-muted mb-1">
                  Contoh baris subtotal tidak cocok (qty &times; harga_satuan &ne; subtotal):
                </div>
                <ul className="space-y-1.5">
                  {result.subtotal_mismatch_examples.map((ex, i) => (
                    <li key={i}>
                      <div className="flex items-center justify-between gap-2 font-mono text-[11px] text-danger">
                        <span>
                          {ex.order_id ? `${ex.order_id}: ` : ''}
                          {ex.qty} &times; {ex.unit_price} = {ex.expected_subtotal} (tertulis: {ex.subtotal})
                        </span>
                        {ex.order_id && (
                          <button
                            onClick={() => {
                              setCorrectingOrderId(ex.order_id)
                              setCorrectionValue(ex.expected_subtotal)
                              setCorrectionMsg(null)
                            }}
                            className="shrink-0 text-[10px] font-sans font-semibold text-accent border border-accent/40 rounded px-2 py-0.5 hover:bg-accent/10 transition"
                          >
                            Perbaiki
                          </button>
                        )}
                      </div>

                      {correctingOrderId === ex.order_id && (
                        <div className="mt-1.5 bg-ink-surface border border-ink-border rounded-md p-2 space-y-1.5">
                          <label className="block text-[10px] text-text-muted font-sans">
                            Nilai subtotal yang benar
                            <input
                              type="text"
                              value={correctionValue}
                              onChange={(e) => setCorrectionValue(e.target.value)}
                              className="mt-0.5 w-full bg-ink-elevated border border-ink-border rounded px-2 py-1 text-xs text-text-primary font-mono"
                            />
                          </label>
                          <label className="block text-[10px] text-text-muted font-sans">
                            Alasan koreksi
                            <input
                              type="text"
                              value={correctionReason}
                              onChange={(e) => setCorrectionReason(e.target.value)}
                              placeholder="mis. Harga salah input di sumber"
                              className="mt-0.5 w-full bg-ink-elevated border border-ink-border rounded px-2 py-1 text-xs text-text-primary font-sans"
                            />
                          </label>
                          <div className="flex items-center gap-2 pt-0.5">
                            <button
                              onClick={() => submitCorrection(ex.order_id)}
                              disabled={correctionSaving}
                              className="text-[11px] font-semibold text-ink bg-accent rounded px-2.5 py-1 hover:brightness-110 disabled:opacity-50 font-sans"
                            >
                              {correctionSaving ? 'Menyimpan…' : 'Simpan Koreksi'}
                            </button>
                            <button
                              onClick={() => setCorrectingOrderId(null)}
                              className="text-[11px] text-text-muted hover:text-text-primary font-sans"
                            >
                              Batal
                            </button>
                          </div>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
                {correctionMsg && (
                  <div
                    className={`mt-2 font-sans text-[11px] ${correctionMsg.type === 'success' ? 'text-success' : 'text-danger'}`}
                  >
                    {correctionMsg.text}
                  </div>
                )}
              </div>
            )}
          </div>
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
          {result && result.blocked && (
            <div className="text-warning text-[11px] flex items-center gap-1">
              <ShieldAlert size={11} /> {result.reason}
            </div>
          )}
          {result && !result.processed && !result.blocked && (
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
          {result && result.blocked && (
            <div className="text-warning text-[11px] flex items-center gap-1">
              <ShieldAlert size={11} /> {result.reason}
            </div>
          )}
          {result && !result.processed && !result.blocked && (
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

/* ---------- Data Passport + Reconciliation — spec section 6 & 16 ----------
   Sengaja DILUAR daftar 7-step pipeline: keduanya bukan step yang "dijalankan
   sekali lalu selesai", tapi alat yang dibuka kapan saja untuk mengaudit
   dataset (Passport) atau mengecek kecocokan dengan angka dari luar
   (Reconciliation). Bentuknya 2 kartu collapsible berdampingan. ---------- */

function DataTrustPanel({ datasetId }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      <DataPassportCard datasetId={datasetId} />
      <ReconciliationCard datasetId={datasetId} />
    </div>
  )
}

function DataPassportCard({ datasetId }) {
  const [open, setOpen] = useState(false)
  const [passport, setPassport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function load() {
    setOpen(true)
    setLoading(true)
    setError(null)
    try {
      const res = await api.getDataPassport(datasetId)
      setPassport(res)
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-ink-surface border border-ink-border rounded-xl p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ScrollText size={15} className="text-accent" />
          <h3 className="text-sm font-semibold text-text-primary">Data Passport</h3>
        </div>
        {!open ? (
          <button
            onClick={load}
            className="text-[11px] text-accent border border-accent/40 rounded-md px-2.5 py-1 hover:bg-accent/10 transition"
          >
            Buka
          </button>
        ) : (
          <button onClick={() => setOpen(false)} className="text-text-muted hover:text-text-primary">
            <X size={14} />
          </button>
        )}
      </div>
      <p className="text-[11px] text-text-muted mt-1">
        Dari mana data ini, sudah divalidasi apa belum, dan apa yang pernah dikoreksi — dalam 1 tempat.
      </p>

      {open && (
        <div className="mt-3 space-y-2 text-xs">
          {loading && <div className="text-text-muted">Memuat…</div>}
          {error && <div className="text-danger">{error}</div>}
          {passport && (
            <>
              <PassportRow label="Trust Status">
                <TrustPill status={passport.dataset.trust_status} />
              </PassportRow>
              <PassportRow label="Sumber data">
                {passport.provenance.total_batches} batch upload, {formatNumber(passport.provenance.total_raw_records)} baris mentah
              </PassportRow>
              <PassportRow label="File asli">
                <ul className="space-y-0.5">
                  {passport.provenance.sources.map((s) => (
                    <li key={s.batch_id} className="font-mono text-[10px] text-text-muted truncate">
                      {s.filename || '(tanpa file)'} — {s.uploaded_at ? new Date(s.uploaded_at).toLocaleDateString('id-ID') : '?'}
                    </li>
                  ))}
                </ul>
              </PassportRow>
              <PassportRow label="Baris di Core saat ini">
                {formatNumber(passport.current_state.total_records_in_core)}
              </PassportRow>
              <PassportRow label="Data Quality Score">
                {passport.current_state.quality_score != null ? `${passport.current_state.quality_score}%` : '—'}
              </PassportRow>
              <PassportRow label="Koreksi manual (sepanjang waktu)">
                {formatNumber(passport.corrections.total_applied_ever)}
              </PassportRow>
              <PassportRow label="Reconciliation terakhir">
                {passport.reconciliation ? (
                  <span className={passport.reconciliation.status === 'PASSED' ? 'text-success' : 'text-danger'}>
                    {passport.reconciliation.period_label}: {passport.reconciliation.status} (selisih {passport.reconciliation.difference})
                  </span>
                ) : (
                  'Belum pernah dicek'
                )}
              </PassportRow>
            </>
          )}
        </div>
      )}
    </div>
  )
}

function PassportRow({ label, children }) {
  return (
    <div className="flex items-start justify-between gap-3 border-b border-ink-border/50 pb-1.5 last:border-0">
      <span className="text-text-muted shrink-0">{label}</span>
      <span className="text-text-primary text-right">{children}</span>
    </div>
  )
}

function ReconciliationCard({ datasetId }) {
  const [open, setOpen] = useState(false)
  const [period, setPeriod] = useState('')
  const [sourceTotal, setSourceTotal] = useState('')
  const [notes, setNotes] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [history, setHistory] = useState(null)

  async function loadHistory() {
    try {
      const res = await api.listReconciliations(datasetId)
      setHistory(res)
    } catch {
      // riwayat gagal dimuat bukan blocker, biarkan silent di panel kecil ini
    }
  }

  async function submit() {
    if (!period.trim() || !sourceTotal.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      await api.runReconciliation(datasetId, {
        period_label: period.trim(),
        source_total: sourceTotal.trim(),
        notes: notes.trim() || undefined,
      })
      setSourceTotal('')
      setNotes('')
      await loadHistory()
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-ink-surface border border-ink-border rounded-xl p-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Scale size={15} className="text-accent" />
          <h3 className="text-sm font-semibold text-text-primary">Reconciliation</h3>
        </div>
        {!open ? (
          <button
            onClick={() => {
              setOpen(true)
              loadHistory()
            }}
            className="text-[11px] text-accent border border-accent/40 rounded-md px-2.5 py-1 hover:bg-accent/10 transition"
          >
            Buka
          </button>
        ) : (
          <button onClick={() => setOpen(false)} className="text-text-muted hover:text-text-primary">
            <X size={14} />
          </button>
        )}
      </div>
      <p className="text-[11px] text-text-muted mt-1">
        Banding total revenue dari sumber luar (mis. dashboard marketplace asli) vs hasil hitung Talatee.
      </p>

      {open && (
        <div className="mt-3 space-y-2 text-xs">
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="2026-01"
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
              className="w-24 bg-ink-elevated border border-ink-border rounded px-2 py-1 text-xs font-mono"
            />
            <input
              type="text"
              placeholder="Total dari sumber luar"
              value={sourceTotal}
              onChange={(e) => setSourceTotal(e.target.value)}
              className="flex-1 bg-ink-elevated border border-ink-border rounded px-2 py-1 text-xs"
            />
          </div>
          <input
            type="text"
            placeholder="Catatan (opsional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full bg-ink-elevated border border-ink-border rounded px-2 py-1 text-xs"
          />
          <button
            onClick={submit}
            disabled={submitting}
            className="text-[11px] font-semibold text-ink bg-accent rounded px-2.5 py-1 hover:brightness-110 disabled:opacity-50"
          >
            {submitting ? 'Mengecek…' : 'Cek Reconciliation'}
          </button>
          {error && <div className="text-danger">{error}</div>}

          {history?.length > 0 && (
            <ul className="mt-2 space-y-1 border-t border-ink-border pt-2">
              {history.map((h) => (
                <li key={h.id} className="flex items-center justify-between font-mono text-[10px]">
                  <span className="text-text-muted">{h.period_label}</span>
                  <span className={h.status === 'PASSED' ? 'text-success' : 'text-danger'}>
                    {h.status} (selisih {h.difference})
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}