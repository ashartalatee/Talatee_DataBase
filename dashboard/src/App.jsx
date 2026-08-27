import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Overview from './pages/Overview'
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
            </Routes>
          </div>
        </main>
      </div>
    </BrowserRouter>
  )
}
