import { useCallback, useEffect, useState } from 'react'
import { Radio, RefreshCw } from 'lucide-react'
import { api } from '../api/client'

// Ruang kendali: hanya terlihat dari dalam dashboard (di balik login dan
// sidebar). Penonton tidak pernah melihat halaman ini, hanya /stage.
const PLANNED = [
  { title: 'Simulator data', note: 'Mengirim transaksi demo lewat jalur upload asli.' },
  { title: 'Reset demo', note: 'Mengembalikan data demo ke keadaan bersih sebelum siaran.' },
  { title: 'Log Hermes', note: 'Pertanyaan, tool yang dipanggil, dan sumber jawaban.' },
]

const POLL_MS = 10000

const STATUS_STYLE = {
  ok: { dot: 'bg-success', text: 'text-success', label: 'Normal' },
  slow: { dot: 'bg-warning', text: 'text-warning', label: 'Lambat' },
  down: { dot: 'bg-danger', text: 'text-danger', label: 'Mati' },
  unconfigured: { dot: 'bg-text-muted', text: 'text-text-muted', label: 'Belum diatur' },
}

const OVERALL_TEXT = {
  ok: 'Semua komponen normal',
  degraded: 'Ada komponen yang lambat',
  down: 'Ada komponen yang mati',
}

function HealthCard() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [checking, setChecking] = useState(false)

  const check = useCallback(async () => {
    setChecking(true)
    try {
      const res = await api.getShowcaseHealth()
      setData(res)
      setError(null)
    } catch {
      // Pesan sengaja generik: tidak menampilkan galat mentah di layar.
      setError('Tidak bisa menghubungi API')
    } finally {
      setChecking(false)
    }
  }, [])

  useEffect(() => {
    check()
    const id = setInterval(check, POLL_MS)
    return () => clearInterval(id)
  }, [check])

  const summary = error ? error : data ? OVERALL_TEXT[data.overall] : 'Memeriksa…'
  const summaryColor = error
    ? 'text-danger'
    : data?.overall === 'ok'
      ? 'text-success'
      : data?.overall === 'degraded'
        ? 'text-warning'
        : data?.overall === 'down'
          ? 'text-danger'
          : 'text-text-muted'

  return (
    <div className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="text-text-primary text-sm font-medium">Status kesehatan</div>
          <div className={`text-xs mt-1 ${summaryColor}`}>{summary}</div>
        </div>
        <button
          onClick={check}
          disabled={checking}
          className="flex items-center gap-1.5 text-xs text-accent hover:underline disabled:opacity-50"
        >
          <RefreshCw size={12} className={checking ? 'animate-spin' : ''} />
          Periksa sekarang
        </button>
      </div>

      {data && (
        <ul className="mt-4 divide-y divide-ink-border">
          {data.components.map((c) => {
            const s = STATUS_STYLE[c.status] || STATUS_STYLE.unconfigured
            return (
              <li key={c.id} className="py-2.5 flex items-center gap-3 text-sm">
                <span className={`w-2 h-2 rounded-full shrink-0 ${s.dot}`} />
                <span className="text-text-primary w-44 shrink-0">{c.label}</span>
                <span className={`text-xs w-24 shrink-0 ${s.text}`}>{s.label}</span>
                <span className="text-text-muted text-xs font-display w-16 shrink-0 tabular-nums">
                  {c.latency_ms != null ? `${c.latency_ms} ms` : ''}
                </span>
                <span className="text-text-muted text-xs min-w-0 truncate">{c.note}</span>
              </li>
            )
          })}
        </ul>
      )}

      {data && (
        <div className="text-text-muted text-[11px] font-display mt-3">
          Diperiksa {new Date(data.checked_at).toLocaleTimeString('id-ID')}
          {error ? ' (data terakhir yang berhasil)' : ' · otomatis tiap 10 detik'}
        </div>
      )}
    </div>
  )
}

export default function ShowcaseControl() {
  function openStage() {
    window.open('/stage', '_blank', 'noopener')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <div className="flex items-center gap-2">
            <Radio size={18} className="text-accent" strokeWidth={1.75} />
            <h1 className="font-display text-xl text-text-primary">Showcase</h1>
          </div>
          <p className="text-text-muted text-sm mt-1 max-w-xl">
            Ruang kendali untuk Panggung. Dari sini kamu menyiapkan data demo dan membuka
            tampilan yang dibagikan ke penonton.
          </p>
        </div>
        <button
          onClick={openStage}
          className="glow-accent-sm bg-accent text-ink font-medium text-sm rounded-md px-4 py-2 hover:bg-accent-soft transition-colors"
        >
          Buka Panggung
        </button>
      </div>

      <HealthCard />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {PLANNED.map((item) => (
          <div
            key={item.title}
            className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4"
          >
            <div className="text-text-primary text-sm font-medium">{item.title}</div>
            <div className="text-text-muted text-xs mt-1">{item.note}</div>
            <div className="text-text-muted text-xs mt-3">Belum dibangun</div>
          </div>
        ))}
      </div>
    </div>
  )
}
