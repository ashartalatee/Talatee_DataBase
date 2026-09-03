import { NavLink } from 'react-router-dom'
import {
  LayoutGrid,
  FlaskConical,
  FolderKanban,
  Users,
  Activity,
  Database,
  Workflow,
  BarChart3,
  Bot,
  ScrollText,
  Plug,
  FileText,
  Settings,
  UploadCloud,
} from 'lucide-react'

const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: LayoutGrid, end: true },
  { to: '/laboratorium', label: 'Talatee Laboratorium', icon: FlaskConical },
  { to: '/proyek', label: 'Proyek', icon: FolderKanban },
  { to: '/businesses', label: 'Clients', icon: Users },
  { to: '/monitoring', label: 'Monitoring', icon: Activity },
  { to: '/datasets', label: 'Databases', icon: Database },
  { to: '/automations', label: 'Automations', icon: Workflow },
  { to: '/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/ai-analyst', label: 'AI Analyst', icon: Bot },
  { to: '/jobs', label: 'Logs & Errors', icon: ScrollText },
  { to: '/sources', label: 'Integrations', icon: Plug },
  { to: '/reports', label: 'Reports', icon: FileText },
  { to: '/settings', label: 'Settings', icon: Settings },
]

function navLinkClass({ isActive }) {
  return `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
    isActive
      ? 'glow-accent-sm bg-ink-elevated text-accent border border-accent/40'
      : 'text-text-muted hover:text-text-primary hover:bg-ink-elevated/60'
  }`
}

export default function Sidebar() {
  return (
    <aside className="w-64 shrink-0 border-r border-ink-border bg-ink-surface flex flex-col">
      <div className="px-5 py-6 border-b border-ink-border">
        <div className="font-display text-accent text-sm tracking-widest uppercase">
          Talatee
        </div>
        <div className="text-text-muted text-xs mt-1">Control Center</div>
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

      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={navLinkClass}>
            <Icon size={16} strokeWidth={1.75} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-4 py-4 border-t border-ink-border flex items-center gap-3">
        <div className="w-8 h-8 rounded-full bg-accent/15 border border-accent/30 flex items-center justify-center text-accent text-xs font-display font-semibold shrink-0">
          A
        </div>
        <div className="min-w-0">
          <div className="text-text-primary text-sm truncate">Ashar</div>
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-success" />
            <span className="text-text-muted text-xs">Owner</span>
          </div>
        </div>
      </div>
    </aside>
  )
}
