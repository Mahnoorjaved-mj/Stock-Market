import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/context'

export default function Profile() {
  const { getProfile, updateProfile, changePassword, deleteAccount, logout, toast } = useApp()
  const navigate = useNavigate()
  const [profile, setProfile] = useState(null)
  const [name, setName] = useState('')
  const [pw, setPw] = useState({ old_password: '', new_password: '' })

  useEffect(() => {
    getProfile()
      .then((res) => {
        setProfile(res.profile)
        setName(res.profile.name || '')
      })
      .catch((err) => toast(err.message, 'error'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const saveName = async (e) => {
    e.preventDefault()
    try {
      await updateProfile({ name })
      toast('Profile updated', 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const savePassword = async (e) => {
    e.preventDefault()
    try {
      await changePassword(pw.old_password, pw.new_password)
      toast('Password changed', 'success')
      setPw({ old_password: '', new_password: '' })
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const removeAccount = async () => {
    if (!window.confirm('Delete your account permanently? This cannot be undone.')) return
    try {
      await deleteAccount()
      await logout()
      toast('Account deleted', 'success')
      navigate('/register')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  if (!profile) return <div className="text-secondary">Loading…</div>

  return (
    <div className="max-w-2xl space-y-6">
      <h1 className="text-xl font-semibold text-primary">Profile</h1>

      <form onSubmit={saveName} className="ss-card space-y-4 p-5">
        <h2 className="text-sm font-semibold text-primary">Account</h2>
        <div>
          <label className="ss-label">Email</label>
          <input className="ss-input" value={profile.email} disabled />
        </div>
        <div>
          <label className="ss-label">Name</label>
          <input className="ss-input" value={name} onChange={(e) => setName(e.target.value)} />
        </div>
        <button className="ss-btn">Save</button>
      </form>

      <form onSubmit={savePassword} className="ss-card space-y-4 p-5">
        <h2 className="text-sm font-semibold text-primary">Change password</h2>
        <div>
          <label className="ss-label">Current password</label>
          <input
            type="password"
            className="ss-input"
            value={pw.old_password}
            onChange={(e) => setPw({ ...pw, old_password: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="ss-label">New password</label>
          <input
            type="password"
            className="ss-input"
            value={pw.new_password}
            onChange={(e) => setPw({ ...pw, new_password: e.target.value })}
            required
          />
        </div>
        <button className="ss-btn">Update password</button>
      </form>

      <div className="ss-card space-y-3 p-5">
        <h2 className="text-sm font-semibold text-down">Danger zone</h2>
        <p className="text-sm text-secondary">Permanently delete your account and all data.</p>
        <button
          onClick={removeAccount}
          className="rounded border border-down px-4 py-2 text-sm font-medium text-down hover:bg-down-soft"
        >
          Delete account
        </button>
      </div>
    </div>
  )
}
