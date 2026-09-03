import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Activity, Workflow, BarChart3, Bot, FileText, Settings } from 'lucide-react'
import Sidebar from './components/Sidebar'
import ComingSoon from './components/ComingSoon'
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
import Jobs from './pages/Jobs'
import JobDetail from './pages/JobDetail'
import Storage from './pages/Storage'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-ink font-body">
        <Sidebar />
        <main className="flex-1 overflow-y-auto px-8 py-8">
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
              <Route path="/jobs" element={<Jobs />} />
              <Route path="/jobs/:id" element={<JobDetail />} />
              <Route path="/storage" element={<Storage />} />

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
              <Route
                path="/ai-analyst"
                element={
                  <ComingSoon
                    icon={Bot}
                    title="AI Analyst"
                    description="Tanya data pakai bahasa natural, misal 'produk apa yang penjualannya naik bulan ini?'. Belum dibangun."
                  />
                }
              />
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
              <Route
                path="/settings"
                element={
                  <ComingSoon
                    icon={Settings}
                    title="Settings"
                    description="Pengaturan akun, API key, dan preferensi Control Center. Belum dibangun."
                  />
                }
              />
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  )
}
