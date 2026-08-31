import { ArrowRight } from 'lucide-react'

const STAGES = [
  { title: 'Alat Tempur Utama', detail: 'Konten TikTok, Live, Branding' },
  { title: 'Menarik & Menemukan Client', detail: 'Audience \u2192 Tertarik \u2192 DM \u2192 Deal' },
  { title: 'Proyek untuk Client', detail: 'Dashboard, Automation, Database' },
  { title: 'Talatee Control Center', detail: 'Monitor, Analisa, Kelola', highlight: true },
  { title: 'Client Bertambah', detail: 'Lebih banyak client & impact' },
]

/**
 * Diagram alur ekosistem Talatee, diambil dari kata-kata visi kamu sendiri
 * (Alat Tempur -> Client -> Proyek -> Talatee Control Center -> Client
 * Bertambah, lalu berputar lagi lewat "Belajar dari data -> Improve").
 * Full-width, satu baris di layar besar (wrap otomatis di layar sempit) —
 * label TIDAK PERNAH dipotong (...), lebih baik turun baris.
 */
export default function EcosystemDiagram() {
  return (
    <div className="w-full">
      <div className="flex flex-wrap items-stretch gap-2.5">
        {STAGES.map((stage, i) => (
          <div key={stage.title} className="flex items-center gap-2.5">
            <div
              className={`w-40 shrink-0 rounded-lg border px-3.5 py-3 ${
                stage.highlight
                  ? 'border-accent/50 bg-accent/5 glow-accent-sm'
                  : 'border-ink-border bg-ink-elevated'
              }`}
            >
              <div
                className={`text-xs font-medium leading-snug ${
                  stage.highlight ? 'text-accent' : 'text-text-primary'
                }`}
              >
                {stage.title}
              </div>
              <div className="text-[11px] text-text-muted mt-1.5 leading-snug">
                {stage.detail}
              </div>
            </div>
            {i < STAGES.length - 1 && (
              <ArrowRight
                size={16}
                className="text-text-muted shrink-0"
                strokeWidth={1.75}
              />
            )}
          </div>
        ))}
      </div>
      <div className="text-text-muted text-[11px] mt-3 font-display tracking-wide">
        BELAJAR DARI DATA &rarr; IMPROVE &rarr; BUAT LAGI &rarr; SKALA
      </div>
    </div>
  )
}
