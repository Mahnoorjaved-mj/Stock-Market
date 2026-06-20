import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { TrendingUp } from 'lucide-react'
import { useApp } from '../context/context'

export default function Login() {
  const { login, toast } = useApp()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await login(email, password)
      toast('Welcome back!', 'success')
      navigate('/')
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-app px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-2">
          <TrendingUp className="text-accent" size={26} />
          <span className="text-xl font-semibold text-primary">StockSense</span>
        </div>
        <form onSubmit={submit} className="ss-card space-y-4 p-6">
          <h1 className="text-lg font-semibold text-primary">Sign in</h1>
          <div>
            <label className="ss-label">Email</label>
            <input
              type="email"
              className="ss-input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="ss-label">Password</label>
            <input
              type="password"
              className="ss-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button className="ss-btn w-full" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in'}
          </button>
          <div className="flex justify-between text-sm">
            <Link to="/forgot-password" className="text-accent hover:underline">
              Forgot password?
            </Link>
            <Link to="/register" className="text-secondary hover:text-primary">
              Create account
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
