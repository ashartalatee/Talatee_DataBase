const BASE_URL = 'http://localhost:8000'

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { Accept: 'application/json' },
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch {
      // response tidak berbentuk JSON, pakai statusText apa adanya
    }
    throw new Error(`${res.status}: ${detail}`)
  }
  if (res.status === 204) {
    return null
  }
  return res.json()
}

export const api = {
  getOverview: () => request('/stats/overview'),

  listBusinessCategories: () => request('/businesses/categories'),
  listBusinesses: () => request('/businesses'),
  getBusiness: (id) => request(`/businesses/${id}`),
  getBusinessSources: (id) => request(`/businesses/${id}/sources`),

  listSources: (businessId) =>
    request(businessId ? `/sources?business_id=${businessId}` : '/sources'),
  getSource: (id) => request(`/sources/${id}`),

  listDatasets: () => request('/datasets'),
  getDataset: (id) => request(`/datasets/${id}`),

  listBatches: (datasetId) =>
    request(datasetId ? `/batches?dataset_id=${datasetId}` : '/batches'),
  getBatch: (id) => request(`/batches/${id}`),

  uploadFile: (businessName, businessCategory, sourceName, datasetName, file) => {
    const formData = new FormData()
    formData.append('business_name', businessName)
    formData.append('business_category', businessCategory)
    formData.append('source_name', sourceName)
    formData.append('dataset_name', datasetName)
    formData.append('file', file)
    return request('/ingest/upload/dashboard', { method: 'POST', body: formData })
  },

  fileDownloadUrl: (id) => `${BASE_URL}/files/${id}/download`,

  processDataset: (id) => request(`/datasets/${id}/process`, { method: 'POST' }),
  getInsights: (id) => request(`/datasets/${id}/insights`),

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
}
