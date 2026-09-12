import { useState, useRef, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { UploadCloud, FileText, X, CheckCircle2, XCircle, Layers } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import StatusBadge from '../components/StatusBadge'
import { formatNumber } from '../lib/format'

const ACCEPTED_EXTENSIONS = ['.csv', '.xlsx']
const NEW_BUSINESS = '__new__'
const NEW_CHANNEL = '__new__'
const MIXED_CHANNEL = '__mixed__'

export default function Upload() {
  const { data: categories } = useFetch(() => api.listBusinessCategories(), [])
  const { data: businesses, loading: businessesLoading } = useFetch(() => api.listBusinesses(), [])

  const [businessId, setBusinessId] = useState('')
  const [newBusinessName, setNewBusinessName] = useState('')
  const [newBusinessCategory, setNewBusinessCategory] = useState('lainnya')

  const [sources, setSources] = useState([])
  const [sourcesLoading, setSourcesLoading] = useState(false)
  const [channelChoice, setChannelChoice] = useState('')
  const [newChannelName, setNewChannelName] = useState('')

  const [datasetName, setDatasetName] = useState('')
  const [file, setFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null) // single batch OR array of batches (mode campur)
  const fileInputRef = useRef(null)

  // Begitu business (yang SUDAH ADA) dipilih, ambil daftar channel/source
  // yang sudah pernah dipakai di business itu -- supaya user tinggal PILIH,
  // tidak ngetik ulang nama yang gampang typo/beda kapitalisasi.
  useEffect(() => {
    setChannelChoice('')
    setNewChannelName('')
    if (!businessId || businessId === NEW_BUSINESS) {
      setSources([])
      return
    }
    setSourcesLoading(true)
    api
      .getBusinessSources(businessId)
      .then((list) => setSources(list))
      .catch(() => setSources([]))
      .finally(() => setSourcesLoading(false))
  }, [businessId])

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

  const resolvedBusinessName =
    businessId === NEW_BUSINESS ? newBusinessName.trim() : businesses?.find((b) => b.id === businessId)?.name || ''
  const resolvedBusinessCategory = businessId === NEW_BUSINESS ? newBusinessCategory : 'lainnya'
  const resolvedChannelName = channelChoice === NEW_CHANNEL ? newChannelName.trim() : channelChoice
  const isMixedMode = channelChoice === MIXED_CHANNEL

  const canSubmit =
    file &&
    resolvedBusinessName &&
    datasetName.trim() &&
    (isMixedMode || resolvedChannelName)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit) {
      setError('Lengkapi Business, Channel, Dataset Name, dan pilih file terlebih dulu.')
      return
    }
    setUploading(true)
    setError(null)
    setResult(null)
    try {
      if (isMixedMode) {
        const batches = await api.uploadFileMixed(
          resolvedBusinessName,
          resolvedBusinessCategory,
          datasetName.trim(),
          file
        )
        setResult(batches)
      } else {
        const batch = await api.uploadFile(
          resolvedBusinessName,
          resolvedBusinessCategory,
          resolvedChannelName,
          datasetName.trim(),
          file
        )
        setResult(batch)
      }
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
        Array.isArray(result) ? (
          <MixedResultCard batches={result} onUploadAnother={resetForm} />
        ) : (
          <ResultCard batch={result} onUploadAnother={resetForm} />
        )
      ) : (
        <form
          onSubmit={handleSubmit}
          className="bg-ink-surface border border-ink-border rounded-lg px-6 py-6 space-y-5"
        >
          {/* Business — dropdown dari yang sudah ada, supaya tidak ada
              typo/variasi kapitalisasi yang bikin business kepecah jadi 2. */}
          <div>
            <label className="block text-xs text-text-muted uppercase tracking-wider mb-1.5">
              Business
            </label>
            <select
              value={businessId}
              onChange={(e) => setBusinessId(e.target.value)}
              className="w-full bg-ink-elevated border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent"
            >
              <option value="">{businessesLoading ? 'Memuat…' : '-- Pilih business --'}</option>
              {(businesses || []).map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
              <option value={NEW_BUSINESS}>+ Business baru…</option>
            </select>
          </div>

          {businessId === NEW_BUSINESS && (
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <label className="block text-xs text-text-muted uppercase tracking-wider mb-1.5">
                  Nama Business Baru
                </label>
                <input
                  type="text"
                  value={newBusinessName}
                  onChange={(e) => setNewBusinessName(e.target.value)}
                  placeholder="misal: Resto Padang Jaya"
                  className="w-full bg-ink-elevated border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-accent"
                />
              </div>
              <div>
                <label className="block text-xs text-text-muted uppercase tracking-wider mb-1.5">
                  Category
                </label>
                <select
                  value={newBusinessCategory}
                  onChange={(e) => setNewBusinessCategory(e.target.value)}
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
          )}

          {/* Channel data ini dari mana — dropdown dari channel yang sudah
              ada di business ini, "+ Channel baru", atau mode campur. */}
          {businessId && (
            <div>
              <label className="block text-xs text-text-muted uppercase tracking-wider mb-1.5">
                Channel data ini dari mana? *
              </label>
              <select
                value={channelChoice}
                onChange={(e) => setChannelChoice(e.target.value)}
                disabled={businessId !== NEW_BUSINESS && sourcesLoading}
                className="w-full bg-ink-elevated border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent"
              >
                <option value="">-- Pilih dulu --</option>
                {sources.map((s) => (
                  <option key={s.id} value={s.name}>
                    {s.name}
                  </option>
                ))}
                <option value={NEW_CHANNEL}>+ Channel baru…</option>
                <option value={MIXED_CHANNEL}>File ini campur beberapa channel (pakai kolom "channel" di file)</option>
              </select>

              {channelChoice === NEW_CHANNEL && (
                <input
                  type="text"
                  value={newChannelName}
                  onChange={(e) => setNewChannelName(e.target.value)}
                  placeholder="misal: Shopee"
                  className="mt-2 w-full bg-ink-elevated border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted/60 focus:outline-none focus:border-accent"
                />
              )}

              {isMixedMode && (
                <div className="mt-2 flex items-start gap-2 bg-accent/10 border border-accent/30 rounded-md px-3 py-2.5">
                  <Layers size={15} className="text-accent shrink-0 mt-0.5" strokeWidth={1.75} />
                  <span className="text-sm text-text-primary">
                    File WAJIB punya kolom <span className="font-display text-xs">channel</span>{' '}
                    (atau <span className="font-display text-xs">platform</span>/
                    <span className="font-display text-xs">marketplace</span>/
                    <span className="font-display text-xs">sumber</span>) berisi nama channel di
                    setiap baris. Sistem otomatis memecah jadi beberapa batch, satu per channel
                    yang ditemukan.
                  </span>
                </div>
              )}
            </div>
          )}

          <div>
            <label className="block text-xs text-text-muted uppercase tracking-wider mb-1.5">
              Dataset Name
            </label>
            <input
              type="text"
              value={datasetName}
              onChange={(e) => setDatasetName(e.target.value)}
              placeholder="misal: Transaksi Harian"
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
            disabled={uploading || !canSubmit}
            className="glow-accent-sm w-full bg-accent text-ink font-medium text-sm rounded-md py-2.5 hover:bg-accent-soft transition-colors disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none"
          >
            {uploading
              ? 'Mengirim ke ledger…'
              : isMixedMode
                ? 'Pisahkan & Upload per Channel'
                : 'Upload & Ingest'}
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

function MixedResultCard({ batches, onUploadAnother }) {
  const successCount = batches.filter((b) => b.status === 'success').length
  return (
    <div className="bg-ink-surface border border-ink-border rounded-lg px-6 py-6 space-y-4">
      <div className="flex items-center gap-3">
        <Layers size={22} className="text-accent" strokeWidth={1.75} />
        <div>
          <div className="text-text-primary text-sm font-medium">
            File terpecah jadi {batches.length} channel — {successCount} berhasil
          </div>
          <div className="text-text-muted text-xs mt-0.5">
            Masing-masing channel jadi batch terpisah di source-nya sendiri.
          </div>
        </div>
      </div>

      <ul className="divide-y divide-ink-border border border-ink-border rounded-md overflow-hidden">
        {batches.map((b) => (
          <li key={b.id} className="px-4 py-3 flex items-center justify-between bg-ink-elevated">
            <div className="min-w-0">
              <div className="text-sm text-text-primary">{b.channel_name}</div>
              <div className="text-text-muted text-xs mt-0.5 font-display truncate">
                {formatNumber(b.records_saved)} records
              </div>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <StatusBadge status={b.status} />
              <Link to={`/jobs/${b.id}`} className="text-xs text-accent hover:underline">
                Detail
              </Link>
            </div>
          </li>
        ))}
      </ul>

      <button
        onClick={onUploadAnother}
        className="glow-accent-sm w-full bg-accent text-ink font-medium text-sm rounded-md py-2 hover:bg-accent-soft transition-colors"
      >
        Upload Lagi
      </button>
    </div>
  )
}
