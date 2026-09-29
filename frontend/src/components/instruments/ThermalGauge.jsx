import React from 'react'
import { Thermometer, Flame } from 'lucide-react'

export default function ThermalGauge({
  temperatureC = 38.5,
  size = 140,
}) {
  const minTemp = 10
  const maxTemp = 50
  const pct = Math.min(100, Math.max(0, ((temperatureC - minTemp) / (maxTemp - minTemp)) * 100))
  const radius = size * 0.38
  const strokeWidth = 9
  const center = size / 2
  const circumference = 2 * Math.PI * radius
  // Open 240 degree gauge arc
  const arcLength = circumference * 0.67
  const strokeDashoffset = arcLength - (pct / 100) * arcLength

  let category = 'Normal Thermal Range'
  let color = '#38bdf8'
  let alertBadge = null

  if (temperatureC >= 45.0) {
    category = 'Severe Heat Wave'
    color = '#1E3A8A'
    alertBadge = 'TIER 1 (SEVERE HEAT)'
  } else if (temperatureC >= 40.0) {
    category = 'Heat Wave Warning'
    color = '#2563EB'
    alertBadge = 'TIER 2 (HEAT WAVE)'
  } else if (temperatureC <= 10.0) {
    category = 'Cold Wave Conditions'
    color = '#38BDF8'
    alertBadge = 'COLD WAVE'
  }

  return (
    <div className="scientific-instrument-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Base track */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="rgba(255, 255, 255, 0.06)"
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
            style={{ transform: 'rotate(150deg)', transformOrigin: `${center}px ${center}px` }}
          />

          {/* Active Fill Arc */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{
              transform: 'rotate(150deg)',
              transformOrigin: `${center}px ${center}px`,
              transition: 'stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
              filter: `drop-shadow(0 0 6px ${color}88)`,
            }}
          />
        </svg>

        {/* Center Readout */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            textAlign: 'center',
            pointerEvents: 'none',
          }}
        >
          <div style={{ fontSize: '1.45rem', fontWeight: 800, color: '#f8fafc', lineHeight: 1, fontFamily: 'monospace' }}>
            {temperatureC}°
          </div>
          <div style={{ fontSize: '0.68rem', color: '#94a3b8', fontWeight: 600 }}>
            Celsius (2m)
          </div>
          {alertBadge && (
            <span
              style={{
                fontSize: '0.58rem',
                fontWeight: 800,
                background: `${color}22`,
                color: color,
                border: `1px solid ${color}55`,
                padding: '1px 5px',
                borderRadius: '3px',
                marginTop: '3px',
              }}
            >
              {alertBadge}
            </span>
          )}
        </div>
      </div>

      {/* Thermodynamic State Readout */}
      <div style={{ marginTop: '4px', textAlign: 'center' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: 700, color }}>
          {category}
        </div>
        <div style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '1px', fontFamily: 'monospace' }}>
          Physical Bounds: [-60°C, +65°C]
        </div>
      </div>
    </div>
  )
}
