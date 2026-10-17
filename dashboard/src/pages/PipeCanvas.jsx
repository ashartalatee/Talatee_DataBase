// Kanvas alur data Panggung: lima node dan kurva penghubung.
// Semua gerak dipicu data nyata (cap waktu flow.*.last lewat "ticks", langkah agen lewat "working"), bukan timer.
import { Upload, Database, ShieldCheck, MessageSquare, FileText } from 'lucide-react'

const W = 208
const H = 148
const YS = [30, 8, 42, 12, 34]
const WIRES = [
  'M208 104 C249 104 249 82 290 82',
  'M498 82 C539 82 539 116 580 116',
  'M788 116 C829 116 829 86 870 86',
  'M1078 86 C1119 86 1119 108 1160 108',
]
const NODES = [
  { key: 'file', Icon: Upload, title: 'File masuk', sub: 'Upload atau bridge', busy: 'Menerima file...' },
  { key: 'batch', Icon: Database, title: 'Batch tercatat', sub: 'Postgres + mentah', busy: 'Mencatat batch...' },
  { key: 'trust', Icon: ShieldCheck, title: 'Status kepercayaan', sub: 'Baru ke terpercaya', busy: 'Memvalidasi aturan...' },
  { key: 'question', Icon: MessageSquare, title: 'Hermes bertanya', sub: 'Lewat MCP, hanya baca', busy: 'Hermes membaca data...' },
  { key: 'answer', Icon: FileText, title: 'Jawaban + sumbernya', sub: 'Dengan sumber data', busy: 'Menyusun jawaban...' },
]

export default function PipeCanvas({ val, ticks, working, now, hermesOn, trustParts, ago }) {
  const total = trustParts.reduce((n, p) => n + p.n, 0)
  return (
    <section className="pc" aria-label="Alur data">
      <svg className="pc-svg" viewBox="0 0 1368 200" role="img" aria-label="Alur data lima tahap, dari file masuk sampai jawaban dengan sumbernya">
        <defs>
          <pattern id="pc-dg" width="24" height="24" patternUnits="userSpaceOnUse"><circle className="pc-dc" cx="2" cy="2" r="1.1" /></pattern>
          <radialGradient id="pc-vg" cx=".5" cy=".5" r=".72">
            <stop offset=".55" style={{ stopColor: 'var(--panel)', stopOpacity: 0 }} />
            <stop offset="1" style={{ stopColor: 'var(--panel)', stopOpacity: 0.95 }} />
          </radialGradient>
        </defs>
        <rect width="1368" height="200" fill="url(#pc-dg)" />
        <rect width="1368" height="200" fill="url(#pc-vg)" />
        {WIRES.map((d, i) => (
          <g key={d}>
            <path className="pc-w" d={d} />
            {ticks[i + 1] > 0 && <path key={ticks[i + 1]} className="pc-tv" pathLength="100" d={d} />}
          </g>
        ))}
        {NODES.map(({ key, Icon, title, sub, busy }, i) => {
          const [v, last] = val[key]
          const off = !hermesOn && (key === 'question' || key === 'answer')
          const on = !off && !!(working[key] || (last && now - last < 2500))
          const t = ticks[i]
          let bx = 20
          return (
            <g key={key} transform={'translate(' + i * 290 + ',' + YS[i] + ')'} className={'pc-n' + (on ? ' on' : '') + (off ? ' off' : '')}>
              <rect className="pc-nb" width={W} height={H} rx="16" />
              <rect className="pc-ng" width={W} height={H} rx="16" />
              {t > 0 && <rect key={'f' + t} className="pc-fl" width={W} height={H} rx="16" />}
              <circle className="pc-ring" cx="38" cy="36" r="18" />
              <circle className="pc-ic" cx="38" cy="36" r="18" />
              <Icon x="26" y="24" size={24} strokeWidth={1.8} />
              {t > 0 && <text key={'p' + t} className="pc-pl" x="186" y="20" textAnchor="end">+1</text>}
              <text className="pc-num" x="186" y="50" textAnchor="end">{v}</text>
              <text className="pc-t" x="20" y="84">{title}</text>
              <text className="pc-s" x="20" y="100">{sub}</text>
              {key === 'trust' && (
                <g>
                  <rect x="20" y="106" width="168" height="5" rx="2.5" className="pc-track" />
                  {trustParts.map((p, k) => {
                    const w = total ? (p.n / total) * 168 : 0
                    const x = bx
                    bx += w
                    return w > 0 ? <rect key={k} x={x} y="106" width={Math.max(w - 2, 1)} height="5" rx="2.5" fill={p.c} /> : null
                  })}
                </g>
              )}
              <line className="pc-sp" x1="20" x2="188" y1="120" y2="120" />
              <circle className="pc-dot" cx="25" cy="135" r="3.5" />
              <text className="pc-ag" x="36" y="139">{off ? 'Belum tersambung' : on ? busy : ago(last, now)}</text>
              {i > 0 && <circle className="pc-po" cx="0" cy="74" r="5" />}
              {i < NODES.length - 1 && <circle className="pc-po" cx={W} cy="74" r="5" />}
            </g>
          )
        })}
      </svg>
    </section>
  )
}
