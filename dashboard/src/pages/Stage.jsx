import { useEffect } from 'react'

// Nama publik Panggung. Ganti di satu tempat ini kalau merek sudah diputuskan.
// Sengaja tidak memuat kata "Talatee": halaman ini dirender TANPA Sidebar
// (lihat cabang '/stage' di App.jsx) supaya yang terlihat penonton hanya
// merek ini, bukan Control Center.
const STAGE_NAME = 'Panggung'

const ICON =
  'data:image/svg+xml,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0b0f0c"/><circle cx="16" cy="16" r="6" fill="#22ff66"/></svg>'
  )

// Alur ujung ke ujung yang nanti diisi data nyata. Urutannya memang
// berurutan (file masuk sampai jawaban), jadi dirender sebagai rangkaian.
const FLOW = [
  { title: 'File masuk', hint: 'Upload atau bridge' },
  { title: 'Batch tercatat', hint: 'Postgres + penyimpanan mentah' },
  { title: 'Status kepercayaan', hint: 'Dari baru masuk ke terpercaya' },
  { title: 'Hermes bertanya', hint: 'Lewat MCP, hanya baca' },
  { title: 'Jawaban + sumbernya', hint: 'Dataset dan batch yang dipakai' },
]

export default function Stage() {
  // Judul tab dan ikon diganti selama halaman ini terbuka, lalu dikembalikan.
  // index.html masih bertuliskan "Talatee" sampai React jalan, jadi untuk
  // siaran langsung buka halaman ini sebelum mulai berbagi layar.
  useEffect(() => {
    const prevTitle = document.title
    document.title = STAGE_NAME

    let link = document.querySelector("link[rel~='icon']")
    const created = !link
    if (!link) {
      link = document.createElement('link')
      link.rel = 'icon'
      document.head.appendChild(link)
    }
    const prevHref = link.getAttribute('href')
    link.setAttribute('href', ICON)

    return () => {
      document.title = prevTitle
      if (created) link.remove()
      else if (prevHref) link.setAttribute('href', prevHref)
    }
  }, [])

  return (
    <div className="min-h-screen bg-ink text-text-primary font-body px-6 md:px-12 py-10">
      <header className="max-w-6xl mx-auto flex items-baseline justify-between gap-4">
        <h1 className="font-display text-2xl">{STAGE_NAME}</h1>
        <span className="text-xs text-text-muted">Data demo</span>
      </header>

      <main className="max-w-6xl mx-auto mt-12">
        <p className="text-text-muted text-sm max-w-xl">
          Satu alur dari file masuk sampai jawaban yang bisa dilacak. Setiap tahap di bawah
          akan terisi data hidup setelah simulator dan log Hermes tersambung.
        </p>

        <ol className="mt-8 grid grid-cols-1 md:grid-cols-5 gap-3">
          {FLOW.map((step) => (
            <li
              key={step.title}
              className="bg-ink-surface border border-ink-border rounded-lg px-4 py-5"
            >
              <div className="text-sm font-medium">{step.title}</div>
              <div className="text-text-muted text-xs mt-1">{step.hint}</div>
              <div className="text-text-muted text-xs mt-4">Belum tersambung</div>
            </li>
          ))}
        </ol>
      </main>
    </div>
  )
}
