// Sumber data Panggung.
//  - VITE_STAGE_MODE=mock (default): data demo dibangkitkan di browser, untuk menyiapkan tampilan & rekaman.
//  - VITE_STAGE_MODE=api : membaca GET /stage/summary lewat api.getStageSummary().
//  - ?mock di URL memaksa mode mock tanpa mengubah .env.
//
// Kontrak data (bentuk yang sama dipakai mock dan API):
// {
//   flow: { file:{count,last}, batch:{count,last}, trust:{INGESTED,VALIDATING,NEEDS_REVIEW,TRUSTED,last},
//           question:{count,last}, answer:{count,last} },          // last = epoch ms atau null
//   trend: [{ d:"1", rev:2400000, ord:85 }, ...],                  // 30 hari terakhir, hanya batch TRUSTED
//   categories: [{ name, value }], channels: [{ name, value }],
//   low_stock: [{ name, stok }],
//   hermes: [{ q, a, sources:["get_top_products", ...] }],         // terbaru di atas
//   feed: [{ t, text, tone:"g"|"b"|"y" }],                         // terbaru di atas
//   hermes_connected: true|false,
//   // --- tambahan untuk halaman Gudang Data, Data Bersih, dan Agen (opsional; belum ada di /stage/summary) ---
//   batches: [{ id, file, channel, rows, status:"masuk"|"diproses"|"bersih"|"tinjau", t, cols:[...],
//               raw:[{ c:{kolom:nilai}, flags:{kolom:"empty"|"format"|"dup"} }],
//               clean:[{ c:{...}, fixed:[kolom] }], stats:{ kept, dup, empty, fmt } }],   // terbaru di atas
//   events: [{ t, kind:"file"|"read"|"clean"|"validate"|"trust"|"insight"|"hermes"|"info", text, tone, batchId,
//              q?, a?, sources? }],                                // terbaru di atas
//   agent: { status:"idle"|"working", step:"read"|"clean"|"validate"|"trust"|"insight"|null, batchId, label, lastDone },
//   insights: [{ id, title, text, tone, batchId }]
// }
//
// Aksi laci Kendali. Mock: jalan di browser. API: memanggil fungsi di client.js bila ada
// (kalau belum ada, tombolnya nonaktif):
//   api.stageTrigger()      POST /showcase/simulator/trigger  (kirim satu batch demo, olah + promote otomatis)
//   api.stageBackfill()     POST /showcase/demo/backfill      (isi data 30 hari ke belakang)
//   api.stageUpload(file, {promote})  POST /showcase/demo/upload  (unggah file ke bisnis demo)
//   api.stageResetPreview() GET  /showcase/reset/preview      (jumlah yang akan dihapus)
//   api.stageReset()        POST /showcase/reset              (hanya bisnis is_demo, body {confirm:true})
import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'

const flag = (name) => new URLSearchParams(window.location.search).has(name)
// ?mock memaksa data simulasi (untuk menyiapkan tampilan tanpa backend), apa pun isi VITE_STAGE_MODE.
const MODE = flag('mock') ? 'mock' : (import.meta.env.VITE_STAGE_MODE || 'mock')

const CATS = [['Skincare', 0.32], ['Makeup', 0.22], ['Perawatan Rambut', 0.16], ['Body Care', 0.13], ['Lainnya', 0.17]]
const CHAN = [['TikTok Shop', 0.36], ['Shopee', 0.3], ['Lazada', 0.17], ['WhatsApp', 0.1], ['Website', 0.07]]
const CATALOG = [
  ['Serum Vitamin C', 'Skincare', 89000], ['Moisturizer Gel', 'Skincare', 65000], ['Sunscreen SPF50', 'Skincare', 75000],
  ['Lip Cream Matte', 'Makeup', 55000], ['Cushion Foundation', 'Makeup', 129000],
  ['Shampoo Anti Ketombe', 'Perawatan Rambut', 48000], ['Body Lotion', 'Body Care', 42000],
]
const PROD = { 'Serum Vitamin C': 310, 'Moisturizer Gel': 260, 'Sunscreen SPF50': 240, 'Lip Cream Matte': 180, 'Cushion Foundation': 90, 'Shampoo Anti Ketombe': 170, 'Body Lotion': 200 }
const COLS = ['order_id', 'tanggal', 'produk', 'kategori', 'qty', 'harga_satuan', 'subtotal', 'status']
const rp = (v) => (v >= 1e6 ? `Rp ${(v / 1e6).toFixed(2).replace('.', ',')} jt` : `Rp ${Math.round(v / 1000)} rb`)
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)]

