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
        borderColor: '#2563EB',
        backgroundColor: 'rgba(37, 99, 235, 0.35)',
        fill: true,
        tension: 0.35,
      },
      {
        label: 'NWP Model B (ECMWF)',
        data: [32, 31, 29, 26, 22, 18, 16, 13],
        borderColor: '#1E3A8A',
        backgroundColor: 'rgba(30, 58, 138, 0.35)',
        fill: true,
        tension: 0.35,
      },
      {
        label: 'Ensemble Forecast',
        data: [18, 20, 22, 26, 29, 32, 34, 37],
        borderColor: '#0284C7',
        backgroundColor: 'rgba(2, 132, 199, 0.35)',
        fill: true,
        tension: 0.35,
      },
      {
        label: 'AI/ML Forecast (GraphCast)',
        data: [15, 16, 19, 24, 29, 34, 36, 38],
        borderColor: '#38BDF8',
        backgroundColor: 'rgba(56, 189, 248, 0.35)',
        fill: true,
        tension: 0.35,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: '#243746', font: { size: 11, weight: '600' }, boxWidth: 12 },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: '#FFFFFF',
        titleColor: '#294E6B',
        bodyColor: '#243746',
        borderColor: 'rgba(77, 145, 201, 0.3)',
        borderWidth: 1,
        callbacks: {
          label: (context) => `${context.dataset.label}: ${context.raw}% weight`,
        },
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(77, 145, 201, 0.12)' },
        ticks: { color: '#657886', font: { weight: 600 } },
        title: { display: true, text: 'Forecast Lead Time Horizon', color: '#405565', font: { weight: 600 } },
      },
      y: {
        stacked: true,
        max: 100,
        grid: { color: 'rgba(77, 145, 201, 0.12)' },
        ticks: {
          color: '#657886',
          callback: (val) => `${val}%`,
        },
        title: { display: true, text: 'Normalized Model Weight (%)', color: '#405565', font: { weight: 600 } },
      },
    },
  }

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="card-header" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
        <div className="card-title">
          <Clock size={18} color="#4D91C9" />
          <span>Model Weights Evolution Over Lead Time Horizon</span>
        </div>
        <span style={{ fontSize: '0.78rem', color: '#657886', fontWeight: 500 }}>
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
            background: 'rgba(234, 242, 247, 0.65)',
            borderRadius: '6px',
            border: '1px solid rgba(77, 145, 201, 0.20)',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.72rem',
            color: '#405565',
          }}
        >
          <Info size={14} color="#4D91C9" style={{ flexShrink: 0 }} />
          <span>
            <strong>Adaptive Dynamics:</strong> Physical NWP models dominate the <strong>short-range (6h-24h)</strong> with 60-67% total weight due to explicit convective and boundary-layer physics. In the <strong>extended medium-range (72h-168h)</strong>, AI/ML emulators and Ensembles dynamically gain up to 75% weight as single-model NWP spread increases.
          </span>
        </div>
      </div>
    </div>
  )
}
