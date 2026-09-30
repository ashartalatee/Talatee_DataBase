import { useEffect, useState } from 'react'
import { BookOpen, Check, ChevronDown, FileText, Plus, RefreshCw, Trash2, Undo2, Video } from 'lucide-react'
import { api } from '../api/client'

const DAILY_LIMIT = 3
const SHOW = 4

const pad = (n) => String(n).padStart(2, '0')
const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

function timeAgo(iso) {
  if (!iso) return ''
  const h = Math.floor((Date.now() - new Date(iso).getTime()) / 36e5)
  if (h < 1) return 'baru saja'
  if (h < 24) return `${h} jam lalu`
  return `${Math.floor(h / 24)} hari lalu`
}

function errText(err, fallback) {
  const m = String(err?.message || '')
  return /^400:/.test(m) ? m.replace(/^400:\s*/, '') : fallback
}

function IconBtn({ label, onClick, disabled, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      title={label}
      className="w-8 h-8 shrink-0 rounded-md flex items-center justify-center text-text-muted hover:text-accent hover:bg-ink-elevated disabled:opacity-30 disabled:hover:text-text-muted disabled:hover:bg-transparent transition-colors"
    >
      {children}
    </button>
  )
}

function Title({ item, muted }) {
  const Icon = item.kind === 'video' ? Video : FileText
  return (
    <div className="flex-1 min-w-0 flex items-start gap-2">
      <Icon size={15} className="text-accent/80 shrink-0 mt-0.5" strokeWidth={1.75} />
      <div className="min-w-0">
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className={`text-sm break-words hover:text-accent ${muted ? 'text-text-muted line-through' : 'text-text-primary'}`}
        >
          {item.title}
        </a>
        <div className="text-xs text-text-muted flex flex-wrap items-center gap-x-1.5">
          {item.origin === 'auto' && <span className="text-accent/80">Otomatis</span>}
          <span>{item.source_name || hostOf(item.url)}</span>
          {item.published_at && <span>· {timeAgo(item.published_at)}</span>}
        </div>
      </div>
    </div>
  )
}

