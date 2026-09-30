import { NavLink } from 'react-router-dom'
import {
  LayoutGrid,
  Compass,
  FlaskConical,
  FolderKanban,
  Users,
  Database,
  Bot,
  Terminal,
  ScrollText,
  Settings,
  UploadCloud,
  X,
} from 'lucide-react'

// Sengaja rata, TANPA section header -- percobaan sebelumnya (grup + header
// "Data Klien"/"Pengembangan Proyek"/"Sistem") malah menambah tinggi scroll,
// bukan mengurangi. Perbaikan sebenarnya: buang menu yang belum ada isinya
// sama sekali (Monitoring/Automations/Analytics/Reports -- semua masih
// ComingSoon, routenya tetap ada di App.jsx, cuma tidak ditaut dari sini
// sampai beneran dibangun -- lihat TALATEE_CONTROL_CENTER.md untuk
// roadmap-nya), dan gabung Databases+Integrations jadi satu "Data Explorer"
// bertab (sama pola dengan Settings/Sampah di bawah -- keduanya cuma
// laporan audit lintas-klien, jarang dibuka langsung dibanding Clients).
//
// "AI Analyst" sempat dibuang dari daftar ini waktu masih ComingSoon kosong,
// sekarang dikembalikan karena beneran jalan (chat asli ke Hermes lewat
// /api/chat -- lihat pages/AIAnalyst.jsx), ditaruh dekat Hermes karena
// dua-duanya soal AI. "Talatee Laboratorium" tetap "Eksperimen" (tabrakan
// nama sama kolom "01 -- Laboratorium" di papan Proyek).
const NAV_ITEMS = [
  { to: '/', label: 'Kompas', icon: Compass, end: true },
  { to: '/overview', label: 'Overview', icon: LayoutGrid },
  { to: '/businesses', label: 'Clients', icon: Users },
  { to: '/data-explorer', label: 'Data Explorer', icon: Database },
  { to: '/proyek', label: 'Proyek', icon: FolderKanban },
  { to: '/laboratorium', label: 'Eksperimen', icon: FlaskConical },
  { to: '/ai-analyst', label: 'AI Analyst', icon: Bot },
  { to: '/hermes', label: 'Hermes', icon: Terminal },
  { to: '/jobs', label: 'Logs & Errors', icon: ScrollText },
  { to: '/settings', label: 'Settings', icon: Settings },
]

function navLinkClass({ isActive }) {
  return `flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors ${
    isActive
      ? 'glow-accent-sm bg-ink-elevated text-accent border border-accent/40'
      : 'text-text-muted hover:text-text-primary hover:bg-ink-elevated/60'
  }`
}

// Sidebar HARUS selalu terlihat di desktop (md ke atas, statis di layout
// flex seperti semula), tapi di layar sempit (HP) dia jadi drawer yang
// nge-slide dari kiri, ditumpuk di atas backdrop gelap -- dikontrol lewat
// prop `open`/`onClose` dari App.jsx. Tanpa ini, sidebar w-64 fixed akan
// mendorong konten utama sampai overflow di layar sempit (persis bug yang
// terlihat di screenshot HP).
export default function Sidebar({ open, onClose }) {
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 bg-black/60 z-30 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-40 w-64 shrink-0 border-r border-ink-border bg-ink-surface flex flex-col
          transform transition-transform duration-200 ease-out
          md:static md:translate-x-0
          ${open ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="px-5 py-6 border-b border-ink-border flex items-center justify-between">
          <div>
            <div className="font-display text-accent text-sm tracking-widest uppercase">
              Talatee
            </div>
            <div className="text-text-muted text-xs mt-1">Control Center</div>
          </div>
          <button onClick={onClose} className="md:hidden text-text-muted hover:text-text-primary p-1">
            <X size={18} />
          </button>
        </div>

        <div className="px-3 pt-4">
          <NavLink
            to="/upload"
            onClick={onClose}
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
            <NavLink key={to} to={to} end={end} className={navLinkClass} onClick={onClose}>
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
    </>
  )
}
