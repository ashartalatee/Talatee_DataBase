import { useEffect, useState } from 'react'
import { ChevronDown, NotebookPen } from 'lucide-react'
import { api } from '../api/client'

const QUESTIONS = [
  { key: 'built', label: 'Apa yang saya bangun minggu ini?' },
  { key: 'improve', label: 'Apa satu hal yang harus saya perbaiki minggu depan?' },
  { key: 'proud', label: 'Konten mana yang paling saya banggakan?' },
]
const HABIT_LABELS = [
  ['project', 'Projek'],
  ['speaking', 'Speaking'],
  ['content', 'Konten'],
]
const EMPTY = { built: '', improve: '', proud: '' }

const pad = (n) => String(n).padStart(2, '0')
const ymd = (d) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
const parseYmd = (s) => {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}
function mondayOf(d) {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  x.setDate(x.getDate() - ((x.getDay() + 6) % 7))
  return x
}
function weekLabel(start) {
  const a = parseYmd(start)
  const b = new Date(a)
  b.setDate(b.getDate() + 6)
  const f = { day: 'numeric', month: 'short' }
  return `${a.toLocaleDateString('id-ID', f)} – ${b.toLocaleDateString('id-ID', { ...f, year: 'numeric' })}`
}

export default function KompasReview({ log }) {
  const [reviews, setReviews] = useState([])
  const [load, setLoad] = useState('loading') // loading | ok | error
  const [answers, setAnswers] = useState(EMPTY)
  const [open, setOpen] = useState(() => window.matchMedia('(min-width: 768px)').matches)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState({ text: '', bad: false })
  const [showHistory, setShowHistory] = useState(false)

  const now = new Date()
  const dow = now.getDay()
  const weekend = dow === 0 || dow === 6
  const thisWeek = ymd(mondayOf(now))
  const lastDate = new Date(now)
  lastDate.setDate(lastDate.getDate() - 7)
  const lastWeek = ymd(mondayOf(lastDate))

  const byWeek = Object.fromEntries(reviews.map((r) => [r.week_start, r]))
  // Sabtu/Minggu: review minggu ini. Senin-Jumat: tawarkan menyusul minggu lalu kalau belum ada.
  const target = weekend ? thisWeek : load === 'ok' && !byWeek[lastWeek] ? lastWeek : null
  const existing = target ? byWeek[target] : null
  const pending = load === 'ok' && target && !existing

  useEffect(() => {
    let cancelled = false
    api
      .listKompasReviews()
      .then((d) => {
        if (!cancelled) {
          setReviews(d)
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
    if (load !== 'ok') return
    setAnswers(existing ? { built: existing.built, improve: existing.improve, proud: existing.proud } : EMPTY)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [load, target, existing?.updated_at])

  useEffect(() => {
    if (pending) setOpen(true)
  }, [pending])

  async function save(e) {
    e.preventDefault()
    if (!target || saving || !Object.values(answers).some((v) => v.trim())) return
    setSaving(true)
    setMsg({ text: '', bad: false })
    try {
      const saved = await api.saveKompasReview(target, answers)
      setReviews((prev) =>
        [saved, ...prev.filter((r) => r.week_start !== saved.week_start)].sort((a, b) =>
          b.week_start.localeCompare(a.week_start),
        ),
      )
      setMsg({ text: 'Tersimpan.', bad: false })
    } catch {
      setMsg({ text: 'Gagal menyimpan. Coba lagi.', bad: true })
    } finally {
      setSaving(false)
    }
  }

  const statWeek = target || thisWeek
  const weekDays = new Set(
    Array.from({ length: 7 }, (_, i) => {
      const d = parseYmd(statWeek)
      d.setDate(d.getDate() + i)
      return ymd(d)
    }),
  )
  const counts = HABIT_LABELS.map(([id, label]) => [label, (log[id] || []).filter((x) => weekDays.has(x)).length])
  const history = reviews.filter((r) => r.week_start !== target)

  const status =
    load !== 'ok'
      ? ''
      : pending
        ? weekend
          ? 'Waktunya review'
          : 'Minggu lalu belum direview'
        : existing
          ? 'Sudah direview'
          : 'Dibuka hari Sabtu'

  return (
    <section className="rounded-xl border border-ink-border bg-ink-surface p-4 md:p-5">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-3 text-left"
      >
        <h2 className="font-display text-base text-text-primary flex items-center gap-2">
          <NotebookPen size={16} className="text-accent" strokeWidth={1.75} />
          Review akhir pekan
        </h2>
        <span className="flex items-center gap-2 text-xs text-text-muted">
          {status && <span className={pending ? 'text-accent' : ''}>{status}</span>}
          <ChevronDown size={16} className={`transition-transform ${open ? 'rotate-180' : ''}`} />
        </span>
      </button>

      {open && (
        <div className="mt-3">
          {load === 'loading' && <p className="text-xs text-text-muted">Memuat…</p>}
          {load === 'error' && (
            <p className="text-xs text-warning">Belum bisa memuat. Pastikan backend menyala, lalu muat ulang halaman.</p>
          )}

          {load === 'ok' && !target && (
            <p className="text-sm text-text-muted">
              Review dibuka setiap Sabtu dan Minggu. Tiga pertanyaan, sekitar lima menit.
            </p>
          )}

          {load === 'ok' && target && (
            <form onSubmit={save}>
              <p className="text-sm text-text-primary">
                Minggu {weekLabel(target)}
                {!weekend && <span className="text-xs text-text-muted"> · menyusul</span>}
              </p>
              <p className="text-xs text-text-muted mt-1">
                {counts.map(([label, n]) => `${label} ${n}/7`).join(' · ')}
              </p>

              <div className="mt-3 space-y-3">
                {QUESTIONS.map(({ key, label }) => (
                  <label key={key} className="block">
                    <span className="text-xs text-text-muted">{label}</span>
                    <textarea
                      value={answers[key]}
                      onChange={(e) => setAnswers((a) => ({ ...a, [key]: e.target.value }))}
                      maxLength={1000}
                      rows={2}
                      className="mt-1 w-full bg-ink border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent/60 resize-y"
                    />
                  </label>
                ))}
              </div>

              <div className="mt-3 flex items-center gap-3">
                <button
                  type="submit"
                  disabled={saving || !Object.values(answers).some((v) => v.trim())}
                  className="px-3 py-2 rounded-md text-sm border border-accent text-accent hover:bg-accent/10 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  {existing ? 'Perbarui review' : 'Simpan review'}
                </button>
                {msg.text && <span className={`text-xs ${msg.bad ? 'text-warning' : 'text-accent'}`}>{msg.text}</span>}
              </div>
            </form>
          )}

          {history.length > 0 && (
            <div className="mt-4 pt-3 border-t border-ink-border">
              <button
                type="button"
                onClick={() => setShowHistory((v) => !v)}
                aria-expanded={showHistory}
                className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-primary"
              >
                <ChevronDown size={14} className={`transition-transform ${showHistory ? 'rotate-180' : ''}`} />
                Riwayat review ({history.length})
              </button>
              {showHistory && (
                <ul className="mt-2 divide-y divide-ink-border">
                  {history.map((r) => (
                    <li key={r.week_start} className="py-3">
                      <div className="text-sm text-text-primary">Minggu {weekLabel(r.week_start)}</div>
                      {QUESTIONS.map(({ key, label }) =>
                        r[key] ? (
                          <div key={key} className="mt-1.5">
                            <div className="text-[11px] text-text-muted">{label}</div>
                            <div className="text-sm text-text-primary whitespace-pre-wrap break-words">{r[key]}</div>
                          </div>
                        ) : null,
                      )}
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
