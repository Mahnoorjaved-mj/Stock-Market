import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Plus } from 'lucide-react'
import { useApp } from '../context/context'
import PriceChart from '../components/PriceChart'

const RANGES = ['5d', '1mo', '3mo', '1y', '5y']

export default function StockDetail() {
  const { symbol } = useParams()
  const { getStock, getStockHistory, predict, addWatchlist, user, toast } = useApp()
  const [info, setInfo] = useState(null)
  const [history, setHistory] = useState(null)
  const [range, setRange] = useState('1mo')
  const [pred, setPred] = useState(null)

  useEffect(() => {
    getStock(symbol).then(setInfo).catch((e) => toast(e.message, 'error'))
    predict(symbol).then(setPred).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol])

  useEffect(() => {
    getStockHistory(symbol, range).then(setHistory).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, range])

  const addToWatchlist = async () => {
    if (!user) return toast('Sign in to use the watchlist', 'warn')
    try {
      await addWatchlist({ symbol })
      toast(`${symbol} added to watchlist`, 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const up = (info?.change_percent ?? 0) >= 0

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-primary">{symbol}</h1>
          <p className="text-sm text-secondary">{info?.name}</p>
        </div>
        <div className="flex items-center gap-4">
          {info && (
            <div className="text-right">
              <div className="text-2xl font-semibold text-primary">
                {info.currency} {info.price?.toFixed(2)}
              </div>
              <div className={up ? 'text-up' : 'text-down'}>
                {up ? '+' : ''}
                {info.change_percent?.toFixed(2)}%
              </div>
            </div>
          )}
          <button className="ss-btn" onClick={addToWatchlist}>
            <Plus size={16} /> Watchlist
          </button>
        </div>
      </div>

      <div className="ss-card p-5">
        <div className="mb-4 flex gap-1">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`rounded px-3 py-1 text-xs font-medium ${
                range === r ? 'bg-accent-soft text-accent' : 'text-secondary hover:bg-surface-hover'
              }`}
            >
              {r}
            </button>
          ))}
        </div>
        {history ? (
          <PriceChart
            labels={history.dates}
            datasets={[
              {
                label: symbol,
                data: history.prices,
                borderColor: 'var(--accent)',
                backgroundColor: 'rgba(79,140,255,0.08)',
              },
            ]}
          />
        ) : (
          <div className="py-16 text-center text-tertiary">Loading chart…</div>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="ss-card p-5">
          <h2 className="mb-3 text-sm font-semibold text-primary">AI Forecast</h2>
          {pred ? (
            <>
              <div className="mb-3 flex items-baseline gap-2">
                <span
                  className={`text-2xl font-semibold ${
                    (pred.predictions?.prediction_change ?? 0) >= 0 ? 'text-up' : 'text-down'
                  }`}
                >
                  {pred.predictions?.prediction_change > 0 ? '+' : ''}
                  {pred.predictions?.prediction_change?.toFixed(2)}%
                </span>
                <span className="text-sm text-secondary">
                  {pred.confidence}% confidence · {pred.model_type}
                </span>
              </div>
              <PriceChart
                height={180}
                labels={pred.predictions?.dates || []}
                datasets={[
                  {
                    label: 'Forecast',
                    data: pred.predictions?.prices || [],
                    borderColor: 'var(--color-up)',
                    backgroundColor: 'rgba(16,185,129,0.08)',
                  },
                ]}
              />
            </>
          ) : (
            <div className="py-10 text-center text-tertiary">Loading prediction…</div>
          )}
        </div>

        <div className="ss-card p-5">
          <h2 className="mb-3 text-sm font-semibold text-primary">Key stats</h2>
          {info && (
            <dl className="grid grid-cols-2 gap-3 text-sm">
              {[
                ['Open', info.open],
                ['High', info.high],
                ['Low', info.low],
                ['Prev close', info.prev_close],
                ['Volume', info.volume?.toLocaleString()],
                ['Country', info.country],
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between border-b border-subtle pb-1.5">
                  <dt className="text-tertiary">{k}</dt>
                  <dd className="text-primary">{typeof v === 'number' ? v.toFixed(2) : v || '—'}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </div>
    </div>
  )
}
