import React from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import { PieChart, Clock, Info } from 'lucide-react'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

export default function WeightLeadTimeChart({ variable = 'rainfall', weightsData }) {
  const leadTimes = [6, 12, 24, 48, 72, 96, 120, 168]
  const labels = leadTimes.map((lt) => `T+${lt}h`)

  // Dynamic adaptive weight transition over lead time
  // Short range: NWP Model A and B have higher weight due to convective initiation physics
  // Medium range: AI/ML and Ensemble gain higher weight due to superior scale-invariance & slower error growth
  const data = {
    labels,
    datasets: [
      {
        label: 'NWP Model A (GFS)',
        data: [35, 33, 30, 24, 20, 16, 14, 12],
        borderColor: '#0284c7',
        backgroundColor: 'rgba(2, 132, 199, 0.4)',
        fill: true,
        tension: 0.3,
      },
      {
        label: 'NWP Model B (ECMWF)',
        data: [32, 31, 29, 26, 22, 18, 16, 13],
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.4)',
        fill: true,
        tension: 0.3,
      },
      {
        label: 'Ensemble Forecast',
        data: [18, 20, 22, 26, 29, 32, 34, 37],
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.4)',
        fill: true,
        tension: 0.3,
      },
      {
        label: 'AI/ML Forecast (GraphCast)',
        data: [15, 16, 19, 24, 29, 34, 36, 38],
        borderColor: '#8b5cf6',
        backgroundColor: 'rgba(139, 92, 246, 0.4)',
        fill: true,
        tension: 0.3,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: '#cbd5e1', font: { size: 11 }, boxWidth: 12 },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        titleColor: '#38bdf8',
        bodyColor: '#f1f5f9',
        callbacks: {
          label: (context) => `${context.dataset.label}: ${context.raw}% weight`,
        },
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#94a3b8' },
        title: { display: true, text: 'Forecast Lead Time Horizon', color: '#94a3b8' },
      },
      y: {
        stacked: true,
        max: 100,
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: {
          color: '#94a3b8',
          callback: (val) => `${val}%`,
        },
        title: { display: true, text: 'Normalized Model Weight (%)', color: '#94a3b8' },
      },
    },
  }

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="card-header" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
        <div className="card-title">
          <Clock size={18} color="#f59e0b" />
          <span>Model Weights Evolution Over Lead Time Horizon</span>
        </div>
        <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
          Simplex Constraint ∑ w(t) = 100%
        </span>
      </div>

      <div className="card-body">
        <div style={{ height: '250px' }}>
          <Line data={data} options={options} />
        </div>

        {/* Scientific Interpretation Callout */}
        <div
          style={{
            marginTop: '0.75rem',
            padding: '8px 12px',
            background: 'rgba(30, 41, 59, 0.5)',
            borderRadius: '6px',
            border: '1px solid var(--border-color)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.72rem',
            color: '#cbd5e1',
          }}
        >
          <Info size={14} color="#38bdf8" style={{ flexShrink: 0 }} />
          <span>
            <strong>Adaptive Dynamics:</strong> Physical NWP models dominate the <strong>short-range (6h-24h)</strong> with 60-67% total weight due to explicit convective and boundary-layer physics. In the <strong>extended medium-range (72h-168h)</strong>, AI/ML emulators and Ensembles dynamically gain up to 75% weight as single-model NWP spread increases.
          </span>
        </div>
      </div>
    </div>
  )
}
