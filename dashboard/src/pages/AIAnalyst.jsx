import { useEffect, useRef, useState } from 'react'
import { Bot, Send, User, Trash2 } from 'lucide-react'
import { api } from '../api/client'

// Riwayat chat disimpan di localStorage browser (bukan backend) -- jadi
// tetap ada kalau halaman di-refresh, tapi cuma di browser/device ini, dan
// hilang kalau user clear browser data atau klik "Percakapan baru".
const STORAGE_KEY = 'talatee_ai_analyst_history'

function loadHistory() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}

// Bubble sederhana; role 'user' rata kanan, 'assistant'/'error' rata kiri.
function Bubble({ role, content }) {
  const isUser = role === 'user'
  const isError = role === 'error'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`flex gap-2 max-w-[80%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
        <div
          className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
            isUser ? 'bg-accent/20 text-accent' : 'bg-ink-elevated text-text-muted'
          }`}
        >
          {isUser ? <User size={14} /> : <Bot size={14} />}
        </div>
        <div
          className={`rounded-lg px-3 py-2 text-sm whitespace-pre-wrap ${
            isUser
              ? 'bg-accent/15 text-text-primary'
              : isError
                ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                : 'bg-ink-surface border border-ink-border text-text-primary'
          }`}
        >
          {content}
        </div>
      </div>
    </div>
  )
}

export default function AIAnalyst() {
  const [messages, setMessages] = useState(loadHistory)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(messages))
    } catch {
      // localStorage penuh/diblokir browser -- riwayat cukup hilang saat
      // refresh, tidak perlu ganggu alur chat dengan error.
    }
  }, [messages])

  function clearHistory() {
    setMessages([])
    try {
      localStorage.removeItem(STORAGE_KEY)
    } catch {
      // sama seperti di atas -- aman diabaikan.
    }
  }

  async function send() {
    const text = input.trim()
    if (!text || sending) return

    const history = messages.map(({ role, content }) => ({ role, content }))
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInput('')
    setSending(true)

    try {
      const { reply } = await api.sendChatMessage(text, history)
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }])
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'error', content: err.message }])
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-6rem)]">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display text-xl text-text-primary">AI Analyst</h1>
          <p className="text-text-muted text-sm mt-1">
            Tanya soal data bisnismu, langsung di sini -- tanpa buka Hermes.
          </p>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearHistory}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs text-text-muted hover:text-text-primary hover:bg-ink-elevated/60 border border-ink-border"
          >
            <Trash2 size={13} />
            Percakapan baru
          </button>
        )}
      </div>

      <div className="flex-1 min-h-0 bg-ink-surface border border-ink-border rounded-lg mt-4 flex flex-col overflow-hidden">
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center gap-2 text-text-muted">
              <Bot size={28} strokeWidth={1.5} />
              <p className="text-sm max-w-xs">
                Contoh: "Bagaimana penjualan Test Warung minggu ini?" atau "produk apa yang paling laku bulan ini?"
              </p>
            </div>
          )}
          {messages.map((m, i) => (
            <Bubble key={i} role={m.role} content={m.content} />
          ))}
          {sending && (
            <Bubble role="assistant" content="Mengetik..." />
          )}
          <div ref={scrollRef} />
        </div>

        <div className="border-t border-ink-border p-3 flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Tanya sesuatu... (Enter kirim, Shift+Enter baris baru)"
            rows={1}
            className="flex-1 resize-none bg-ink-elevated border border-ink-border rounded-md px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-accent"
          />
          <button
            onClick={send}
            disabled={sending || !input.trim()}
            className="w-9 h-9 shrink-0 rounded-md bg-accent text-ink flex items-center justify-center disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  )
}
