import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  BookOpen,
  Check,
  Flame,
  Hammer,
  Mic,
  Video,
} from 'lucide-react'
import { api } from '../api/client'
import KompasIdeaBank from '../components/KompasIdeaBank'
import KompasParkir from '../components/KompasParkir'
import KompasReview from '../components/KompasReview'

const CACHE_KEY = 'talatee_kompas_v2'
const TARGET = new Date(2027, 0, 1)

const HABITS = [
  { id: 'project', name: 'Projek', icon: Hammer, min: 'Kerjakan satu hal kecil di projek hari ini.' },
  {
    id: 'speaking',
    name: 'Speaking',
    icon: Mic,
    min: 'Ceritakan hasil kerjamu 10 menit: masalah, proses, penemuan, solusi, pelajaran.',
  },
  {
    id: 'content',
    name: 'Konten',
    icon: Video,
    min: 'Rekam layar atau tulis satu konten mentah. Tanpa edit rumit.',
  },
]

const SOON = [
  { icon: BookOpen, title: 'Bacaan terpilih' },
]

const EMPTY = { project: [], speaking: [], content: [] }
const CIRC = 2 * Math.PI * 52
const CELL = ['bg-ink-border', 'bg-accent/25', 'bg-accent/55', 'bg-accent']

const ymd = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

const daysAgo = (n) => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return d
}

function streakOf(dates, today) {
  const set = new Set(dates)
  let n = 0
  const d = new Date()
  if (!set.has(today)) d.setDate(d.getDate() - 1)
  while (set.has(ymd(d))) {
    n += 1
    d.setDate(d.getDate() - 1)
  }
  return n
}

function greeting(h) {
  if (h < 11) return 'Selamat pagi'
  if (h < 15) return 'Selamat siang'
  if (h < 18) return 'Selamat sore'
  return 'Selamat malam'
}

function readCache() {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (raw) {
      const p = JSON.parse(raw)
      return { log: { ...EMPTY, ...p.log }, synced: !!p.synced }
    }
  } catch {
    /* penyimpanan browser tidak tersedia */
  }
  return { log: EMPTY, synced: false }
}

function writeCache(log, synced) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify({ log, synced }))
  } catch {
    /* abaikan */
  }
}

