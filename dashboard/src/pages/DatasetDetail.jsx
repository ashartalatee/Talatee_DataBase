import { useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { UploadCloud, FileText, X, CheckCircle2, XCircle, Sparkles, TrendingUp, TrendingDown } from 'lucide-react'
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
import { LoadingState, ErrorState, EmptyState } from '../components/States'
import StatusBadge from '../components/StatusBadge'
import { formatDateTime, formatNumber, formatCurrency } from '../lib/format'

const ACCEPTED_EXTENSIONS = ['.csv', '.xlsx']

export default function DatasetDetail() {
  const { id } = useParams()
  const { data, loading, error, reload } = useFetch(() => api.getDataset(id), [id])

  if (loading) return <LoadingState label="Memuat dataset" />
  if (error) return <ErrorState message={error} />

  const columns = data.schema?.columns || []

  return (
    <div className="space-y-6">
      <div>
        <Link to="/datasets" className="text-xs text-text-muted hover:text-accent">
          &larr; Datasets
        </Link>
        <h1 className="font-display text-xl text-text-primary mt-1">{data.name}</h1>
        <p className="text-text-muted text-sm mt-1">
          {data.description || 'Tidak ada deskripsi'} &middot; dibuat{' '}
          {formatDateTime(data.created_at)}
        </p>
      </div>

      <AddBatchCard
        businessName={data.business_name}
        sourceName={data.source_name}
        datasetName={data.name}
        onUploaded={reload}
      />

      <InsightsPanel datasetId={id} />

      {columns.length > 0 && (
        <div className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4">
          <h2 className="text-sm font-medium text-text-primary mb-3">
            Schema <span className="text-text-muted font-normal">(dari batch terakhir)</span>
          </h2>
          <div className="flex flex-wrap gap-2">
            {columns.map((c) => (
              <span
                key={c}
                className="font-display text-xs px-2.5 py-1 rounded border border-ink-border text-text-muted bg-ink-elevated"
              >
                {c}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="bg-ink-surface border border-ink-border rounded-lg">
        <div className="px-5 py-4 border-b border-ink-border">
          <h2 className="text-sm font-medium text-text-primary">
            Riwayat Batch <span className="text-text-muted font-normal">({data.batches.length})</span>
          </h2>
        </div>
        {data.batches.length === 0 ? (
          <EmptyState label="Belum ada batch untuk dataset ini." />
        ) : (
          <ul className="divide-y divide-ink-border">
            {data.batches.map((b) => (
              <li key={b.id} className="px-5 py-3 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <Link
                    to={`/jobs/${b.id}`}
                    className="font-display text-xs text-text-primary hover:text-accent truncate block"
                  >
                    {b.id}
                  </Link>
                  <div className="text-text-muted text-xs mt-0.5 font-display">
                    {formatDateTime(b.started_at)}
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <StatusBadge status={b.status} />
                  <div className="text-xs text-text-muted mt-0.5 font-display">
                    {formatNumber(b.records_saved)} records
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

/**
 * Upload batch baru langsung ke dataset ini. Business/Source/Dataset name
 * TIDAK bisa diketik ulang (dikunci dari data dataset yang sedang dibuka) —
 * ini yang mencegah data "tercecer" jadi dataset terpisah gara-gara typo
 * nama saat upload bulan/minggu berikutnya. Kalau perlu bikin dataset BARU,
 * tetap pakai halaman Upload umum di sidebar.
 */
function AddBatchCard({ businessName, sourceName, datasetName, onUploaded }) {
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const fileInputRef = useRef(null)

  const isValidExtension = (f) =>
    f && ACCEPTED_EXTENSIONS.some((ext) => f.name.toLowerCase().endsWith(ext))

  function handleFileChosen(f) {
    setResult(null)
    setError(null)
    if (!isValidExtension(f)) {
      setError(`File "${f.name}" bukan .csv atau .xlsx. Pilih file lain.`)
      setFile(null)
      return
    }
    setFile(f)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files?.[0]
    if (f) handleFileChosen(f)
  }

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setError(null)
    setResult(null)
    try {
      // businessCategory diabaikan backend kalau business sudah ada (selalu
      // ada di titik ini, karena kita datang dari dataset yang sudah eksis).
      const batch = await api.uploadFile(businessName, 'lainnya', sourceName, datasetName, file)
      setResult(batch)
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      onUploaded?.()
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4 space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-text-primary">Upload Batch Baru</h2>
        <span className="text-text-muted text-xs font-display">
          {businessName} &rsaquo; {sourceName} &rsaquo; {datasetName}
        </span>
      </div>
      <p className="text-text-muted text-xs -mt-1">
        Otomatis masuk ke dataset ini juga — nama business/source/dataset tidak perlu diketik
        ulang, jadi tidak mungkin salah ketik dan bikin data terpecah.
      </p>

      {result ? (
        <div className="flex items-center gap-3 bg-ink-elevated border border-ink-border rounded-md px-4 py-3">
          {result.status === 'success' ? (
            <CheckCircle2 size={18} className="text-success shrink-0" strokeWidth={1.75} />
          ) : (
            <XCircle size={18} className="text-danger shrink-0" strokeWidth={1.75} />
          )}
          <div className="min-w-0 flex-1">
            <div className="text-text-primary text-sm">
              {result.status === 'success'
                ? `Batch baru tersimpan — ${formatNumber(result.records_saved)} records`
                : 'Batch gagal — tetap tercatat'}
            </div>
            {result.error_message && (
              <div className="text-danger text-xs mt-0.5">{result.error_message}</div>
            )}
          </div>
          <Link
            to={`/jobs/${result.id}`}
            className="shrink-0 text-xs text-accent hover:underline whitespace-nowrap"
          >
            Lihat Detail
          </Link>
          <button
            onClick={() => setResult(null)}
            className="shrink-0 text-xs text-text-muted hover:text-text-primary whitespace-nowrap"
          >
            Upload Lagi
          </button>
        </div>
      ) : (
        <>
          <div
            onDragOver={(e) => {
              e.preventDefault()
              setDragOver(true)
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border border-dashed rounded-md px-4 py-5 text-center cursor-pointer transition-all ${
              dragOver
                ? 'glow-accent-sm border-accent bg-accent/5'
                : 'border-ink-border hover:border-text-muted'
            }`}
          >
            {file ? (
              <div className="flex items-center justify-center gap-2 text-sm text-text-primary">
                <FileText size={16} className="text-accent" strokeWidth={1.75} />
                {file.name}
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    setFile(null)
                    if (fileInputRef.current) fileInputRef.current.value = ''
                  }}
                  className="text-text-muted hover:text-danger"
                >
                  <X size={14} />
                </button>
              </div>
            ) : (
              <>
                <UploadCloud
                  size={18}
                  className="mx-auto text-text-muted mb-1.5"
                  strokeWidth={1.5}
                />
                <div className="text-sm text-text-muted">
                  Drag & drop file di sini, atau klik untuk pilih
                </div>
                <div className="text-xs text-text-muted/60 mt-1 font-display">.csv atau .xlsx</div>
              </>
            )}
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx"
              onChange={(e) => e.target.files?.[0] && handleFileChosen(e.target.files[0])}
              className="hidden"
            />
          </div>

          {error && (
            <div className="flex items-start gap-2 bg-danger/10 border border-danger/30 rounded-md px-3 py-2.5">
              <XCircle size={15} className="text-danger shrink-0 mt-0.5" strokeWidth={1.75} />
              <span className="text-sm text-text-primary">{error}</span>
            </div>
          )}

          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="glow-accent-sm w-full bg-accent text-ink font-medium text-sm rounded-md py-2 hover:bg-accent-soft transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          >
            {uploading ? 'Mengirim ke ledger…' : 'Upload ke Dataset Ini'}
          </button>
        </>
      )}
    </div>
  )
}

/**
 * Panel "Layer Core -> Insight". Menampilkan tombol Process Data (memicu
 * app/ingestion/core_processor.py lewat POST /datasets/{id}/process) dan,
 * setelah diproses, insight yang dihitung dari core_transactions: revenue +
 * growth per bulan, top produk, dan breakdown status transaksi.
 */
function InsightsPanel({ datasetId }) {
  const { data: insights, loading, error, reload } = useFetch(
    () => api.getInsights(datasetId),
    [datasetId]
  )
  const [processing, setProcessing] = useState(false)
  const [processError, setProcessError] = useState(null)

  async function handleProcess() {
    setProcessing(true)
    setProcessError(null)
    try {
      await api.processDataset(datasetId)
      await reload()
    } catch (err) {
      setProcessError(err.message || String(err))
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles size={16} className="text-accent" strokeWidth={1.75} />
          <h2 className="text-sm font-medium text-text-primary">Insight</h2>
        </div>
        <button
          onClick={handleProcess}
          disabled={processing}
          className="glow-accent-sm bg-accent text-ink font-medium text-xs rounded-md px-3 py-1.5 hover:bg-accent-soft transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
        >
          {processing ? 'Memproses…' : insights?.processed ? 'Process Ulang' : 'Process Data'}
        </button>
      </div>

      {processError && (
        <div className="flex items-start gap-2 bg-danger/10 border border-danger/30 rounded-md px-3 py-2.5">
          <XCircle size={15} className="text-danger shrink-0 mt-0.5" strokeWidth={1.75} />
          <span className="text-sm text-text-primary">{processError}</span>
        </div>
      )}

      {loading && !insights ? (
        <div className="text-text-muted text-sm">Memuat insight…</div>
      ) : error ? (
        <ErrorState message={error} />
      ) : !insights?.processed ? (
        <div className="text-text-muted text-sm">
          Belum pernah diproses. Klik <span className="text-text-primary">Process Data</span>{' '}
          untuk membaca semua batch di dataset ini dan menghitung revenue, growth, dan produk
          terlaris.
        </div>
      ) : (
        <div className="space-y-5">
          {insights.revenue_by_month.length > 0 && (
            <div>
              <h3 className="text-xs text-text-muted uppercase tracking-wider mb-2">
                Revenue per Bulan
              </h3>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={insights.revenue_by_month}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-ink-border)" />
                    <XAxis dataKey="month" tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }} />
                    <YAxis
                      tick={{ fontSize: 11, fill: 'var(--color-text-muted)' }}
                      tickFormatter={(v) => formatCurrency(v).replace('Rp', '').trim()}
                      width={70}
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
                    <Bar dataKey="revenue" fill="var(--color-accent)" radius={[3, 3, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <div className="grid grid-cols-3 gap-2 mt-3">
                {insights.revenue_by_month.map((m) => (
                  <div
                    key={m.month}
                    className="bg-ink-elevated border border-ink-border rounded-md px-3 py-2"
                  >
                    <div className="text-text-muted text-[11px] font-display">{m.month}</div>
                    <div className="text-text-primary text-sm font-medium mt-0.5">
                      {formatCurrency(m.revenue)}
                    </div>
                    <div className="flex items-center gap-1 mt-0.5">
                      {m.growth_pct == null ? (
                        <span className="text-text-muted text-[11px]">
                          {m.order_count} order
                        </span>
                      ) : (
                        <>
                          {m.growth_pct >= 0 ? (
                            <TrendingUp size={11} className="text-success" />
                          ) : (
                            <TrendingDown size={11} className="text-danger" />
                          )}
                          <span
                            className={`text-[11px] ${m.growth_pct >= 0 ? 'text-success' : 'text-danger'}`}
                          >
                            {m.growth_pct >= 0 ? '+' : ''}
                            {m.growth_pct}% vs bulan lalu
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {insights.top_products.length > 0 && (
            <div>
              <h3 className="text-xs text-text-muted uppercase tracking-wider mb-2">
                Top Produk (by Revenue)
              </h3>
              <ul className="divide-y divide-ink-border border border-ink-border rounded-md overflow-hidden">
                {insights.top_products.map((p, i) => (
                  <li
                    key={p.product_name}
                    className="flex items-center justify-between px-3 py-2 bg-ink-elevated"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-text-muted text-xs font-display w-4 shrink-0">
                        {i + 1}
                      </span>
                      <span className="text-text-primary text-sm truncate">{p.product_name}</span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-text-muted text-xs font-display">
                        {formatNumber(p.qty_sold)} terjual
                      </span>
                      <span className="text-text-primary text-sm font-display">
                        {formatCurrency(p.revenue)}
                      </span>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div>
            <h3 className="text-xs text-text-muted uppercase tracking-wider mb-2">
              Breakdown Status ({formatNumber(insights.total_rows)} baris)
            </h3>
            <div className="flex flex-wrap gap-2">
              {insights.status_breakdown.map((s) => (
                <span
                  key={s.status}
                  className="text-xs px-2.5 py-1 rounded border border-ink-border text-text-muted bg-ink-elevated font-display"
                >
                  {s.status}: {s.count}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
