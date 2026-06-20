import { useEffect, useState } from 'react'
import { Play } from 'lucide-react'
import { useApp } from '../context/context'

const TYPE_LABEL = {
  pct_move: '% move',
  target_high: 'Above target',
  target_low: 'Below target',
}

export default function Alerts() {
  const { getAlertHistory, runAlertsNow, toast } = useApp()
  const [items, setItems] = useState([])
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const res = await getAlertHistory()
      setItems(res.items || [])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const runNow = async () => {
    setBusy(true)
    try {
      const res = await runAlertsNow()
      const s = res.summary || {}
      toast(`Sweep done: ${s.sent ?? 0} sent, ${s.skipped ?? 0} skipped`, 'success')
      load()
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-primary">Alerts</h1>
        <button className="ss-btn" onClick={runNow} disabled={busy}>
          <Play size={15} /> {busy ? 'Running…' : 'Run sweep now'}
        </button>
      </div>

      <div className="ss-card overflow-x-auto">
        <table className="ss-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Type</th>
              <th>Price</th>
              <th>Change</th>
              <th>Sent</th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id}>
                <td className="font-medium">{i.symbol}</td>
                <td>
                  <span className="rounded bg-accent-soft px-2 py-0.5 text-xs text-accent">
                    {TYPE_LABEL[i.alert_type] || i.alert_type}
                  </span>
                </td>
                <td>{i.price?.toFixed(2)}</td>
                <td className={(i.change_pct ?? 0) >= 0 ? 'text-up' : 'text-down'}>
                  {i.change_pct != null ? `${i.change_pct.toFixed(2)}%` : '—'}
                </td>
                <td className="text-xs text-tertiary">
                  {i.sent_at ? new Date(i.sent_at).toLocaleString() : '—'}
                </td>
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={5} className="py-8 text-center text-tertiary">
                  No alerts yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
