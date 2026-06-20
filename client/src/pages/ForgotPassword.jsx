import { useState } from 'react'
import { Link } from 'react-router-dom'
import { TrendingUp } from 'lucide-react'
import { useApp } from '../context/context'

export default function ForgotPassword() {
  const { forgotPassword, toast } = useApp()
  const [email, setEmail] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await forgotPassword(email)
      setSent(true)
      toast('If that email exists, a reset link was sent', 'success')
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
          <h1 className="text-lg font-semibold text-primary">Reset password</h1>
          {sent ? (
            <p className="text-sm text-secondary">
              Check your inbox for a reset link. It expires in 1 hour.
            </p>
          ) : (
            <>
              <p className="text-sm text-secondary">
                Enter your email and we'll send you a reset link.
              </p>
              <input
                type="email"
                className="ss-input"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
              <button className="ss-btn w-full" disabled={busy}>
                {busy ? 'Sending…' : 'Send reset link'}
              </button>
            </>
          )}
          <div className="text-center text-sm">
            <Link to="/login" className="text-secondary hover:text-primary">
              Back to sign in
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
