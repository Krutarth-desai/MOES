import React from 'react'
import { Thermometer, Sun, TrendingUp, AlertTriangle } from 'lucide-react'

export default function ThermalAtmosphericCard({
  value = 32.4,
  unit = '°C',
  ci10 = 30.8,
  ci90 = 34.2,
  departure = 1.2,
  minTemp = 26.2,
  maxTemp = 34.5,
  stationName = 'Mumbai',
}) {
  // IMD Heatwave Criteria
  const getThermalStatus = (temp, dep) => {
    if (temp >= 45 || dep >= 6.4) {
      return { status: 'Severe Heatwave', color: '#1E3A8A', bg: 'rgba(30, 58, 138, 0.15)', alert: 'High Thermal Tier' }
    }
    if ((temp >= 40 && dep >= 4.5) || temp >= 44) {
      return { status: 'Heatwave Condition', color: '#2563EB', bg: 'rgba(37, 99, 235, 0.15)', alert: 'Elevated Heat Alert' }
    }
    if (dep >= 3.0) {
      return { status: 'Above Normal', color: '#0284C7', bg: 'rgba(2, 132, 199, 0.15)', alert: 'Thermal Advisory' }
    }
    return { status: 'Normal Thermal Range', color: '#38BDF8', bg: 'rgba(56, 189, 248, 0.12)', alert: 'Baseline Normal' }
  }

  const { status, color, bg, alert } = getThermalStatus(value, departure)

  return (
    <div className="weather-card">
      <div className="weather-card-header">
        <div className="weather-card-title-group">
          <div className="weather-icon-badge" style={{ background: 'rgba(37, 99, 235, 0.12)', color: '#2563EB' }}>
            <Thermometer size={18} />
          </div>
          <div>
            <h4 className="weather-card-title">Surface Thermodynamic Profile</h4>
            <span className="weather-card-subtitle">2m Air Temperature · {stationName}</span>
          </div>
        </div>

        <span
          className="weather-category-badge"
          style={{ background: bg, color, border: `1px solid ${color}35` }}
        >
          {status}
        </span>
      </div>

      <div className="weather-value-hero">
        <div className="weather-metric-large">
          <span className="value-num">{value}</span>
          <span className="value-unit">{unit}</span>
        </div>
        <div className="weather-envelope-tag">
          <span>Departure from Climatology:</span>
          <strong style={{ color: departure > 0 ? '#2563EB' : '#0284C7' }}>
            {departure > 0 ? `+${departure}` : departure} {unit}
          </strong>
        </div>
      </div>

      {/* Diurnal Thermal Range Track */}
      <div className="diurnal-range-container">
        <div className="diurnal-endpoints">
          <span className="diurnal-label">Min: <strong>{minTemp}{unit}</strong></span>
          <span className="diurnal-label">Consensus: <strong>{value}{unit}</strong></span>
          <span className="diurnal-label">Max: <strong>{maxTemp}{unit}</strong></span>
        </div>
        <div className="diurnal-track">
          <div
            className="diurnal-fill"
            style={{
              left: '25%',
              width: '50%',
              background: 'linear-gradient(90deg, #BAE6FD, #2563EB)',
            }}
          />
        </div>
      </div>

      {/* Atmospheric Micro-indicators */}
      <div className="weather-sub-metrics">
        <div className="weather-sub-item">
          <Sun size={13} color="#2563EB" />
          <span className="sub-label">Heat Stress:</span>
          <span className="sub-value">{alert}</span>
        </div>
        <div className="weather-sub-item">
          <TrendingUp size={13} color="#4D91C9" />
          <span className="sub-label">90% Range:</span>
          <span className="sub-value">{ci10} – {ci90} {unit}</span>
        </div>
      </div>
    </div>
  )
}
