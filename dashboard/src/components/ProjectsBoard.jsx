import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FlaskConical, FolderKanban, Rocket, Plus, Trash2, X, Check, Download } from 'lucide-react'
import { api } from '../api/client'
import { useFetch } from '../lib/useFetch'
import { formatNumber } from '../lib/format'

export const TIERS = [
  { key: 'laboratorium', title: '01 — Laboratorium', subtitle: 'Masih coba-coba & bereksperimen', icon: FlaskConical, emptyLabel: 'Belum ada eksperimen tercatat di sini.' },
  { key: 'siap_publikasi', title: '02 — Siap Publikasi', subtitle: 'Matang, siap demo & publikasi', icon: FolderKanban, emptyLabel: 'Belum ada proyek di tahap ini.' },
  { key: 'live', title: '03 — Live / Client', subtitle: 'Sudah dipakai & dimonitor', icon: Rocket, emptyLabel: 'Belum ada proyek live di sini.' },
]

/**
 * Satu-satunya sumber logic untuk registry Project — dipakai di Overview
 * (variant="compact") DAN halaman /proyek (variant="full"). SENGAJA tidak
 * diduplikasi jadi 2 salinan kode terpisah, supaya keduanya otomatis selalu
 * sinkron (baca dari GET /projects yang sama) dan tidak bisa "ketinggalan"
 * seperti yang terjadi ke halaman placeholder sebelumnya.
 *
 * variant="full" (dipakai /proyek) dapat 1 kemampuan ekstra yang Overview
 * tidak punya: checklist bisa dicentang langsung di kartu — itu yang bikin
 * halaman /proyek benar-benar punya alasan sendiri untuk ada, bukan cuma
 * salinan Overview yang lebih besar.
 */
