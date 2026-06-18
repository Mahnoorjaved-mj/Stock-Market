import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler)

// Reusable line chart for price history / AI forecasts.
export default function PriceChart({ labels, datasets, height = 280 }) {
  const data = {
    labels,
    datasets: datasets.map((d) => ({
      tension: 0.3,
      pointRadius: 0,
      borderWidth: 2,
      fill: true,
      ...d,
    })),
  }
  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: datasets.length > 1, labels: { color: '#a1a1aa' } } },
    scales: {
      x: { ticks: { color: '#71717a', maxTicksLimit: 8 }, grid: { display: false } },
      y: { ticks: { color: '#71717a' }, grid: { color: 'rgba(255,255,255,0.05)' } },
    },
  }
  return (
    <div style={{ height }}>
      <Line data={data} options={options} />
    </div>
  )
}
