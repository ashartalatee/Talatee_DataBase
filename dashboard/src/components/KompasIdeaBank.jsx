import { useEffect, useState } from 'react'
import { Check, ChevronDown, Lightbulb, Plus, RotateCcw, Trash2 } from 'lucide-react'
import { api } from '../api/client'

const SHOW = 4

function IconBtn({ label, onClick, children }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className="w-8 h-8 shrink-0 rounded-md flex items-center justify-center text-text-muted hover:text-accent hover:bg-ink-elevated transition-colors"
    >
      {children}
    </button>
  )
}

export default function KompasIdeaBank() {
  const [ideas, setIdeas] = useState([])
  const [text, setText] = useState('')
  const [load, setLoad] = useState('loading') // loading | ok | error
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [showAll, setShowAll] = useState(false)
  const [showUsed, setShowUsed] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .listKompasIdeas()
      .then((d) => {
        if (!cancelled) {
          setIdeas(d)
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

  async function add(e) {
    e.preventDefault()
    const t = text.trim()
    if (!t || busy) return
    setBusy(true)
    setError('')
    try {
      const created = await api.createKompasIdea(t)
      setIdeas((prev) => [created, ...prev])
      setText('')
    } catch {
      setError('Gagal menyimpan ide. Coba lagi.')
    } finally {
      setBusy(false)
    }
  }

  async function setStatus(id, status) {
    setError('')
    try {
      const updated = await api.updateKompasIdea(id, { status })
      setIdeas((prev) => prev.map((i) => (i.id === id ? updated : i)))
    } catch {
      setError('Gagal memperbarui ide. Coba lagi.')
    }
  }

  async function remove(id) {
    setError('')
    try {
      await api.deleteKompasIdea(id)
      setIdeas((prev) => prev.filter((i) => i.id !== id))
    } catch {
      setError('Gagal menghapus ide. Coba lagi.')
    }
  }

  const fresh = ideas.filter((i) => i.status === 'baru')
  const used = ideas.filter((i) => i.status === 'dipakai')
  const visible = showAll ? fresh : fresh.slice(0, SHOW)

  return (
    <section className="rounded-xl border border-ink-border bg-ink-surface p-4 md:p-5">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-display text-base text-text-primary flex items-center gap-2">
          <Lightbulb size={16} className="text-accent" strokeWidth={1.75} />
          Bank ide konten
        </h2>
        {load === 'ok' && <span className="text-xs text-text-muted">{fresh.length} siap pakai</span>}
      </div>

      <form onSubmit={add} className="flex gap-2 mt-3">
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={280}
          placeholder="Tulis satu ide, sependek apa pun"
          aria-label="Ide konten baru"
          className="flex-1 min-w-0 bg-ink border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/60"
        />
        <button
          type="submit"
          disabled={!text.trim() || busy}
          className="flex items-center gap-1.5 px-3 py-2 rounded-md text-sm border border-accent text-accent hover:bg-accent/10 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Plus size={14} strokeWidth={2.5} />
          <span className="max-md:hidden">Simpan</span>
        </button>
      </form>

      {error && <p className="text-xs text-warning mt-2">{error}</p>}

      {load === 'loading' && <p className="text-xs text-text-muted mt-3">Memuat ide…</p>}
      {load === 'error' && (
        <p className="text-xs text-warning mt-3">
          Belum bisa memuat ide. Pastikan backend menyala, lalu muat ulang halaman.
        </p>
      )}

      {load === 'ok' && fresh.length === 0 && (
        <p className="text-sm text-text-muted mt-3">
          Belum ada ide. Catat satu tiap kali terpikir sesuatu saat mengerjakan projek.
        </p>
      )}

      {visible.length > 0 && (
        <ul className="mt-3 divide-y divide-ink-border">
          {visible.map((i) => (
            <li key={i.id} className="flex items-center gap-2 py-2">
              <span className="flex-1 min-w-0 text-sm text-text-primary break-words">{i.text}</span>
              <IconBtn label="Tandai sudah dipakai" onClick={() => setStatus(i.id, 'dipakai')}>
                <Check size={16} strokeWidth={2.25} />
              </IconBtn>
              <IconBtn label="Hapus ide" onClick={() => remove(i.id)}>
                <Trash2 size={15} strokeWidth={1.75} />
              </IconBtn>
            </li>
          ))}
        </ul>
      )}

      {fresh.length > SHOW && (
        <button
          type="button"
          onClick={() => setShowAll((v) => !v)}
          className="text-xs text-text-muted hover:text-text-primary mt-2"
        >
          {showAll ? 'Ringkas' : `Lihat semua (${fresh.length})`}
        </button>
      )}

      {used.length > 0 && (
        <div className="mt-3 pt-3 border-t border-ink-border">
          <button
            type="button"
            onClick={() => setShowUsed((v) => !v)}
            aria-expanded={showUsed}
            className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-primary"
          >
            <ChevronDown size={14} className={`transition-transform ${showUsed ? 'rotate-180' : ''}`} />
            Sudah dipakai ({used.length})
          </button>
          {showUsed && (
            <ul className="mt-2 divide-y divide-ink-border">
              {used.map((i) => (
                <li key={i.id} className="flex items-center gap-2 py-2">
                  <span className="flex-1 min-w-0 text-sm text-text-muted line-through break-words">{i.text}</span>
                  <IconBtn label="Kembalikan ke siap pakai" onClick={() => setStatus(i.id, 'baru')}>
                    <RotateCcw size={15} strokeWidth={1.75} />
                  </IconBtn>
                  <IconBtn label="Hapus ide" onClick={() => remove(i.id)}>
                    <Trash2 size={15} strokeWidth={1.75} />
                  </IconBtn>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  )
}
