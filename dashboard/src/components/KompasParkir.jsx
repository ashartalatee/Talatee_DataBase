import { useEffect, useState } from 'react'
import { Archive, ChevronDown, FlaskConical, Plus, Trash2 } from 'lucide-react'
import { api } from '../api/client'

function daysLeft(reviewOn) {
  const [y, m, d] = reviewOn.split('-').map(Number)
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  return Math.ceil((new Date(y, m - 1, d) - start) / 864e5)
}

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

function TextBtn({ icon: Icon, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-1.5 shrink-0 px-2.5 py-1.5 rounded-md text-xs border border-accent text-accent hover:bg-accent/10 transition-colors"
    >
      {Icon && <Icon size={13} strokeWidth={2} />}
      {children}
    </button>
  )
}

export default function KompasParkir() {
  const [items, setItems] = useState([])
  const [text, setText] = useState('')
  const [reason, setReason] = useState('')
  const [load, setLoad] = useState('loading') // loading | ok | error
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [open, setOpen] = useState(() => window.matchMedia('(min-width: 768px)').matches)
  const [showDone, setShowDone] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .listKompasParked()
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

  useEffect(() => {
    // Ide yang diparkir dari bagian Arah ikut muncul di sini tanpa muat ulang.
    const onParked = (e) => {
      const item = e.detail
      if (!item) return
      setItems((prev) => (prev.some((i) => i.id === item.id) ? prev : [...prev, item]))
    }
    window.addEventListener('kompas:parked', onParked)
    return () => window.removeEventListener('kompas:parked', onParked)
  }, [])

  const replace = (u) => setItems((prev) => prev.map((i) => (i.id === u.id ? u : i)))

  async function add(e) {
    e.preventDefault()
    const t = text.trim()
    if (!t || busy) return
    setBusy(true)
    setError('')
    try {
      const created = await api.createKompasParked(t, reason.trim())
      setItems((prev) => [...prev, created])
      setText('')
      setReason('')
    } catch {
      setError('Gagal memarkir ide. Coba lagi.')
    } finally {
      setBusy(false)
    }
  }

  async function decide(id, status) {
    setError('')
    try {
      replace(await api.updateKompasParked(id, { status }))
    } catch (err) {
      setError(err.message?.includes('30 hari') ? 'Masa tunggu 30 hari belum selesai.' : 'Gagal memperbarui ide.')
    }
  }

  async function toExperiment(item) {
    setError('')
    try {
      await api.createLabEntry({ name: item.text.slice(0, 120), note: item.reason || 'Dari Parkir ide Kompas' })
      replace(await api.updateKompasParked(item.id, { status: 'eksperimen' }))
    } catch {
      setError('Gagal mencatat di Eksperimen. Coba lagi.')
    }
  }

  async function remove(id) {
    setError('')
    try {
      await api.deleteKompasParked(id)
      setItems((prev) => prev.filter((i) => i.id !== id))
    } catch {
      setError('Gagal melepas ide. Coba lagi.')
    }
  }

  const waiting = items.filter((i) => i.status === 'parkir')
  const passed = items.filter((i) => i.status === 'lolos')
  const done = items.filter((i) => i.status === 'eksperimen')
  const ready = waiting.filter((i) => daysLeft(i.review_on) <= 0).length

  return (
    <section className="rounded-xl border border-ink-border bg-ink-surface p-4 md:p-5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-3 text-left"
      >
        <h2 className="font-display text-base text-text-primary flex items-center gap-2">
          <Archive size={16} className="text-accent" strokeWidth={1.75} />
          Parkir ide
        </h2>
        <span className="flex items-center gap-2 text-xs text-text-muted">
          {load === 'ok' && (
            <span className={ready + passed.length > 0 ? 'text-accent' : ''}>
              {waiting.length} diparkir
              {ready + passed.length > 0 ? ` · ${ready + passed.length} perlu keputusan` : ''}
            </span>
          )}
          <ChevronDown size={16} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
        </span>
      </button>

      {open && (
        <div className="mt-3">
          <p className="text-xs text-text-muted">
            Terpikir bidang lain? Taruh di sini. Baru boleh ditinjau setelah 30 hari, bukan hari ini.
          </p>

          <form onSubmit={add} className="mt-3 flex flex-col md:flex-row gap-2">
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              maxLength={200}
              placeholder="Idenya apa?"
              aria-label="Ide yang diparkir"
              className="flex-1 min-w-0 bg-ink border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/60"
            />
            <input
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              maxLength={280}
              placeholder="Kenapa menarik? (opsional)"
              aria-label="Alasan ide menarik"
              className="flex-1 min-w-0 bg-ink border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/60"
            />
            <button
              type="submit"
              disabled={!text.trim() || busy}
              className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-sm border border-accent text-accent hover:bg-accent/10 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              <Plus size={14} strokeWidth={2.5} />
              Parkir
            </button>
          </form>

          {error && <p className="text-xs text-warning mt-2">{error}</p>}
          {load === 'loading' && <p className="text-xs text-text-muted mt-3">Memuat…</p>}
          {load === 'error' && (
            <p className="text-xs text-warning mt-3">
              Belum bisa memuat. Pastikan backend menyala, lalu muat ulang halaman.
            </p>
          )}
          {load === 'ok' && items.length === 0 && (
            <p className="text-sm text-text-muted mt-3">Belum ada ide yang diparkir.</p>
          )}

          {passed.length > 0 && (
            <div className="mt-4">
              <h3 className="text-xs text-accent mb-1">Lolos tinjauan</h3>
              <ul className="divide-y divide-ink-border">
                {passed.map((i) => (
                  <li key={i.id} className="flex items-center gap-2 py-2">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-text-primary break-words">{i.text}</div>
                      {i.reason && <div className="text-xs text-text-muted break-words">{i.reason}</div>}
                    </div>
                    <TextBtn icon={FlaskConical} onClick={() => toExperiment(i)}>
                      Catat di Eksperimen
                    </TextBtn>
                    <IconBtn label="Lepas ide" onClick={() => remove(i.id)}>
                      <Trash2 size={15} strokeWidth={1.75} />
                    </IconBtn>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {waiting.length > 0 && (
            <ul className="mt-3 divide-y divide-ink-border">
              {waiting.map((i) => {
                const left = daysLeft(i.review_on)
                const isReady = left <= 0
                return (
                  <li key={i.id} className="flex items-center gap-2 py-2">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-text-primary break-words">{i.text}</div>
                      {i.reason && <div className="text-xs text-text-muted break-words">{i.reason}</div>}
                      <div className={`text-xs mt-0.5 ${isReady ? 'text-accent' : 'text-warning'}`}>
                        {isReady ? 'Siap ditinjau. Apakah masih menarik?' : `Tinjau lagi dalam ${left} hari`}
                      </div>
                    </div>
                    {isReady && <TextBtn onClick={() => decide(i.id, 'lolos')}>Masih menarik</TextBtn>}
                    <IconBtn label="Lepas ide" onClick={() => remove(i.id)}>
                      <Trash2 size={15} strokeWidth={1.75} />
                    </IconBtn>
                  </li>
                )
              })}
            </ul>
          )}

          {done.length > 0 && (
            <div className="mt-3 pt-3 border-t border-ink-border">
              <button
                type="button"
                onClick={() => setShowDone((v) => !v)}
                aria-expanded={showDone}
                className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-primary"
              >
                <ChevronDown size={14} className={`transition-transform ${showDone ? 'rotate-180' : ''}`} />
                Sudah jadi eksperimen ({done.length})
              </button>
              {showDone && (
                <ul className="mt-2 divide-y divide-ink-border">
                  {done.map((i) => (
                    <li key={i.id} className="py-2 text-sm text-text-muted break-words">
                      {i.text}
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
