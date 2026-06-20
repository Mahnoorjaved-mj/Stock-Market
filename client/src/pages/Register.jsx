import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { TrendingUp } from 'lucide-react'
import { useApp } from '../context/context'

// Password strength hint mirroring the backend rules.
function strength(pw) {
  let s = 0
  if (pw.length >= 10) s++
  if (/[A-Za-z]/.test(pw) && /\d/.test(pw)) s++
  if (/[^A-Za-z0-9]/.test(pw) || pw.length >= 14) s++
  return s // 0..3
}

export default function Register() {
  const { register, verifyOtp, toast } = useApp()
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [otp, setOtp] = useState('')
  const [busy, setBusy] = useState(false)

  const s = strength(password)
  const strengthLabel = ['Too weak', 'Weak', 'Good', 'Strong'][s]
  const strengthColor = ['var(--color-down)', 'var(--color-warn)', 'var(--accent)', 'var(--color-up)'][s]

  const submitStep1 = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await register(email, password, name)
      toast('OTP sent to your email', 'success')
      setStep(2)
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const submitStep2 = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      await verifyOtp(email, otp)
      toast('Account created!', 'success')
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

        {step === 1 ? (
          <form onSubmit={submitStep1} className="ss-card space-y-4 p-6">
            <h1 className="text-lg font-semibold text-primary">Create your account</h1>
            <div>
              <label className="ss-label">Name</label>
              <input className="ss-input" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
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
              {password && (
                <div className="mt-1.5 flex items-center gap-2">
                  <div className="h-1 flex-1 rounded bg-surface-hover">
                    <div
                      className="h-1 rounded transition-all"
                      style={{ width: `${(s / 3) * 100}%`, background: strengthColor }}
                    />
                  </div>
                  <span className="text-xs" style={{ color: strengthColor }}>
                    {strengthLabel}
                  </span>
                </div>
              )}
            </div>
            <button className="ss-btn w-full" disabled={busy}>
              {busy ? 'Sending…' : 'Continue'}
            </button>
            <div className="text-center text-sm">
              <Link to="/login" className="text-secondary hover:text-primary">
                Already have an account? Sign in
              </Link>
            </div>
          </form>
        ) : (
          <form onSubmit={submitStep2} className="ss-card space-y-4 p-6">
            <h1 className="text-lg font-semibold text-primary">Verify your email</h1>
            <p className="text-sm text-secondary">
              Enter the 6-digit code we sent to <span className="text-primary">{email}</span>.
            </p>
            <input
              className="ss-input text-center text-lg tracking-[0.3em]"
              maxLength={6}
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
              required
            />
            <button className="ss-btn w-full" disabled={busy}>
              {busy ? 'Verifying…' : 'Verify & create account'}
            </button>
            <button
              type="button"
              className="w-full text-center text-sm text-secondary hover:text-primary"
              onClick={() => setStep(1)}
            >
              Back
            </button>
          </form>
        )}
      </div>
    </div>
  )
}
