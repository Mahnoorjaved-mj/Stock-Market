import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { TrendingUp } from 'lucide-react'
import { useApp } from '../context/context'

export default function ResetPassword() {
  const { resetPassword, toast } = useApp()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const token = params.get('token') || ''
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await resetPassword(token, password)
      toast('Password updated — sign in', 'success')
      navigate('/login')
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
          <h1 className="text-lg font-semibold text-primary">Set a new password</h1>
          {!token ? (
            <p className="text-sm text-down">Missing or invalid reset token.</p>
          ) : (
            <>
              <input
                type="password"
                className="ss-input"
                placeholder="New password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button className="ss-btn w-full" disabled={busy}>
                {busy ? 'Updating…' : 'Update password'}
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
