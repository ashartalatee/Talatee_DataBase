/**
 * Halaman placeholder untuk bagian Control Center yang sudah ada di peta
 * (visi TALATEE_CONTROL_CENTER.md) tapi belum dibangun beneran — misal AI
 * Analyst, Automations, Monitoring. Sengaja TIDAK menampilkan angka palsu
 * (konsisten dengan prinsip "jangan pernah memalsukan data" yang sudah
 * dipegang di proyek lain) — cuma penanda "segera" yang jujur.
 */
export default function ComingSoon({ icon: Icon, title, description, tier }) {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-text-primary">{title}</h1>
        {tier && (
          <span className="inline-block mt-2 text-[11px] font-display uppercase tracking-wider px-2 py-0.5 rounded border border-ink-border text-text-muted">
            {tier}
          </span>
        )}
      </div>

      <div className="bg-ink-surface border border-ink-border rounded-lg px-8 py-16 flex flex-col items-center text-center gap-3">
        {Icon && (
          <div className="w-12 h-12 rounded-full bg-ink-elevated border border-ink-border flex items-center justify-center">
            <Icon size={20} className="text-accent" strokeWidth={1.5} />
          </div>
        )}
        <div className="text-text-primary text-sm font-medium">Segera hadir</div>
        <p className="text-text-muted text-sm max-w-md">{description}</p>
      </div>
    </div>
  )
}
