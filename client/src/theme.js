// =====================================================================
// Global theme — single source of truth for color values used in JS
// (Chart.js canvas, inline styles, etc.). These mirror the CSS-variable
// design tokens in src/index.css that drive Tailwind + light/dark mode.
//
// Use these (real hex/rgba) anywhere a CSS `var(--token)` won't resolve —
// e.g. canvas charts. For normal DOM styling prefer Tailwind classes.
// =====================================================================

export const theme = {
  // Brand / accent
  accent: '#4f8cff',
  accentHover: '#3a7aef',
  accentSoft: 'rgba(79, 140, 255, 0.10)',

  // Market direction
  up: '#10b981',
  upSoft: 'rgba(16, 185, 129, 0.10)',
  down: '#ef4444',
  downSoft: 'rgba(239, 68, 68, 0.10)',
  warn: '#f59e0b',

  // Chart axis + grid (tuned to read well in both light and dark themes)
  chartAxis: '#71717a',
  chartGrid: 'rgba(148, 163, 184, 0.18)',
  chartLegend: '#a1a1aa',
}

// Sentiment label -> color, matches the backend's sentiment palette.
export const sentimentColors = {
  STRONG_BUY: '#16a34a',
  BUY: '#22c55e',
  HOLD: '#f59e0b',
  SELL: '#ef4444',
  STRONG_SELL: '#991b1b',
}

export default theme
