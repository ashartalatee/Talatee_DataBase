import { useState } from 'react'
import { Database, Plug } from 'lucide-react'
import Datasets from './Datasets'
import Sources from './Sources'

// Gabungan Databases + Integrations -- keduanya sebenarnya laporan audit
// LINTAS-klien (semua dataset / semua source dari semua business digabung
// jadi satu list datar), bukan alur kerja harian. Alur harian tetap lewat
// Clients -> klik satu klien -> BusinessDetail (yang sudah menampilkan
// sources klien itu sendiri). Komponen Datasets.jsx dan Sources.jsx dipakai
// ulang persis apa adanya, cuma pindah dari 2 menu utama jadi 1 menu bertab
// (hasil diskusi navbar).
const TABS = [
  { id: 'databases', label: 'Databases', icon: Database },
  { id: 'integrations', label: 'Integrations', icon: Plug },
]

export default function DataExplorer() {
  const [tab, setTab] = useState('databases')

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-1 border-b border-ink-border">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm border-b-2 -mb-px transition-colors ${
              tab === t.id
                ? 'border-accent text-accent'
                : 'border-transparent text-text-muted hover:text-text-primary'
            }`}
          >
            <t.icon size={14} strokeWidth={1.75} />
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'databases' && <Datasets />}
      {tab === 'integrations' && <Sources />}
    </div>
  )
}
