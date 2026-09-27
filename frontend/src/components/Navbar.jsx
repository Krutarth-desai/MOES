import React from 'react'
import { WeatherVariables, VariableMetadata } from '../types'
import { CloudLightning, Sliders, Activity } from 'lucide-react'

export default function Navbar({
  selectedVariable,
  onVariableChange,
  selectedLeadTime,
  onLeadTimeChange,
  activeRegime,
}) {
  return (
    <header className="navbar">
      <div className="brand-section">
        <div className="brand-badge">MOES</div>
        <div>
          <div className="brand-title">Hybrid AI–NWP Multi-Model Blending System</div>
          <div className="brand-sub">Operational Prototype · India Meteorological Department (IMD) Benchmark</div>
        </div>
      </div>

      <div className="header-controls">
        {/* Active Regime Pill */}
        {activeRegime && (
          <div className="control-pill" title={activeRegime.synoptic_summary}>
            <Activity size={14} style={{ marginRight: '6px', color: '#38bdf8' }} />
            <span style={{ fontSize: '0.8rem', color: '#94a3b8', marginRight: '4px' }}>Regime:</span>
            <strong style={{ color: '#38bdf8' }}>{activeRegime.regime_name}</strong>
          </div>
        )}

        {/* Variable Selector */}
        <div className="control-pill">
          <Sliders size={14} style={{ marginRight: '6px', color: '#f59e0b' }} />
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', marginRight: '4px' }}>Variable:</span>
          <select
            className="control-select"
            value={selectedVariable}
            onChange={(e) => onVariableChange(e.target.value)}
          >
            {Object.entries(VariableMetadata).map(([key, meta]) => (
              <option key={key} value={key}>
                {meta.label} ({meta.unit})
              </option>
            ))}
          </select>
        </div>

        {/* Lead Time Selector */}
        <div className="control-pill">
          <CloudLightning size={14} style={{ marginRight: '6px', color: '#10b981' }} />
          <span style={{ fontSize: '0.8rem', color: '#94a3b8', marginRight: '4px' }}>Lead Time:</span>
          <select
            className="control-select"
            value={selectedLeadTime}
            onChange={(e) => onLeadTimeChange(Number(e.target.value))}
          >
            <option value={24}>T+24h (Day 1)</option>
            <option value={48}>T+48h (Day 2)</option>
            <option value={72}>T+72h (Day 3)</option>
            <option value={96}>T+96h (Day 4)</option>
            <option value={120}>T+120h (Day 5)</option>
            <option value={168}>T+168h (Day 7)</option>
          </select>
        </div>
      </div>
    </header>
  )
}
