import React from 'react'
import { CloudRain, Droplets, TrendingUp, Info } from 'lucide-react'

export default function PrecipitationIntensityCard({
  value = 38.5,
  unit = 'mm',
  ci10 = 34.6,
  ci90 = 42.4,
  leadTime = 24,
  stationName = 'Mumbai',
}) {
  // IMD Rainfall classification thresholds (mm in 24 hours)
  const getRainfallCategory = (val) => {
    if (val < 2.5) return { category: 'Very Light', color: '#64748B', badgeBg: 'rgba(100, 116, 139, 0.12)', rate: 'Scattered' }
    if (val <= 15.5) return { category: 'Light Rain', color: '#38BDF8', badgeBg: 'rgba(56, 189, 248, 0.15)', rate: 'Steady' }
    if (val <= 64.4) return { category: 'Moderate Rain', color: '#0284C7', badgeBg: 'rgba(2, 132, 199, 0.15)', rate: 'Convective' }
    if (val <= 115.5) return { category: 'Heavy Rain', color: '#2563EB', badgeBg: 'rgba(37, 99, 235, 0.15)', rate: 'Intense (Advisory Tier)' }
    if (val <= 204.4) return { category: 'Very Heavy Rain', color: '#1D4ED8', badgeBg: 'rgba(29, 78, 216, 0.18)', rate: 'Downpour (Elevated Tier)' }
    return { category: 'Extremely Heavy', color: '#1E3A8A', badgeBg: 'rgba(30, 58, 138, 0.18)', rate: 'Torrential (Priority Tier)' }
  }

  const { category, color, badgeBg, rate } = getRainfallCategory(value)
  const progressPct = Math.min(100, Math.round((value / 150) * 100))

  return (
    <div className="weather-card">
      <div className="weather-card-header">
        <div className="weather-card-title-group">
          <div className="weather-icon-badge" style={{ background: 'rgba(77, 145, 201, 0.15)', color: '#4D91C9' }}>
            <CloudRain size={18} />
          </div>
          <div>
            <h4 className="weather-card-title">Precipitation Intensity</h4>
            <span className="weather-card-subtitle">Tweedie Compound Poisson · {stationName}</span>
          </div>
        </div>

        <span
          className="weather-category-badge"
          style={{ background: badgeBg, color, border: `1px solid ${color}40` }}
        >
          {category}
        </span>
      </div>

      <div className="weather-value-hero">
        <div className="weather-metric-large">
          <span className="value-num">{value}</span>
          <span className="value-unit">{unit} / 24h</span>
        </div>
        <div className="weather-envelope-tag">
          <span>90% Envelope:</span>
          <strong>{ci10} – {ci90} {unit}</strong>
        </div>
      </div>

      {/* Meteorological Intensity Gauge Bar */}
      <div className="weather-gauge-container">
        <div className="weather-gauge-labels">
          <span>0mm</span>
          <span>15.5 (Mod)</span>
          <span>64.5 (Hvy)</span>
          <span>115.5 (V.Hvy)</span>
          <span>&gt;200mm</span>
        </div>
        <div className="weather-gauge-track">
          <div
            className="weather-gauge-fill"
            style={{
              width: `${progressPct}%`,
              background: `linear-gradient(90deg, #78B8DF, ${color})`,
            }}
          />
          {/* Active pointer marker */}
          <div
            className="weather-gauge-needle"
            style={{ left: `${progressPct}%`, borderColor: color }}
          />
        </div>
      </div>

      {/* Short-Range Ingestion Telemetry */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', margin: '0.65rem 0' }}>
        <div style={{ background: 'rgba(56, 145, 218, 0.08)', borderRadius: '6px', padding: '4px 6px', textAlign: 'center' }}>
          <div style={{ fontSize: '0.62rem', color: '#64748B', fontWeight: 600 }}>6h Acc</div>
          <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#0F2942' }}>{(value * 0.28).toFixed(1)} {unit}</div>
        </div>
        <div style={{ background: 'rgba(56, 145, 218, 0.08)', borderRadius: '6px', padding: '4px 6px', textAlign: 'center' }}>
          <div style={{ fontSize: '0.62rem', color: '#64748B', fontWeight: 600 }}>12h Acc</div>
          <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#0F2942' }}>{(value * 0.58).toFixed(1)} {unit}</div>
        </div>
        <div style={{ background: 'rgba(56, 145, 218, 0.08)', borderRadius: '6px', padding: '4px 6px', textAlign: 'center' }}>
          <div style={{ fontSize: '0.62rem', color: '#64748B', fontWeight: 600 }}>Tweedie φ</div>
          <div style={{ fontSize: '0.75rem', fontWeight: 800, color: '#2563EB' }}>1.42</div>
        </div>
      </div>

      {/* Atmospheric Micro-indicators */}
      <div className="weather-sub-metrics">
        <div className="weather-sub-item">
          <Droplets size={13} color="#4D91C9" />
          <span className="sub-label">Regime:</span>
          <span className="sub-value">{rate}</span>
        </div>
        <div className="weather-sub-item">
          <TrendingUp size={13} color="#2563EB" />
          <span className="sub-label">Lead Time:</span>
          <span className="sub-value">T+{leadTime}h</span>
        </div>
        <div className="weather-sub-item">
          <Info size={13} color="#657886" />
          <span className="sub-label">Zero-Inflation:</span>
          <span className="sub-value">P(Rain&gt;0) = 94%</span>
        </div>
      </div>
    </div>
  )
}