export default function KompasBacaan() {
  const [items, setItems] = useState([])
  const [url, setUrl] = useState('')
  const [title, setTitle] = useState('')
  const [load, setLoad] = useState('loading') // loading | ok | error
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState(() => window.matchMedia('(min-width: 768px)').matches)
  const [showAll, setShowAll] = useState(false)
  const [showRead, setShowRead] = useState(false)

  const todayStr = ymd(new Date())

  useEffect(() => {
    let cancelled = false
    api
      .listKompasReading(ymd(new Date()))
      .then((d) => {
        if (!cancelled) {
          setItems(d)
          setLoad('ok')
        }
      })
      .catch(() => {
        if (!cancelled) setLoad('error')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const replace = (u) => setItems((prev) => prev.map((i) => (i.id === u.id ? u : i)))

  async function add(e) {
    e.preventDefault()
    const u = url.trim()
    if (!u || busy) return
    setBusy(true)
    setError('')
    try {
      const created = await api.createKompasReading(u, title.trim())
      setItems((prev) => [created, ...prev.filter((i) => i.id !== created.id)])
      setUrl('')
      setTitle('')
    } catch (err) {
      setError(errText(err, 'Gagal menyimpan tautan. Coba lagi.'))
    } finally {
      setBusy(false)
    }
  }

  async function act(id, payload) {
    setError('')
    try {
      replace(await api.updateKompasReading(id, payload))
    } catch (err) {
      setError(errText(err, 'Gagal memperbarui. Coba lagi.'))
    }
  }

  async function skip(id) {
    setError('')
    try {
      await api.updateKompasReading(id, { action: 'skip', day: todayStr })
      setItems(await api.listKompasReading(todayStr))
    } catch (err) {
      setError(errText(err, 'Gagal mengganti. Coba lagi.'))
    }
  }

  async function remove(id) {
    setError('')
    try {
      await api.deleteKompasReading(id)
      setItems((prev) => prev.filter((i) => i.id !== id))
    } catch {
      setError('Gagal menghapus. Coba lagi.')
    }
  }

  const today = items.filter((i) => i.planned_for === todayStr)
  const saved = items.filter((i) => i.origin !== 'auto' && !i.read_at && i.planned_for !== todayStr)
  const readList = items.filter((i) => i.read_at && i.planned_for !== todayStr)
  const full = today.length >= DAILY_LIMIT
  const visible = showAll ? saved : saved.slice(0, SHOW)
  const readToday = today.filter((i) => i.read_at).length

  return (
    <section className="rounded-xl border border-ink-border bg-ink-surface p-4 md:p-5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-3 text-left"
      >
        <h2 className="font-display text-base text-text-primary flex items-center gap-2">
          <BookOpen size={16} className="text-accent" strokeWidth={1.75} />
          Bacaan terpilih
        </h2>
        <span className="flex items-center gap-2 text-xs text-text-muted">
          {load === 'ok' && (
            <span>
              {readToday}/{today.length} dibaca
              {saved.length > 0 ? ` · ${saved.length} tersimpan` : ''}
            </span>
          )}
          <ChevronDown size={16} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
        </span>
      </button>

      {open && (
        <div className="mt-3">
          <p className="text-xs text-text-muted">
            Tiap pagi terisi otomatis dari sumber pilihan, maksimal {DAILY_LIMIT}. Kurang cocok? Tekan ganti.
          </p>

          {load === 'loading' && <p className="text-xs text-text-muted mt-3">Memuat…</p>}
          {load === 'error' && (
            <p className="text-xs text-warning mt-3">
              Belum bisa memuat. Pastikan backend menyala, lalu muat ulang halaman.
            </p>
          )}

          {load === 'ok' && (
            <>
              <h3 className="text-xs text-accent mt-4 mb-1">
                Hari ini ({today.length}/{DAILY_LIMIT})
              </h3>
              {today.length === 0 ? (
                <p className="text-sm text-text-muted">
                  Belum ada bacaan hari ini. Bacaan otomatis muncul setelah pengambilan pagi berjalan, atau pilih
                  dari simpanan.
                </p>
              ) : (
                <ul className="divide-y divide-ink-border">
                  {today.map((i) => (
                    <li key={i.id} className="flex items-center gap-2 py-2">
                      <Title item={i} muted={!!i.read_at} />
                      {i.read_at ? (
                        <IconBtn label="Tandai belum dibaca" onClick={() => act(i.id, { action: 'unread' })}>
                          <Undo2 size={15} strokeWidth={1.75} />
                        </IconBtn>
                      ) : (
                        <>
                          <IconBtn label="Tandai sudah dibaca" onClick={() => act(i.id, { action: 'read' })}>
                            <Check size={16} strokeWidth={2.25} />
                          </IconBtn>
                          {i.origin === 'auto' ? (
                            <IconBtn label="Ganti dengan bacaan lain" onClick={() => skip(i.id)}>
                              <RefreshCw size={15} strokeWidth={1.75} />
                            </IconBtn>
                          ) : (
                            <IconBtn label="Kembalikan ke simpanan" onClick={() => act(i.id, { action: 'unplan' })}>
                              <Undo2 size={15} strokeWidth={1.75} />
                            </IconBtn>
                          )}
                        </>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}

          <form onSubmit={add} className="mt-4 flex flex-col md:flex-row gap-2">
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              maxLength={2000}
              inputMode="url"
              placeholder="Punya tautan sendiri? Tempel di sini (https://…)"
              aria-label="Tautan bacaan"
              className="flex-1 min-w-0 bg-ink border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/60"
            />
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={200}
              placeholder="Judul (opsional)"
              aria-label="Judul bacaan"
              className="flex-1 min-w-0 bg-ink border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/60"
            />
            <button
              type="submit"
              disabled={!url.trim() || busy}
              className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-sm border border-accent text-accent hover:bg-accent/10 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <Plus size={14} strokeWidth={2.5} />
              Simpan
            </button>
          </form>

          {error && <p className="text-xs text-warning mt-2">{error}</p>}

          {load === 'ok' && saved.length > 0 && (
            <div className="mt-4">
              <h3 className="text-xs text-text-muted mb-1">Simpanan ({saved.length})</h3>
              <ul className="divide-y divide-ink-border">
                {visible.map((i) => (
                  <li key={i.id} className="flex items-center gap-2 py-2">
                    <Title item={i} />
                    <IconBtn
                      label={full ? `Sudah ${DAILY_LIMIT} bacaan hari ini` : 'Baca hari ini'}
                      disabled={full}
                      onClick={() => act(i.id, { action: 'today', day: todayStr })}
                    >
                      <BookOpen size={15} strokeWidth={1.75} />
                    </IconBtn>
                    <IconBtn label="Hapus" onClick={() => remove(i.id)}>
                      <Trash2 size={15} strokeWidth={1.75} />
                    </IconBtn>
                  </li>
                ))}
              </ul>
              {saved.length > SHOW && (
                <button
                  type="button"
                  onClick={() => setShowAll((v) => !v)}
                  className="text-xs text-text-muted hover:text-text-primary mt-2"
                >
                  {showAll ? 'Ringkas' : `Lihat semua (${saved.length})`}
                </button>
              )}
            </div>
          )}

          {readList.length > 0 && (
            <div className="mt-3 pt-3 border-t border-ink-border">
              <button
                type="button"
                onClick={() => setShowRead((v) => !v)}
                aria-expanded={showRead}
                className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-primary"
              >
                <ChevronDown size={14} className={`transition-transform ${showRead ? 'rotate-180' : ''}`} />
                Sudah dibaca ({readList.length})
              </button>
              {showRead && (
                <ul className="mt-2 divide-y divide-ink-border">
                  {readList.map((i) => (
                    <li key={i.id} className="flex items-center gap-2 py-2">
                      <Title item={i} muted />
                      <IconBtn label="Tandai belum dibaca" onClick={() => act(i.id, { action: 'unread' })}>
                        <Undo2 size={15} strokeWidth={1.75} />
                      </IconBtn>
                      <IconBtn label="Hapus" onClick={() => remove(i.id)}>
                        <Trash2 size={15} strokeWidth={1.75} />
                      </IconBtn>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
    </section>
  )
}
