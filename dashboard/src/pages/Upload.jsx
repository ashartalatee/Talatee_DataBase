import { useState, useRef } from 'react'
import { Link } from 'react-router-dom'
import { UploadCloud, FileText, X, CheckCircle2, XCircle } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import StatusBadge from '../components/StatusBadge'
import { formatNumber } from '../lib/format'

const ACCEPTED_EXTENSIONS = ['.csv', '.xlsx']

export default function Upload() {
  const { data: categories } = useFetch(() => api.listBusinessCategories(), [])

  const [businessName, setBusinessName] = useState('')
  const [businessCategory, setBusinessCategory] = useState('lainnya')
  const [sourceName, setSourceName] = useState('')
  const [datasetName, setDatasetName] = useState('')
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

  async function handleSubmit(e) {
    e.preventDefault()
    if (!file || !businessName.trim() || !sourceName.trim() || !datasetName.trim()) {
      setError('Isi Business Name, Source Name, Dataset Name, dan pilih file terlebih dulu.')
      return
    }
    setUploading(true)
    setError(null)
    setResult(null)
    try {
      const batch = await api.uploadFile(
        businessName.trim(),
        businessCategory,
        sourceName.trim(),
        datasetName.trim(),
        file
      )
      setResult(batch)
      setFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setUploading(false)
    }
  }

  function resetForm() {
    setResult(null)
    setError(null)
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="font-display text-xl text-text-primary">Upload</h1>
        <p className="text-text-muted text-sm mt-1">
          Ingest file CSV atau Excel langsung ke ledger. Setiap upload membuat batch baru — raw
          data tidak pernah ditimpa, walau kamu upload file yang sama persis dua kali.
        </p>
      </div>

      {result ? (
        <ResultCard batch={result} onUploadAnother={resetForm} />
      ) : (
        <form
          onSubmit={handleSubmit}
          className="bg-ink-surface border border-ink-border rounded-lg px-6 py-6 space-y-5"
        >
          <div className="grid grid-cols-3 gap-3">
            <div className="col-span-2">
              <label className="block text-xs text-text-muted uppercase tracking-wider mb-1.5">
                Business Name
              </label>
              <input
                type="text"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                placeholder="misal: Resto Padang Jaya"
                className="w-full bg-ink-elevated border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-accent"
              />
            </div>
            <div>
              <label className="block text-xs text-text-muted uppercase tracking-wider mb-1.5">
                Category
              </label>
              <select
                value={businessCategory}
                onChange={(e) => setBusinessCategory(e.target.value)}
                className="w-full bg-ink-elevated border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent capitalize"
              >
                {(categories || ['lainnya']).map((c) => (
                  <option key={c} value={c} className="capitalize">
                    {c}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <p className="text-text-muted text-xs -mt-3">
            Kalau belum pernah ada, business baru dibuat otomatis dengan kategori di atas. Kalau
            sudah ada (nama sama persis), kategori yang sudah tersimpan tetap dipakai — pilihan
            di atas diabaikan.
          </p>

          <div>
            <label className="block text-xs text-text-muted uppercase tracking-wider mb-1.5">
              Source Name
            </label>
            <input
              type="text"
              value={sourceName}
              onChange={(e) => setSourceName(e.target.value)}
              placeholder="misal: POS Kasir"
              className="w-full bg-ink-elevated border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-accent"
            />
            <p className="text-text-muted text-xs mt-1">
              Kalau belum pernah ada, source baru akan dibuat otomatis.
            </p>
          </div>

          <div>
            <label className="block text-xs text-text-muted uppercase tracking-wider mb-1.5">
              Dataset Name
            </label>
            <input
              type="text"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              placeholder="misal: Orders"
              className="w-full bg-ink-elevated border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-accent"
            />
          </div>

          <div>
            <label className="block text-xs text-text-muted uppercase tracking-wider mb-1.5">
              File
            </label>
            <div
              onDragOver={(e) => {
                e.preventDefault()
                setDragOver(true)
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border border-dashed rounded-md px-4 py-8 text-center cursor-pointer transition-all ${
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
                    size={22}
                    className="mx-auto text-text-muted mb-2"
                    strokeWidth={1.5}
                  />
                  <div className="text-sm text-text-muted">
                    Drag & drop file di sini, atau klik untuk pilih
                  </div>
                  <div className="text-xs text-text-muted/60 mt-1 font-display">
                    .csv atau .xlsx
                  </div>
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
          </div>

          {error && (
            <div className="flex items-start gap-2 bg-danger/10 border border-danger/30 rounded-md px-3 py-2.5">
              <XCircle size={15} className="text-danger shrink-0 mt-0.5" strokeWidth={1.75} />
              <span className="text-sm text-text-primary">{error}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={uploading}
            className="glow-accent-sm w-full bg-accent text-ink font-medium text-sm rounded-md py-2.5 hover:bg-accent-soft transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          >
            {uploading ? 'Mengirim ke ledger…' : 'Upload & Ingest'}
          </button>
        </form>
      )}
    </div>
  )
}

function ResultCard({ batch, onUploadAnother }) {
  const isSuccess = batch.status === 'success'
  return (
    <div className="bg-ink-surface border border-ink-border rounded-lg px-6 py-6 space-y-4">
      <div className="flex items-center gap-3">
        {isSuccess ? (
          <CheckCircle2 size={22} className="text-success" strokeWidth={1.75} />
        ) : (
          <XCircle size={22} className="text-danger" strokeWidth={1.75} />
        )}
        <div>
          <div className="text-text-primary text-sm font-medium">
            {isSuccess ? 'Batch berhasil dibuat' : 'Batch gagal — tetap tercatat'}
          </div>
          <StatusBadge status={batch.status} />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div className="bg-ink-elevated border border-ink-border rounded-md px-3 py-2">
          <div className="text-text-muted text-[11px] uppercase tracking-wider">
            Records Saved
          </div>
          <div className="font-display text-text-primary mt-0.5">
            {formatNumber(batch.records_saved)}
          </div>
        </div>
        <div className="bg-ink-elevated border border-ink-border rounded-md px-3 py-2">
          <div className="text-text-muted text-[11px] uppercase tracking-wider">Batch ID</div>
          <div className="font-display text-text-primary text-xs mt-1 truncate">{batch.id}</div>
        </div>
      </div>

      {batch.error_message && (
        <div className="bg-danger/10 border border-danger/30 rounded-md px-3 py-2.5 text-sm text-text-primary">
          {batch.error_message}
        </div>
      )}

      <div className="flex gap-3 pt-1">
        <Link
          to={`/jobs/${batch.id}`}
          className="flex-1 text-center bg-ink-elevated border border-ink-border text-text-primary text-sm rounded-md py-2 hover:border-accent/50 transition-colors"
        >
          Lihat Detail Job
        </Link>
        <button
          onClick={onUploadAnother}
          className="glow-accent-sm flex-1 bg-accent text-ink font-medium text-sm rounded-md py-2 hover:bg-accent-soft transition-colors"
        >
          Upload Lagi
        </button>
      </div>
    </div>
  )
}
