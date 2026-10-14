// Halaman 1: Gudang Data. Data masuk APA ADANYA (mentah, belum diubah sedikit pun).
import { Lock, ArrowRight } from 'lucide-react'
import { Panel, ago } from './stageUi'

const STATUS = {
  masuk: ['Masuk', 'b'], diproses: ['Diproses', 'y'], bersih: ['Bersih', 'g'], tinjau: ['Perlu ditinjau', 'r'],
}
const LEGEND = [['empty', 'kosong'], ['format', 'format berbeda'], ['dup', 'duplikat']]

export function BatchList({ batches, selectedId, onSelect, now, limit = 5 }) {
  return (
    <div className="st-bl">
      {batches.length === 0 && <p className="st-empty">Belum ada data masuk. Gudang akan terisi begitu file pertama datang.</p>}
      {batches.length > 0 && <div className="st-wait-card"><i className="st-dot" />Menunggu kedatangan berikutnya: upload, bridge, atau API</div>}
      {batches.slice(0, limit).map((b) => {
        const [label, tone] = STATUS[b.status] || STATUS.masuk
        return (
          <button key={b.id} type="button" className={`st-bc${b.id === selectedId ? ' sel' : ''}`} onClick={() => onSelect(b.id)}>
            <span className="st-bct"><b>{b.file}</b><span className={`st-badge ${tone}`}>{b.status === 'diproses' && <i className="st-spin" />}{label}</span></span>
            <span className="st-bcm">{b.channel} · {b.rows} baris · {ago(b.t, now)}</span>
          </button>
        )
      })}
    </div>
  )
}

export function RawTable({ batch, limit = 8 }) {
  if (!batch) return <p className="st-empty">Pilih satu kedatangan untuk melihat isi mentahnya.</p>
  const rows = batch.raw.slice(0, limit)
  return (
    <div className="st-tw">
      <table className="st-table raw">
        <thead><tr><th>#</th>{batch.cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className={Object.values(r.flags).includes('dup') ? 'dup' : ''}>
              <td className="n">{i + 1}</td>
              {batch.cols.map((c) => {
                const f = r.flags[c]
                const v = r.c[c]
                return <td key={c} className={f ? `f-${f}` : ''} title={f ? LEGEND.find((x) => x[0] === f)?.[1] : undefined}>{v === '' ? '∅' : v}</td>
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default function StageGudang({ batches, selected, selectedId, onSelect, onGoClean, now, compact }) {
  return (
    <div className="st-page pg-gudang">
      <Panel title="Kedatangan" note={`${batches.length} file`} className="p-arrive">
        <BatchList batches={batches} selectedId={selectedId} onSelect={onSelect} now={now} limit={compact ? 3 : 6} />
      </Panel>
      <Panel
        title="Data mentah" className="p-raw"
        action={<span className="st-lock"><Lock size={13} strokeWidth={2} />tidak diubah</span>}
      >
        <div className="st-legend">
          {LEGEND.map(([k, l]) => <span key={k}><i className={`lg-${k}`} />{l}</span>)}
        </div>
        <RawTable batch={selected} limit={compact ? 9 : 10} />
        {selected && (
          <div className="st-find">
            <div><b>{selected.rows}</b><span>baris masuk</span></div>
            <div className="y"><b>{selected.stats.fmt + selected.stats.empty}</b><span>nilai perlu diperbaiki</span></div>
            <div className="b"><b>{selected.stats.dup}</b><span>baris duplikat</span></div>
            <div className="r"><b>{selected.stats.empty}</b><span>sel kosong</span></div>
          </div>
        )}
        <div className="st-rawfoot">
          <span>{selected ? `${selected.file}: menampilkan ${Math.min(selected.raw.length, compact ? 9 : 10)} dari ${selected.rows} baris, persis seperti yang masuk` : ''}</span>
          {selected && (selected.status === 'bersih' || selected.status === 'tinjau') && (
            <button type="button" className="st-link" onClick={() => onGoClean(selected.id)}>Lihat versi bersih <ArrowRight size={14} /></button>
          )}
        </div>
      </Panel>
    </div>
  )
}
