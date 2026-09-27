import { ExternalLink, AlertTriangle } from 'lucide-react'

// URL Hermes lokal. Override lewat .env kalau port/profile-nya beda:
//   VITE_HERMES_URL=http://127.0.0.1:9119/chat?profile=default
const HERMES_URL =
  import.meta.env.VITE_HERMES_URL || 'http://127.0.0.1:9119/chat?profile=default'

// Kenapa ada tombol "buka di tab baru" di samping iframe (bukan cuma iframe
// saja): dashboard versi Vercel (https) akan diblokir browser saat mencoba
// menampilkan Hermes yang masih http://127.0.0.1 (mixed content) -- iframe-nya
// blank meski tidak ada error kode. Tombol ini tetap jalan di kedua kondisi,
// jadi halaman ini tetap berguna walau iframe-nya gagal tampil.
export default function Hermes() {
  return (
    <div className="space-y-4 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl text-text-primary">Hermes</h1>
          <p className="text-text-muted text-sm mt-1">Agent yang berpikir di balik Talatee.</p>
        </div>
        <a
          href={HERMES_URL}
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-2 px-3 py-2 rounded-md text-sm text-text-muted hover:text-text-primary hover:bg-ink-elevated/60 border border-ink-border"
        >
          <ExternalLink size={14} />
          Buka di tab baru
        </a>
      </div>

      <div className="bg-ink-surface border border-ink-border rounded-lg flex-1 overflow-hidden min-h-[70vh] relative">
        <iframe
          key={HERMES_URL}
          src={HERMES_URL}
          title="Hermes Agent"
          className="w-full h-full min-h-[70vh] border-0"
        />

        {/* Peringatan mixed-content statis -- iframe yang diblokir browser
            tidak selalu memicu onError, jadi ini tampil selalu sebagai
            pengingat, bukan cuma saat error terdeteksi. */}
        <div className="absolute bottom-3 left-3 right-3 flex items-start gap-2 bg-ink/90 border border-ink-border rounded-md px-3 py-2 text-xs text-text-muted">
          <AlertTriangle size={14} className="text-accent shrink-0 mt-0.5" />
          <span>
            Layar kosong di sini? Berarti browser memblokir konten http di halaman https
            (mixed content) -- normal untuk versi Vercel. Pakai tombol "Buka di tab baru",
            atau jalankan dashboard lewat <code>npm run dev</code> supaya sama-sama http.
          </span>
        </div>
      </div>
    </div>
  )
}