function initial(empty = false) {
  const trend = []
  const cats = Object.fromEntries(CATS.map((c) => [c[0], 0]))
  for (let i = 0; i < 30; i++) {
    let rev = Math.round(2.4e6 + i * 38000 + Math.sin(i * 0.9) * 3.6e5 + Math.cos(i * 2.3) * 1.5e5)
    if (i === 29) rev = Math.round(rev * 0.42)
    if (empty) rev = 0
    trend.push({ d: String(i + 1), rev, ord: Math.round(rev / 28000) })
    CATS.forEach((c) => (cats[c[0]] += Math.round(rev * c[1])))
  }
  const total = trend.reduce((n, x) => n + x.rev, 0)
  return {
    flow: {
      file: { count: 0, last: null }, batch: { count: 0, last: null },
      trust: { INGESTED: 0, VALIDATING: 0, NEEDS_REVIEW: 0, TRUSTED: 0, last: null },
      question: { count: 0, last: null }, answer: { count: 0, last: null },
    },
    trend, cats,
    products: Object.fromEntries(Object.entries(PROD).map(([k, v]) => [k, empty ? 0 : v])),
    chan: Object.fromEntries(CHAN.map((c) => [c[0], Math.round(total * c[1])])),
    low_stock: empty ? [] : [{ name: 'Cushion Foundation', stok: 25 }, { name: 'Serum Vitamin C', stok: 40 }, { name: 'Lip Cream Matte', stok: 60 }],
    hermes_connected: true,
    hermes: [],
    feed: [{ t: Date.now(), text: empty ? 'Data demo dikosongkan.' : 'Panggung siap. Menunggu transaksi demo.', tone: 'b' }],
    batches: [], events: [], insights: [],
    agent: { status: 'idle', step: null, batchId: null, label: '', lastDone: false },
  }
}

function view(S) {
  return {
    ...S,
    categories: Object.entries(S.cats).map(([name, value]) => ({ name, value })).filter((c) => c.value > 0),
    channels: Object.entries(S.chan).map(([name, value]) => ({ name, value })).filter((c) => c.value > 0),
  }
}

// Satu batch mentah yang sengaja "kotor" (format tanggal beda, harga bertuliskan Rp, status huruf besar,
// tanggal kosong, baris duplikat), beserta versi bersihnya. Angka omzet dihitung dari baris bersih.
function makeBatch(id, channel, file) {
  const n = 6 + Math.floor(Math.random() * 7)
  const now = new Date()
  const iso = now.toISOString().slice(0, 10)
  const dmy = `${String(now.getDate()).padStart(2, '0')}/${String(now.getMonth() + 1).padStart(2, '0')}/${now.getFullYear()}`
  const raw = []
  const clean = []
  const st = { kept: 0, dup: 0, empty: 0, fmt: 0, rev: 0, orders: 0 }
  for (let i = 0; i < n; i++) {
    const [name, cat, price] = pick(CATALOG)
    const qty = pick([1, 1, 1, 2, 2, 3])
    const cancelled = Math.random() < 0.1
    const flags = {}
    const c = {
      order_id: `DEMO-${String(id).padStart(2, '0')}${String(i + 1).padStart(3, '0')}`, tanggal: iso, produk: name, kategori: cat,
      qty: String(qty), harga_satuan: String(price), subtotal: String(price * qty), status: cancelled ? 'cancelled' : 'completed',
    }
    if (Math.random() < 0.06) { c.tanggal = ''; flags.tanggal = 'empty'; st.empty++ }
    else if (Math.random() < 0.18) { c.tanggal = dmy; flags.tanggal = 'format'; st.fmt++ }
    if (Math.random() < 0.2) { c.harga_satuan = `Rp ${price.toLocaleString('id-ID')}`; flags.harga_satuan = 'format'; st.fmt++ }
    if (!cancelled && Math.random() < 0.2) { c.status = 'COMPLETED'; flags.status = 'format'; st.fmt++ }
    raw.push({ c, flags })
    clean.push({
      c: { order_id: c.order_id, tanggal: iso, produk: name, kategori: cat, qty, harga_satuan: price, subtotal: price * qty, status: cancelled ? 'cancelled' : 'completed' },
      fixed: Object.keys(flags),
    })
    if (!cancelled) { st.rev += price * qty; st.orders++ }
    if (Math.random() < 0.12) { raw.push({ c: { ...c }, flags: { order_id: 'dup' } }); st.dup++ }
  }
  st.kept = clean.length
  return { id, file, channel, rows: raw.length, status: 'masuk', t: Date.now(), cols: COLS, raw, clean, stats: st }
}

