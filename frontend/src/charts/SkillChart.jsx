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
import { Award, CheckCircle2 } from 'lucide-react'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

export default function SkillChart({ metricsData }) {
  if (!metricsData) return null

  const allModels = [...metricsData.models, metricsData.blended_model]
  const labels = allModels.map((m) => m.model_name.replace(' (NWP)', '').replace(' (AI)', ''))

  const data = {
    labels,
    datasets: [
      {
        label: 'MAE (Mean Absolute Error)',
        data: allModels.map((m) => m.mae),
        backgroundColor: allModels.map((m) =>
          m.model_id === 'blended' ? '#38bdf8' : 'rgba(148, 163, 184, 0.4)'
        ),
        borderColor: allModels.map((m) =>
          m.model_id === 'blended' ? '#38bdf8' : '#64748b'
        ),
        borderWidth: 1,
        borderRadius: 4,
      },
      {
        label: 'RMSE (Root Mean Square Error)',
        data: allModels.map((m) => m.rmse),
        backgroundColor: allModels.map((m) =>
          m.model_id === 'blended' ? '#0284c7' : 'rgba(100, 116, 139, 0.25)'
        ),
        borderColor: allModels.map((m) =>
          m.model_id === 'blended' ? '#0284c7' : '#475569'
        ),
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: '#cbd5e1', font: { size: 11 } },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        titleColor: '#38bdf8',
        bodyColor: '#f1f5f9',
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#94a3b8', font: { size: 10 } },
      },
      y: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#94a3b8' },
        title: { display: true, text: 'Error Magnitude', color: '#94a3b8' },
      },
    },
  }

  return (
    <div className="glass-card">
      <div className="card-header">
        <div className="card-title">
          <Award size={18} color="#10b981" />
          <span>Verification Scorecard (Ground Truth Benchmark)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span className="badge-green">
            +{metricsData.mae_improvement_pct}% Skill Gain
          </span>
        </div>
      </div>
      <div className="card-body">
        <div style={{ height: '240px' }}>
          <Bar data={data} options={options} />
        </div>
        <div style={{ marginTop: '0.75rem', padding: '0.5rem', background: 'rgba(16, 185, 129, 0.08)', borderRadius: '6px', border: '1px solid rgba(16, 185, 129, 0.2)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={16} color="#10b981" />
          <span style={{ fontSize: '0.78rem', color: '#a7f3d0' }}>
            <strong>Proven Superiority:</strong> The Adaptive Hybrid model achieves the lowest MAE ({metricsData.blended_model.mae}) and highest correlation ({metricsData.blended_model.correlation}) by selectively filtering out individual model systematic biases.
          </span>
        </div>
      </div>
    </div>
  )
}
