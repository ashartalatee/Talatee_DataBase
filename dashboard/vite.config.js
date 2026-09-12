import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Vite (versi baru) menolak request yang Host header-nya bukan
    // localhost/127.0.0.1 secara default (proteksi DNS rebinding).
    // allowedHosts: true melonggarkan itu -- aman untuk pemakaian pribadi
    // yang diakses lewat Tailscale/LAN (jaringan privat terpercaya),
    // TAPI jangan pakai pengaturan ini kalau nanti dev server ini pernah
    // ter-expose ke internet publik (mis. lewat devtunnels/port forwarding
    // Public visibility) -- ganti allowedHosts jadi daftar eksplisit di
    // situasi itu.
    host: true,
    allowedHosts: true,
  },
})
