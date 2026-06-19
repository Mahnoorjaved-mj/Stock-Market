import { useEffect, useState } from 'react'
import { Trash2, Plus, Download } from 'lucide-react'
import { useApp } from '../context/context'
import KpiCard from '../components/KpiCard'

const money = (n) => (n == null ? '—' : n.toLocaleString(undefined, { maximumFractionDigits: 2 }))

export default function Portfolio() {
  const { getPortfolio, addHolding, deleteHolding, portfolioCsvUrl, toast } = useApp()
  const [items, setItems] = useState([])
  const [totals, setTotals] = useState({})
  const [form, setForm] = useState({ symbol: '', quantity: '', buy_price: '', buy_date: '', notes: '' })
  const [loading, setLoading] = useState(true)

  const load = async () => {
    try {
      const res = await getPortfolio()
      setItems(res.items || [])
      setTotals(res.totals || {})
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

  const add = async (e) => {
    e.preventDefault()
    try {
      await addHolding(form)
      toast('Holding added', 'success')
      setForm({ symbol: '', quantity: '', buy_price: '', buy_date: '', notes: '' })
      load()
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  const remove = async (id) => {
    try {
      await deleteHolding(id)
      load()
    } catch (err) {
      toast(err.message, 'error')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-primary">Portfolio</h1>
        <a href={portfolioCsvUrl} className="ss-btn-ghost">
          <Download size={15} /> Export CSV
        </a>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Cost basis" value={money(totals.cost_basis)} />
        <KpiCard label="Current value" value={money(totals.current_value)} />
        <KpiCard
          label="P&L"
          value={money(totals.pnl)}
          tone={(totals.pnl ?? 0) >= 0 ? 'up' : 'down'}
        />
        <KpiCard
          label="Return"
          value={totals.pnl_pct != null ? `${totals.pnl_pct.toFixed(2)}%` : '—'}
          tone={(totals.pnl_pct ?? 0) >= 0 ? 'up' : 'down'}
        />
      </div>

      <form onSubmit={add} className="ss-card grid grid-cols-2 gap-3 p-4 md:grid-cols-6 md:items-end">
        <div>
          <label className="ss-label">Symbol</label>
          <input
            className="ss-input uppercase"
            value={form.symbol}
            onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
            required
          />
        </div>
        <div>
          <label className="ss-label">Quantity</label>
          <input
            type="number"
            step="any"
            className="ss-input"
            value={form.quantity}
            onChange={(e) => setForm({ ...form, quantity: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="ss-label">Buy price</label>
          <input
            type="number"
            step="any"
            className="ss-input"
            value={form.buy_price}
            onChange={(e) => setForm({ ...form, buy_price: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="ss-label">Buy date</label>
          <input
            type="date"
            className="ss-input"
            value={form.buy_date}
            onChange={(e) => setForm({ ...form, buy_date: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="ss-label">Notes</label>
          <input
            className="ss-input"
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
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
              <th>Qty</th>
              <th>Buy</th>
              <th>Current</th>
              <th>Value</th>
              <th>P&L</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id}>
                <td>
                  <div className="font-medium">{i.symbol}</div>
                  <div className="text-xs text-tertiary">{i.buy_date}</div>
                </td>
                <td>{i.quantity}</td>
                <td>{money(i.buy_price)}</td>
                <td>{money(i.current_price)}</td>
                <td>{money(i.current_value)}</td>
                <td className={(i.pnl ?? 0) >= 0 ? 'text-up' : 'text-down'}>
                  {money(i.pnl)} ({(i.pnl_pct ?? 0).toFixed(1)}%)
                </td>
                <td>
                  <button onClick={() => remove(i.id)} className="text-tertiary hover:text-down">
                    <Trash2 size={16} />
                  </button>
                </td>
              </tr>
            ))}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={7} className="py-8 text-center text-tertiary">
                  No holdings yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
