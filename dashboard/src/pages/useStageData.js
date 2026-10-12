// Sumber data Panggung.
//  - VITE_STAGE_MODE=mock (default): data demo dibangkitkan di browser, untuk menyiapkan tampilan & rekaman.
//  - VITE_STAGE_MODE=api : membaca GET /stage/summary lewat api.getStageSummary() (belum ada, lihat kontrak di bawah).
//
// Kontrak data (bentuk yang sama dipakai mock dan API):
// {
//   flow: { file:{count,last}, batch:{count,last}, trust:{INGESTED,VALIDATING,NEEDS_REVIEW,TRUSTED,last},
//           question:{count,last}, answer:{count,last} },          // last = epoch ms atau null
//   trend: [{ d:"1", rev:2400000, ord:85 }, ...],                  // 30 hari terakhir, hanya batch TRUSTED
//   categories: [{ name, value }], channels: [{ name, value }],
//   low_stock: [{ name, stok }],
//   hermes: [{ q, a, sources:["get_top_products", ...] }],         // terbaru di atas
//   feed: [{ t, text, tone:"g"|"b"|"y" }]                          // terbaru di atas
// }
import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'

const MODE = import.meta.env.VITE_STAGE_MODE || 'mock'

const CATS = [['Skincare', 0.32], ['Makeup', 0.22], ['Perawatan Rambut', 0.16], ['Body Care', 0.13], ['Lainnya', 0.17]]
const CHAN = [['TikTok Shop', 0.36], ['Shopee', 0.3], ['Lazada', 0.17], ['WhatsApp', 0.1], ['Website', 0.07]]
const PROD = { 'Serum Vitamin C': 310, 'Moisturizer Gel': 260, 'Sunscreen SPF50': 240, 'Body Lotion': 200, 'Lip Cream Matte': 180, 'Shampoo Anti Ketombe': 170 }
const rp = (v) => (v >= 1e6 ? `Rp ${(v / 1e6).toFixed(2).replace('.', ',')} jt` : `Rp ${Math.round(v / 1000)} rb`)

function initial() {
  const trend = []
  const cats = Object.fromEntries(CATS.map((c) => [c[0], 0]))
  for (let i = 0; i < 30; i++) {
    let rev = Math.round(2.4e6 + i * 38000 + Math.sin(i * 0.9) * 3.6e5 + Math.cos(i * 2.3) * 1.5e5)
    if (i === 29) rev = Math.round(rev * 0.42)
    trend.push({ d: String(i + 1), rev, ord: Math.round(rev / 28000) })
    CATS.forEach((c) => (cats[c[0]] += Math.round(rev * c[1])))
  }
  const total = trend.reduce((n, x) => n + x.rev, 0)
  const now = Date.now()
  return {
    flow: {
      file: { count: 0, last: null }, batch: { count: 0, last: null },
      trust: { INGESTED: 0, VALIDATING: 0, NEEDS_REVIEW: 0, TRUSTED: 0, last: null },
      question: { count: 0, last: null }, answer: { count: 0, last: null },
    },
    trend, cats, products: { ...PROD },
    chan: Object.fromEntries(CHAN.map((c) => [c[0], Math.round(total * c[1])])),
    low_stock: [{ name: 'Cushion Foundation', stok: 25 }, { name: 'Serum Vitamin C', stok: 40 }, { name: 'Lip Cream Matte', stok: 60 }],
    hermes: [], feed: [{ t: now, text: 'Panggung siap. Menunggu transaksi demo.', tone: 'b' }],
  }
}

function view(S) {
  return {
    ...S,
    categories: Object.entries(S.cats).map(([name, value]) => ({ name, value })),
    channels: Object.entries(S.chan).map(([name, value]) => ({ name, value })),
  }
}

