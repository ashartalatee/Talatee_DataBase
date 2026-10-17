// Halaman 2: Data Bersih dan Insight. Hasil kerja agen: tabel bersih, angka, grafik, dan insight.
import { ArrowLeft, Sparkles, Wrench } from 'lucide-react'
import { Panel, Money, TrendChart, COLORS, fmt, rp } from './stageUi'

const SHOW = ['order_id', 'tanggal', 'produk', 'qty', 'harga_satuan', 'subtotal', 'status']
const LABEL = { harga_satuan: 'harga' }

function CleanTable({ batch, limit }) {
  if (!batch) return <p className="st-empty">Belum ada data bersih.</p>
  if (batch.status === 'masuk' || batch.status === 'diproses') {
    return <div className="st-wait"><i className="st-spin" />Agen sedang membersihkan {batch.file}…</div>
  }
  const cols = batch.cols.filter((c) => SHOW.includes(c))
  return (
    <div className="st-tw">
      <table className="st-table clean">
        <thead><tr><th>#</th>{cols.map((c) => <th key={c}>{LABEL[c] || c}</th>)}</tr></thead>
        <tbody>
          {batch.clean.slice(0, limit).map((r, i) => (
            <tr key={i}>
              <td className="n">{i + 1}</td>
              {cols.map((c) => <td key={c} className={r.fixed.includes(c) ? 'fx' : ''} title={r.fixed.includes(c) ? 'diperbaiki agen' : undefined}>{r.c[c]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function StageBersih({
  metrics, trendView, range, setRange, insights, categories, channels, batches, selected, onSelect, onGoRaw, compact,
}) {
  const { omzet, order, last7, deltaTxt, deltaTone, trusted, trustTotal, today } = metrics
  const chanMax = Math.max(1, ...channels.map((c) => c.value))
  const catTotal = categories.reduce((n, c) => n + c.value, 0) || 1
  const st = selected && selected.stats
  return (
    <div className="st-page pg-bersih">
      <section className="st-hero">
        <div className="st-panel st-herocard">
          <small className="st-label">Omzet 30 hari</small>
          <div className="st-herov"><Money v={omzet} /></div>
          <div className="st-d">{order > 0 ? `rata-rata ${rp(omzet / order)} per order` : 'dari batch terpercaya'}{deltaTone && <span className={`st-chip ${deltaTone}`}>{deltaTxt}</span>}</div>
        </div>
        <div className="st-panel st-kpi"><small className="st-label">Order 30 hari</small><div className="st-kv">{fmt(order)}</div><div className="st-d">hari ini: {fmt(today)}</div></div>
        <div className="st-panel st-kpi"><small className="st-label">Omzet 7 hari</small><div className="st-kv"><Money v={last7} /></div><div className={`st-d ${deltaTone}`}>{deltaTxt}</div></div>
        <div className="st-panel st-kpi"><small className="st-label">Batch terpercaya</small><div className="st-kv">{trustTotal ? `${Math.round((trusted / trustTotal) * 100)}%` : '–'}</div><div className="st-d">{trusted} dari {trustTotal} batch</div></div>
      </section>

      <div className="st-brow2">
        <Panel
          title="Tren penjualan" className="p-trend"
          action={<span className="st-seg" role="group" aria-label="Rentang tren">{[7, 30].map((r) => <button key={r} type="button" aria-pressed={range === r} className={range === r ? 'on' : ''} onClick={() => setRange(r)}>{r}H</button>)}</span>}
        >
          <TrendChart trend={trendView} />
        </Panel>
        <Panel title="Insight dari agen" note={insights.length ? `${insights.length} terbaru` : ''} className="p-ins">
          <ul className="st-ins">
            {insights.length === 0 && <li className="st-tlempty">Insight muncul setelah agen selesai memproses data.</li>}
            {insights.slice(0, compact ? 2 : 3).map((x) => (
              <li key={x.id} className={`${x.tone || ''}${x.batchId ? ' link' : ''}`} onClick={() => x.batchId && onSelect(x.batchId)}>
                <span className="st-insi"><Sparkles size={15} strokeWidth={2} /></span>
                <div><b>{x.title}</b><span>{x.text}</span></div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      <div className="st-brow3">
        <Panel
          title="Data bersih" className="p-clean"
          action={selected ? <button type="button" className="st-link" onClick={() => onGoRaw(selected.id)}><ArrowLeft size={14} />Lihat data mentah</button> : null}
        >
          <CleanTable batch={selected} limit={compact ? 4 : 5} />
          {st && selected.status !== 'masuk' && selected.status !== 'diproses' && (
            <div className="st-fixsum"><Wrench size={14} />{selected.rows} baris mentah menjadi {st.kept} baris bersih: {st.dup} duplikat dibuang, {st.fmt + st.empty} nilai diperbaiki</div>
          )}
        </Panel>
        <Panel title="Omzet per channel" note="30 hari" className="p-chan">
          {channels.length === 0 && <p className="st-empty">Belum ada data channel.</p>}
          {channels.slice(0, 5).map((c, i) => (
            <div key={c.name} className="st-rb"><span>{c.name}</span><div className="st-rt"><i style={{ width: `${(c.value / chanMax) * 100}%`, background: COLORS[i % COLORS.length] }} /></div><b>{rp(c.value)}</b></div>
          ))}
          {categories.length > 0 && (
            <div className="st-catbar">
              <div className="st-bar">{categories.map((c, i) => <i key={c.name} style={{ width: `${(c.value / catTotal) * 100}%`, background: COLORS[i % COLORS.length] }} />)}</div>
              <div className="st-minileg catleg">{categories.map((c, i) => <span key={c.name}><i style={{ background: COLORS[i % COLORS.length] }} />{c.name} {Math.round((c.value / catTotal) * 100)}%</span>)}</div>
            </div>
          )}
        </Panel>
      </div>
    </div>
  )
}
