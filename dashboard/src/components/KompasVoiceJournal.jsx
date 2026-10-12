import { useEffect, useRef, useState } from 'react'
import { ChevronDown, Loader2, Mic, RotateCcw, Square, Trash2 } from 'lucide-react'
import { api } from '../api/client'

const MAX_SECONDS = 600 // ~2,4 MB pada 32 kbps, aman untuk batas request Vercel

const ymd = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

const clock = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`

const hhmm = (iso) =>
  new Date(iso).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' }).replace(':', '.')

function pickMime() {
  if (typeof MediaRecorder === 'undefined') return ''
  const options = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus']
  return options.find((t) => MediaRecorder.isTypeSupported(t)) || ''
}

function statusLabel(j) {
  if (j.status === 'pending' && j.error)
    return `Percobaan kirim gagal, dicoba lagi sekitar ${hhmm(j.send_at)}`
  if (j.status === 'pending') return `Hook dikirim ke Telegram sekitar ${hhmm(j.send_at)}`
  if (j.status === 'processing') return 'Hook sedang disusun'
  if (j.status === 'sent') return `Terkirim ke Telegram ${hhmm(j.sent_at)} ? ketuk untuk lihat hook`
  return 'Gagal dikirim, akan dicek manual'
}

export default function KompasVoiceJournal({ onSaved }) {
  const [phase, setPhase] = useState('idle') // idle | recording | transcribing | failed | review | saving
  const [seconds, setSeconds] = useState(0)
  const [raw, setRaw] = useState('')
  const [text, setText] = useState('')
  const [error, setError] = useState('')
  const [journals, setJournals] = useState([])
  const [open, setOpen] = useState(null)

  const recRef = useRef(null)
  const chunksRef = useRef([])
  const blobRef = useRef(null)
  const timerRef = useRef(null)
  const secondsRef = useRef(0)

  function loadJournals() {
    api
      .listKompasJournals()
      .then(setJournals)
      .catch(() => {})
  }

  useEffect(() => {
    loadJournals()
    return () => {
      clearInterval(timerRef.current)
      const rec = recRef.current
      if (rec && rec.state !== 'inactive') {
        rec.onstop = null
        rec.stop()
        rec.stream?.getTracks().forEach((t) => t.stop())
      }
    }
  }, [])

  useEffect(() => {
    const active = journals.some((j) => j.status === 'pending' || j.status === 'processing')
    if (!active) return undefined
    const id = setInterval(loadJournals, 60000)
    const onFocus = () => loadJournals()
    window.addEventListener('focus', onFocus)
    return () => {
      clearInterval(id)
      window.removeEventListener('focus', onFocus)
    }
  }, [journals])

  async function start() {
    setError('')
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      setError('Browser ini tidak bisa merekam. Buka lewat HTTPS atau localhost.')
      return
    }
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setError('Akses mikrofon ditolak. Izinkan mikrofon di pengaturan browser, lalu coba lagi.')
      return
    }
    const mime = pickMime()
    const rec = new MediaRecorder(stream, { ...(mime ? { mimeType: mime } : {}), audioBitsPerSecond: 32000 })
    chunksRef.current = []
    rec.ondataavailable = (e) => {
      if (e.data.size) chunksRef.current.push(e.data)
    }
    rec.onstop = () => {
      stream.getTracks().forEach((t) => t.stop())
      blobRef.current = new Blob(chunksRef.current, { type: rec.mimeType || mime || 'audio/webm' })
      transcribe()
    }
    recRef.current = rec
    rec.start(1000)
    secondsRef.current = 0
    setSeconds(0)
    setPhase('recording')
    timerRef.current = setInterval(() => {
      secondsRef.current += 1
      setSeconds(secondsRef.current)
      if (secondsRef.current >= MAX_SECONDS) stop()
    }, 1000)
  }

  function stop() {
    clearInterval(timerRef.current)
    const rec = recRef.current
    if (rec && rec.state !== 'inactive') rec.stop()
  }

  async function transcribe() {
    setPhase('transcribing')
    setError('')
    try {
      const res = await api.transcribeKompasJournal(blobRef.current)
      setRaw(res.text)
      setText(res.text)
      setPhase('review')
    } catch (e) {
      setError(e.message || 'Transkripsi gagal.')
      setPhase('failed')
    }
  }

  function writeManually() {
    setRaw('')
    setText('')
    setPhase('review')
  }

  function reset() {
    blobRef.current = null
    setRaw('')
    setText('')
    setError('')
    setPhase('idle')
  }

  async function save() {
    const body = text.trim()
    if (phase === 'saving' || body.length < 20) return
    setPhase('saving')
    setError('')
    try {
      const created = await api.createKompasJournal({
        raw_transcript: raw || body,
        text: body,
        day: ymd(new Date()),
        duration_seconds: secondsRef.current || null,
      })
      setJournals((prev) => [created, ...prev])
      reset()
      onSaved?.()
    } catch (e) {
      setError(e.message || 'Gagal menyimpan jurnal. Teksmu masih ada, coba lagi.')
      setPhase('review')
    }
  }

  async function remove(id) {
    try {
      await api.deleteKompasJournal(id)
      setJournals((prev) => prev.filter((j) => j.id !== id))
    } catch (e) {
      setError(e.message || 'Gagal menghapus jurnal.')
    }
  }

  return (
    <section className="rounded-xl border border-ink-border bg-ink-surface p-4 md:p-5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 className="font-display text-base text-text-primary">Jurnal suara</h2>
        <span className="text-xs text-text-muted">5 hook dikirim 3 jam setelah disimpan</span>
      </div>

      {phase === 'idle' && (
        <div className="mt-4 flex items-center gap-4">
          <button
            type="button"
            onClick={start}
            className="shrink-0 h-14 w-14 rounded-full bg-accent text-ink flex items-center justify-center glow-accent-sm active:scale-95 transition-transform"
            aria-label="Mulai rekam jurnal"
          >
            <Mic size={24} strokeWidth={2} />
          </button>
          <p className="text-sm text-text-muted">
            Ceritakan apa yang kamu pelajari, hadapi, dan temukan hari ini. 2 sampai 5 menit cukup, dengan bahasamu sendiri.
          </p>
        </div>
      )}

      {phase === 'recording' && (
        <div className="mt-4 flex items-center gap-4">
          <button
            type="button"
            onClick={stop}
            className="shrink-0 h-14 w-14 rounded-full border-2 border-accent text-accent flex items-center justify-center animate-pulse"
            aria-label="Berhenti merekam"
          >
            <Square size={20} fill="currentColor" />
          </button>
          <div>
            <p className="font-display text-2xl text-text-primary tabular-nums">{clock(seconds)}</p>
            <p className="text-xs text-text-muted">Merekam. Tekan kotak untuk berhenti.</p>
          </div>
        </div>
      )}

      {phase === 'transcribing' && (
        <p className="mt-4 flex items-center gap-2 text-sm text-text-muted">
          <Loader2 size={16} className="animate-spin" /> Mengubah suara menjadi teks…
        </p>
      )}

      {phase === 'failed' && (
        <div className="mt-4 space-y-3">
          <p className="text-sm text-warning">{error}</p>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={transcribe}
              className="px-3 py-2 rounded-lg border border-ink-border text-sm text-text-primary hover:border-accent/50 flex items-center gap-1.5"
            >
              <RotateCcw size={14} /> Transkripsi ulang
            </button>
            <button
              type="button"
              onClick={writeManually}
              className="px-3 py-2 rounded-lg border border-ink-border text-sm text-text-muted hover:border-accent/50"
            >
              Tulis manual
            </button>
            <button type="button" onClick={reset} className="px-3 py-2 text-sm text-text-muted hover:text-text-primary">
              Buang rekaman
            </button>
          </div>
        </div>
      )}

      {(phase === 'review' || phase === 'saving') && (
        <div className="mt-4 space-y-3">
          <label htmlFor="journal-text" className="text-xs text-text-muted">
            Baca dan koreksi dulu. Transkrip asli tetap tersimpan terpisah.
          </label>
          <textarea
            id="journal-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            disabled={phase === 'saving'}
            className="w-full rounded-lg bg-ink-elevated border border-ink-border p-3 text-sm text-text-primary leading-relaxed focus:outline-none focus:border-accent"
          />
          {error && <p className="text-sm text-warning">{error}</p>}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={save}
              disabled={phase === 'saving' || text.trim().length < 20}
              className="px-4 py-2 rounded-lg bg-accent text-ink text-sm font-medium disabled:opacity-40 flex items-center gap-1.5"
            >
              {phase === 'saving' && <Loader2 size={14} className="animate-spin" />}
              Simpan jurnal
            </button>
            <button type="button" onClick={reset} disabled={phase === 'saving'} className="px-3 py-2 text-sm text-text-muted hover:text-text-primary">
              Buang
            </button>
          </div>
        </div>
      )}

      {error && phase === 'idle' && <p className="mt-3 text-sm text-warning">{error}</p>}

      {journals.length > 0 && (
        <ul className="mt-5 divide-y divide-ink-border border-t border-ink-border">
          {journals.slice(0, 7).map((j) => (
            <li key={j.id} className="py-2.5">
              <div className="flex items-center justify-between gap-2">
                <button
                  type="button"
                  onClick={() => setOpen(open === j.id ? null : j.id)}
                  className="flex-1 min-w-0 text-left"
                  aria-expanded={open === j.id}
                >
                  <p className="text-sm text-text-primary truncate">{j.edited_text}</p>
                  <p className={`text-xs mt-0.5 ${j.status === 'failed' ? 'text-warning' : 'text-text-muted'}`}>
                    {j.day} · {statusLabel(j)}
                  </p>
                </button>
                {j.hooks && (
                  <ChevronDown size={16} className={`shrink-0 text-text-muted transition-transform ${open === j.id ? 'rotate-180' : ''}`} />
                )}
                {(j.status === 'pending' || j.status === 'failed') && (
                  <button
                    type="button"
                    onClick={() => remove(j.id)}
                    aria-label="Hapus jurnal"
                    title="Hapus jurnal"
                    className="w-8 h-8 shrink-0 rounded-md flex items-center justify-center text-text-muted hover:text-accent hover:bg-ink-elevated"
                  >
                    <Trash2 size={15} />
                  </button>
                )}
              </div>
              {open === j.id && j.hooks && (
                <ol className="mt-2 space-y-3 pl-1">
                  {j.hooks.map((h, i) => (
                    <li key={i} className="text-sm">
                      <p className="text-text-primary">“{h.hook}”</p>
                      <p className="text-xs text-text-muted mt-0.5">
                        {h.pola} · {h.format}
                      </p>
                      <p className="text-xs text-text-muted mt-1">Kenapa kuat: {h.alasan}</p>
                      <p className="text-xs text-text-muted mt-1">Sumber: “{h.kutipan}”</p>
                    </li>
                  ))}
                </ol>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
