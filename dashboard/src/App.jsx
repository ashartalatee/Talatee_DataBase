import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import { Activity, Workflow, BarChart3, FileText, Menu } from 'lucide-react'
import Sidebar from './components/Sidebar'
import ComingSoon from './components/ComingSoon'
import Login from './pages/Login'
import Overview from './pages/Overview'
import Laboratorium from './pages/Laboratorium'
import LabEntryDetail from './pages/LabEntryDetail'
import Proyek from './pages/Proyek'
import Upload from './pages/Upload'
import Businesses from './pages/Businesses'
import BusinessDetail from './pages/BusinessDetail'
import Sources from './pages/Sources'
import SourceDetail from './pages/SourceDetail'
import Datasets from './pages/Datasets'
import DatasetDetail from './pages/DatasetDetail'
import DataExplorer from './pages/DataExplorer'
import Jobs from './pages/Jobs'
import JobDetail from './pages/JobDetail'
import Storage from './pages/Storage'
import Trash from './pages/Trash'
import Hermes from './pages/Hermes'
import SettingsPage from './pages/Settings'
import AIAnalyst from './pages/AIAnalyst'

// Halaman /login dirender BERDIRI SENDIRI (full-screen, tanpa Sidebar) --
// beda dari semua halaman lain yang selalu dibungkus layout Sidebar+main.
// Dipisah lewat useLocation() di sini, bukan direstrukturisasi total ke pola
// nested-route+Outlet, supaya semua <Route> yang sudah ada di bawah tidak
// perlu diubah sama sekali.
function AppShell() {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Tutup sidebar otomatis tiap kali pindah halaman (UX standar untuk
  // mobile drawer -- tanpa ini, sidebar tetap terbuka menutupi halaman
  // baru setelah user klik salah satu menu).
  useEffect(() => {
    setSidebarOpen(false)
  }, [location.pathname])

  if (location.pathname === '/login') {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
      </Routes>
    )
  }

  return (
    <div className="flex h-screen bg-ink font-body">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
        <div className="flex-1 flex flex-col min-w-0">
          {/* Top bar cuma tampil di layar sempit (HP/tablet) -- di desktop
              sidebar selalu terlihat jadi tidak perlu tombol menu. */}
          <div className="md:hidden flex items-center gap-3 px-4 py-3 border-b border-ink-border bg-ink-surface shrink-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="text-text-muted hover:text-text-primary p-1"
              aria-label="Buka menu"
            >
              <Menu size={20} />
            </button>
            <span className="font-display text-accent text-xs tracking-widest uppercase">
              Talatee
            </span>
          </div>

          <main className="flex-1 overflow-y-auto px-4 md:px-8 py-4 md:py-8">
            <div className="max-w-6xl mx-auto">
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/laboratorium" element={<Laboratorium />} />
              <Route path="/laboratorium/:id" element={<LabEntryDetail />} />
              <Route path="/proyek" element={<Proyek />} />
              <Route path="/upload" element={<Upload />} />
              <Route path="/businesses" element={<Businesses />} />
              <Route path="/businesses/:id" element={<BusinessDetail />} />
              <Route path="/sources" element={<Sources />} />
              <Route path="/sources/:id" element={<SourceDetail />} />
              <Route path="/datasets" element={<Datasets />} />
              <Route path="/datasets/:id" element={<DatasetDetail />} />
              <Route path="/data-explorer" element={<DataExplorer />} />
              <Route path="/jobs" element={<Jobs />} />
              <Route path="/jobs/:id" element={<JobDetail />} />
              <Route path="/storage" element={<Storage />} />
              <Route path="/trash" element={<Trash />} />
              <Route path="/hermes" element={<Hermes />} />

              {/* Bagian yang masih di peta visi, belum dibangun beneran —
                  lihat TALATEE_CONTROL_CENTER.md untuk rencana lengkapnya. */}
              <Route
                path="/monitoring"
                element={
                  <ComingSoon
                    icon={Activity}
                    title="Monitoring"
                    description="Status kesehatan sistem per client (online/warning/error) — akan aktif begitu ada automation nyata yang perlu dipantau."
                  />
                }
              />
              <Route
                path="/automations"
                element={
                  <ComingSoon
                    icon={Workflow}
                    title="Automations"
                    description="Daftar automation (n8n, webhook, scheduled job) beserta statusnya. Belum ada automation yang tersambung ke Talatee."
                  />
                }
              />
              <Route
                path="/analytics"
                element={
                  <ComingSoon
                    icon={BarChart3}
                    title="Analytics"
                    description="Insight gabungan lintas client/dataset. Saat ini insight baru tersedia per dataset — buka salah satu dataset untuk lihat revenue, growth, dan top produk."
                  />
                }
              />
              <Route path="/ai-analyst" element={<AIAnalyst />} />
              <Route
                path="/reports"
                element={
                  <ComingSoon
                    icon={FileText}
                    title="Reports"
                    description="Laporan siap-kirim (PDF/WA) yang dirangkum otomatis dari insight tiap dataset. Belum dibangun."
                  />
                }
              />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
            </div>
          </main>
        </div>
      </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  )
}