function createMock(onChange, { paused: startPaused = true } = {}) {
  let paused = startPaused
  const S = initial()
  const timers = []
  const queue = []
  let busy = false
  let nb = 0
  let qi = 0
  let ii = 0
  const later = (f, ms) => timers.push(setTimeout(f, ms))
  const emit = () => onChange(view(structuredClone(S)))
  const log = (text, tone) => { S.feed.unshift({ t: Date.now(), text, tone }); S.feed.length = Math.min(S.feed.length, 30) }
  const ev = (kind, text, tone, batchId, extra = {}) => {
    S.events.unshift({ t: Date.now(), kind, text, tone, batchId, ...extra })
    S.events.length = Math.min(S.events.length, 40)
    if (kind !== 'hermes') log(text, tone)
  }
  const tr = () => { S.flow.trust.last = Date.now() }
  const agent = (step, label, batchId) => { S.agent = { status: 'working', step, batchId, label, lastDone: false } }

  function arrive(fname, promote = true, channel) {
    const id = ++nb
    const b = makeBatch(id, channel || pick(CHAN)[0], fname || `demo_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}_${String(id).padStart(2, '0')}.csv`)
    S.batches.unshift(b)
    S.batches.length = Math.min(S.batches.length, 12)
    S.flow.file.count++; S.flow.file.last = Date.now()
    S.flow.batch.count++; S.flow.batch.last = Date.now()
    S.flow.trust.INGESTED++; tr()
    ev('file', `Menemukan file baru: ${b.file} (${b.channel})`, 'b', id)
    queue.push({ b, promote })
    emit()
    pump()
  }

  function pump() {
    if (busy || !queue.length) return
    busy = true
    const { b, promote } = queue.shift()
    const find = () => S.batches.find((x) => x.id === b.id)
    const st = b.stats
    const step = (ms, fn) => later(fn, ms)

    b.status = 'diproses'
    agent('read', `Membaca ${b.file}`, b.id)
    ev('read', `Membaca ${b.rows} baris mentah dari ${b.channel}`, 'b', b.id)
    emit()

    step(1100, () => {
      agent('clean', `Merapikan ${b.file}`, b.id)
      const parts = []
      if (st.dup) parts.push(`${st.dup} duplikat dibuang`)
      if (st.empty) parts.push(`${st.empty} tanggal kosong diisi`)
      if (st.fmt) parts.push(`${st.fmt} nilai diseragamkan`)
      ev('clean', parts.length ? `Merapikan: ${parts.join(', ')}` : 'Tidak ada yang perlu diperbaiki', 'y', b.id)
      emit()
    })
    step(2700, () => {
      S.flow.trust.INGESTED--; S.flow.trust.VALIDATING++; tr()
      agent('validate', `Memeriksa aturan di ${b.file}`, b.id)
      ev('validate', 'Memeriksa aturan: order unik, qty × harga = subtotal', 'y', b.id)
      emit()
    })
    step(4100, () => {
      agent('trust', `Menetapkan status ${b.file}`, b.id)
      if (!promote) {
        ev('trust', `${b.file} divalidasi, menunggu promote`, 'y', b.id)
        const x = find(); if (x) x.status = 'bersih'
      } else if (Math.random() > 0.1) {
        S.flow.trust.VALIDATING--; S.flow.trust.TRUSTED++; tr()
        const d = S.trend[29]; d.rev += st.rev; d.ord += st.orders
        b.clean.forEach((r) => {
          if (r.c.status !== 'completed') return
          S.cats[r.c.kategori] = (S.cats[r.c.kategori] || 0) + r.c.subtotal
          S.products[r.c.produk] = (S.products[r.c.produk] || 0) + r.c.qty
        })
        S.chan[b.channel] = (S.chan[b.channel] || 0) + st.rev
        const x = find(); if (x) x.status = 'bersih'
        ev('trust', `Terpercaya: +${st.orders} order (${rp(st.rev)}) masuk ke omzet`, 'g', b.id)
      } else {
        S.flow.trust.VALIDATING--; S.flow.trust.NEEDS_REVIEW++; tr()
        const x = find(); if (x) x.status = 'tinjau'
        ev('trust', `${b.file} perlu ditinjau, belum dihitung ke omzet`, 'y', b.id)
      }
      emit()
    })
    step(5300, () => {
      agent('insight', 'Menyusun insight', b.id)
      const topP = Object.entries(S.products).sort((a, c) => c[1] - a[1])[0]
      const topC = Object.entries(S.chan).sort((a, c) => c[1] - a[1])[0]
      const low = [...S.low_stock].sort((a, c) => a.stok - c.stok)[0]
      const options = [
        { title: 'Produk terlaris', text: `${topP[0]} (${topP[1]} terjual dalam 30 hari)`, tone: 'g' },
        { title: 'Channel teratas', text: `${topC[0]} menyumbang ${rp(topC[1])} dalam 30 hari`, tone: 'b' },
        low && { title: 'Stok perlu perhatian', text: `${low.name} tinggal ${low.stok} unit`, tone: 'y' },
      ].filter(Boolean)
      let ins = options[ii++ % options.length]
      if (st.dup) ins = { title: 'Duplikat dicegah', text: `${st.dup} baris ganda di ${b.file} dibuang, omzet tidak terhitung dobel`, tone: 'y' }
      S.insights.unshift({ id: `${b.id}-${Date.now()}`, ...ins, batchId: b.id })
      S.insights.length = Math.min(S.insights.length, 6)
      ev('insight', `Insight baru: ${ins.title.toLowerCase()}`, 'g', b.id)
      emit()
    })
    step(6300, () => {
      S.agent = { status: 'idle', step: null, batchId: b.id, label: '', lastDone: true }
      busy = false
      emit()
      pump()
    })
  }

  function ask() {
    if (S.trend.every((x) => x.rev === 0)) return // belum ada data terpercaya untuk dijawab
    const qs = [
      ['Produk apa yang paling laris bulan ini?', () => { const [p, n] = Object.entries(S.products).sort((a, b) => b[1] - a[1])[0]; return `${p}, ${n} terjual dalam 30 hari.` }, ['get_top_products']],
      ['Channel mana yang omzetnya terbesar?', () => { const [c, v] = Object.entries(S.chan).sort((a, b) => b[1] - a[1])[0]; return `${c}, sekitar ${rp(v)} dalam 30 hari.` }, ['get_revenue_by_channel']],
      ['Stok apa yang hampir habis?', () => { const s = [...S.low_stock].sort((a, b) => a.stok - b.stok)[0]; return s ? `${s.name}, sisa ${s.stok} unit.` : 'Belum ada data stok.' }, ['get_low_stock']],
    ]
    const [q, a, src] = qs[qi++ % qs.length]
    S.flow.question.count++; S.flow.question.last = Date.now(); log('Hermes ditanya', 'b'); emit()
    later(() => {
      const answer = a()
      const sources = [...src, 'dataset: Penjualan (TRUSTED)']
      S.hermes.unshift({ q, a: answer, sources }); S.hermes.length = Math.min(S.hermes.length, 6)
      ev('hermes', q, 'b', null, { q, a: answer, sources })
      S.flow.answer.count++; S.flow.answer.last = Date.now(); log('Hermes menjawab dengan sumber', 'g'); emit()
    }, 1600)
  }

  const i1 = setInterval(() => { if (!paused) arrive() }, 9000)
  const i2 = setInterval(() => { if (!paused) ask() }, 22000)
  if (!paused) { arrive(); later(() => { if (!paused) ask() }, 12000) }
  emit()
  return {
    stop: () => { clearInterval(i1); clearInterval(i2); timers.splice(0).forEach(clearTimeout) },
    pause: () => { paused = true }, resume: () => { paused = false }, isPaused: () => paused,
    trigger: async () => { arrive(); return 'Transaksi demo dikirim' },
    upload: async (file, { promote = true } = {}) => { arrive(file?.name || 'unggahan.csv', promote); return `File ${file?.name || ''} dikirim`.trim() },
    backfill: async () => {
      const f = initial(); S.trend = f.trend; S.cats = f.cats; S.chan = f.chan; S.products = f.products; S.low_stock = f.low_stock
      ev('info', 'Riwayat 30 hari diisi', 'b'); emit(); return 'Data 30 hari diisi'
    },
    resetPreview: async () => `Akan dihapus: ${S.flow.file.count} file, ${S.flow.batch.count} batch, dan seluruh angka penjualan demo.`,
    reset: async () => {
      timers.splice(0).forEach(clearTimeout); queue.length = 0; busy = false
      Object.assign(S, initial(true)); nb = 0; qi = 0; ii = 0; emit(); return 'Data demo dikosongkan'
    },
  }
}