export default function ProjectsBoard({ variant = 'compact', tierFilter = null }) {
  const { data: businesses } = useFetch(() => api.listBusinesses(), [])
  const { data: projects, loading, reload } = useFetch(() => api.listProjects(), [])
  const [showAddForm, setShowAddForm] = useState(false)
  const [showImportForm, setShowImportForm] = useState(false)

  const linkedBusinessIds = new Set((projects || []).map((p) => p.business_id).filter(Boolean))
  const unlinkedBusinesses = (businesses || []).filter((b) => !linkedBusinessIds.has(b.id))
  const visibleTiers = tierFilter ? TIERS.filter((t) => t.key === tierFilter) : TIERS

  const projectsByTier = (tierKey) =>
    projects === null ? null : projects.filter((p) => p.tier === tierKey)

  async function handleTierChange(project, newTier) {
    await api.updateProject(project.id, { tier: newTier })
    reload()
  }

  async function handleDeleteProject(project) {
    if (
      !window.confirm(
        `Hapus proyek "${project.name}"? Ini cuma menghapus catatan tahap-nya, bukan data client (kalau ada).`
      )
    ) {
      return
    }
    await api.deleteProject(project.id)
    reload()
  }

  async function handleDemoteProject(project) {
    if (
      !window.confirm(
        `Kembalikan "${project.name}" ke Talatee Laboratorium (staging)? Ini akan menghapus statusnya sebagai Project resmi — bisa di-promosikan lagi nanti dari halaman Laboratorium.`
      )
    ) {
      return
    }
    await api.demoteProject(project.id)
    reload()
  }

  async function handleToggleChecklistItem(project, itemIndex) {
    const newChecklist = project.checklist.map((item, i) =>
      i === itemIndex ? { ...item, done: !item.done } : item
    )
    await api.updateProject(project.id, { checklist: newChecklist })
    reload()
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        {variant === 'full' ? (
          <div>
            <h1 className="font-display text-xl text-text-primary">
              {tierFilter ? visibleTiers[0]?.title.replace(/^0\d — /, '') : 'Proyek'}
            </h1>
            <p className="text-text-muted text-xs mt-1">
              {tierFilter
                ? visibleTiers[0]?.subtitle + ' — tambah, update status, dan centang checklist di sini.'
                : 'Registry proyek nyata — tambah, pindah tahap, dan centang checklist di sini.'}
            </p>
          </div>
        ) : (
          <h2 className="text-sm font-medium text-text-primary">Proyek Saya</h2>
        )}
        <button
          onClick={() => setShowAddForm((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-accent hover:underline shrink-0"
        >
          {showAddForm ? <X size={13} /> : <Plus size={13} />}
          {showAddForm ? 'Batal' : 'Tambah Proyek'}
        </button>
      </div>

      {unlinkedBusinesses.length > 0 && !showAddForm && (
        <button
          onClick={() => setShowImportForm((v) => !v)}
          className="flex items-center gap-1.5 text-xs text-text-muted hover:text-accent mb-3 -mt-1"
        >
          {showImportForm ? <X size={12} /> : <Download size={12} />}
          {showImportForm
            ? 'Batal impor'
            : `Impor dari Client (${unlinkedBusinesses.length} belum masuk registry)`}
        </button>
      )}

      {showImportForm && (
        <ImportClientsForm
          businesses={unlinkedBusinesses}
          onImported={() => {
            setShowImportForm(false)
            reload()
          }}
        />
      )}

      {showAddForm && (
        <AddProjectForm
          businesses={businesses || []}
          defaultTier={tierFilter || 'laboratorium'}
          onCreated={() => {
            setShowAddForm(false)
            reload()
          }}
        />
      )}

      <div className={`grid grid-cols-1 gap-4 mt-3 ${tierFilter ? '' : 'lg:grid-cols-3'}`}>
        {visibleTiers.map((tier) => (
          <ProyekTierCard
            key={tier.key}
            icon={tier.icon}
            title={tier.title}
            subtitle={tier.subtitle}
            emptyLabel={tier.emptyLabel}
            tierKey={tier.key}
            projects={loading ? null : projectsByTier(tier.key)}
            onTierChange={handleTierChange}
            onDelete={handleDeleteProject}
            onDemote={variant === 'full' ? handleDemoteProject : null}
            onToggleChecklistItem={variant === 'full' ? handleToggleChecklistItem : null}
          />
        ))}
      </div>
    </div>
  )
}

function ProyekTierCard({
  icon: Icon,
  title,
  subtitle,
  projects,
  emptyLabel,
  tierKey,
  onTierChange,
  onDelete,
  onDemote,
  onToggleChecklistItem,
}) {
  return (
    <div className="bg-ink-surface border border-ink-border rounded-lg px-4 py-4">
      <div className="flex items-center gap-2 mb-1">
        <Icon size={15} className="text-accent" strokeWidth={1.75} />
        <span className="text-text-primary text-sm font-medium">{title}</span>
      </div>
      <p className="text-text-muted text-xs mb-3">{subtitle}</p>
      {projects === null ? (
        <div className="text-text-muted text-xs py-4 text-center">Memuat…</div>
      ) : projects.length === 0 ? (
        <div className="text-text-muted text-xs py-4 text-center border border-dashed border-ink-border rounded-md">
          {emptyLabel}
        </div>
      ) : (
        <ul className="space-y-2">
          {projects.map((p) => {
            const checklist = p.checklist || []
            const doneCount = checklist.filter((c) => c.done).length
            return (
              <li key={p.id} className="rounded-md bg-ink-elevated px-3 py-2.5">
                <div className="flex items-start justify-between gap-2">
                  <span className="text-text-primary text-xs font-medium leading-snug">
                    {p.name}
                  </span>
                  <button
                    onClick={() => onDelete(p)}
                    className="shrink-0 text-text-muted hover:text-danger transition-colors"
                    title="Hapus proyek"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
                {p.status_note && (
                  <p className="text-text-muted text-[11px] mt-1 leading-snug">{p.status_note}</p>
                )}
                {p.business_name && (
                  <Link
                    to={`/businesses/${p.business_id}`}
                    className="block text-[11px] text-accent mt-1 font-display hover:underline"
                  >
                    {p.business_name} &middot; {formatNumber(p.business_total_records)} records
                  </Link>
                )}

                {checklist.length > 0 && onToggleChecklistItem ? (
                  <ul className="mt-2 space-y-1">
                    {checklist.map((item, i) => (
                      <li key={i}>
                        <button
                          onClick={() => onToggleChecklistItem(p, i)}
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
                            className={`text-[11px] leading-snug ${
                              item.done ? 'text-text-muted line-through' : 'text-text-primary'
                            }`}
                          >
                            {item.label}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                ) : checklist.length > 0 ? (
                  <div className="text-[11px] text-text-muted mt-1 font-display">
                    Checklist: {doneCount}/{checklist.length} selesai
                  </div>
                ) : null}

                <select
                  value={tierKey}
                  onChange={(e) => onTierChange(p, e.target.value)}
                  className="mt-2 w-full text-[11px] bg-ink border border-ink-border rounded px-2 py-1 text-text-muted focus:outline-none focus:border-accent/50"
                >
                  {TIERS.map((t) => (
                    <option key={t.key} value={t.key}>
                      Pindah ke: {t.title}
                    </option>
                  ))}
                </select>

                {onDemote && (
                  <button
                    onClick={() => onDemote(p)}
                    className="mt-1.5 w-full flex items-center justify-center gap-1.5 text-[11px] text-text-muted hover:text-accent transition-colors py-1"
                  >
                    <FlaskConical size={11} />
                    Kembalikan ke Laboratorium
                  </button>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function ImportClientsForm({ businesses, onImported }) {
  const [selected, setSelected] = useState(() => new Set(businesses.map((b) => b.id)))
  const [tier, setTier] = useState('laboratorium')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  function toggle(id) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  async function handleImport() {
    if (selected.size === 0) return
    setSubmitting(true)
    setError(null)
    try {
      // Dibuat satu-satu (bukan bulk endpoint) — jumlahnya kecil dan ini
      // dipakai jarang, jadi tidak perlu endpoint khusus di backend.
      for (const b of businesses.filter((biz) => selected.has(biz.id))) {
        await api.createProject({
          name: b.name,
          tier,
          status_note: 'Diimpor dari data Client — status belum ditinjau',
          business_id: b.id,
        })
      }
      onImported()
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4 mb-3 space-y-3">
      <p className="text-text-muted text-xs">
        Client ini punya data di Talatee tapi belum tercatat sebagai Project. Pilih mana yang
        mau dimasukkan, dan ke tahap mana:
      </p>

      <ul className="space-y-1.5 max-h-56 overflow-y-auto">
        {businesses.map((b) => (
          <li key={b.id}>
            <label className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-md hover:bg-ink-elevated cursor-pointer">
              <span
                onClick={() => toggle(b.id)}
                className={`w-3.5 h-3.5 rounded-sm border shrink-0 flex items-center justify-center transition-colors ${
                  selected.has(b.id) ? 'bg-accent border-accent' : 'border-ink-border'
                }`}
              >
                {selected.has(b.id) && <Check size={10} className="text-ink" strokeWidth={3} />}
              </span>
              <span className="text-text-primary text-xs flex-1">{b.name}</span>
              <span className="text-text-muted text-[11px] font-display">
                {formatNumber(b.total_records)} records
              </span>
            </label>
          </li>
        ))}
      </ul>

      <div className="flex items-center gap-2">
        <label className="text-xs text-text-muted shrink-0">Masukkan ke tahap:</label>
        <select
          value={tier}
          onChange={(e) => setTier(e.target.value)}
          className="flex-1 bg-ink border border-ink-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent/50"
        >
          {TIERS.map((t) => (
            <option key={t.key} value={t.key}>
              {t.title}
            </option>
          ))}
        </select>
      </div>

      {error && <div className="text-danger text-xs">{error}</div>}

      <button
        onClick={handleImport}
        disabled={submitting || selected.size === 0}
        className="glow-accent-sm bg-accent text-ink font-medium text-sm rounded-md px-4 py-2 hover:bg-accent-soft transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitting ? 'Mengimpor…' : `Impor ${selected.size} Proyek`}
      </button>
    </div>
  )
}

function AddProjectForm({ businesses, onCreated, defaultTier = 'laboratorium' }) {
  const [name, setName] = useState('')
  const [tier, setTier] = useState(defaultTier)
  const [statusNote, setStatusNote] = useState('')
  const [businessId, setBusinessId] = useState('')
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

      await api.createProject({
        name: name.trim(),
        tier,
        status_note: statusNote.trim() || null,
        business_id: businessId || null,
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
      className="bg-ink-surface border border-ink-border rounded-lg px-5 py-4 mb-3 space-y-3"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="text-xs text-text-muted block mb-1">Nama Proyek</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="misal: Buku Kas Warung"
            className="w-full bg-ink border border-ink-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent/50"
          />
        </div>
        <div>
          <label className="text-xs text-text-muted block mb-1">Tahap</label>
          <select
            value={tier}
            onChange={(e) => setTier(e.target.value)}
            className="w-full bg-ink border border-ink-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent/50"
          >
            {TIERS.map((t) => (
              <option key={t.key} value={t.key}>
                {t.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="text-xs text-text-muted block mb-1">Catatan Status</label>
        <input
          value={statusNote}
          onChange={(e) => setStatusNote(e.target.value)}
          placeholder="misal: Testing integrasi WA/n8n, belum deploy VPS"
          className="w-full bg-ink border border-ink-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent/50"
        />
      </div>

      <div>
        <label className="text-xs text-text-muted block mb-1">
          Tautkan ke Client (opsional — kalau proyek ini punya data nyata di Talatee)
        </label>
        <select
          value={businessId}
          onChange={(e) => setBusinessId(e.target.value)}
          className="w-full bg-ink border border-ink-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent/50"
        >
          <option value="">Tidak ditautkan</option>
          {businesses.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
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
          placeholder={'Test WA bot end-to-end\nDeploy ke VPS'}
          className="w-full bg-ink border border-ink-border rounded px-3 py-1.5 text-sm text-text-primary focus:outline-none focus:border-accent/50"
        />
      </div>

      {error && <div className="text-danger text-xs">{error}</div>}

      <button
        type="submit"
        disabled={submitting || !name.trim()}
        className="glow-accent-sm bg-accent text-ink font-medium text-sm rounded-md px-4 py-2 hover:bg-accent-soft transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitting ? 'Menyimpan…' : 'Simpan Proyek'}
      </button>
    </form>
  )
}
