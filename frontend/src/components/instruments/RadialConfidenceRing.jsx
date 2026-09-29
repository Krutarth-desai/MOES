import React from 'react'
import { Shield, TrendingUp } from 'lucide-react'

export default function RadialConfidenceRing({
  confidence = 88,
  entropy = 0.88,
  ci10 = 34.6,
  ci90 = 42.4,
  unit = 'mm',
  size = 140,
}) {
  const radius = size * 0.38
  const strokeWidth = 9
  const center = size / 2
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (confidence / 100) * circumference

  // Color gradient according to confidence (Strict Shades of Blue)
  const strokeColor = confidence >= 80 ? '#2563EB' : confidence >= 60 ? '#0284C7' : '#1E3A8A'
  const confidenceLabel = confidence >= 80 ? 'HIGH CONSENSUS' : confidence >= 60 ? 'MODERATE SPREAD' : 'DIVERGENT'

  return (
    <div className="scientific-instrument-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
          {/* Outer radar grid ring */}
          <circle
            cx={center}
            cy={center}
            r={radius + 6}
            fill="none"
            stroke="rgba(56, 189, 248, 0.12)"
            strokeWidth="1"
            strokeDasharray="3 3"
          />

          {/* Background track */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="rgba(255, 255, 255, 0.08)"
            strokeWidth={strokeWidth}
          />

          {/* Active Confidence Arc */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke={strokeColor}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            style={{
              transition: 'stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
              filter: `drop-shadow(0 0 6px ${strokeColor}66)`,
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
            {confidence}%
          </div>
          <div style={{ fontSize: '0.62rem', color: strokeColor, fontWeight: 700, letterSpacing: '0.05em', marginTop: '2px' }}>
            {confidenceLabel}
          </div>
        </div>
      </div>

      {/* Uncertainty Band Readout */}
      <div style={{ marginTop: '8px', width: '100%', textAlign: 'center' }}>
        <div style={{ fontSize: '0.72rem', color: '#cbd5e1', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '4px' }}>
          <Shield size={12} color={strokeColor} />
          <span>90% CI: <strong>{ci10} – {ci90} {unit}</strong></span>
        </div>
        <div style={{ fontSize: '0.66rem', color: '#94a3b8', marginTop: '2px', fontFamily: 'monospace' }}>
          Entropy: {entropy} / 1.0 (Low Dispersion)
        </div>
      </div>
    </div>
  )
}
