// Isi mentah + laporan masalah satu batch DEMO (hanya mode API), diambil dari GET /stage/batches/{id}.
// Isi batch tidak berubah setelah masuk, jadi hasilnya disimpan per id.
import { useEffect, useState } from 'react'
import { api } from '../api/client'

const cache = new Map()

export function useBatchDetail(id) {
  const [, bump] = useState(0)
  useEffect(() => {
    if (!id || cache.has(id) || !api.getStageBatch) return undefined
    let alive = true
    api.getStageBatch(id)
      .then((d) => { cache.set(id, d); if (alive) bump((n) => n + 1) })
      .catch((e) => { console.warn('[panggung]', e) })
    return () => { alive = false }
  }, [id])
  return id ? cache.get(id) || null : null
}

// Menggabungkan detail ke batch dari ringkasan, dalam bentuk yang dipahami tabel Data mentah.
export function mergeDetail(batch, d) {
  if (!batch || !d || !d.raw || !d.raw.columns) return batch
  const cols = d.raw.columns
  const issues = (d.issues && d.issues.issues) || []
  const flags = {}
  const dupRows = new Set()
  let fmt = 0
  let empty = 0
  for (const it of issues) {
    const r = it.row - 1
    flags[r] = flags[r] || {}
    if (it.type === 'duplikat') { dupRows.add(r); flags[r]._row = 'dup'; continue }
    const kind = String(it.value || '').trim() === '' ? 'empty' : 'format'
    if (it.column) flags[r][it.column] = kind
    if (kind === 'empty') empty += 1
    else fmt += 1
  }
  const raw = d.raw.rows.map((vals, i) => ({
    c: Object.fromEntries(cols.map((c, j) => [c, vals[j] ?? ''])),
    flags: flags[i] || {},
  }))
  const total = d.raw.total_rows ?? batch.rows
  return { ...batch, cols, raw, rows: total, stats: { kept: Math.max(0, total - dupRows.size), dup: dupRows.size, empty, fmt } }
}
