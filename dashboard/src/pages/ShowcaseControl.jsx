import { Radio } from 'lucide-react'

// Ruang kendali: hanya terlihat dari dalam dashboard (di balik login dan
// sidebar). Penonton tidak pernah melihat halaman ini, hanya /stage.
const PLANNED = [
  { title: 'Simulator data', note: 'Mengirim transaksi demo lewat jalur upload asli.' },
  { title: 'Reset demo', note: 'Mengembalikan data demo ke keadaan bersih sebelum siaran.' },
  { title: 'Status kesehatan', note: 'Postgres, penyimpanan, API, WhatsApp, dan Hermes dalam satu layar.' },
  { title: 'Log Hermes', note: 'Pertanyaan, tool yang dipanggil, dan sumber jawaban.' },
]

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

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
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
