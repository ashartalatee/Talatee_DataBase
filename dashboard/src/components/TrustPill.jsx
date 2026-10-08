import { ShieldAlert, ShieldCheck, ShieldQuestion } from 'lucide-react'

const TRUST_META = {
  INGESTED: {
    label: 'INGESTED',
    desc: 'Data masuk, belum divalidasi',
    cls: 'text-text-muted border-ink-border',
    icon: ShieldQuestion,
  },
  VALIDATING: {
    label: 'VALIDATING',
    desc: 'Lolos quality check, belum di-promote',
    cls: 'text-warning border-warning/40',
    icon: ShieldAlert,
  },
  NEEDS_REVIEW: {
    label: 'NEEDS REVIEW',
    desc: 'Ada error, perlu ditinjau sebelum dipercaya',
    cls: 'text-danger border-danger/40',
    icon: ShieldAlert,
  },
  TRUSTED: {
    label: 'TRUSTED',
    desc: 'Sudah di-promote, aman untuk analisis',
    cls: 'text-success border-success/40',
    icon: ShieldCheck,
  },
}

export default function TrustPill({ status }) {
  const cfg = TRUST_META[status] || TRUST_META.INGESTED
  const Icon = cfg.icon
  return (
    <span
      title={cfg.desc}
      className={`inline-flex items-center gap-1 text-[10px] font-display tracking-wider border rounded-full px-2 py-0.5 shrink-0 ${cfg.cls}`}
    >
      <Icon size={10} /> {cfg.label}
    </span>
  )
}
