import { useNavigate } from 'react-router-dom'
import { Menu, Search, Sun, Moon, LogIn, LogOut } from 'lucide-react'
import { useApp } from '../context/context'
import NotificationBell from './NotificationBell'

export default function Header({ onMenuClick, onOpenPalette }) {
  const { user, theme, toggleTheme, logout, toast } = useApp()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    toast('Logged out', 'success')
    navigate('/login')
  }

  return (
    <header className="flex h-14 items-center gap-3 border-b border-line bg-app px-4">
      <button className="md:hidden text-secondary hover:text-primary" onClick={onMenuClick}>
        <Menu size={20} />
      </button>

      <button
        onClick={onOpenPalette}
        className="flex flex-1 max-w-sm items-center gap-2 rounded border border-line bg-input px-3 py-1.5 text-sm text-tertiary hover:border-line-strong"
      >
        <Search size={15} />
        <span>Search…</span>
        <kbd className="ml-auto rounded bg-surface-hover px-1.5 py-0.5 text-[10px] text-secondary">
          Ctrl K
        </kbd>
      </button>

      <div className="ml-auto flex items-center gap-1">
        <button
          onClick={toggleTheme}
          className="rounded p-2 text-secondary hover:bg-surface-hover hover:text-primary"
          title="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        {user && <NotificationBell />}

        {user ? (
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 rounded px-3 py-2 text-sm text-secondary hover:bg-surface-hover hover:text-primary"
          >
            <LogOut size={16} />
            <span className="hidden sm:inline">Logout</span>
          </button>
        ) : (
          <button
            onClick={() => navigate('/login')}
            className="flex items-center gap-2 rounded px-3 py-2 text-sm text-accent hover:bg-accent-soft"
          >
            <LogIn size={16} />
            <span className="hidden sm:inline">Login</span>
          </button>
        )}
      </div>
    </header>
  )
}
