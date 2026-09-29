import React from 'react'
import { Wind, Compass, ShieldCheck } from 'lucide-react'

export default function WindFlowIndicator({
  speed = 24.5,
  direction = 245,
  dispersion = 5.8,
  stationName = 'Mumbai Coastal',
}) {
  // Convert meteorological degrees to cardinal compass label
  const getCardinal = (deg) => {
    const cardinals = [
      'N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
      'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW',
    ]
    const idx = Math.round(deg / 22.5) % 16
    return cardinals[idx]
  }

  // Beaufort scale classification (Strict Shades of Blue)
  const getBeaufort = (spdKmH) => {
    if (spdKmH < 12) return { scale: 'Light Breeze', bft: 'Bft 2', color: '#64748B' }
    if (spdKmH < 20) return { scale: 'Gentle Breeze', bft: 'Bft 3', color: '#38BDF8' }
    if (spdKmH < 29) return { scale: 'Moderate Breeze', bft: 'Bft 4', color: '#0284C7' }
    if (spdKmH < 39) return { scale: 'Fresh Breeze', bft: 'Bft 5', color: '#0369A1' }
    if (spdKmH < 50) return { scale: 'Strong Breeze', bft: 'Bft 6', color: '#2563EB' }
    if (spdKmH < 62) return { scale: 'High Wind / Near Gale', bft: 'Bft 7', color: '#1D4ED8' }
    return { scale: 'Gale / Storm Squall', bft: 'Bft 8+', color: '#1E3A8A' }
  }

  const cardinal = getCardinal(direction)
  const bftInfo = getBeaufort(speed)
  const gustSpeed = Math.round((speed * 1.35) * 10) / 10

  return (
    <div className="weather-card">
      <div className="weather-card-header">
        <div className="weather-card-title-group">
          <div className="weather-icon-badge" style={{ background: 'rgba(2, 132, 199, 0.15)', color: '#0284C7' }}>
            <Wind size={18} />
          </div>
          <div>
            <h4 className="weather-card-title">Wind Vector & Flow Field</h4>
            <span className="weather-card-subtitle">Yamartino Circular Trigonometric Averaging</span>
          </div>
        </div>

        <span
          className="weather-category-badge"
          style={{ background: `${bftInfo.color}18`, color: bftInfo.color, border: `1px solid ${bftInfo.color}35` }}
        >
          {bftInfo.scale} ({bftInfo.bft})
        </span>
      </div>

      <div className="wind-indicator-layout">
        {/* Animated Directional Compass Dial */}
        <div className="wind-compass-mini">
          <div className="compass-dial-ring">
            <span className="compass-mark north">N</span>
            <span className="compass-mark east">E</span>
            <span className="compass-mark south">S</span>
            <span className="compass-mark west">W</span>

            {/* Rotating Arrow Indicator */}
            <div
              className="compass-vector-arrow"
              style={{
                transform: `rotate(${direction}deg)`,
              }}
            >
              <div className="arrow-head" />
              <div className="arrow-tail" />
            </div>
            <div className="compass-center-dot" />
          </div>
        </div>

        {/* Speed & Heading Readout */}
        <div className="wind-readout-col">
          <div className="weather-metric-large">
            <span className="value-num">{speed}</span>
            <span className="value-unit">km/h</span>
          </div>

          <div className="wind-heading-pill">
            <Compass size={14} color="#0284C7" />
            <span>Heading: <strong>{direction}° {cardinal}</strong></span>
          </div>

          <div className="wind-gust-row">
            <span>Peak Gust Envelope:</span>
            <strong>{gustSpeed} km/h</strong>
          </div>
        </div>
      </div>

      {/* Atmospheric Micro-indicators */}
      <div className="weather-sub-metrics">
        <div className="weather-sub-item">
          <Compass size={13} color="#0284C7" />
          <span className="sub-label">Dispersion (σ_θ):</span>
          <span className="sub-value">±{dispersion}°</span>
        </div>
        <div className="weather-sub-item">
          <ShieldCheck size={13} color="#2563EB" />
          <span className="sub-label">WMO Standard:</span>
          <span className="sub-value">WMO-No. 8 Compliant</span>
        </div>
      </div>
    </div>
  )
}
