# StockSense Frontend 💻

> **Modern, High-Performance React 19 Single Page Application for Real-Time Stock Analytics & AI Forecasting.**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://stocksense-dashboard.vercel.app)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=for-the-badge&logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

---

## 📸 Preview

<p align="center">
  <img src="public/preview.png" alt="StockSense Frontend Preview" width="100%">
</p>

---

## 🌟 Architecture & Features

The client is built with **React 19** and bundled with **Vite 8**, featuring an institutional-grade dark/light financial dashboard aesthetic.

- **Global Context Architecture (`src/context/context.jsx`)**: Centralized state management for authentication, JWT storage, theme state, real-time toast alerts, and all API interactions.
- **Server-Sent Events (SSE) Live Feed**: Subscribes directly to backend market streaming events (`/stream/prices`) with automated polling fallback.
- **Interactive Financial Visualizations**: Powered by **Chart.js 4** and `react-chartjs-2`, offering multi-timeframe candlestick and line charts with technical indicators (MA, RSI, Bollinger Bands, MACD).
- **Command Palette (`src/components/CommandPalette.jsx`)**: Global `Ctrl + K` quick switcher for ticker fuzzy search and instant page navigation.
- **Responsive Layout**: Designed for all screen sizes from mobile devices to ultra-wide displays with off-canvas sidebar drawers and touch optimizations.
- **Design System Tokens (`src/index.css` & `src/theme.js`)**: Cohesive CSS variables mirroring dark slate `#0a0a0c` and emerald/ruby gain-loss indicators.

---

## 📁 Frontend Directory Layout

```text
client/
├── public/                 # Static assets, favicon, preview banner
├── src/
│   ├── components/         # Reusable UI building blocks
│   │   ├── CommandPalette.jsx  # Quick command & search modal (Ctrl+K)
│   │   ├── Header.jsx          # Top navigation bar with theme toggle & pulse
│   │   ├── KpiCard.jsx         # Metric card display with trend pills
│   │   ├── Layout.jsx          # App shell wrapper with sidebar & header
│   │   ├── NotificationBell.jsx# Dropdown alert notification drawer
│   │   ├── PriceChart.jsx      # Financial Chart.js component
│   │   ├── ProtectedRoute.jsx  # Client-side JWT route guard
│   │   └── Sidebar.jsx         # Collapsible desktop & mobile drawer
│   ├── context/
│   │   └── context.jsx         # App context provider & API client methods
│   ├── pages/
│   │   ├── AIPredictions.jsx   # Multi-horizon LSTM price forecast view
│   │   ├── AdminMetrics.jsx    # System metrics and user analytics
│   │   ├── Alerts.jsx          # Target price alert management
│   │   ├── Dashboard.jsx       # Live market overview & quick-add grid
│   │   ├── ForgotPassword.jsx  # Password recovery token request
│   │   ├── Login.jsx           # Sign-in page with 2FA support
│   │   ├── MarketAnalysis.jsx  # Gainers, losers & market movers
│   │   ├── Portfolio.jsx       # Holdings valuation & transaction tracker
│   │   ├── Profile.jsx         # User settings & security management
│   │   ├── Register.jsx        # Account registration with email OTP
│   │   ├── ResetPassword.jsx   # Password reset execution
│   │   ├── Settings.jsx        # App preferences & theme configuration
│   │   ├── StockDetail.jsx     # Deep-dive interactive ticker view
│   │   └── Watchlist.jsx       # Custom tracked stock lists
│   ├── App.jsx             # React Router 7 route definitions
│   ├── index.css           # Tailwind base styles and CSS design variables
│   ├── main.jsx            # Application entrypoint
│   └── theme.js            # Unified Chart.js color definitions
├── .env.example            # Environment configuration template
├── package.json            # Node.js dependencies and scripts
├── tailwind.config.js      # Tailwind design configuration
├── vercel.json             # Vercel SPA URL rewrite rules
└── vite.config.js          # Vite build and proxy settings
```

---

## 🚀 Getting Started

### 1. Installation

```bash
npm install
```

### 2. Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

| Variable | Description | Default |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Base URL of deployed FastAPI backend | Blank (uses Vite reverse proxy to `127.0.0.1:8000`) |

### 3. Local Development

```bash
npm run dev
```

The application will be accessible at **`http://localhost:5173`**.

### 4. Production Build & Preview

```bash
# Build optimized static distribution
npm run build

# Preview production build locally
npm run preview
```

---

## 🌐 Production Deployment (Vercel)

The repository includes `vercel.json` configured for Single Page Application client-side routing.
When deploying on Vercel:
- **Framework Preset**: Vite
- **Root Directory**: `client`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Environment Variables**:
  - `VITE_API_BASE_URL`: `https://your-backend-api.onrender.com`
