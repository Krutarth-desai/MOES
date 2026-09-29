import React from 'react'
import { CloudRain, AlertTriangle } from 'lucide-react'

export default function PrecipitationGauge({
  rainfallMm = 84.5,
  size = 140,
}) {
  const maxScale = 220
  const pct = Math.min(100, Math.max(0, (rainfallMm / maxScale) * 100))
  const radius = size * 0.38
  const strokeWidth = 9
  const center = size / 2
  const circumference = 2 * Math.PI * radius
  // Open 240 degree gauge arc
  const arcLength = circumference * 0.67
  const strokeDashoffset = arcLength - (pct / 100) * arcLength

  let category = 'Moderate Rain'
  let color = '#38bdf8'
  let alertBadge = null

  if (rainfallMm >= 204.5) {
    category = 'Extremely Heavy'
    color = '#1E3A8A'
    alertBadge = 'TIER 1 (EXTREME)'
  } else if (rainfallMm >= 115.6) {
    category = 'Very Heavy'
    color = '#1D4ED8'
    alertBadge = 'TIER 2 (VERY HEAVY)'
  } else if (rainfallMm >= 64.5) {
    category = 'Heavy Rainfall'
    color = '#2563EB'
    alertBadge = 'TIER 3 (HEAVY)'
  } else if (rainfallMm < 15.6) {
    category = 'Light / Trace'
    color = '#38BDF8'
  }

  return (
    <div className="scientific-instrument-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Base gauge track */}
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
            {rainfallMm}
          </div>
          <div style={{ fontSize: '0.68rem', color: '#94a3b8', fontWeight: 600 }}>
            mm / 24h
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

      {/* IMD Category Readout */}
      <div style={{ marginTop: '4px', textAlign: 'center' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: 700, color }}>
          {category}
        </div>
        <div style={{ fontSize: '0.65rem', color: '#64748b', marginTop: '1px', fontFamily: 'monospace' }}>
          Tweedie Physical Bound: R ≥ 0.0 mm
        </div>
      </div>
    </div>
  )
}
