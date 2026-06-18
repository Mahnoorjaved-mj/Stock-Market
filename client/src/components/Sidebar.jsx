import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Eye,
  Briefcase,
  Bell,
  Brain,
  BarChart3,
  Settings,
  User,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react'
import { useApp } from '../context/context'

const PUBLIC_LINKS = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/market', label: 'Market Analysis', icon: BarChart3 },
  { to: '/ai', label: 'AI Predictions', icon: Brain },
]
const AUTH_LINKS = [
  { to: '/watchlist', label: 'Watchlist', icon: Eye },
  { to: '/portfolio', label: 'Portfolio', icon: Briefcase },
  { to: '/alerts', label: 'Alerts', icon: Bell },
]
const ACCOUNT_LINKS = [
  { to: '/profile', label: 'Profile', icon: User },
  { to: '/settings', label: 'Settings', icon: Settings },
]

function LinkItem({ to, label, icon: Icon, end, onNavigate }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onNavigate}
      className={({ isActive }) =>
        `flex items-center gap-3 rounded px-3 py-2 text-sm font-medium transition-colors ${
          isActive
            ? 'bg-accent-soft text-accent'
            : 'text-secondary hover:bg-surface-hover hover:text-primary'
        }`
      }
    >
      <Icon size={18} />
      {label}
    </NavLink>
  )
}

export default function Sidebar({ onNavigate }) {
  const { user } = useApp()

  return (
    <aside className="flex h-full w-60 flex-col border-r border-line bg-surface">
      <div className="flex items-center gap-2 px-5 py-5">
        <TrendingUp className="text-accent" size={22} />
        <span className="text-lg font-semibold text-primary">StockSense</span>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 pb-4">
        {PUBLIC_LINKS.map((l) => (
          <LinkItem key={l.to} {...l} onNavigate={onNavigate} />
        ))}

        {user && (
          <>
            <div className="px-3 pt-4 pb-1 text-[11px] font-semibold uppercase tracking-wider text-tertiary">
              Personal
            </div>
            {AUTH_LINKS.map((l) => (
              <LinkItem key={l.to} {...l} onNavigate={onNavigate} />
            ))}
            <div className="px-3 pt-4 pb-1 text-[11px] font-semibold uppercase tracking-wider text-tertiary">
              Account
            </div>
            {ACCOUNT_LINKS.map((l) => (
              <LinkItem key={l.to} {...l} onNavigate={onNavigate} />
            ))}
            {user.is_admin && (
              <LinkItem to="/admin" label="Admin" icon={ShieldCheck} onNavigate={onNavigate} />
            )}
          </>
        )}
      </nav>
    </aside>
  )
}
