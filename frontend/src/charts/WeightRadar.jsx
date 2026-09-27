import React from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar } from 'react-chartjs-2'
import { PieChart } from 'lucide-react'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

export default function WeightRadar({ weightsData }) {
  if (!weightsData || !weightsData.regional_weights) return null

  const regions = weightsData.regional_weights
  const labels = regions.map((r) => r.region_name)

  const models = [
    { id: 'gfs', name: 'NOAA GFS', color: '#f59e0b' },
    { id: 'ecmwf', name: 'ECMWF IFS', color: '#10b981' },
    { id: 'graphcast', name: 'GraphCast (AI)', color: '#8b5cf6' },
    { id: 'pangu', name: 'Pangu (AI)', color: '#ec4899' },
  ]

  const datasets = models.map((m) => ({
    label: m.name,
    data: regions.map((r) => {
      const w = r.weights.find((item) => item.model_id === m.id)
      return w ? Math.round(w.weight * 100) : 25
    }),
    backgroundColor: m.color,
    borderRadius: 2,
  }))

  const data = { labels, datasets }

  const options = {
    indexAxis: 'y', // Horizontal stacked bar
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: '#cbd5e1', font: { size: 10 } },
      },
      tooltip: {
        callbacks: {
          label: (context) => `${context.dataset.label}: ${context.raw}%`,
        },
      },
    },
    scales: {
      x: {
        stacked: true,
        max: 100,
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#94a3b8', callback: (val) => `${val}%` },
      },
      y: {
        stacked: true,
        grid: { display: false },
        ticks: { color: '#94a3b8', font: { size: 10 } },
      },
    },
  }

  return (
    <div className="glass-card">
      <div className="card-header">
        <div className="card-title">
          <PieChart size={18} color="#f59e0b" />
          <span>Adaptive Weight Breakdown by Geographic Zone</span>
        </div>
        <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
          Simplex ∑ w = 100%
        </span>
      </div>
      <div className="card-body" style={{ height: '240px' }}>
        <Bar data={data} options={options} />
      </div>
    </div>
  )
}
