import React from 'react'
import { Award, Layers } from 'lucide-react'

export default function SegmentedModelContributionArc({
  weights = {
    'NWP Model A': 0.24,
    'NWP Model B': 0.38,
    'Ensemble Forecast': 0.20,
    'AI/ML Forecast': 0.18,
  },
  dominantModel = 'NWP Model B',
  size = 140,
}) {
  const modelColors = {
    'NWP Model A': '#2563EB',       // Royal Blue (GFS)
    'NWP Model B': '#1E3A8A',       // Midnight Navy (ECMWF)
    'Ensemble Forecast': '#0284C7',  // Ocean Cerulean (GEFS/EPS)
    'AI/ML Forecast': '#38BDF8',     // Vivid Sky Blue (GraphCast)
  }

  const radius = size * 0.38
  const strokeWidth = 9
  const center = size / 2
  const circumference = 2 * Math.PI * radius

  // Calculate segment offsets
  let accumulated = 0
  const segments = Object.entries(weights).map(([model, weightVal]) => {
    const w = typeof weightVal === 'number' ? weightVal : 0.25
    const dashLength = Math.max(0, w * circumference - 3) // 3px gap between segments
    const offset = -(accumulated * circumference)
    accumulated += w
    return {
      model,
      weight: Math.round(w * 100),
      color: modelColors[model] || '#38bdf8',
      dashArray: `${dashLength} ${circumference - dashLength}`,
      dashOffset: offset,
      isDominant: model === dominantModel,
    }
  })

  const dominantPct = Math.round((weights[dominantModel] || 0.38) * 100)

  return (
    <div className="scientific-instrument-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
          {/* Subtle background track */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="none"
            stroke="rgba(255, 255, 255, 0.05)"
            strokeWidth={strokeWidth}
          />

          {/* Segmented Arcs */}
          {segments.map((seg) => (
            <circle
              key={seg.model}
              cx={center}
              cy={center}
              r={radius}
              fill="none"
              stroke={seg.color}
              strokeWidth={seg.isDominant ? strokeWidth + 2 : strokeWidth}
              strokeDasharray={seg.dashArray}
              strokeDashoffset={seg.dashOffset}
              style={{
                transition: 'all 0.6s ease',
                filter: seg.isDominant ? `drop-shadow(0 0 6px ${seg.color}88)` : 'none',
              }}
            />
          ))}
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
          <div style={{ fontSize: '0.62rem', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 700 }}>
            LEAD MODEL
          </div>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#f8fafc', lineHeight: 1.1 }}>
            {dominantPct}%
          </div>
          <div style={{ fontSize: '0.65rem', color: '#38bdf8', fontWeight: 700 }}>
            {dominantModel?.replace('Model ', '') || 'ECMWF'}
          </div>
        </div>
      </div>

      {/* Mini Legend */}
      <div style={{ marginTop: '8px', display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '4px', width: '100%', fontSize: '0.66rem' }}>
        {segments.map((seg) => (
          <div key={seg.model} style={{ display: 'flex', alignItems: 'center', gap: '4px', color: seg.isDominant ? '#f8fafc' : '#94a3b8' }}>
            <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: seg.color, flexShrink: 0 }} />
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {seg.model.replace(' Forecast', '').replace('Model ', '')}: <strong>{seg.weight}%</strong>
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