export default function Kompas() {
  const [log, setLog] = useState(() => readCache().log)
  const [status, setStatus] = useState('loading') // loading | ok | offline
  const syncedRef = useRef(readCache().synced)

  const now = new Date()
  const today = ymd(now)
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const left = Math.ceil((TARGET - start) / 864e5)

  useEffect(() => {
    let cancelled = false
    async function sync() {
      try {
        let server = await api.getKompasCheckins()
        if (!syncedRef.current) {
          // Pertama kali: pindahkan centang lama dari browser ke database.
          const local = readCache().log
          if (HABITS.some((h) => local[h.id].length > 0)) {
            await api.importKompas({ log: local })
            server = await api.getKompasCheckins()
          }
        }
        if (cancelled) return
        const merged = { ...EMPTY, ...server }
        syncedRef.current = true
        setLog(merged)
        writeCache(merged, true)
        setStatus('ok')
      } catch {
        if (!cancelled) setStatus('offline')
      }
    }
    sync()
    return () => {
      cancelled = true
    }
  }, [])

  async function toggle(id) {
    const has = log[id].includes(today)
    const next = { ...log, [id]: has ? log[id].filter((x) => x !== today) : [...log[id], today] }
    setLog(next)
    try {
      await api.setKompasCheckin(id, today, !has)
      writeCache(next, syncedRef.current)
    } catch {
      syncedRef.current = false
      writeCache(next, false)
      setStatus('offline')
    }
  }

  const done = HABITS.filter((h) => log[h.id].includes(today)).length
  const countOn = (date) => HABITS.filter((h) => log[h.id].includes(date)).length
  const perfectDays = new Set(HABITS.flatMap((h) => log[h.id]).filter((d) => countOn(d) === 3)).size

  const message =
    done === 3
      ? 'Ketiganya selesai. Rantai hari ini aman.'
      : done === 0
        ? 'Mulai dari yang paling kecil. Satu centang sudah cukup untuk bergerak.'
        : `Sisa ${3 - done}. Kamu sudah mulai, tinggal dilanjutkan.`

  return (
    <div className="max-w-4xl mx-auto space-y-3 md:space-y-5">
      <section className="relative overflow-hidden rounded-xl border border-ink-border bg-ink-surface bg-[radial-gradient(ellipse_at_top_right,rgba(124,252,60,0.13),transparent_60%)] p-4 md:p-8">
        <div className="flex items-center justify-between gap-3 md:gap-6">
          <div className="min-w-0">
            <p className="text-text-muted text-sm">{greeting(now.getHours())}, Ashar.</p>
            <div className="flex items-baseline gap-2 md:gap-3 mt-1 md:mt-2">
              <span className="font-display text-5xl md:text-8xl leading-none text-accent glow-text-accent">
                {left > 0 ? left : 0}
              </span>
              <span className="font-display text-base md:text-xl text-text-primary">hari</span>
            </div>
            <p className="text-text-muted text-xs md:text-sm mt-2 md:mt-3">
              menuju 1 Januari 2027. Bangun ritmenya dari sekarang.
            </p>
            <p className={`text-xs md:text-sm mt-2 md:mt-4 max-w-sm ${done === 3 ? 'text-accent' : 'text-text-primary'}`}>
              {message}
            </p>
          </div>

          <div className="relative shrink-0 w-20 h-20 md:w-40 md:h-40" aria-label={`${done} dari 3 selesai hari ini`}>
            <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
              <circle cx="60" cy="60" r="52" fill="none" strokeWidth="9" className="stroke-ink-border" />
              <circle
                cx="60"
                cy="60"
                r="52"
                fill="none"
                strokeWidth="9"
                strokeLinecap="round"
                strokeDasharray={CIRC}
                strokeDashoffset={CIRC * (1 - done / 3)}
                className="stroke-accent transition-[stroke-dashoffset] duration-500"
                style={{ filter: 'drop-shadow(0 0 6px rgba(124,252,60,0.6))' }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-display text-xl md:text-4xl text-text-primary">{done}/3</span>
              <span className="text-[9px] md:text-[11px] text-text-muted">hari ini</span>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-2 md:gap-4">
        {HABITS.map(({ id, name, icon: Icon, min }) => {
          const dates = log[id]
          const ok = dates.includes(today)
          const streak = streakOf(dates, today)
          return (
            <button
              key={id}
              onClick={() => toggle(id)}
              aria-pressed={ok}
              className={`group text-left rounded-xl border p-3 md:p-5 flex flex-row md:flex-col items-center md:items-stretch gap-3 md:gap-4 md:min-h-[190px] transition-all ${
                ok
                  ? 'border-accent bg-accent/10 glow-accent-sm'
                  : 'border-ink-border bg-ink-surface hover:border-accent/50 hover:-translate-y-0.5'
              }`}
            >
              <div className="flex items-start justify-between max-md:contents">
                <span
                  className={`w-9 h-9 md:w-11 md:h-11 max-md:order-1 shrink-0 rounded-lg flex items-center justify-center ${
                    ok ? 'bg-accent text-ink' : 'bg-ink-elevated text-accent'
                  }`}
                >
                  <Icon size={22} strokeWidth={1.75} />
                </span>
                <span
                  className={`w-7 h-7 md:w-9 md:h-9 max-md:order-3 shrink-0 rounded-full flex items-center justify-center border-2 transition-colors ${
                    ok
                      ? 'bg-accent border-accent text-ink'
                      : 'border-ink-border text-transparent group-hover:border-accent/60 group-hover:text-accent/50'
                  }`}
                >
                  <Check size={18} strokeWidth={3} />
                </span>
              </div>

              <div className="flex-1 min-w-0 max-md:order-2">
                <h2 className="font-display text-base md:text-xl text-text-primary">{name}</h2>
                <p className="text-text-muted text-xs md:text-sm mt-0.5 md:mt-1 leading-snug max-md:truncate">{min}</p>
                <div className="md:hidden flex items-center gap-1 text-xs mt-1">
                  <Flame size={12} className={streak > 0 ? 'text-warning' : 'text-ink-border'} strokeWidth={2} />
                  <span className={streak > 0 ? 'text-text-primary' : 'text-text-muted'}>{streak} hari</span>
                </div>
              </div>

              <div className="hidden md:flex items-center gap-1.5 text-sm">
                <Flame size={16} className={streak > 0 ? 'text-warning' : 'text-ink-border'} strokeWidth={2} />
                <span className={streak > 0 ? 'text-text-primary' : 'text-text-muted'}>
                  {streak} hari berturut-turut
                </span>
              </div>
            </button>
          )
        })}
      </section>

      <KompasIdeaBank />

      <KompasParkir />

      <KompasReview log={log} />

      <section className="grid grid-cols-1 md:grid-cols-5 gap-3 md:gap-4">
        <div className="md:col-span-3 rounded-xl border border-ink-border bg-ink-surface p-4 md:p-5">
          <div className="flex items-baseline justify-between gap-3">
            <h2 className="font-display text-base text-text-primary">28 hari terakhir</h2>
            <span className="text-xs text-text-muted">{perfectDays} hari sempurna</span>
          </div>
          <div className="grid grid-cols-7 gap-1.5 mt-4">
            {Array.from({ length: 28 }, (_, i) => {
              const d = daysAgo(27 - i)
              const c = countOn(ymd(d))
              return (
                <span
                  key={i}
                  title={`${d.getDate()}/${d.getMonth() + 1}: ${c} dari 3`}
                  className={`h-5 md:h-7 rounded-md ${CELL[c]} ${ymd(d) === today ? 'ring-1 ring-text-muted' : ''}`}
                />
              )
            })}
          </div>
          <p className="text-xs text-text-muted mt-3">Makin terang, makin banyak yang kamu selesaikan.</p>
        </div>

        <div className="md:col-span-2 rounded-xl border border-dashed border-ink-border p-4 md:p-5">
          <h2 className="font-display text-base text-text-primary">Segera hadir</h2>
          <ul className="mt-3 grid grid-cols-2 md:grid-cols-1 gap-2.5">
            {SOON.map(({ icon: Icon, title }) => (
              <li key={title} className="flex items-center gap-2.5 text-sm text-text-muted">
                <Icon size={15} className="text-accent/70" strokeWidth={1.75} />
                {title}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <p className={`text-xs ${status === 'offline' ? 'text-warning' : 'text-text-muted'}`}>
        {status === 'loading' && 'Menyinkronkan…'}
        {status === 'ok' && 'Tersimpan di database Talatee.'}
        {status === 'offline' &&
          'Belum tersinkron ke server. Perubahan tersimpan sementara di browser ini.'}
      </p>

      <Link
        to="/overview"
        className="flex items-center justify-between gap-3 px-4 md:px-5 py-2.5 md:py-3 rounded-xl border border-ink-border text-sm text-text-muted hover:border-accent/50 hover:text-text-primary transition-colors"
      >
        <span>Lihat kondisi client dan data</span>
        <span className="flex items-center gap-1.5">
          Buka Overview <ArrowRight size={14} />
        </span>
      </Link>
    </div>
  )
}