function createMock(onChange, { paused: startPaused = false } = {}) {
  let paused = startPaused
  const S = initial()
  const timers = []
  const later = (f, ms) => timers.push(setTimeout(f, ms))
  const emit = () => onChange(view(structuredClone(S)))
  const log = (text, tone) => { S.feed.unshift({ t: Date.now(), text, tone }); S.feed.length = Math.min(S.feed.length, 30) }
  const tr = () => { S.flow.trust.last = Date.now() }
  let nb = 0, qi = 0

  function tx() {
    S.flow.file.count++; S.flow.file.last = Date.now(); log('File transaksi masuk', 'g'); emit()
    later(() => {
      const id = ++nb
      S.flow.batch.count++; S.flow.batch.last = Date.now(); S.flow.trust.INGESTED++; tr(); log(`Batch #${id} tercatat`, 'b'); emit()
      later(() => {
        S.flow.trust.INGESTED--; S.flow.trust.VALIDATING++; tr(); log(`Batch #${id} divalidasi`, 'y'); emit()
        later(() => {
          const ok = Math.random() > 0.12
          S.flow.trust.VALIDATING--; S.flow.trust[ok ? 'TRUSTED' : 'NEEDS_REVIEW']++; tr()
          if (ok) {
            const n = 12 + Math.floor(Math.random() * 14), rev = n * (26000 + Math.floor(Math.random() * 8000))
            const d = S.trend[29]; d.rev += rev; d.ord += n
            CATS.forEach((c) => (S.cats[c[0]] += Math.round(rev * (c[1] + (Math.random() - 0.5) * 0.06))))
            CHAN.forEach((c) => (S.chan[c[0]] += Math.round(rev * c[1])))
            Object.keys(S.products).forEach((p) => (S.products[p] += Math.random() < 0.4 ? 1 + Math.floor(Math.random() * 3) : 0))
            log(`Batch #${id} terpercaya: +${n} order (${rp(rev)})`, 'g')
          } else log(`Batch #${id} perlu ditinjau, belum dihitung`, 'y')
          emit()
        }, 1700)
      }, 1300)
    }, 700)
  }

  function ask() {
    const qs = [
      ['Produk apa yang paling laris bulan ini?', () => { const [p, n] = Object.entries(S.products).sort((a, b) => b[1] - a[1])[0]; return `${p}, ${n} terjual dalam 30 hari.` }, ['get_top_products']],
      ['Channel mana yang omzetnya terbesar?', () => { const [c, v] = Object.entries(S.chan).sort((a, b) => b[1] - a[1])[0]; return `${c}, sekitar ${rp(v)} dalam 30 hari.` }, ['get_revenue_by_channel']],
      ['Stok apa yang hampir habis?', () => { const s = [...S.low_stock].sort((a, b) => a.stok - b.stok)[0]; return `${s.name}, sisa ${s.stok} unit.` }, ['get_low_stock']],
    ]
    const [q, a, src] = qs[qi++ % qs.length]
    S.flow.question.count++; S.flow.question.last = Date.now(); log('Hermes ditanya', 'b'); emit()
    later(() => {
      S.hermes.unshift({ q, a: a(), sources: [...src, 'dataset: Penjualan (TRUSTED)'] }); S.hermes.length = Math.min(S.hermes.length, 6)
      S.flow.answer.count++; S.flow.answer.last = Date.now(); log('Hermes menjawab dengan sumber', 'g'); emit()
    }, 1600)
  }

  const i1 = setInterval(() => { if (!paused) tx() }, 4500)
  const i2 = setInterval(() => { if (!paused) ask() }, 16000)
  if (!paused) { tx(); later(() => { if (!paused) ask() }, 6000) }
  emit()
  return {
    stop: () => { clearInterval(i1); clearInterval(i2); timers.forEach(clearTimeout) },
    pause: () => { paused = true }, resume: () => { paused = false }, isPaused: () => paused,
  }
}

export function useStageData() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const ctl = useRef(null)
  // Simulasi bisa dijeda: tekan P di Panggung, atau buka dengan ?diam supaya mulai dalam keadaan diam.
  const [paused, setPaused] = useState(() => new URLSearchParams(window.location.search).has('diam'))
  useEffect(() => {
    if (MODE === 'mock') {
      const m = createMock(setData, { paused: new URLSearchParams(window.location.search).has('diam') })
      ctl.current = m
      return m.stop
    }
    let alive = true
    const pull = async () => {
      try {
        if (!api.getStageSummary) throw new Error('api.getStageSummary belum dibuat di client.js')
        const d = await api.getStageSummary()
        if (alive) { setData(d); setError(null) }
      } catch (e) { if (alive) setError(e.message || 'Gagal mengambil data') }
    }
    pull()
    const id = setInterval(pull, 3000)
    return () => { alive = false; clearInterval(id) }
  }, [])
  const togglePause = () => {
    const m = ctl.current
    if (!m) return
    if (m.isPaused()) m.resume(); else m.pause()
    setPaused(m.isPaused())
  }
  return { data, error, mode: MODE, paused, togglePause }
}
