// Rel "Agen Hermes": status kerja, langkah yang sedang berjalan, dan garis waktu kejadian.
// Isinya kejadian pipeline yang nyata (baca, bersihkan, validasi, percaya, insight) plus jawaban Hermes.
import { Bot, Upload, Search, Eraser, ShieldCheck, Sparkles, MessageSquare, FileText } from 'lucide-react'
import { ago } from './stageUi'

const STEPS = [
  ['read', 'Baca', Search], ['clean', 'Bersihkan', Eraser], ['validate', 'Validasi', ShieldCheck],
  ['trust', 'Percaya', ShieldCheck], ['insight', 'Insight', Sparkles],
]
const ICONS = { file: Upload, read: Search, clean: Eraser, validate: ShieldCheck, trust: ShieldCheck, insight: Sparkles, hermes: MessageSquare, info: FileText }

export default function StageAgent({ agent, events, now, onPick, limit = 6, hermesOn }) {
  const working = agent.status === 'working'
  const stepIdx = STEPS.findIndex(([k]) => k === agent.step)
  return (
    <section className="st-panel st-agent" aria-label="Agen Hermes">
      <header className="st-ah">
        <span className={`st-orb${working ? ' on' : ''}`}><Bot size={22} strokeWidth={1.75} /></span>
        <div className="st-ahtx">
          <b>Agen Hermes</b>
          <small>{working ? agent.label : 'Siaga, menunggu data masuk'}</small>
        </div>
        <span className={`st-state${working ? ' on' : ''}`}>{working ? 'Bekerja' : 'Siaga'}</span>
      </header>

      <ol className="st-steps" aria-label="Langkah agen">
        {STEPS.map(([k, label, Icon], i) => (
          <li key={k} className={working ? (i < stepIdx ? 'done' : i === stepIdx ? 'now' : '') : (agent.lastDone ? 'done' : '')}>
            <span className="st-si"><Icon size={14} strokeWidth={2} /></span>
            <em>{label}</em>
          </li>
        ))}
      </ol>

      <ul className="st-tl">
        {events.length === 0 && <li className="st-tlempty">{hermesOn === false ? 'Belum ada kejadian. Log Hermes belum tersambung.' : 'Belum ada kejadian. Agen akan bekerja begitu data masuk.'}</li>}
        {events.slice(0, limit).map((e, i) => {
          const Icon = ICONS[e.kind] || FileText
          return (
            <li key={`${e.t}-${i}`} className={`k-${e.kind} ${e.tone || ''}${e.batchId ? ' link' : ''}`} onClick={() => e.batchId && onPick(e)}>
              <span className="st-tli"><Icon size={14} strokeWidth={2} /></span>
              <div className="st-tlb">
                <span className="st-tlt">{e.kind === 'hermes' ? e.q : e.text}</span>
                {e.kind === 'hermes' && <span className="st-tla">{e.a}</span>}
                {e.kind === 'hermes' && <span className="st-tlc">{(e.sources || []).map((s) => <span key={s} className="st-chip src">{s}</span>)}</span>}
                <time>{ago(e.t, now)}</time>
              </div>
            </li>
          )
        })}
      </ul>
    </section>
  )
}
