import { useState } from 'react'
import { useFetch } from '../lib/useFetch'
import { api } from '../api/client'
import { LoadingState, ErrorState } from './States'

const TABS = [
    { id: 'banding', label: 'Perbandingan' },
    { id: 'bersih', label: 'Data Bersih' },
    { id: 'karantina', label: 'Karantina' },
    { id: 'dibuang', label: 'Dibuang' },
]

function Val({ v }) {
    return v === '' ? <span className="text-text-muted">∅</span> : <span>{v}</span>
}

export default function BatchCleanView({ batchId }) {
    const { data, loading, error } = useFetch(() => api.getBatchClean(batchId), [batchId])
    const [tab, setTab] = useState('banding')
    const [busy, setBusy] = useState(false)
    const [msg, setMsg] = useState(null)

    async function decide(body) {
        setBusy(true)
        setMsg(null)
        try {
            await api.addBatchDecision(batchId, body)
            window.location.reload()
        } catch (err) {
            setMsg(err.message || String(err))
            setBusy(false)
        }
    }

    function dropRow(row) {
        const reason = window.prompt(`Buang baris ${row}? Tulis alasannya (wajib):`)
        if (reason && reason.trim()) decide({ row_number: row, action: 'drop_row', reason })
    }

    function setValue(row, column, current) {
        const value = window.prompt(`Nilai baru untuk "${column}" di baris ${row}:`, current)
        if (value === null) return
        const reason = window.prompt('Alasan perubahan (wajib):')
        if (reason && reason.trim()) {
            decide({ row_number: row, action: 'set_value', column_name: column, new_value: value, reason })
        }
    }

    function undoDrop(row) {
        const reason = window.prompt(`Batalkan pembuangan baris ${row}? Tulis alasannya (wajib):`)
        if (reason && reason.trim()) decide({ row_number: row, action: 'revert', reason })
    }

    if (loading) return <LoadingState label="Memuat data bersih" />
    if (error) return <ErrorState message={error} />
    if (!data) return null

    const rec = data.reconciliation
    const cols = data.columns
    const dropped = data.dropped || []
    const manual = data.manual_changes || []

    const changeMap = {}
    for (const c of data.changes) changeMap[`${c.row}|${c.column}`] = c

    const manualMap = {}
    for (const m of manual) manualMap[`${m.row}|${m.column}`] = m

    const qMap = {}
    for (const q of data.quarantine) qMap[q.row] = q

    const all = [
        ...data.clean.map((r) => ({ ...r, status: 'bersih' })),
        ...data.quarantine.map((q) => ({ row: q.row, values: q.values, status: 'karantina' })),
        ...dropped.map((d) => ({ row: d.row, values: d.values, status: 'dibuang', reason: d.reason })),
    ].sort((a, b) => a.row - b.row)

    const th = 'px-4 py-2'
    const td = 'px-4 py-2 text-text-primary whitespace-pre'

    const statusLabel = (s) =>
        s === 'bersih' ? (
            <span className="text-accent">Bersih</span>
        ) : s === 'dibuang' ? (
            <span className="text-danger">Dibuang</span>
        ) : (
            <span className="text-yellow-400">Karantina</span>
        )

    return (
        <div className="bg-ink-surface border border-ink-border rounded-lg">
            <div className="px-5 py-4 border-b border-ink-border">
                <h2 className="text-sm font-medium text-text-primary">Data Bersih dan Perbandingan</h2>
                <p className="text-xs text-text-muted mt-1">
                    Layer terpisah dari Data Asli (asli tidak diubah). Hanya perbaikan yang pasti dilakukan otomatis;
                    sisanya masuk karantina sampai kamu memutuskan. Setiap keputusan tercatat dengan alasan.
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
                    Aturan otomatis: {data.rules.map((r) => `${r.label}: ${r.cells} sel`).join(' · ')}
                    {manual.length > 0 && ` · Keputusan manual: ${manual.length} sel`}
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
                        {t.id === 'dibuang' && ` (${rec.dropped})`}
                    </button>
                ))}
            </div>

            {msg && <div className="px-5 py-2 text-xs text-danger border-b border-ink-border">{msg}</div>}

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
                                    <tr key={r.row} className={r.status === 'dibuang' ? 'opacity-50' : ''}>
                                        <td className="px-4 py-2 text-text-muted">{r.row}</td>
                                        <td className="px-4 py-2">{statusLabel(r.status)}</td>
                                        {cols.map((c, j) => {
                                            const ch = changeMap[`${r.row}|${c}`]
                                            const mm = manualMap[`${r.row}|${c}`]
                                            return (
                                                <td
                                                    key={j}
                                                    className={`${td} ${mm
                                                            ? 'bg-blue-500/15 outline outline-1 outline-blue-500/40'
                                                            : ch
                                                                ? 'bg-green-500/15 outline outline-1 outline-green-500/40'
                                                                : ''
                                                        }`}
                                                    title={mm ? `Keputusan manual: ${mm.reason}` : ''}
                                                >
                                                    {mm ? (
                                                        <>
                                                            <span className="line-through text-text-muted">{mm.before === '' ? '∅' : mm.before}</span>
                                                            {' → '}
                                                            <span>{mm.after}</span>
                                                        </>
                                                    ) : ch ? (
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
                                            {r.status === 'dibuang'
                                                ? `Dibuang: ${r.reason}`
                                                : q
                                                    ? q.reasons.map((x) => x.message).join('; ')
                                                    : ''}
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
                                        <td
                                            key={j}
                                            className={`${td} ${manualMap[`${r.row}|${c}`]
                                                    ? 'bg-blue-500/15'
                                                    : changeMap[`${r.row}|${c}`]
                                                        ? 'bg-green-500/15'
                                                        : ''
                                                }`}
                                        >
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
                                <th className={th}>Keputusan</th>
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
                                    <td className="px-4 py-2 whitespace-nowrap">
                                        {q.reasons
                                            .filter((x) => x.column)
                                            .map((x) => (
                                                <button
                                                    key={x.column + x.type}
                                                    disabled={busy}
                                                    onClick={() => setValue(q.row, x.column, x.value)}
                                                    className="mr-3 text-accent hover:underline disabled:opacity-50"
                                                >
                                                    Isi {x.column}
                                                </button>
                                            ))}
                                        <button
                                            disabled={busy}
                                            onClick={() => dropRow(q.row)}
                                            className="text-danger hover:underline disabled:opacity-50"
                                        >
                                            Buang baris
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {data.quarantine.length === 0 && (
                                <tr>
                                    <td className="px-4 py-3 text-text-muted" colSpan={cols.length + 3}>
                                        Karantina kosong.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                )}

                {tab === 'dibuang' && (
                    <table className="w-full text-xs font-display">
                        <thead>
                            <tr className="text-left text-text-muted uppercase tracking-wider">
                                <th className={`${th} w-12`}>#</th>
                                {cols.map((c, i) => <th key={i} className={th}>{c}</th>)}
                                <th className={th}>Alasan</th>
                                <th className={th}>Oleh</th>
                                <th className={th}>Aksi</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-ink-border">
                            {dropped.map((d) => (
                                <tr key={d.row}>
                                    <td className="px-4 py-2 text-text-muted">{d.row}</td>
                                    {cols.map((c, j) => (
                                        <td key={j} className={td}><Val v={d.values[j] ?? ''} /></td>
                                    ))}
                                    <td className="px-4 py-2 text-text-muted">{d.reason}</td>
                                    <td className="px-4 py-2 text-text-muted">{d.by || '-'}</td>
                                    <td className="px-4 py-2">
                                        <button
                                            disabled={busy}
                                            onClick={() => undoDrop(d.row)}
                                            className="text-accent hover:underline disabled:opacity-50"
                                        >
                                            Batalkan
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {dropped.length === 0 && (
                                <tr>
                                    <td className="px-4 py-3 text-text-muted" colSpan={cols.length + 4}>
                                        Belum ada baris yang dibuang.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                )}
            </div>
        </div>
    )
}