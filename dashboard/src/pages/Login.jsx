import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await api.login(username, password)
      navigate('/')
    } catch (err) {
      setError('Username atau password salah.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex h-screen items-center justify-center bg-ink font-body">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-4 rounded-lg border border-white/10 bg-white/5 p-8"
      >
        <h1 className="text-xl font-semibold text-white">Talatee Control Center</h1>
        <p className="text-sm text-white/60">Masuk untuk melanjutkan.</p>

        {error && (
          <p className="rounded bg-red-500/10 px-3 py-2 text-sm text-red-400">{error}</p>
        )}

        <div>
          <label className="mb-1 block text-sm text-white/70">Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full rounded border border-white/10 bg-white/5 px-3 py-2 text-white outline-none focus:border-white/30"
            autoFocus
          />
        </div>

        <div>
          <label className="mb-1 block text-sm text-white/70">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded border border-white/10 bg-white/5 px-3 py-2 text-white outline-none focus:border-white/30"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-white/10 py-2 text-white transition hover:bg-white/20 disabled:opacity-50"
        >
          {loading ? 'Memproses...' : 'Masuk'}
        </button>
      </form>
    </div>
  )
}
