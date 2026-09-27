import { useState } from 'react'
import { Settings as SettingsIcon, Trash2 } from 'lucide-react'
import Trash from './Trash'

// Settings sekarang punya isi (sebelumnya cuma ComingSoon). Tab "Sampah"
// merender ulang komponen Trash.jsx yang sudah ada persis apa adanya --
// fungsinya (lihat/pulihkan/hapus permanen) tidak berubah sama sekali, cuma
// pindah dari menu utama sendiri jadi tab di sini (hasil diskusi navbar).
const TABS = [
  { id: 'umum', label: 'Umum' },
  { id: 'sampah', label: 'Sampah', icon: Trash2 },
]

export default function Settings() {
  const [tab, setTab] = useState('umum')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-text-primary">Settings</h1>
        <p className="text-text-muted text-sm mt-1">Pengaturan akun dan platform.</p>
      </div>

      <div className="flex items-center gap-1 border-b border-ink-border">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm border-b-2 -mb-px transition-colors ${
              tab === t.id
                ? 'border-accent text-accent'
                : 'border-transparent text-text-muted hover:text-text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'umum' && (
        <div className="bg-ink-surface border border-ink-border rounded-lg px-8 py-16 flex flex-col items-center text-center gap-3">
          <div className="w-12 h-12 rounded-full bg-ink-elevated border border-ink-border flex items-center justify-center">
            <SettingsIcon size={20} className="text-accent" strokeWidth={1.5} />
          </div>
          <div className="text-text-primary text-sm font-medium">Segera hadir</div>
          <p className="text-text-muted text-sm max-w-md">
            Pengaturan akun, API key, dan konfigurasi platform lainnya. Belum dibangun.
          </p>
        </div>
      )}

      {tab === 'sampah' && <Trash />}
    </div>
  )
}
