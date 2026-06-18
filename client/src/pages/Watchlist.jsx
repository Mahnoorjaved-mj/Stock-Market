import { useEffect, useState } from 'react'
import { Trash2, Plus } from 'lucide-react'
import { useApp } from '../context/context'

export default function Watchlist() {
  const { getWatchlist, addWatchlist, deleteWatchlist, getSymbols, toast } = useApp()
  const [items, setItems] = useState([])
  const [symbols, setSymbols] = useState([])
  const [form, setForm] = useState({ symbol: '', threshold_pct: '', target_price_high: '', target_price_low: '' })
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const res = await getWatchlist()
      setItems(res.items || [])
    } catch (err) {
      toast(err.message, 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    getSymbols().then((r) => setSymbols(r.symbols || [])).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const add = async (e) => {
    e.preventDefault()
    try {
      await addWatchlist({
        symbol: form.symbol,
        threshold_pct: form.threshold_pct || null,
        target_price_high: form.target_price_high || null,
        target_price_low: form.target_price_low || null,
      })
      toast(`${form.symbol.toUpperCase()} added`, 'success')
      setForm({ symbol: '', threshold_pct: '', target_price_high: '', target_price_low: '' })
      load()
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const remove = async (id) => {
    try {
      await deleteWatchlist(id)
      setItems((l) => l.filter((i) => i.id !== id))
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-xl font-semibold text-primary">Watchlist</h1>

      <form onSubmit={add} className="ss-card grid grid-cols-2 gap-3 p-4 md:grid-cols-5 md:items-end">
        <div className="col-span-2 md:col-span-1">
          <label className="ss-label">Symbol</label>
          <input
            list="symbols"
            className="ss-input uppercase"
            value={form.symbol}
            onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
            required
          />
          <datalist id="symbols">
            {symbols.slice(0, 500).map((s) => (
              <option key={s.symbol} value={s.symbol}>
                {s.name}
              </option>
            ))}
          </datalist>
        </div>
        <div>
          <label className="ss-label">Alert ±%</label>
          <input
            type="number"
            step="0.1"
            className="ss-input"
            value={form.threshold_pct}
            onChange={(e) => setForm({ ...form, threshold_pct: e.target.value })}
          />
        </div>
        <div>
          <label className="ss-label">Target high</label>
          <input
            type="number"
            step="0.01"
            className="ss-input"
            value={form.target_price_high}
            onChange={(e) => setForm({ ...form, target_price_high: e.target.value })}
          />
        </div>
        <div>
          <label className="ss-label">Target low</label>
          <input
            type="number"
            step="0.01"
            className="ss-input"
            value={form.target_price_low}
            onChange={(e) => setForm({ ...form, target_price_low: e.target.value })}
          />
        </div>
        <button className="ss-btn">
          <Plus size={16} /> Add
        </button>
      </form>

      <div className="ss-card overflow-x-auto">
        <table className="ss-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Price</th>
              <th>Change</th>
              <th>Alert ±%</th>
              <th>Targets</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id}>
                <td>
                  <div className="font-medium">{i.symbol}</div>
                  <div className="text-xs text-tertiary">{i.name}</div>
                </td>
                <td>{i.price != null ? i.price.toFixed(2) : '—'}</td>
                <td className={(i.change_percent ?? 0) >= 0 ? 'text-up' : 'text-down'}>
                  {i.change_percent != null ? `${i.change_percent.toFixed(2)}%` : '—'}
                </td>
                <td>{i.threshold_pct ?? '—'}</td>
                <td className="text-xs text-secondary">
                  {i.target_price_high ? `▲ ${i.target_price_high}` : ''}{' '}
                  {i.target_price_low ? `▼ ${i.target_price_low}` : ''}
                  {!i.target_price_high && !i.target_price_low ? '—' : ''}
                </td>
                <td>
                  <button
                    onClick={() => remove(i.id)}
                    className="text-tertiary hover:text-down"
                    title="Remove"
                  >
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={6} className="py-8 text-center text-tertiary">
                  Your watchlist is empty.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
