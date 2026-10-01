import { useEffect, useState } from 'react'
import { pickQuote } from '../lib/quotes'
import { prefersReducedMotion } from '../lib/motion'

// Dipisah supaya setiap kalimat baru memudar masuk dengan lembut (key = teksnya).
function Line({ text }) {
  const [on, setOn] = useState(() => prefersReducedMotion())
  useEffect(() => {
    const id = setTimeout(() => setOn(true), 60)
    return () => clearTimeout(id)
  }, [])
  return (
    <p
      className={`text-xs md:text-sm leading-relaxed text-text-primary/90 transition-opacity duration-1000 motion-reduce:transition-none ${
        on ? 'opacity-100' : 'opacity-0'
      }`}
    >
      {text}
    </p>
  )
}

export default function DailyQuote({ done, streaks, left }) {
  const { text } = pickQuote({ done, streaks, left })
  return (
    <div className="mt-4 md:mt-6 border-l-2 border-accent/60 pl-3 md:pl-4" aria-live="polite">
      <div className="max-md:hidden text-[10px] uppercase tracking-widest text-text-muted font-display mb-1">
        Pemantik hari ini
      </div>
      <Line key={text} text={text} />
    </div>
  )
}
