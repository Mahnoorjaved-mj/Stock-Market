import { useEffect, useState } from 'react'
import { useApp } from '../context/context'

const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

export default function Settings() {
  const { getProfile, updateProfile, twoFaSetup, twoFaVerify, twoFaDisable, theme, toggleTheme, toast } =
    useApp()
  const [profile, setProfile] = useState(null)
  const [twofa, setTwofa] = useState(null) // { secret, otpauth }
  const [code, setCode] = useState('')

  useEffect(() => {
    getProfile()
      .then((res) => setProfile(res.profile))
      .catch((err) => toast(err.message, 'error'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const saveAlerts = async (e) => {
    e.preventDefault()
    try {
      await updateProfile({
        alert_threshold_pct: Number(profile.alert_threshold_pct),
        digest_frequency: profile.digest_frequency,
        digest_day: Number(profile.digest_day),
      })
      toast('Settings saved', 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const setupTwoFa = async () => {
    try {
      setTwofa(await twoFaSetup())
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const verifyTwoFa = async () => {
    try {
      await twoFaVerify(code)
      toast('2FA enabled', 'success')
      setTwofa(null)
      setCode('')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const disableTwoFa = async () => {
    try {
      await twoFaDisable()
      toast('2FA disabled', 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  if (!profile) return <div className="text-secondary">Loading…</div>

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-xl font-semibold text-primary">Settings</h1>

      <form onSubmit={saveAlerts} className="ss-card space-y-4 p-5">
        <h2 className="text-sm font-semibold text-primary">Alerts & digests</h2>
        <div>
          <label className="ss-label">Default alert threshold (%)</label>
          <input
            type="number"
            step="0.1"
            className="ss-input"
            value={profile.alert_threshold_pct}
            onChange={(e) => setProfile({ ...profile, alert_threshold_pct: e.target.value })}
          />
        </div>
        <div>
          <label className="ss-label">Digest frequency</label>
          <select
            className="ss-input"
            value={profile.digest_frequency}
            onChange={(e) => setProfile({ ...profile, digest_frequency: e.target.value })}
          >
            <option value="off">Off</option>
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
          </select>
        </div>
        <div>
          <label className="ss-label">Weekly digest day</label>
          <select
            className="ss-input"
            value={profile.digest_day}
            onChange={(e) => setProfile({ ...profile, digest_day: e.target.value })}
          >
            {DAYS.map((d, i) => (
              <option key={d} value={i}>
                {d}
              </option>
            ))}
          </select>
        </div>
        <button className="ss-btn">Save</button>
      </form>

      <div className="ss-card space-y-4 p-5">
        <h2 className="text-sm font-semibold text-primary">Two-factor authentication</h2>
        {!twofa ? (
          <div className="flex gap-2">
            <button className="ss-btn" onClick={setupTwoFa}>
              Set up 2FA
            </button>
            <button className="ss-btn-ghost" onClick={disableTwoFa}>
              Disable
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-secondary">
              Add this secret to your authenticator app, then enter the 6-digit code:
            </p>
            <code className="block break-all rounded bg-input p-2 text-xs text-accent">
              {twofa.secret}
            </code>
            <div className="flex gap-2">
              <input
                className="ss-input"
                placeholder="123456"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              />
              <button className="ss-btn" onClick={verifyTwoFa}>
                Verify
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="ss-card flex items-center justify-between p-5">
        <div>
          <h2 className="text-sm font-semibold text-primary">Appearance</h2>
          <p className="text-sm text-secondary">Current theme: {theme}</p>
        </div>
        <button className="ss-btn-ghost" onClick={toggleTheme}>
          Toggle theme
        </button>
      </div>
    </div>
  )
}
