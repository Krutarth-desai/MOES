import React from 'react'
import { AlertTriangle, ShieldAlert } from 'lucide-react'

export default function HazardSeverityRadar({
  activeAlertsCount = 2,
  highestLevel = 'RED WARNING',
  riskScore = 88,
  zoneName = 'Konkan & Western Ghats',
  size = 140,
}) {
  const center = size / 2
  const radius = size * 0.42

  const isRed = highestLevel.includes('RED') || highestLevel.includes('TIER 1')
  const isOrange = highestLevel.includes('ORANGE') || highestLevel.includes('TIER 2')
  const color = isRed ? '#1E3A8A' : isOrange ? '#2563EB' : '#0284C7'

  return (
    <div className="scientific-instrument-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Concentric radar rings */}
          <circle cx={center} cy={center} r={radius} fill="rgba(15, 23, 42, 0.5)" stroke="rgba(255, 255, 255, 0.1)" strokeWidth="1" />
          <circle cx={center} cy={center} r={radius * 0.72} fill="none" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />
          <circle cx={center} cy={center} r={radius * 0.45} fill="none" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />

          {/* Crosshairs */}
          <line x1={center} y1={center - radius} x2={center} y2={center + radius} stroke="rgba(255, 255, 255, 0.06)" strokeWidth="1" />
          <line x1={center - radius} y1={center} x2={center + radius} y2={center} stroke="rgba(255, 255, 255, 0.06)" strokeWidth="1" />

          {/* Animated radar sweep line */}
          <g style={{ transformOrigin: `${center}px ${center}px`, animation: 'radarSweep 3.5s linear infinite' }}>
            <line x1={center} y1={center} x2={center} y2={center - radius} stroke={color} strokeWidth="1.5" strokeOpacity="0.8" />
            <polygon
              points={`${center},${center} ${center},${center - radius} ${center + radius * 0.4},${center - radius * 0.85}`}
              fill={color}
              opacity="0.12"
            />
          </g>

          {/* Outer active warning ring (pulsing) */}
          <circle
            cx={center}
            cy={center}
            r={radius - 1}
            fill="none"
            stroke={color}
            strokeWidth="2"
            strokeDasharray="4 4"
            className="hazard-radar-ring"
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
          <div style={{ fontSize: '1.45rem', fontWeight: 800, color, lineHeight: 1, fontFamily: 'monospace' }}>
            {activeAlertsCount}
          </div>
          <div style={{ fontSize: '0.62rem', color: '#f8fafc', fontWeight: 700, letterSpacing: '0.04em' }}>
            ACTIVE ALERTS
          </div>
          <div style={{ fontSize: '0.58rem', color, fontWeight: 800, marginTop: '2px', background: `${color}22`, padding: '1px 5px', borderRadius: '3px' }}>
            RISK: {riskScore}%
          </div>
        </div>
      </div>

      {/* Advisory Status Readout */}
      <div style={{ marginTop: '4px', textAlign: 'center' }}>
        <div style={{ fontSize: '0.78rem', fontWeight: 700, color }}>
          {highestLevel}
        </div>
        <div style={{ fontSize: '0.66rem', color: '#94a3b8', marginTop: '1px' }}>
          Impact Zone: {zoneName.split('&')[0]}
        </div>
      </div>
    </div>
  )
}
