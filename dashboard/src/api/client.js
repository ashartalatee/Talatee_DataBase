// BASE_URL fleksibel supaya dashboard tetap bisa manggil backend walau
// diakses lewat VS Code port forwarding (devtunnels), bukan cuma localhost:
//
// 1. Kalau ada env var VITE_API_BASE_URL (isi di dashboard/.env), itu yang
//    dipakai -- cara paling eksplisit/aman, cocok kalau backend di-deploy
//    ke tempat lain sama sekali.
// 2. Kalau hostname sekarang 'localhost'/'127.0.0.1', backend diasumsikan
//    juga di localhost:8000 (kondisi dev normal sehari-hari).
// 3. Kalau hostname berbentuk devtunnels (mis. https://abc123-5173.asse.devtunnels.ms),
//    otomatis diganti jadi port 8000 dengan pola URL yang sama
//    (https://abc123-8000.asse.devtunnels.ms) -- INI ASUMSI: backend HARUS
//    di-forward juga di VS Code dengan tunnel id yang SAMA, port 8000.
// 4. Fallback terakhir: origin yang sama, port 8000 (untuk kasus lain
//    seperti akses lewat IP LAN dengan port beda).
function resolveBaseUrl() {
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }

  const { hostname, protocol } = window.location

  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000'
  }

  // Pola devtunnels: <tunnel-id>-<port>.<region>.devtunnels.ms
  const devtunnelMatch = hostname.match(/^(.+)-(\d+)(\..+\.devtunnels\.ms)$/)
  if (devtunnelMatch) {
    const [, tunnelId, , suffix] = devtunnelMatch
    return `${protocol}//${tunnelId}-8000${suffix}`
  }

  return `${protocol}//${hostname}:8000`
}

const BASE_URL = resolveBaseUrl()

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { Accept: 'application/json' },
    credentials: 'include',
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      if (body.detail && typeof body.detail === 'object') {
        // beberapa endpoint (mis. POST /datasets/{id}/promote) mengirim
        // detail berbentuk {message, errors, warnings} biar frontend bisa
        // tampilkan rinci — di sini cukup ambil message-nya untuk Error()
        detail = body.detail.message || JSON.stringify(body.detail)
      } else {
        detail = body.detail || detail
      }
    } catch {
      // response tidak berbentuk JSON, pakai statusText apa adanya
    }
    if (
      res.status === 401 &&
      path !== '/auth/login' &&
      path !== '/auth/me' &&
      window.location.pathname !== '/login'
    ) {
      window.location.href = '/login'
    }
    throw new Error(`${res.status}: ${detail}`)
  }
  if (res.status === 204) {
    return null
  }
  return res.json()
}

