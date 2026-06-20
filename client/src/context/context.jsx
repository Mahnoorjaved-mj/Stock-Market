import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
} from 'react'
import { CheckCircle, AlertCircle, AlertTriangle, Info, X } from 'lucide-react'

// =====================================================================
// Single app context — holds auth + theme + toast state AND every API
// call the app makes. Components consume it via `useApp()`.
// =====================================================================

const AppContext = createContext(null)
export const useApp = () => useContext(AppContext)

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const TOKEN_KEY = 'ss_token'

// ---- low-level request helper (base URL + Bearer + JSON + 401) ----
async function request(method, path, body, { raw = false } = {}) {
  const headers = {}
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) headers['Authorization'] = `Bearer ${token}`

  const opts = { method, headers }
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    opts.body = JSON.stringify(body)
  }

  const res = await fetch(`${API_BASE}${path}`, opts)

  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY)
    window.dispatchEvent(new CustomEvent('auth:unauthorized'))
  }
  if (raw) return res

  let data = null
  const ct = res.headers.get('content-type') || ''
  data = ct.includes('application/json') ? await res.json() : await res.text()

  if (!res.ok) {
    const msg = (data && (data.detail || data.message || data.error)) || `Request failed (${res.status})`
    throw new Error(typeof msg === 'string' ? msg : 'Request failed')
  }
  return data
}

const ICONS = { success: CheckCircle, error: AlertCircle, warn: AlertTriangle, info: Info }
const TOAST_COLORS = {
  success: 'var(--color-up)',
  error: 'var(--color-down)',
  warn: 'var(--color-warn)',
  info: 'var(--accent)',
}
let toastSeq = 0

