// Bagian bersama Panggung: format angka, panel, grafik tren.
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceDot,
} from 'recharts'

export const COLORS = ['#7cfc3c', '#5bb8d4', '#a77bff', '#f5b942', '#8a9484']
export const flag = (name) => new URLSearchParams(window.location.search).has(name)
export const fmt = (n) => new Intl.NumberFormat('id-ID').format(n)
export const sum = (rows, k) => rows.reduce((n, x) => n + (x[k] || 0), 0)
export const money = (v) => (v >= 1e6 ? { num: (v / 1e6).toFixed(2).replace('.', ','), unit: 'jt' } : { num: String(Math.round(v / 1000)), unit: 'rb' })
export const rp = (v) => { const m = money(v); return `Rp ${m.num} ${m.unit}` }
const axisMoney = (v) => (v === 0 ? '0' : v >= 1e6 ? `${(v / 1e6).toFixed(1).replace('.', ',')} jt` : `${Math.round(v / 1000)} rb`)
const dayFmt = new Intl.DateTimeFormat('id-ID', { day: 'numeric', month: 'short' })

export function Money({ v }) {
  const m = money(v)
  return <span className="st-money"><span className="st-cur">Rp</span>{m.num}<span className="st-unit">{m.unit}</span></span>
}

export function ago(t, now) {
  if (!t) return 'belum ada'
  const s = Math.max(0, ((now - t) / 1000) | 0)
  return s < 5 ? 'baru saja' : s < 60 ? `${s} dtk lalu` : s < 3600 ? `${(s / 60) | 0} mnt lalu` : `${(s / 3600) | 0} jam lalu`
}

export function Panel({ title, note, action, children, className = '' }) {
  return (
    <section className={`st-panel ${className}`}>
      {title && <h2><span>{title}</span>{note && <span className="st-note">{note}</span>}{action}</h2>}
      {children}
    </section>
  )
}

export function TrendChart({ trend }) {
  const n = trend.length
  const empty = trend.every((x) => x.rev === 0)
  const todayMs = Date.now()
  const data = trend.map((x, i) => ({
    label: dayFmt.format(new Date(todayMs - (n - 1 - i) * 864e5)),
    full: i < n - 1 ? x.rev : null,
    today: i >= n - 2 ? x.rev : null, // hari ini belum penuh: putus-putus supaya tidak terbaca "penjualan anjlok"
  }))
  const last = data[n - 1]
  return (
    <div className="st-chart">
      {empty && <div className="st-chart-empty">Belum ada penjualan dari dataset terpercaya</div>}
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 20, right: 64, left: 0, bottom: 4 }} accessibilityLayer={false}>
          <defs>
            <linearGradient id="stg" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7cfc3c" stopOpacity={0.32} />
              <stop offset="100%" stopColor="#7cfc3c" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#232b20" strokeDasharray="3 6" vertical={false} />
          <XAxis dataKey="label" tick={{ fill: '#8a9484', fontSize: 12 }} axisLine={false} tickLine={false} interval={n > 14 ? 4 : 0} />
          <YAxis hide={empty} width={58} tickCount={4} domain={[0, 'auto']} tick={{ fill: '#8a9484', fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={axisMoney} />
          {!empty && <Tooltip formatter={(v, name) => [rp(v), name]} contentStyle={{ background: '#12160f', border: '1px solid #232b20', borderRadius: 10, color: '#e8ede5' }} />}
          {!empty && <Area type="monotone" dataKey="full" name="Omzet" stroke="#7cfc3c" strokeWidth={2.5} fill="url(#stg)" isAnimationActive={false} connectNulls={false} />}
          {!empty && <Area type="monotone" dataKey="today" name="Hari ini" stroke="#7cfc3c" strokeWidth={2.5} strokeDasharray="5 5" fill="none" isAnimationActive={false} connectNulls={false} />}
          {!empty && last.today > 0 && (
            <ReferenceDot
              x={last.label} y={last.today} r={5.5} fill="#7cfc3c" stroke="#0a0d0a" strokeWidth={2} ifOverflow="extendDomain"
              label={{ value: `Hari ini ${rp(last.today)}`, position: 'bottom', fill: '#e8ede5', fontSize: 13 }}
            />
          )}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
