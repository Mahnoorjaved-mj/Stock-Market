import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, RefreshCw } from 'lucide-react'
import { useApp } from '../context/context'

export default function AIPredictions() {
  const { sentiment, trainModel, topPicks, toast } = useApp()
  const navigate = useNavigate()
  const [symbol, setSymbol] = useState('')
  const [result, setResult] = useState(null)
  const [picks, setPicks] = useState([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    topPicks().then((r) => setPicks(r.top_picks || [])).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const analyze = async (e) => {
    e.preventDefault()
    if (!symbol) return
    setBusy(true)
    try {
      setResult(await sentiment(symbol.toUpperCase()))
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const retrain = async () => {
    if (!symbol) return
    setBusy(true)
    try {
      const res = await trainModel(symbol.toUpperCase())
      toast(res.message || (res.success ? 'Training started' : 'Training failed'), res.success ? 'success' : 'error')
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setBusy(false)
    }
  }

  const sent = result?.sentiment

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-primary">AI Predictions</h1>

      <form onSubmit={analyze} className="ss-card flex flex-wrap items-end gap-3 p-4">
        <div className="flex-1">
          <label className="ss-label">Symbol</label>
          <input
            className="ss-input uppercase"
            placeholder="AAPL"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          />
        </div>
        <button className="ss-btn" disabled={busy}>
          <Search size={15} /> Analyze
        </button>
        <button type="button" className="ss-btn-ghost" onClick={retrain} disabled={busy}>
          <RefreshCw size={15} /> Retrain
        </button>
      </form>

      {sent && (
        <div className="ss-card p-5">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{sent.emoji}</span>
            <div>
              <div className="text-lg font-semibold" style={{ color: sent.color }}>
                {sent.sentiment}
              </div>
              <div className="text-sm text-secondary">
                {sent.confidence}% confidence · predicted {sent.predicted_change > 0 ? '+' : ''}
                {sent.predicted_change}% · {sent.model}
              </div>
            </div>
          </div>
          {sent.reasoning && <p className="mt-3 text-sm text-secondary">{sent.reasoning}</p>}
        </div>
      )}

      <div>
        <h2 className="mb-3 text-sm font-semibold text-primary">Top picks</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {picks.map((p, i) => (
            <button
              key={p.symbol}
              onClick={() => navigate(`/stock/${p.symbol}`)}
              className="ss-card p-4 text-left hover:bg-surface-hover"
            >
              <div className="flex items-center justify-between">
                <span className="font-semibold text-primary">
                  #{i + 1} {p.symbol}
                </span>
                <span className="text-xl">{p.emoji}</span>
              </div>
              <div className="text-xs text-tertiary">{p.name}</div>
              <div className="mt-2 flex items-center justify-between text-sm">
                <span style={{ color: p.color }}>{p.sentiment}</span>
                <span className="text-secondary">{p.confidence}%</span>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
