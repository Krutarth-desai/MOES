import React from 'react'
import { Clock, Play, Pause, ChevronLeft, ChevronRight } from 'lucide-react'

const TIMELINE_STEPS = [
  { hours: 6, label: 'T+6h', desc: 'Nowcast' },
  { hours: 12, label: 'T+12h', desc: 'Half-Day' },
  { hours: 24, label: 'T+24h', desc: 'Day 1' },
  { hours: 48, label: 'T+48h', desc: 'Day 2' },
  { hours: 72, label: 'T+72h', desc: 'Day 3' },
  { hours: 96, label: 'T+96h', desc: 'Day 4' },
  { hours: 120, label: 'T+120h', desc: 'Day 5' },
  { hours: 168, label: 'T+168h', desc: 'Day 7' },
]

export default function ForecastTimelineSlider({
  selectedLeadTime = 24,
  onLeadTimeChange,
}) {
  const currentIndex = TIMELINE_STEPS.findIndex((s) => s.hours === selectedLeadTime)
  const safeIndex = currentIndex >= 0 ? currentIndex : 2

  const handlePrev = () => {
    if (safeIndex > 0) {
      onLeadTimeChange(TIMELINE_STEPS[safeIndex - 1].hours)
    }
  }

  const handleNext = () => {
    if (safeIndex < TIMELINE_STEPS.length - 1) {
      onLeadTimeChange(TIMELINE_STEPS[safeIndex + 1].hours)
    }
  }

  return (
    <div className="forecast-timeline-container glass-card" style={{ padding: '0.85rem 1.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Clock size={16} color="#38bdf8" />
          <span style={{ fontSize: '0.82rem', fontWeight: 800, color: '#f8fafc', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Forecast Synoptic Lead-Time Horizon
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <button
            onClick={handlePrev}
            disabled={safeIndex === 0}
            className="timeline-step-btn"
            title="Step backward in lead-time"
          >
            <ChevronLeft size={14} />
          </button>
          <div style={{ fontSize: '0.78rem', fontWeight: 800, color: '#38bdf8', fontFamily: 'monospace', padding: '2px 8px', background: 'rgba(56, 189, 248, 0.1)', borderRadius: '4px' }}>
            {TIMELINE_STEPS[safeIndex].label} · {TIMELINE_STEPS[safeIndex].desc}
          </div>
          <button
            onClick={handleNext}
            disabled={safeIndex === TIMELINE_STEPS.length - 1}
            className="timeline-step-btn"
            title="Step forward in lead-time"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* Scrub Track */}
      <div className="timeline-track-wrap">
        <div className="timeline-track-line" />
        <div
          className="timeline-track-fill"
          style={{ width: `${(safeIndex / (TIMELINE_STEPS.length - 1)) * 100}%` }}
        />

        <div className="timeline-nodes-row">
          {TIMELINE_STEPS.map((step, idx) => {
            const isActive = step.hours === selectedLeadTime
            const isPast = idx <= safeIndex

            return (
              <button
                key={step.hours}
                onClick={() => onLeadTimeChange(step.hours)}
                className={`timeline-node-btn ${isActive ? 'active' : ''} ${isPast ? 'passed' : ''}`}
                title={`Switch to ${step.label} (${step.desc})`}
              >
                <div className="timeline-node-bullet" />
                <span className="timeline-node-label">{step.label}</span>
                <span className="timeline-node-desc">{step.desc}</span>
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
