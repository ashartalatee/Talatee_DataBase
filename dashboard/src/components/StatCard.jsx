export default function StatCard({ label, value, sublabel }) {
  return (
    <div className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4">
      <div className="text-text-muted text-xs uppercase tracking-wider">{label}</div>
      <div className="font-display text-3xl text-text-primary mt-2 tabular-nums">
        {value}
      </div>
      {sublabel && <div className="text-text-muted text-xs mt-1">{sublabel}</div>}
    </div>
  )
}