export const api = {
  login: (username, password) =>
    request('/auth/login', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/auth/me'),

  getOverview: () => request('/stats/overview'),

  listBusinessCategories: () => request('/businesses/categories'),
  listBusinesses: (trust) => request(trust ? `/businesses?trust=${trust}` : '/businesses'),
  getBusiness: (id) => request(`/businesses/${id}`),
  getBusinessSources: (id) => request(`/businesses/${id}/sources`),

  listSources: (businessId) =>
    request(businessId ? `/sources?business_id=${businessId}` : '/sources'),
  getSource: (id) => request(`/sources/${id}`),

  listDatasets: (trust) => request(trust ? `/datasets?trust=${trust}` : '/datasets'),
  getDataset: (id) => request(`/datasets/${id}`),
  listBatches: (datasetId) =>
    request(datasetId ? `/batches?dataset_id=${datasetId}` : '/batches'),
  getBatch: (id) => request(`/batches/${id}`),
  getBatchRows: (id) => request(`/batches/${id}/rows`),
  getBatchIssues: (id) => request(`/batches/${id}/issues`),
  getBatchClean: (id) => request(`/batches/${id}/clean`),

  // Trash (hapus sesaat) & Purge (hapus permanen) — satu pola konsisten di
  // 3 level (source/dataset/batch). purge* butuh confirmName yang harus
  // persis sama dengan nama entity-nya (dicek juga di backend) supaya
  // hapus permanen tidak pernah ke-klik tanpa sengaja.
  listTrash: () => request('/trash'),
  listDeletionLog: () => request('/trash/log'),

  trashBusiness: (id) => request(`/businesses/${id}/trash`, { method: 'POST' }),
  restoreBusiness: (id) => request(`/businesses/${id}/restore`, { method: 'POST' }),
  purgeBusiness: (id, confirmName, reason) =>
    request(`/businesses/${id}/permanent`, {
      method: 'DELETE',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm_name: confirmName, reason }),
    }),

  trashSource: (id) => request(`/sources/${id}/trash`, { method: 'POST' }),
  restoreSource: (id) => request(`/sources/${id}/restore`, { method: 'POST' }),
  purgeSource: (id, confirmName, reason) =>
    request(`/sources/${id}/permanent`, {
      method: 'DELETE',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm_name: confirmName, reason }),
    }),

  trashDataset: (id) => request(`/datasets/${id}/trash`, { method: 'POST' }),
  restoreDataset: (id) => request(`/datasets/${id}/restore`, { method: 'POST' }),
  purgeDataset: (id, confirmName, reason) =>
    request(`/datasets/${id}/permanent`, {
      method: 'DELETE',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm_name: confirmName, reason }),
    }),

  trashBatch: (id) => request(`/batches/${id}/trash`, { method: 'POST' }),
  restoreBatch: (id) => request(`/batches/${id}/restore`, { method: 'POST' }),
  purgeBatch: (id, confirmName, reason) =>
    request(`/batches/${id}/permanent`, {
      method: 'DELETE',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm_name: confirmName, reason }),
    }),

  uploadFile: (businessName, businessCategory, sourceName, datasetName, file) => {
    const formData = new FormData()
    formData.append('business_name', businessName)
    formData.append('business_category', businessCategory)
    formData.append('source_name', sourceName)
    formData.append('dataset_name', datasetName)
    formData.append('file', file)
    return request('/ingest/upload/dashboard', { method: 'POST', body: formData })
  },

  // Mode "File ini campur beberapa channel" -- TANPA source_name, karena
  // source-nya diambil dari kolom channel/platform/marketplace/sumber di
  // dalam file itu sendiri (lihat app/ingestion/mixed_channel.py). Return
  // LIST of batches (satu per channel yang ditemukan), bukan satu batch.
  uploadFileMixed: (businessName, businessCategory, datasetName, file) => {
    const formData = new FormData()
    formData.append('business_name', businessName)
    formData.append('business_category', businessCategory)
    formData.append('dataset_name', datasetName)
    formData.append('file', file)
    return request('/ingest/upload/mixed/dashboard', { method: 'POST', body: formData })
  },

  fileDownloadUrl: (id) => `${BASE_URL}/files/${id}/download`,

  processDataset: (id) => request(`/datasets/${id}/process`, { method: 'POST' }),
  getInsights: (id) => request(`/datasets/${id}/insights`),
  getDatasetQuality: (id) => request(`/datasets/${id}/quality`),
  promoteDataset: (id) => request(`/datasets/${id}/promote`, { method: 'POST' }),
  createCorrection: (id, body) =>
    request(`/datasets/${id}/corrections`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listCorrections: (id) => request(`/datasets/${id}/corrections`),
  runReconciliation: (id, body) =>
    request(`/datasets/${id}/reconciliation`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }),
  listReconciliations: (id) => request(`/datasets/${id}/reconciliation`),
  getDataPassport: (id) => request(`/datasets/${id}/passport`),

  getKompasCheckins: () => request('/kompas/checkins'),
  setKompasCheckin: (habit, day, done) =>
    request('/kompas/checkins', {
      method: 'PUT',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ habit, day, done }),
    }),
  importKompas: (payload) =>
    request('/kompas/import', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  listKompasIdeas: () => request('/kompas/ideas'),
  createKompasIdea: (text) =>
    request('/kompas/ideas', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    }),
  updateKompasIdea: (id, payload) =>
    request(`/kompas/ideas/${id}`, {
      method: 'PATCH',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  deleteKompasIdea: (id) => request(`/kompas/ideas/${id}`, { method: 'DELETE' }),

  listKompasParked: () => request('/kompas/parked'),
  createKompasParked: (text, reason) =>
    request('/kompas/parked', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, reason: reason || null }),
    }),
  updateKompasParked: (id, payload) =>
    request(`/kompas/parked/${id}`, {
      method: 'PATCH',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  deleteKompasParked: (id) => request(`/kompas/parked/${id}`, { method: 'DELETE' }),

  getKompasFunnel: () => request('/kompas/funnel'),
  bumpKompasFunnel: (stream, stage, delta) =>
    request(`/kompas/funnel/${stream}/${stage}`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ delta }),
    }),

  listKompasReviews: () => request('/kompas/reviews'),
  saveKompasReview: (weekStart, payload) =>
    request(`/kompas/reviews/${weekStart}`, {
      method: 'PUT',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),

  listKompasReading: (day) => request(day ? `/kompas/reading?day=${day}` : '/kompas/reading'),
  createKompasReading: (url, title) =>
    request('/kompas/reading', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, title: title || null }),
    }),
  updateKompasReading: (id, payload) =>
    request(`/kompas/reading/${id}`, {
      method: 'PATCH',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  deleteKompasReading: (id) => request(`/kompas/reading/${id}`, { method: 'DELETE' }),

  listProjects: () => request('/projects'),
  createProject: (payload) =>
    request('/projects', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  updateProject: (id, payload) =>
    request(`/projects/${id}`, {
      method: 'PATCH',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  deleteProject: (id) => request(`/projects/${id}`, { method: 'DELETE' }),
  demoteProject: (id) => request(`/projects/${id}/demote`, { method: 'POST' }),

  listLabEntries: () => request('/lab-entries'),
  getLabEntry: (id) => request(`/lab-entries/${id}`),
  createLabEntry: (payload) =>
    request('/lab-entries', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  updateLabEntry: (id, payload) =>
    request(`/lab-entries/${id}`, {
      method: 'PATCH',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }),
  deleteLabEntry: (id) => request(`/lab-entries/${id}`, { method: 'DELETE' }),
  promoteLabEntry: (id) => request(`/lab-entries/${id}/promote`, { method: 'POST' }),

  // AI Analyst -- diteruskan lewat backend (bukan browser -> Hermes
  // langsung), supaya API key Hermes tidak pernah sampai ke browser.
  // Stateless di sisi server: `history` (state React di AIAnalyst.jsx)
  // dikirim ulang tiap kali supaya Hermes tetap tahu konteks percakapan.
  sendChatMessage: (message, history) =>
    request('/api/chat', {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
    }),
}
