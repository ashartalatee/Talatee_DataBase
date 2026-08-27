import { statusStyle } from '../lib/format'

export default function StatusBadge({ status }) {
  const { label, dot, text } = statusStyle(status)
  return (
    <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  )
}
