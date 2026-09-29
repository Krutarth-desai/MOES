import React from 'react'
import { Compass, Wind } from 'lucide-react'

export default function WindCompassInstrument({
  directionDegrees = 240,
  speedKmh = 42.5,
  size = 140,
}) {
  const center = size / 2
  const radius = size * 0.42
  const speedKnots = Math.round(speedKmh * 0.539957 * 10) / 10

  const getCardinal = (deg) => {
    const val = Math.floor((deg / 22.5) + 0.5)
    const arr = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    return arr[val % 16]
  }

  const cardinal = getCardinal(directionDegrees)
  const isGale = speedKmh >= 62
  const isSquall = speedKmh >= 50 && speedKmh < 62

  return (
    <div className="scientific-instrument-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Compass Dial Outer Ring */}
          <circle
            cx={center}
            cy={center}
            r={radius}
            fill="rgba(15, 23, 42, 0.6)"
            stroke="rgba(56, 189, 248, 0.25)"
            strokeWidth="1.5"
          />

          {/* Compass Cardinal Points */}
          <text x={center} y={center - radius + 11} fill="#f8fafc" fontSize="8" fontWeight="800" textAnchor="middle">N</text>
          <text x={center + radius - 9} y={center + 3} fill="#94a3b8" fontSize="8" fontWeight="700" textAnchor="middle">E</text>
          <text x={center} y={center + radius - 4} fill="#94a3b8" fontSize="8" fontWeight="700" textAnchor="middle">S</text>
          <text x={center - radius + 9} y={center + 3} fill="#94a3b8" fontSize="8" fontWeight="700" textAnchor="middle">W</text>

          {/* Azimuth tick marks */}
          {[0, 45, 90, 135, 180, 225, 270, 315].map((ang) => {
            const rad = (ang - 90) * (Math.PI / 180)
            const x1 = center + (radius - 3) * Math.cos(rad)
            const y1 = center + (radius - 3) * Math.sin(rad)
            const x2 = center + radius * Math.cos(rad)
            const y2 = center + radius * Math.sin(rad)
            return (
              <line
                key={ang}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={ang === 0 ? '#ef4444' : 'rgba(255, 255, 255, 0.2)'}
                strokeWidth={ang % 90 === 0 ? 1.5 : 1}
              />
            )
          })}

          {/* Inner concentric ring */}
          <circle
            cx={center}
            cy={center}
            r={radius * 0.6}
            fill="none"
            stroke="rgba(56, 189, 248, 0.1)"
            strokeWidth="1"
            strokeDasharray="2 2"
          />

          {/* Rotating Vector Needle (rotates around center) */}
          <g
            style={{
              transformOrigin: `${center}px ${center}px`,
              transform: `rotate(${directionDegrees}deg)`,
              transition: 'transform 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          >
            {/* North-pointing arrow head */}
            <polygon
              points={`${center},${center - radius + 14} ${center - 4},${center - 4} ${center + 4},${center - 4}`}
              fill="#38bdf8"
              filter="drop-shadow(0 0 4px #38bdf8)"
            />
            {/* Tail needle */}
            <line
              x1={center}
              y1={center - 4}
              x2={center}
              y2={center + radius * 0.45}
              stroke="rgba(255, 255, 255, 0.4)"
              strokeWidth="1.5"
            />
            {/* Center Pivot Pin */}
            <circle cx={center} cy={center} r={3} fill="#f8fafc" />
          </g>
        </svg>

        {/* Bottom floating speed badge */}
        <div
          style={{
            position: 'absolute',
            bottom: '4px',
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'rgba(15, 23, 42, 0.9)',
            border: '1px solid rgba(56, 189, 248, 0.3)',
            borderRadius: '4px',
            padding: '1px 6px',
            fontSize: '0.65rem',
            fontFamily: 'monospace',
            color: '#38bdf8',
            fontWeight: 700,
            whiteSpace: 'nowrap',
          }}
        >
          {directionDegrees}° {cardinal}
        </div>
      </div>

      {/* Speed Readouts */}
      <div style={{ marginTop: '8px', textAlign: 'center' }}>
        <div style={{ fontSize: '1.25rem', fontWeight: 800, color: isGale ? '#ef4444' : isSquall ? '#f59e0b' : '#f8fafc', lineHeight: 1 }}>
          {speedKmh} <span style={{ fontSize: '0.72rem', color: '#94a3b8' }}>km/h</span>
        </div>
        <div style={{ fontSize: '0.66rem', color: '#94a3b8', marginTop: '2px', fontFamily: 'monospace' }}>
          {speedKnots} kts · Yamartino Vector Avg
        </div>
      </div>
    </div>
  )
}
