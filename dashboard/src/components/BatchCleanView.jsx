import { useState } from 'react'
import { useFetch } from '../lib/useFetch'
import { api } from '../api/client'
import { LoadingState, ErrorState } from './States'

const TABS = [
    { id: 'banding', label: 'Perbandingan' },
    { id: 'bersih', label: 'Data Bersih' },
    { id: 'karantina', label: 'Karantina' },
]

function Val({ v }) {
    return v === '' ? <span className="text-text-muted">∅</span> : <span>{v}</span>
}

export default function BatchCleanView({ batchId }) {
    const { data, loading, error } = useFetch(() => api.getBatchClean(batchId), [batchId])
    const [tab, setTab] = useState('banding')

    if (loading) return <LoadingState label="Memuat data bersih" />
    if (error) return <ErrorState message={error} />
    if (!data) return null

    const rec = data.reconciliation
    const cols = data.columns

    const changeMap = {}
    for (const c of data.changes) changeMap[`${c.row}|${c.column}`] = c

    const qMap = {}
    for (const q of data.quarantine) qMap[q.row] = q

    const all = [
        ...data.clean.map((r) => ({ ...r, status: 'bersih' })),
        ...data.quarantine.map((q) => ({ row: q.row, values: q.values, status: 'karantina' })),
    ].sort((a, b) => a.row - b.row)

    const th = 'px-4 py-2'
    const td = 'px-4 py-2 text-text-primary whitespace-pre'

    return (
        <div className="bg-ink-surface border border-ink-border rounded-lg">
            <div className="px-5 py-4 border-b border-ink-border">
                <h2 className="text-sm font-medium text-text-primary">Data Bersih dan Perbandingan</h2>
                <p className="text-xs text-text-muted mt-1">
                    Layer terpisah dari Data Asli (asli tidak diubah). Hanya perbaikan yang pasti dilakukan otomatis;
                    sisanya masuk karantina, tidak ditebak dan tidak dihapus.
                </p>
            </div>

            <div className="px-5 py-3 border-b border-ink-border text-xs space-y-2">
                <div className="text-text-primary font-display">
                    Asli {rec.original} = Bersih {rec.clean} + Karantina {rec.quarantine} + Dibuang {rec.dropped}{' '}
                    {rec.balanced ? (
                        <span className="text-accent">✓ cocok</span>
                    ) : (
                        <span className="text-danger">✗ TIDAK COCOK, ada data hilang</span>
                    )}
                </div>
                <div className="text-text-muted">
                    Aturan otomatis:{' '}
                    {data.rules.map((r) => `${r.label}: ${r.cells} sel`).join(' · ')}
                </div>
            </div>

            <div className="px-5 pt-3 flex gap-2 border-b border-ink-border">
                {TABS.map((t) => (
                    <button
                        key={t.id}
                        onClick={() => setTab(t.id)}
                        className={`px-3 py-2 text-xs border-b-2 ${tab === t.id ? 'border-accent text-accent' : 'border-transparent text-text-muted hover:text-text-primary'
                            }`}
                    >
                        {t.label}
                        {t.id === 'bersih' && ` (${rec.clean})`}
                        {t.id === 'karantina' && ` (${rec.quarantine})`}
                    </button>
                ))}
            </div>

            <div className="overflow-x-auto">
                {tab === 'banding' && (
                    <table className="w-full text-xs font-display">
                        <thead>
                            <tr className="text-left text-text-muted uppercase tracking-wider">
                                <th className={`${th} w-12`}>#</th>
                                <th className={th}>Status</th>
                                {cols.map((c, i) => <th key={i} className={th}>{c}</th>)}
                                <th className={th}>Keterangan</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-ink-border">
                            {all.map((r) => {
                                const q = qMap[r.row]
                                return (
                                    <tr key={r.row}>
                                        <td className="px-4 py-2 text-text-muted">{r.row}</td>
                                        <td className="px-4 py-2">
                                            {r.status === 'bersih' ? (
                                                <span className="text-accent">Bersih</span>
                                            ) : (
                                                <span className="text-yellow-400">Karantina</span>
                                            )}
                                        </td>
                                        {cols.map((c, j) => {
                                            const ch = changeMap[`${r.row}|${c}`]
                                            return (
                                                <td key={j} className={`${td} ${ch ? 'bg-green-500/15 outline outline-1 outline-green-500/40' : ''}`}>
                                                    {ch ? (
                                                        <>
                                                            <span className="line-through text-text-muted">{ch.before.replace(/ /g, '·')}</span>
                                                            {' → '}
                                                            <span>{ch.after}</span>
                                                        </>
                                                    ) : (
                                                        <Val v={r.values[j] ?? ''} />
                                                    )}
                                                </td>
                                            )
                                        })}
                                        <td className="px-4 py-2 text-text-muted">
                                            {q ? q.reasons.map((x) => x.message).join('; ') : ''}
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                )}

                {tab === 'bersih' && (
                    <table className="w-full text-xs font-display">
                        <thead>
                            <tr className="text-left text-text-muted uppercase tracking-wider">
                                <th className={`${th} w-12`}>#</th>
                                {cols.map((c, i) => <th key={i} className={th}>{c}</th>)}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-ink-border">
                            {data.clean.map((r) => (
                                <tr key={r.row}>
                                    <td className="px-4 py-2 text-text-muted">{r.row}</td>
                                    {cols.map((c, j) => (
                                        <td key={j} className={`${td} ${changeMap[`${r.row}|${c}`] ? 'bg-green-500/15' : ''}`}>
                                            <Val v={r.values[j] ?? ''} />
                                        </td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}

                {tab === 'karantina' && (
                    <table className="w-full text-xs font-display">
                        <thead>
                            <tr className="text-left text-text-muted uppercase tracking-wider">
                                <th className={`${th} w-12`}>#</th>
                                {cols.map((c, i) => <th key={i} className={th}>{c}</th>)}
                                <th className={th}>Alasan</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-ink-border">
                            {data.quarantine.map((q) => (
                                <tr key={q.row}>
                                    <td className="px-4 py-2 text-text-muted">{q.row}</td>
                                    {cols.map((c, j) => (
                                        <td key={j} className={td}><Val v={q.values[j] ?? ''} /></td>
                                    ))}
                                    <td className="px-4 py-2 text-yellow-400">
                                        {q.reasons.map((x) => (x.column ? `${x.column}: ${x.message}` : x.message)).join('; ')}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    )
}