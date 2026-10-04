import { useFetch } from '../lib/useFetch'
import { api } from '../api/client'
import { LoadingState, ErrorState } from './States'

const TYPE_LABEL = {
    duplikat: 'Duplikat',
    format_tanggal_campur: 'Format tanggal campur',
    tanggal_mustahil: 'Tanggal mustahil',
    tanggal_tidak_dikenali: 'Tanggal tidak dikenali',
    kosong: 'Sel kosong',
    spasi_tepi: 'Spasi di tepi',
    ejaan_beda: 'Ejaan beda',
    angka_negatif: 'Angka negatif',
    bukan_angka: 'Teks di kolom angka',
}

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

function cellClass(list) {
    if (!list) return ''
    return list.some((x) => x.severity === 'error')
        ? 'bg-red-500/15 outline outline-1 outline-red-500/50'
        : 'bg-yellow-500/15 outline outline-1 outline-yellow-500/50'
}

export default function BatchRawTable({ batchId }) {
    const rowsQ = useFetch(() => api.getBatchRows(batchId), [batchId])
    const issuesQ = useFetch(() => api.getBatchIssues(batchId), [batchId])

    const data = rowsQ.data
    const report = issuesQ.data

    // Peta masalah: "baris|kolom" -> daftar, dan baris -> daftar (untuk duplikat)
    const cellIssues = {}
    const rowIssues = {}
    if (report) {
        for (const it of report.issues) {
            if (it.column) {
                const k = `${it.row}|${it.column}`
                    ; (cellIssues[k] ||= []).push(it)
            } else {
                ; (rowIssues[it.row] ||= []).push(it)
            }
        }
    }

    return (
        <div className="bg-ink-surface border border-ink-border rounded-lg">
            <div className="px-5 py-4 border-b border-ink-border">
                <h2 className="text-sm font-medium text-text-primary">Data Asli</h2>
                <p className="text-xs text-text-muted mt-1">
                    Isi file persis seperti saat diupload, tanpa pembersihan. ∅ = sel kosong, · = spasi tersembunyi.
                    Sel berwarna = temuan pemeriksa (arahkan kursor untuk alasannya).
                </p>
            </div>

            {report && (
                <div className="px-5 py-3 border-b border-ink-border text-xs space-y-2">
                    <div className="text-text-primary">
                        {report.rows_with_issues === 0
                            ? `Tidak ada masalah ditemukan di ${report.total_rows} baris.`
                            : `${report.rows_with_issues} dari ${report.total_rows} baris bermasalah (${report.total_issues} temuan).`}
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {Object.entries(report.by_type).map(([t, n]) => (
                            <span key={t} className="px-2 py-0.5 rounded border border-ink-border text-text-muted">
                                {TYPE_LABEL[t] || t}: <span className="text-text-primary">{n}</span>
                            </span>
                        ))}
                    </div>
                    <div className="text-text-muted">
                        <span className="text-red-400">■</span> error &nbsp;
                        <span className="text-yellow-400">■</span> peringatan &nbsp;(tipe kolom ditebak dari namanya)
                    </div>
                </div>
            )}
            {issuesQ.error && (
                <div className="px-5 py-2 text-xs text-danger border-b border-ink-border">
                    Pemeriksa gagal: {String(issuesQ.error)}
                </div>
            )}

            {rowsQ.loading && <LoadingState label="Memuat isi file" />}
            {rowsQ.error && <ErrorState message={rowsQ.error} />}

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
                                {data.rows.map((r, i) => {
                                    const rn = i + 1
                                    const dup = rowIssues[rn]
                                    return (
                                        <tr key={i} className={dup ? 'opacity-70' : ''}>
                                            <td className="px-4 py-2 text-text-muted" title={dup ? dup.map((x) => x.message).join('; ') : ''}>
                                                {rn}
                                                {dup && <span className="ml-1 text-yellow-400">⧉</span>}
                                            </td>
                                            {data.columns.map((col, j) => {
                                                const list = cellIssues[`${rn}|${col}`]
                                                return (
                                                    <td
                                                        key={j}
                                                        className={`px-4 py-2 text-text-primary whitespace-pre ${cellClass(list)}`}
                                                        title={list ? list.map((x) => x.message).join('; ') : ''}
                                                    >
                                                        <Cell value={r[j] ?? ''} />
                                                    </td>
                                                )
                                            })}
                                        </tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    </div>
                </>
            )}
        </div>
    )
}