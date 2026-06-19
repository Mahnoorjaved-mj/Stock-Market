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
import { theme } from '../theme'

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
    plugins: { legend: { display: datasets.length > 1, labels: { color: theme.chartLegend } } },
    scales: {
      x: { ticks: { color: theme.chartAxis, maxTicksLimit: 8 }, grid: { display: false } },
      y: { ticks: { color: theme.chartAxis }, grid: { color: theme.chartGrid } },
    },
  }
  return (
    <div style={{ height }}>
      <Line data={data} options={options} />
    </div>
  )
}
