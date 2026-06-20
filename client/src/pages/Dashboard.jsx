import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, Search } from 'lucide-react'
import { useApp } from '../context/context'
import KpiCard from '../components/KpiCard'

const PAGE_SIZE = 24

export default function Dashboard() {
  const { getLiveData, streamUrl, addWatchlist, user, toast } = useApp()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const [live, setLive] = useState(false)
  const esRef = useRef(null)

  useEffect(() => {
    let pollId
    // Prefer SSE; fall back to polling if it errors.
    getLiveData().then(setData).catch(() => {})

    try {
      const es = new EventSource(streamUrl)
      esRef.current = es
      es.addEventListener('snapshot', (e) => {
        setData(JSON.parse(e.data))
        setLive(true)
      })
      es.onerror = () => {
        setLive(false)
        es.close()
        esRef.current = null
        pollId = setInterval(() => getLiveData().then(setData).catch(() => {}), 60000)
      }
    } catch {
      pollId = setInterval(() => getLiveData().then(setData).catch(() => {}), 60000)
    }

    return () => {
      esRef.current?.close()
      if (pollId) clearInterval(pollId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const stocks = data?.stocks_data || []
  const ind = data?.market_indicators || {}

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return stocks
    return stocks.filter(
      (s) =>
        s.symbol.toLowerCase().includes(q) || (s.name || '').toLowerCase().includes(q)
    )
  }, [stocks, query])

  const pageCount = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))
  const pageItems = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  const quickAdd = async (symbol) => {
    if (!user) {
      navigate('/login')
      return
    }
    try {
      await addWatchlist({ symbol })
      toast(`${symbol} added to watchlist`, 'success')
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-primary">Global Markets</h1>
          <p className="text-sm text-secondary">
            {live ? (
              <span className="text-up">● Live</span>
            ) : (
              <span className="text-tertiary">○ Polling</span>
            )}{' '}
            · {stocks.length} stocks tracked
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Sentiment" value={`${ind.sentiment ?? '—'}%`} sub="bullish" tone="up" />
        <KpiCard label="Volatility" value={ind.volatility ?? '—'} />
        <KpiCard label="Stocks" value={ind.total_stocks ?? stocks.length} />
        <KpiCard label="Countries" value={ind.countries_covered ?? '—'} />
      </div>

      <div className="ss-card">
        <div className="flex items-center gap-2 border-b border-line px-4 py-3">
          <Search size={16} className="text-tertiary" />
          <input
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setPage(1)
            }}
            placeholder="Filter symbols…"
            className="w-full bg-transparent text-sm text-primary outline-none placeholder:text-tertiary"
          />
        </div>

        <div className="grid grid-cols-1 gap-px bg-line sm:grid-cols-2 lg:grid-cols-3">
          {pageItems.map((s) => {
            const upd = (s.change_percent ?? 0) >= 0
            return (
              <div
                key={s.symbol}
                className="flex items-center justify-between bg-surface px-4 py-3 hover:bg-surface-hover"
              >
                <button
                  className="min-w-0 flex-1 text-left"
                  onClick={() => navigate(`/stock/${s.symbol}`)}
                >
                  <div className="truncate text-sm font-medium text-primary">{s.symbol}</div>
                  <div className="truncate text-xs text-tertiary">{s.name}</div>
                </button>
                <div className="px-3 text-right">
                  <div className="text-sm font-medium text-primary">
                    {s.price ? s.price.toFixed(2) : '—'}
                  </div>
                  <div className={`text-xs ${upd ? 'text-up' : 'text-down'}`}>
                    {upd ? '+' : ''}
                    {(s.change_percent ?? 0).toFixed(2)}%
                  </div>
                </div>
                <button
                  onClick={() => quickAdd(s.symbol)}
                  className="rounded p-1.5 text-tertiary hover:bg-accent-soft hover:text-accent"
                  title="Add to watchlist"
                >
                  <Plus size={16} />
                </button>
              </div>
            )
          })}
        </div>

        {!data && (
          <div className="px-4 py-10 text-center text-sm text-tertiary">Loading live data…</div>
        )}

        {pageCount > 1 && (
          <div className="flex items-center justify-between border-t border-line px-4 py-3 text-sm">
            <button
              className="ss-btn-ghost"
              disabled={page === 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Prev
            </button>
            <span className="text-tertiary">
              Page {page} / {pageCount}
            </span>
            <button
              className="ss-btn-ghost"
              disabled={page === pageCount}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
