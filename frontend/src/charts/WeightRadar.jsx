import React, { useState } from 'react'
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
import { PieChart, Info, ShieldCheck, MapPin } from 'lucide-react'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const MODEL_CONFIGS = [
  { id: 'NWP Model A', label: 'NWP Model A', color: '#0284c7' },
  { id: 'NWP Model B', label: 'NWP Model B', color: '#10b981' },
  { id: 'Ensemble Forecast', label: 'Ensemble', color: '#f59e0b' },
  { id: 'AI/ML Forecast', label: 'AI/ML', color: '#8b5cf6' },
]

export default function WeightRadar({ weightsData, weightGridData }) {
  const [selectedRegionId, setSelectedRegionId] = useState('western_ghats')

  // Fallback to legacy regional_weights if weightGridData not yet loaded
  const regionalSummaries = weightGridData?.regional_summaries || []
  const legacyWeights = weightsData?.regional_weights || []

  const labels = regionalSummaries.length > 0
    ? regionalSummaries.map((r) => r.region_name.split(' (')[0].replace(' & ', '/'))
    : legacyWeights.map((r) => r.region_name.split(' (')[0].replace(' & ', '/'))

  const datasets = MODEL_CONFIGS.map((m) => ({
    label: m.label,
    data: regionalSummaries.length > 0
      ? regionalSummaries.map((r) => Math.round((r.weights[m.id] || 0.25) * 100))
      : legacyWeights.map((r) => {
          const item = r.weights?.find((w) => w.model_id?.toLowerCase() === m.id.toLowerCase() || m.id.toLowerCase().includes(w.model_id?.toLowerCase()))
          return item ? Math.round(item.weight * 100) : 25
        }),
    backgroundColor: m.color,
    borderRadius: 2,
  }))

  const chartData = { labels, datasets }

  const chartOptions = {
    indexAxis: 'y', // Horizontal stacked bar
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: { color: '#cbd5e1', font: { size: 10 }, boxWidth: 10 },
      },
      tooltip: {
        callbacks: {
          label: (context) => `${context.dataset.label}: ${context.raw}% weight`,
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

  // Active region summary card data
  const activeRegion = regionalSummaries.find((r) => r.region_id === selectedRegionId) || regionalSummaries[0]

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <div className="card-header" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
        <div className="card-title">
          <PieChart size={18} color="#f59e0b" />
          <span>Regional Model Reliability & Weight Breakdown</span>
        </div>
        <span style={{ fontSize: '0.78rem', color: '#94a3b8' }}>
          Simplex ∑ w = 100%
        </span>
      </div>

      <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', paddingTop: '0.25rem' }}>
        {/* Horizontal Stacked Bar Chart */}
        <div style={{ height: '220px' }}>
          <Bar data={chartData} options={chartOptions} />
        </div>

        {/* Region Selector Pills */}
        {regionalSummaries.length > 0 && (
          <div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <MapPin size={12} color="var(--accent-cyan)" />
              Inspect Region Reliability Summary:
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
              {regionalSummaries.map((r) => (
                <button
                  key={r.region_id}
                  onClick={() => setSelectedRegionId(r.region_id)}
                  style={{
                    background: selectedRegionId === r.region_id ? 'rgba(56, 189, 248, 0.2)' : 'rgba(30, 41, 59, 0.5)',
                    border: `1px solid ${selectedRegionId === r.region_id ? 'var(--accent-cyan)' : 'var(--border-color)'}`,
                    color: selectedRegionId === r.region_id ? '#fff' : '#94a3b8',
                    padding: '3px 8px',
                    borderRadius: '4px',
                    fontSize: '0.7rem',
                    cursor: 'pointer',
                    fontWeight: 600,
                  }}
                >
                  {r.region_name.split(' (')[0]}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Formatted Region Summary Block */}
        {activeRegion && (
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.7)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '8px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
                {activeRegion.region_name}
              </span>
              <span style={{ fontSize: '0.7rem', background: '#1e293b', padding: '2px 6px', borderRadius: '4px', color: '#94a3b8' }}>
                Dominant: <strong>{activeRegion.dominant_model}</strong> ({Math.round(activeRegion.dominant_weight * 100)}%)
              </span>
            </div>

            {/* Structured Text Representation matching user specification */}
            <pre
              style={{
                fontFamily: 'monospace',
                fontSize: '0.74rem',
                color: '#e2e8f0',
                background: 'rgba(30, 41, 59, 0.8)',
                padding: '6px 10px',
                borderRadius: '4px',
                lineHeight: '1.4',
                margin: 0,
              }}
            >
              {activeRegion.summary_formatted}
            </pre>

            {/* Contextual Rationale */}
            {activeRegion.context_explanation && (
              <p style={{ fontSize: '0.72rem', color: '#cbd5e1', lineHeight: '1.35', fontStyle: 'italic' }}>
                {activeRegion.context_explanation}
              </p>
            )}
          </div>
        )}

        {/* Governance Notice: Anti-Global-Best Model Principle */}
        <div
          style={{
            fontSize: '0.68rem',
            color: '#94a3b8',
            background: 'rgba(30, 41, 59, 0.4)',
            padding: '6px 10px',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            borderLeft: '2px solid var(--accent-amber)',
          }}
        >
          <Info size={13} color="var(--accent-amber)" style={{ flexShrink: 0 }} />
          <span>
            <strong>Contextual Reliability Principle:</strong> No model is labeled as "best" globally.
            NWP physics excels in complex orography, AI/ML leads in continental plains advection, and Ensembles lead under convective uncertainty.
          </span>
        </div>
      </div>
    </div>
  )
}