export function useStageData() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const ctl = useRef(null)
  const pullRef = useRef(null)
  // Mock mulai dalam keadaan diam (Otomatis mati) kecuali dibuka dengan ?otomatis.
  const [paused, setPaused] = useState(() => !flag('otomatis'))
  const mock = MODE === 'mock'

  useEffect(() => {
    if (mock) {
      const m = createMock(setData, { paused: !flag('otomatis') })
      ctl.current = m
      return m.stop
    }
    let alive = true
    const pull = async () => {
      try {
        if (!api.getStageSummary) throw new Error('api.getStageSummary belum dibuat di client.js')
        const d = await api.getStageSummary()
        if (alive) { setData(d); setError(null) }
      } catch (e) {
        // Detail hanya ke konsol: layar ini bisa tampil saat siaran, jadi pesannya sengaja umum.
        console.warn('[panggung]', e)
        if (alive) setError('Tidak bisa mengambil data. Cek apakah backend menyala dan kamu sudah login.')
      }
    }
    pullRef.current = pull
    pull()
    // Tab yang tidak terlihat tidak ikut menembak backend (banyak tab terbuka = backend kewalahan).
    const id = setInterval(() => { if (!document.hidden) pull() }, 3000)
    const onVisible = () => { if (!document.hidden) pull() }
    document.addEventListener('visibilitychange', onVisible)
    return () => { alive = false; clearInterval(id); document.removeEventListener('visibilitychange', onVisible) }
  }, [mock])

  const togglePause = () => {
    const m = ctl.current
    if (!m) return
    if (m.isPaused()) m.resume(); else m.pause()
    setPaused(m.isPaused())
  }

  const call = (name) => async (...args) => {
    if (mock) return ctl.current[name](...args)
    const fn = api['stage' + name[0].toUpperCase() + name.slice(1)]
    if (!fn) throw new Error('aksi belum tersedia di backend')
    // Selama aksi berjalan, ambil data tiap detik supaya langkah (masuk, divalidasi, terpercaya) terlihat di layar.
    const fast = setInterval(() => pullRef.current?.(), 1000)
    try {
      const res = await fn(...args)
      await pullRef.current?.()
      return res && typeof res.message === 'string' ? res.message : null
    } finally {
      clearInterval(fast)
    }
  }
  const resetPreview = async () => {
    if (mock) return ctl.current.resetPreview()
    if (!api.stageResetPreview) return null
    const p = await api.stageResetPreview()
    if (!p || (!p.datasets && !p.batches)) return 'Tidak ada data demo untuk dihapus.'
    return `Akan dihapus: ${p.datasets} dataset, ${p.batches} batch, ${p.files} file, ${p.transactions} transaksi.`
  }
  const actions = { trigger: call('trigger'), backfill: call('backfill'), upload: call('upload'), reset: call('reset'), resetPreview }
  const caps = mock
    ? { trigger: true, backfill: true, upload: true, reset: true, resetPreview: true, auto: true }
    : { trigger: !!api.stageTrigger, backfill: !!api.stageBackfill, upload: !!api.stageUpload, reset: !!api.stageReset, resetPreview: !!api.stageResetPreview, auto: false }

  return { data, error, mode: MODE, paused, togglePause, actions, caps }
}
