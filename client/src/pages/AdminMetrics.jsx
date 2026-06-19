import { useEffect, useState } from 'react'
import { useApp } from '../context/context'
import KpiCard from '../components/KpiCard'

export default function AdminMetrics() {
  const { getAdminMetrics, toast } = useApp()
  const [data, setData] = useState(null)

  useEffect(() => {
    getAdminMetrics()
      .then(setData)
      .catch((err) => toast(err.message, 'error'))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const m = data?.metrics || {}

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-primary">Admin Metrics</h1>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Users" value={m.users ?? '—'} />
        <KpiCard label="Watchlist entries" value={m.watchlist ?? '—'} />
        <KpiCard label="Alerts (24h)" value={m.alerts_24h ?? '—'} />
        <KpiCard label="Login failures (24h)" value={m.login_failures_24h ?? '—'} tone="down" />
      </div>

      <div className="ss-card overflow-x-auto">
        <div className="border-b border-line px-4 py-3 text-sm font-semibold text-primary">
          Audit log
        </div>
        <table className="ss-table">
          <thead>
            <tr>
              <th>When</th>
              <th>Action</th>
              <th>User</th>
              <th>IP</th>
            </tr>
          </thead>
          <tbody>
            {(data?.audit || []).map((a, i) => (
              <tr key={i}>
                <td className="text-xs text-tertiary">
                  {a.occurred_at ? new Date(a.occurred_at).toLocaleString() : '—'}
                </td>
                <td>{a.action}</td>
                <td className="text-xs">{a.user_id || '—'}</td>
                <td className="text-xs text-tertiary">{a.ip || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
