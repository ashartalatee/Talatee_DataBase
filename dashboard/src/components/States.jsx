import { AlertTriangle } from 'lucide-react'

export function LoadingState({ label = 'Memuat data' }) {
  return (
    <div className="flex items-center gap-3 text-text-muted text-sm py-12 justify-center">
      <span className="w-3 h-3 rounded-full bg-accent animate-pulse" />
      {label}...
    </div>
  )
}

export function ErrorState({ message }) {
  return (
    <div className="flex flex-col items-center gap-2 text-center py-12">
      <AlertTriangle size={20} className="text-danger" strokeWidth={1.75} />
      <div className="text-text-primary text-sm font-medium">Gagal memuat data</div>
      <div className="text-text-muted text-xs max-w-sm">{message}</div>
      <div className="text-text-muted text-xs mt-2">
        Pastikan backend jalan di <span className="font-display">localhost:8000</span>
      </div>
    </div>
  )
}

export function EmptyState({ label }) {
  return <div className="text-text-muted text-sm py-12 text-center">{label}</div>
}
