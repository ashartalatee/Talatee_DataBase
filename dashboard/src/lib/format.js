export function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const value = bytes / Math.pow(1024, i)
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

export function formatNumber(n) {
  return new Intl.NumberFormat('en-US').format(n ?? 0)
}

export function formatCurrency(n) {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    maximumFractionDigits: 0,
  }).format(n ?? 0)
}

export function formatDateTime(iso) {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatRelative(iso) {
  if (!iso) return '-'
  const then = new Date(iso).getTime()
  const now = Date.now()
  const diffSec = Math.floor((now - then) / 1000)
  if (diffSec < 60) return 'baru saja'
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin} menit lalu`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} jam lalu`
  const diffDay = Math.floor(diffHour / 24)
  return `${diffDay} hari lalu`
}

export const STATUS_STYLES = {
  success: { label: 'Success', dot: 'bg-success', text: 'text-success' },
  running: { label: 'Running', dot: 'bg-info', text: 'text-info' },
  failed: { label: 'Failed', dot: 'bg-danger', text: 'text-danger' },
  partial_failed: { label: 'Partial Failed', dot: 'bg-[#E8C547]', text: 'text-[#E8C547]' },
}

export function statusStyle(status) {
  return STATUS_STYLES[status] || { label: status, dot: 'bg-text-muted', text: 'text-text-muted' }
}

// Palet warna konsisten untuk chart per-source (dipetakan dari index, bukan
// acak, supaya warna source yang sama selalu sama di seluruh dashboard).
// Hijau brand jadi warna utama (source pertama), sisanya variasi untuk
// membedakan source lain tanpa bentrok dengan warna aksen/status.
const CHART_PALETTE = ['#7CFC3C', '#5BB8D4', '#E8C547', '#FF5C5C', '#B08CE0', '#3DDC97', '#E08A6E']

export function colorForIndex(i) {
  return CHART_PALETTE[i % CHART_PALETTE.length]
}
