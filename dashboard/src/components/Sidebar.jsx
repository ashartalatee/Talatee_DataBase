import { NavLink } from 'react-router-dom'
import { LayoutGrid, Briefcase, Database, Boxes, ListOrdered, HardDrive, UploadCloud } from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: LayoutGrid, end: true },
  { to: '/businesses', label: 'Businesses', icon: Briefcase },
  { to: '/sources', label: 'Sources', icon: Database },
  { to: '/datasets', label: 'Datasets', icon: Boxes },
  { to: '/jobs', label: 'Jobs', icon: ListOrdered },
  { to: '/storage', label: 'Storage', icon: HardDrive },
]

export default function Sidebar() {
  return (
    <aside className="w-60 shrink-0 border-r border-ink-border bg-ink-surface flex flex-col">
      <div className="px-5 py-6 border-b border-ink-border">
        <div className="font-display text-accent text-sm tracking-widest uppercase">
          Talatee
        </div>
        <div className="text-text-muted text-xs mt-1">Personal Data Vault</div>
      </div>

      <div className="px-3 pt-4">
        <NavLink
          to="/upload"
          className={({ isActive }) =>
            `glow-accent flex items-center justify-center gap-2 px-3 py-2.5 rounded-md text-sm font-medium transition-all ${
              isActive
                ? 'bg-accent-soft text-ink'
                : 'bg-accent text-ink hover:bg-accent-soft'
            }`
          }
        >
          <UploadCloud size={16} strokeWidth={2} />
          Upload Data
        </NavLink>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
                isActive
                  ? 'glow-accent-sm bg-ink-elevated text-accent border border-accent/40'
                  : 'text-text-muted hover:text-text-primary hover:bg-ink-elevated/60'
              }`
            }
          >
            <Icon size={16} strokeWidth={1.75} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-ink-border">
        <div className="text-[11px] font-display text-text-muted leading-relaxed">
          Raw data is never overwritten.
          <br />
          Every batch is a new ledger line.
        </div>
      </div>
    </aside>
  )
}
