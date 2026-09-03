import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FlaskConical, Plus, Trash2, X, Check, ArrowUpCircle, FlaskConicalOff, ChevronRight } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { formatNumber, formatRelative } from '../lib/format'

/**
 * "Talatee Laboratorium" — ruang staging TERPISAH dari registry Proyek.
 * Apa pun di sini BUKAN Project resmi sampai kamu klik "Promosikan", yang
 * baru saat itu membuat entri di Proyek > 01 Laboratorium. Sengaja beda
 * sumber data dari ProjectsBoard (tabel lab_entries, bukan projects) supaya
 * "belum masuk Proyek sama sekali" ini benar secara data, bukan cuma
 * penyaringan tampilan.
 *
 * Tiap entri bisa ditautkan ke 1 Dataset asli (opsional) — kalau ada,
 * kartunya dapat tombol "Buka Pipeline Testing" ke halaman detail
 * (LabEntryDetail.jsx) untuk menjalankan Ambil Data / Bersihkan / Validasi
 * / Analisis / dst terhadap data itu sebelum promosi.
 */
export default function Laboratorium() {
  const { data: entries, loading, reload } = useFetch(() => api.listLabEntries(), [])
  const [showAddForm, setShowAddForm] = useState(false)
  const [promotingId, setPromotingId] = useState(null)

  async function handleDelete(entry) {
    if (!window.confirm(`Hapus catatan eksperimen "${entry.name}"? Ini permanen.`)) return
    await api.deleteLabEntry(entry.id)
    reload()
  }

  async function handleToggleChecklistItem(entry, itemIndex) {
    const newChecklist = entry.checklist.map((item, i) =>
      i === itemIndex ? { ...item, done: !item.done } : item
    )
    await api.updateLabEntry(entry.id, { checklist: newChecklist })
    reload()
  }

  async function handlePromote(entry) {
    if (
      !window.confirm(
        `Promosikan "${entry.name}" jadi Project resmi di Proyek > 01 Laboratorium? Catatan staging ini akan dihapus setelahnya (datanya pindah jadi Project).`
      )
    ) {
      return
    }
    setPromotingId(entry.id)
    try {
      await api.promoteLabEntry(entry.id)
      reload()
    } finally {
      setPromotingId(null)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2">
            <FlaskConical size={18} className="text-accent" strokeWidth={1.75} />
            <h1 className="font-display text-xl text-text-primary">Talatee Laboratorium</h1>
          </div>
          <p className="text-text-muted text-xs mt-1">
            Ruang coba-coba terpisah dari registry Proyek. Belum jadi Project resmi sampai
            kamu promosikan.
          </p>
        </div>
        <button
          onClick={() => setShowAddForm((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-accent hover:underline shrink-0"
        >
          {showAddForm ? <X size={13} /> : <Plus size={13} />}
          {showAddForm ? 'Batal' : 'Catat Eksperimen Baru'}
        </button>
      </div>

      {showAddForm && (
        <AddLabEntryForm
          onCreated={() => {
            setShowAddForm(false)
            reload()
          }}
        />
      )}

      {loading ? (
        <div className="text-text-muted text-sm py-8 text-center">Memuat…</div>
      ) : entries.length === 0 ? (
        <div className="text-text-muted text-sm py-12 text-center border border-dashed border-ink-border rounded-lg">
          Belum ada catatan eksperimen. Klik "Catat Eksperimen Baru" untuk mulai.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {entries.map((entry) => {
            const checklist = entry.checklist || []
            return (
              <div key={entry.id} className="bg-ink-surface border border-ink-border rounded-lg px-4 py-4">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-text-primary text-sm font-medium leading-snug">
                    {entry.name}
                  </span>
                  <button
                    onClick={() => handleDelete(entry)}
                    className="shrink-0 text-text-muted hover:text-danger transition-colors"
                    title="Hapus"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
                {entry.note && (
                  <p className="text-text-muted text-xs mt-1.5 leading-snug">{entry.note}</p>
                )}
                {entry.business_name && (
                  <Link
                    to={`/businesses/${entry.business_id}`}
                    className="block text-xs text-accent mt-1.5 font-display hover:underline"
                  >
                    {entry.business_name} &middot; {formatNumber(entry.business_total_records)} records
                  </Link>
                )}

                {checklist.length > 0 && (
                  <ul className="mt-2.5 space-y-1">
                    {checklist.map((item, i) => (
                      <li key={i}>
                        <button
                          onClick={() => handleToggleChecklistItem(entry, i)}
                          className="w-full flex items-center gap-2 text-left group"
                        >
                          <span
                            className={`w-3.5 h-3.5 rounded-sm border shrink-0 flex items-center justify-center transition-colors ${
                              item.done
                                ? 'bg-accent border-accent'
                                : 'border-ink-border group-hover:border-text-muted'
                            }`}
                          >
                            {item.done && <Check size={10} className="text-ink" strokeWidth={3} />}
                          </span>
                          <span
                            className={`text-xs leading-snug ${
                              item.done ? 'text-text-muted line-through' : 'text-text-primary'
                            }`}
                          >
                            {item.label}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

                <div className="text-text-muted text-[11px] font-display mt-2.5">
                  Dicatat {formatRelative(entry.created_at)}
                </div>

                {entry.dataset_id ? (
                  <Link
                    to={`/laboratorium/${entry.id}`}
                    className="mt-3 w-full flex items-center justify-center gap-1.5 text-xs bg-accent/10 hover:bg-accent/20 text-accent border border-accent/40 rounded-md py-2 transition-colors"
                  >
                    Buka Pipeline Testing ({entry.dataset_name})
                    <ChevronRight size={13} />
                  </Link>
                ) : (
                  <div className="mt-3 w-full flex items-center justify-center gap-1.5 text-xs text-text-muted/60 border border-dashed border-ink-border rounded-md py-2">
                    <FlaskConicalOff size={12} />
                    Belum ditautkan ke dataset
                  </div>
                )}

                <button
                  onClick={() => handlePromote(entry)}
                  disabled={promotingId === entry.id}
                  className="mt-2 w-full flex items-center justify-center gap-1.5 text-xs bg-ink-elevated hover:bg-accent/10 hover:text-accent border border-ink-border hover:border-accent/40 text-text-muted rounded-md py-2 transition-colors disabled:opacity-50"
                >
                  <ArrowUpCircle size={13} />
                  {promotingId === entry.id ? 'Memproses…' : 'Promosikan ke Proyek 01'}
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function AddLabEntryForm({ onCreated }) {
  const { data: datasets } = useFetch(() => api.listDatasets(), [])
  const [name, setName] = useState('')
  const [note, setNote] = useState('')
  const [datasetId, setDatasetId] = useState('')
  const [checklistText, setChecklistText] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!name.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      const checklist = checklistText
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .map((label) => ({ label, done: false }))

      await api.createLabEntry({
        name: name.trim(),
        note: note.trim() || null,
        dataset_id: datasetId || null,
        checklist: checklist.length > 0 ? checklist : null,
      })
      onCreated()
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4 space-y-3"
    >
      <div>
        <label className="text-xs text-text-muted block mb-1">Nama Eksperimen</label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="misal: Coba model rekomendasi produk"
          className="w-full bg-ink border border-ink-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent/50"
        />
      </div>
      <div>
        <label className="text-xs text-text-muted block mb-1">Catatan (opsional)</label>
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="misal: baru ide, belum dicoba sama sekali"
          className="w-full bg-ink border border-ink-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent/50"
        />
      </div>
      <div>
        <label className="text-xs text-text-muted block mb-1">
          Tautkan ke Dataset (opsional — untuk pipeline testing)
        </label>
        <select
          value={datasetId}
          onChange={(e) => setDatasetId(e.target.value)}
          className="w-full bg-ink border border-ink-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent/50"
        >
          <option value="">Belum ada / masih ide</option>
          {(datasets || []).map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="text-xs text-text-muted block mb-1">
          Checklist (opsional — 1 baris = 1 item)
        </label>
        <textarea
          value={checklistText}
          onChange={(e) => setChecklistText(e.target.value)}
          rows={3}
          placeholder={'Baca paper referensi\nCoba di 1 dataset kecil'}
          className="w-full bg-ink border border-ink-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent/50"
        />
      </div>
      {error && <div className="text-danger text-xs">{error}</div>}
      <button
        type="submit"
        disabled={submitting || !name.trim()}
        className="glow-accent-sm bg-accent text-ink font-medium text-sm rounded-md px-4 py-2 hover:bg-accent-soft transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitting ? 'Menyimpan…' : 'Simpan Catatan'}
      </button>
    </form>
  )
}
