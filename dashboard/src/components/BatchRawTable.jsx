import { useFetch } from '../lib/useFetch'
import { api } from '../api/client'
import { LoadingState, ErrorState } from './States'

// Tampilkan nilai persis seperti di file. Sel kosong -> ∅, spasi di
// awal/akhir -> titik tengah (·) supaya kekotoran terlihat oleh mata.
function Cell({ value }) {
    if (value === '') return <span className="text-text-muted">∅</span>
    const m = value.match(/^(\s*)([\s\S]*?)(\s*)$/)
    const lead = m[1].replace(/ /g, '·')
    const trail = m[3].replace(/ /g, '·')
    return (
        <span>
            {lead && <span className="text-accent">{lead}</span>}
            {m[2]}
            {trail && <span className="text-accent">{trail}</span>}
        </span>
    )
}

export default function BatchRawTable({ batchId }) {
    const { data, loading, error } = useFetch(() => api.getBatchRows(batchId), [batchId])

    return (
        <div className="bg-ink-surface border border-ink-border rounded-lg">
            <div className="px-5 py-4 border-b border-ink-border">
                <h2 className="text-sm font-medium text-text-primary">Data Asli</h2>
                <p className="text-xs text-text-muted mt-1">
                    Isi file persis seperti saat diupload, tanpa pembersihan. ∅ = sel kosong, · = spasi tersembunyi.
                </p>
            </div>

            {loading && <LoadingState label="Memuat isi file" />}
            {error && <ErrorState message={error} />}

            {data && (
                <>
                    <div className="px-5 py-2 text-xs text-text-muted border-b border-ink-border">
                        Menampilkan {data.shown_rows} dari {data.total_rows} baris
                        {data.truncated ? ' (dipotong, unduh file untuk data lengkap)' : ''}
                    </div>
                    <div className="overflow-x-auto">
                        <table className="w-full text-xs font-display">
                            <thead>
                                <tr className="text-left text-text-muted uppercase tracking-wider">
                                    <th className="px-4 py-2 w-12">#</th>
                                    {data.columns.map((c, i) => (
                                        <th key={i} className="px-4 py-2">{c}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-ink-border">
                                {data.rows.map((r, i) => (
                                    <tr key={i}>
                                        <td className="px-4 py-2 text-text-muted">{i + 1}</td>
                                        {data.columns.map((_, j) => (
                                            <td key={j} className="px-4 py-2 text-text-primary whitespace-pre">
                                                <Cell value={r[j] ?? ''} />
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </div>
    )
}