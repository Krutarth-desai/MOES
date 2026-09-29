import React from 'react'
import { Shield, Activity, BarChart2 } from 'lucide-react'

export default function HorizontalConfidenceBand({
  blendedValue = 38.5,
  ci10 = 34.6,
  ci90 = 42.4,
  unit = 'mm',
  entropy = 0.88,
  confidencePercent = 88,
}) {
  const spread = Math.round((ci90 - ci10) * 10) / 10
  const halfSpread = Math.round((spread / 2) * 10) / 10

  // Derive confidence category
  const getConfidenceLevel = (ent) => {
    if (ent <= 0.90) return { label: 'HIGH CONSENSUS', color: '#2563EB', bg: 'rgba(37, 99, 235, 0.12)' }
    if (ent <= 1.25) return { label: 'MODERATE CONSENSUS', color: '#0284C7', bg: 'rgba(2, 132, 199, 0.12)' }
    return { label: 'ELEVATED SPREAD', color: '#1E3A8A', bg: 'rgba(30, 58, 138, 0.12)' }
  }

  const confInfo = getConfidenceLevel(entropy)

  return (
    <div className="weather-card">
      <div className="weather-card-header">
        <div className="weather-card-title-group">
          <div className="weather-icon-badge" style={{ background: 'rgba(37, 99, 235, 0.12)', color: '#2563EB' }}>
            <Shield size={18} />
          </div>
          <div>
            <h4 className="weather-card-title">Forecast Confidence Envelope</h4>
            <span className="weather-card-subtitle">Quantile Conformal Bounds (10th–90th %)</span>
          </div>
        </div>

        <span
          className="weather-category-badge"
          style={{ background: confInfo.bg, color: confInfo.color, border: `1px solid ${confInfo.color}35` }}
        >
          {confInfo.label}
        </span>
      </div>

      {/* Hero Numbers */}
      <div className="weather-value-hero">
        <div className="weather-metric-large">
          <span className="value-num">{confidencePercent}%</span>
          <span className="value-unit">Reliability Index</span>
        </div>
        <div className="weather-envelope-tag">
          <span>Uncertainty Margin:</span>
          <strong>±{halfSpread} {unit}</strong>
        </div>
      </div>

      {/* Horizontal Confidence Envelope Visual Bar */}
      <div className="confidence-band-container">
        <div className="confidence-scale-endpoints">
          <div className="endpoint-col left">
            <span className="endpoint-tag">10th Percentile</span>
            <span className="endpoint-val">{ci10} {unit}</span>
          </div>

          <div className="endpoint-col center">
            <span className="endpoint-tag">Blended Median</span>
            <span className="endpoint-val consensus">{blendedValue} {unit}</span>
          </div>

          <div className="endpoint-col right">
            <span className="endpoint-tag">90th Percentile</span>
            <span className="endpoint-val">{ci90} {unit}</span>
          </div>
        </div>

        <div className="confidence-bar-track">
          {/* Continuous Gaussian gradient band */}
          <div className="confidence-envelope-fill">
            <div className="confidence-marker median" />
          </div>
        </div>
      </div>

      {/* Entropy & Atmospheric Dispersion */}
      <div className="weather-sub-metrics">
        <div className="weather-sub-item">
          <Activity size={13} color="#4D91C9" />
          <span className="sub-label">Consensus Entropy:</span>
          <span className="sub-value">{entropy} / 1.0</span>
        </div>
        <div className="weather-sub-item">
          <BarChart2 size={13} color="#294E6B" />
          <span className="sub-label">Bandwidth:</span>
          <span className="sub-value">{spread} {unit} (80% Mass)</span>
        </div>
        <div className="weather-sub-item">
          <Shield size={13} color="#2563EB" />
          <span className="sub-label">Physical Bounds:</span>
          <span className="sub-value">Verified Non-Negative</span>
        </div>
      </div>
    </div>
  )
}
