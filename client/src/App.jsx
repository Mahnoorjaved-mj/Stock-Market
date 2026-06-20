import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'

import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import ResetPassword from './pages/ResetPassword'
import Watchlist from './pages/Watchlist'
import Portfolio from './pages/Portfolio'
import Alerts from './pages/Alerts'
import Profile from './pages/Profile'
import Settings from './pages/Settings'
import StockDetail from './pages/StockDetail'
import AIPredictions from './pages/AIPredictions'
import MarketAnalysis from './pages/MarketAnalysis'
import AdminMetrics from './pages/AdminMetrics'
import NotFound from './pages/NotFound'

export default function App() {
  return (
    <Routes>
      {/* Auth pages sit outside the app shell. */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />

      {/* Everything else lives inside the sidebar/header layout. */}
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/market" element={<MarketAnalysis />} />
        <Route path="/ai" element={<AIPredictions />} />
        <Route path="/stock/:symbol" element={<StockDetail />} />

        <Route
          path="/watchlist"
          element={
            <ProtectedRoute>
              <Watchlist />
            </ProtectedRoute>
          }
        />
        <Route
          path="/portfolio"
          element={
            <ProtectedRoute>
              <Portfolio />
            </ProtectedRoute>
          }
        />
        <Route
          path="/alerts"
          element={
            <ProtectedRoute>
              <Alerts />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Settings />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute admin>
              <AdminMetrics />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  )
}
