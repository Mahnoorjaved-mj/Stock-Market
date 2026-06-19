import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { useApp } from '../context/context'

export default function MarketAnalysis() {
  const { getMarketAnalysis, toast } = useApp()
  const navigate = useNavigate()
  const [rows, setRows] = useState([])
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState({ key: 'symbol', dir: 1 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMarketAnalysis()
      .then((res) => setRows(res.data || []))
      .catch((err) => toast(err.message, 'error'))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const view = useMemo(() => {
    const q = query.trim().toLowerCase()
    let r = q ? rows.filter((x) => x.symbol.toLowerCase().includes(q)) : rows
    r = [...r].sort((a, b) => {
      const av = a[sort.key]
      const bv = b[sort.key]
      return (av > bv ? 1 : av < bv ? -1 : 0) * sort.dir
    })
    return r
  }, [rows, query, sort])

  const toggleSort = (key) =>
    setSort((s) => ({ key, dir: s.key === key ? -s.dir : 1 }))

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-primary">Market Analysis</h1>

      <div className="ss-card">
        <div className="flex items-center gap-2 border-b border-line px-4 py-3">
          <Search size={16} className="text-tertiary" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter symbols…"
            className="w-full bg-transparent text-sm text-primary outline-none placeholder:text-tertiary"
          />
        </div>
        <div className="overflow-x-auto">
          <table className="ss-table">
            <thead>
              <tr>
                {[
                  ['symbol', 'Symbol'],
                  ['current', 'Current'],
                  ['high', 'High'],
                  ['low', 'Low'],
                ].map(([k, label]) => (
                  <th
                    key={k}
                    className="cursor-pointer select-none"
                    onClick={() => toggleSort(k)}
                  >
                    {label} {sort.key === k ? (sort.dir === 1 ? '↑' : '↓') : ''}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {view.map((r) => (
                <tr
                  key={r.symbol}
                  className="cursor-pointer hover:bg-surface-hover"
                  onClick={() => navigate(`/stock/${r.symbol}`)}
                >
                  <td className="font-medium text-accent">{r.symbol}</td>
                  <td>{r.current}</td>
                  <td>{r.high}</td>
                  <td>{r.low}</td>
                </tr>
              ))}
              {loading && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-tertiary">
                    Loading market data…
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
