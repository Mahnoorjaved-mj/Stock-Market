import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search } from 'lucide-react'
import { useApp } from '../context/context'

const ROUTES = [
  { label: 'Dashboard', to: '/' },
  { label: 'Market Analysis', to: '/market' },
  { label: 'AI Predictions', to: '/ai' },
  { label: 'Watchlist', to: '/watchlist' },
  { label: 'Portfolio', to: '/portfolio' },
  { label: 'Alerts', to: '/alerts' },
  { label: 'Profile', to: '/profile' },
  { label: 'Settings', to: '/settings' },
]

// Cmd/Ctrl+K command palette — ports legacy static/cmdk.js. Searches routes
// and the stock symbol catalog.
export default function CommandPalette({ open, onClose }) {
  const { getSymbols, toggleTheme } = useApp()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [symbols, setSymbols] = useState([])
  const [active, setActive] = useState(0)
  const inputRef = useRef(null)

  useEffect(() => {
    if (open) {
      setQuery('')
      setActive(0)
      setTimeout(() => inputRef.current?.focus(), 30)
      if (symbols.length === 0) {
        getSymbols()
          .then((r) => setSymbols(r.symbols || []))
          .catch(() => {})
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const candidates = useMemo(() => {
    const q = query.trim().toLowerCase()
    const base = [
      ...ROUTES.map((r) => ({ ...r, kind: 'page' })),
      { label: 'Toggle theme', kind: 'action', run: toggleTheme },
    ]
    const symbolCands = symbols.map((s) => ({
      label: `${s.symbol} — ${s.name}`,
      to: `/stock/${s.symbol}`,
      kind: 'stock',
    }))
    const all = [...base, ...symbolCands]
    if (!q) return base.slice(0, 8)
    return all
      .map((c) => {
        const l = c.label.toLowerCase()
        let score = 0
        if (l === q) score = 150
        else if (l.startsWith(q)) score = 100
        else if (l.includes(q)) score = 60
        return { c, score }
      })
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 12)
      .map((x) => x.c)
  }, [query, symbols, toggleTheme])

  const choose = (c) => {
    onClose()
    if (c.run) c.run()
    else if (c.to) navigate(c.to)
  }

  const onKeyDown = (e) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setActive((a) => Math.min(a + 1, candidates.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setActive((a) => Math.max(a - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (candidates[active]) choose(candidates[active])
    } else if (e.key === 'Escape') {
      onClose()
    }
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[90] flex items-start justify-center bg-black/50 pt-[15vh] px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg ss-card overflow-hidden shadow-2xl"
        style={{ background: 'var(--bg-elevated)' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-2 border-b border-line px-4">
          <Search size={16} className="text-tertiary" />
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => {
              setQuery(e.target.value)
              setActive(0)
            }}
            onKeyDown={onKeyDown}
            placeholder="Search pages, stocks, actions…"
            className="w-full bg-transparent py-3 text-sm text-primary outline-none placeholder:text-tertiary"
          />
        </div>
        <div className="max-h-80 overflow-y-auto py-1">
          {candidates.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-tertiary">No results</div>
          ) : (
            candidates.map((c, i) => (
              <button
                key={c.label}
                onMouseEnter={() => setActive(i)}
                onClick={() => choose(c)}
                className={`flex w-full items-center justify-between px-4 py-2 text-left text-sm ${
                  i === active ? 'bg-accent-soft text-accent' : 'text-secondary'
                }`}
              >
                <span>{c.label}</span>
                <span className="text-[10px] uppercase text-tertiary">{c.kind}</span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  )
}
