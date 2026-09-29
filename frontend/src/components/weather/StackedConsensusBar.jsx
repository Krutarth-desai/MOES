import React from 'react'
import { Layers, Award, Sparkles } from 'lucide-react'

export default function StackedConsensusBar({
  weights = {
    'NWP Model A': 0.24,
    'NWP Model B': 0.38,
    'Ensemble Forecast': 0.20,
    'AI/ML Forecast': 0.18,
  },
  dominantModel = 'NWP Model B',
  dominantWeight = 38,
  leadTime = 24,
  individualForecasts = {
    'NWP Model A': 41.2,
    'NWP Model B': 36.8,
    'Ensemble Forecast': 39.4,
    'AI/ML Forecast': 37.1,
  },
  unit = 'mm',
}) {
  const modelColors = {
    'NWP Model A': '#2563EB',       // Royal Blue (GFS)
    'NWP Model B': '#1E3A8A',       // Midnight Navy (ECMWF)
    'Ensemble Forecast': '#0284C7',  // Ocean Cerulean (GEFS)
    'AI/ML Forecast': '#38BDF8',     // Vivid Sky Blue (GraphCast)
  }

  const modelLabels = {
    'NWP Model A': 'NWP Model A (GFS)',
    'NWP Model B': 'NWP Model B (ECMWF)',
    'Ensemble Forecast': 'Multi-Ensemble',
    'AI/ML Forecast': 'AI/ML (GraphCast)',
  }

  // Calculate raw min/max spread
  const forecastVals = Object.values(individualForecasts || {})
  const minVal = forecastVals.length > 0 ? Math.min(...forecastVals) : 36.8
  const maxVal = forecastVals.length > 0 ? Math.max(...forecastVals) : 41.2
  const rawSpread = Math.round((maxVal - minVal) * 10) / 10

  return (
    <div className="weather-card">
      <div className="weather-card-header">
        <div className="weather-card-title-group">
          <div className="weather-icon-badge" style={{ background: 'rgba(37, 99, 235, 0.12)', color: '#2563EB' }}>
            <Layers size={18} />
          </div>
          <div>
            <h4 className="weather-card-title">Multi-Model Consensus Weights</h4>
            <span className="weather-card-subtitle">Dynamic Softmax Simplex · Horizon T+{leadTime}h</span>
          </div>
        </div>

        <div className="weather-dominant-pill">
          <Award size={13} color="#2563EB" />
          <span>Dominant: <strong>{dominantModel}</strong> ({dominantWeight}%)</span>
        </div>
      </div>

      {/* Proportional Stacked Consensus Bar */}
      <div className="stacked-consensus-bar-wrapper">
        <div className="stacked-consensus-track">
          {Object.entries(weights).map(([model, weight]) => {
            const pct = Math.round((typeof weight === 'number' ? weight : 0.25) * 100)
            const color = modelColors[model] || '#4D91C9'
            const isDom = model === dominantModel

            return (
              <div
                key={model}
                className={`stacked-bar-segment ${isDom ? 'dominant' : ''}`}
                style={{
                  width: `${pct}%`,
                  backgroundColor: color,
                }}
                title={`${model}: ${pct}% weight`}
              >
                {pct >= 14 && <span className="segment-label">{pct}%</span>}
              </div>
            )
          })}
        </div>
      </div>

      {/* Candidate Model Chips Grid */}
      <div className="model-chips-grid">
        {Object.entries(weights).map(([model, weight]) => {
          const pct = Math.round((typeof weight === 'number' ? weight : 0.25) * 100)
          const color = modelColors[model] || '#4D91C9'
          const isDom = model === dominantModel
          const fVal = individualForecasts?.[model]

          return (
            <div
              key={model}
              className={`model-chip-card ${isDom ? 'active-dominant' : ''}`}
              style={{
                borderLeftColor: color,
              }}
            >
              <div className="model-chip-header">
                <span className="model-color-dot" style={{ backgroundColor: color }} />
                <span className="model-chip-name">{modelLabels[model] || model}</span>
                {isDom && (
                  <span className="dominant-micro-badge">Leader</span>
                )}
              </div>
              <div className="model-chip-values">
                <span className="model-weight-text" style={{ color }}>{pct}% wt</span>
                {fVal !== undefined && (
                  <span className="model-forecast-text">{fVal} {unit}</span>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Model Spread Footer */}
      <div className="weather-sub-metrics">
        <div className="weather-sub-item">
          <Sparkles size={13} color="#4D91C9" />
          <span className="sub-label">Raw Model Spread:</span>
          <span className="sub-value">{minVal} – {maxVal} {unit} (Δ {rawSpread} {unit})</span>
        </div>
        <div className="weather-sub-item">
          <Layers size={13} color="#2563EB" />
          <span className="sub-label">Simplex Normalization:</span>
          <span className="sub-value">Σ wᵢ = 1.0000</span>
        </div>
      </div>
    </div>
  )
}
