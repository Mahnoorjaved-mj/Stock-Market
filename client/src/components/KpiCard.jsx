// Small KPI tile used across dashboard / portfolio / admin.
export default function KpiCard({ label, value, sub, tone }) {
  const toneClass =
    tone === 'up' ? 'text-up' : tone === 'down' ? 'text-down' : 'text-primary'
  return (
    <div className="ss-card p-4">
      <div className="text-xs font-medium uppercase tracking-wide text-tertiary">{label}</div>
      <div className={`mt-1 text-2xl font-semibold ${toneClass}`}>{value}</div>
      {sub && <div className="mt-0.5 text-xs text-secondary">{sub}</div>}
    </div>
  )
}