export function AppProvider({ children }) {
  // ---- Theme ----
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'dark')
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])
  const toggleTheme = useCallback(() => setTheme((t) => (t === 'dark' ? 'light' : 'dark')), [])

  // ---- Toasts ----
  const [toasts, setToasts] = useState([])
  const dismissToast = useCallback((id) => setToasts((l) => l.filter((t) => t.id !== id)), [])
  const toast = useCallback(
    (message, type = 'info') => {
      const id = ++toastSeq
      setToasts((l) => [...l, { id, message, type }])
      setTimeout(() => dismissToast(id), 3500)
    },
    [dismissToast]
  )

  // ---- Auth ----
  const [user, setUser] = useState(null)
  const [loadingAuth, setLoadingAuth] = useState(true)

  const setToken = (t) => {
    if (t) localStorage.setItem(TOKEN_KEY, t)
    else localStorage.removeItem(TOKEN_KEY)
  }

  useEffect(() => {
    let active = true
    async function hydrate() {
      if (!localStorage.getItem(TOKEN_KEY)) {
        setLoadingAuth(false)
        return
      }
      try {
        const res = await request('GET', '/auth/me')
        if (active) setUser(res.user)
      } catch {
        setToken(null)
        if (active) setUser(null)
      } finally {
        if (active) setLoadingAuth(false)
      }
    }
    hydrate()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    const onUnauth = () => setUser(null)
    window.addEventListener('auth:unauthorized', onUnauth)
    return () => window.removeEventListener('auth:unauthorized', onUnauth)
  }, [])

  // =====================================================================
  // API CALLS — every endpoint the app uses lives here.
  // =====================================================================
  const api = useMemo(() => {
    const applyToken = (res) => {
      setToken(res.token)
      setUser(res.user)
      return res.user
    }
    return {
      // ---- Auth ----
      login: async (email, password) => applyToken(await request('POST', '/auth/login', { email, password })),
      register: (email, password, name) => request('POST', '/auth/register', { email, password, name }),
      verifyOtp: async (email, otp) => applyToken(await request('POST', '/auth/verify-otp', { email, otp })),
      forgotPassword: (email) => request('POST', '/auth/forgot-password', { email }),
      resetPassword: (token, password) => request('POST', '/auth/reset-password', { token, password }),
      logout: async () => {
        try {
          await request('POST', '/auth/logout', {})
        } catch {
          /* ignore */
        }
        setToken(null)
        setUser(null)
      },
      refreshMe: async () => {
        const res = await request('GET', '/auth/me')
        setUser(res.user)
        return res.user
      },
      // ---- 2FA ----
      twoFaSetup: () => request('POST', '/auth/2fa/setup', {}),
      twoFaVerify: (code) => request('POST', '/auth/2fa/verify', { code }),
      twoFaDisable: () => request('POST', '/auth/2fa/disable', {}),

      // ---- Watchlist ----
      getWatchlist: () => request('GET', '/api/watchlist'),
      addWatchlist: (data) => request('POST', '/api/watchlist', data),
      updateWatchlist: (id, data) => request('PUT', `/api/watchlist/${id}`, data),
      deleteWatchlist: (id) => request('DELETE', `/api/watchlist/${id}`),
      getSymbols: () => request('GET', '/api/symbols'),

      // ---- Portfolio ----
      getPortfolio: () => request('GET', '/api/portfolio'),
      addHolding: (data) => request('POST', '/api/portfolio', data),
      updateHolding: (id, data) => request('PUT', `/api/portfolio/${id}`, data),
      deleteHolding: (id) => request('DELETE', `/api/portfolio/${id}`),
      portfolioCsvUrl: `${API_BASE}/api/portfolio/export.csv`,

      // ---- Profile ----
      getProfile: () => request('GET', '/api/profile'),
      updateProfile: (data) => request('PUT', '/api/profile', data),
      changePassword: (old_password, new_password) =>
        request('POST', '/api/change-password', { old_password, new_password }),
      deleteAccount: () => request('DELETE', '/api/profile'),

      // ---- Alerts ----
      getAlertHistory: (limit = 50) => request('GET', `/api/alerts/history?limit=${limit}`),
      runAlertsNow: () => request('POST', '/api/alerts/run-now', {}),

      // ---- Notifications ----
      getNotifications: () => request('GET', '/api/notifications'),
      readAllNotifications: () => request('POST', '/api/notifications/read-all', {}),

      // ---- Market (public) ----
      getLiveData: () => request('GET', '/get_live_data'),
      getMarketAnalysis: () => request('GET', '/api/market-analysis'),
      getStock: (symbol) => request('GET', `/api/stock/${symbol}`),
      getStockHistory: (symbol, range = '1mo') =>
        request('GET', `/api/stock/${symbol}/history?range=${range}`),
      searchSymbols: (q) => request('GET', `/api/search?q=${encodeURIComponent(q)}`),
      streamUrl: `${API_BASE}/stream/prices`,

      // ---- AI ----
      predict: (symbol, days = 7) => request('GET', `/api/predict/${symbol}?days=${days}`),
      sentiment: (symbol) => request('GET', `/api/sentiment/${symbol}`),
      topPicks: () => request('GET', '/api/top_picks'),
      trainModel: (symbol) => request('POST', `/api/train_model/${symbol}`, {}),
      backtest: (symbol) => request('GET', `/api/ai/backtest/${symbol}`),
      personalizedPicks: () => request('GET', '/api/ai/personalized-picks'),

      // ---- Admin ----
      getAdminMetrics: () => request('GET', '/api/admin/metrics'),
    }
  }, [])

  const value = {
    // auth
    user,
    loadingAuth,
    isAuthed: !!user,
    // theme
    theme,
    toggleTheme,
    // toast
    toast,
    // api
    ...api,
  }

  return (
    <AppContext.Provider value={value}>
      {children}
      {/* Toast viewport */}
      <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2">
        {toasts.map((t) => {
          const Icon = ICONS[t.type] || Info
          return (
            <div
              key={t.id}
              className="ss-card flex items-center gap-3 px-4 py-3 shadow-lg min-w-[260px] max-w-sm"
              style={{ animation: 'ss-toast-in 0.2s ease' }}
            >
              <Icon size={18} style={{ color: TOAST_COLORS[t.type] }} />
              <span className="text-sm text-primary flex-1">{t.message}</span>
              <button onClick={() => dismissToast(t.id)} className="text-tertiary hover:text-primary">
                <X size={16} />
              </button>
            </div>
          )
        })}
      </div>
    </AppContext.Provider>
  )
}
