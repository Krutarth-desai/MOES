import React from 'react'
import {
  CloudLightning,
  Sliders,
  Activity,
  Monitor,
  Play,
  RotateCw,
  MapPin,
  Flame,
  BarChart3,
  Layers,
  Map,
  AlertTriangle,
  History,
  FileText,
  Play,
} from 'lucide-react'
import { WeatherVariables, VariableMetadata } from '../types'

export default function Navbar({
  selectedVariable,
  onVariableChange,
  selectedLeadTime,
  onLeadTimeChange,
  selectedStation,
  stations = [],
  onStationChange,
  activeRegime,
  projectorMode,
  onToggleProjectorMode,
  activeSection,
  onSectionClick,
  onRunPipeline,
  isRunningPipeline,
}) {
  const navSections = [
    { id: 'demo-mode', label: '★ Pipeline Simulation', icon: Play },
    { id: 'overview', label: '1. Overview', icon: Activity },
    { id: 'live-forecast', label: '2. Live Forecast', icon: CloudLightning },
    { id: 'comparison', label: '3. Comparison', icon: BarChart3 },
    { id: 'weights', label: '4. Adaptive Weights', icon: Layers },
    { id: 'geo-map', label: '5. Weight Map', icon: Map },
    { id: 'extreme-weather', label: '6. Extreme Weather', icon: AlertTriangle },
    { id: 'backtesting', label: '7. Backtesting', icon: History },
    { id: 'forecast-details', label: '8. Forecast Details', icon: FileText },
  ]

  return (
    <header className="navbar-container" style={{ position: 'sticky', top: 0, zIndex: 1200 }}>
      {/* Top Header Bar */}
      <div className="navbar" style={{ padding: '0.6rem 1.25rem', borderBottom: '1px solid var(--border-color)' }}>
        <div className="brand-section" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div
            className="brand-badge"
            style={{
              background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
              color: '#fff',
              fontWeight: 800,
              fontSize: '0.85rem',
              padding: '6px 10px',
              borderRadius: '8px',
              letterSpacing: '1px',
              boxShadow: '0 2px 8px rgba(2, 132, 199, 0.4)',
            }}
          >
            MoES · IMD
          </div>
          <div>
            <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.02em', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>Hybrid AI–NWP Multi-Model Forecast Blending System</span>
              <span
                style={{
                  background: 'rgba(56, 189, 248, 0.15)',
                  color: '#38bdf8',
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '12px',
                  border: '1px solid rgba(56, 189, 248, 0.3)',
                }}
              >
                LIVE OPERATIONAL PROTOTYPE
              </span>
            </div>
            <div style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
              Ministry of Earth Sciences · IMD Benchmark Multi-Model Consensus Engine
            </div>
          </div>
        </div>

        {/* Global Controls */}
        <div className="header-controls" style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          {/* Active Regime Pill */}
          {activeRegime && (
            <div
              className="control-pill"
              title={activeRegime.synoptic_summary || activeRegime.atmospheric_situation}
              style={{
                background: 'rgba(15, 23, 42, 0.85)',
                border: '1px solid rgba(56, 189, 248, 0.3)',
                padding: '4px 10px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <Activity size={13} color="#38bdf8" />
              <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Regime:</span>
              <strong style={{ fontSize: '0.78rem', color: '#38bdf8' }}>
                {activeRegime.regime_name || activeRegime.diagnosed_regime}
              </strong>
            </div>
          )}

          {/* Station / Location Filter */}
          <div
            className="control-pill"
            style={{
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid var(--border-color)',
              padding: '4px 8px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <MapPin size={13} color="#38bdf8" />
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Station:</span>
            <select
              className="control-select"
              value={selectedStation?.name || ''}
              onChange={(e) => {
                const found = stations.find((s) => s.name === e.target.value)
                if (found) onStationChange(found)
              }}
              style={{
                background: 'transparent',
                color: '#f8fafc',
                border: 'none',
                fontSize: '0.75rem',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              {stations.map((st) => (
                <option key={st.name} value={st.name} style={{ background: '#0f172a', color: '#fff' }}>
                  {st.name} ({st.region_type?.split(' ')[0] || 'Zone'})
                </option>
              ))}
            </select>
          </div>

          {/* Variable Selector */}
          <div
            className="control-pill"
            style={{
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid var(--border-color)',
              padding: '4px 8px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <Sliders size={13} color="#f59e0b" />
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Variable:</span>
            <select
              className="control-select"
              value={selectedVariable}
              onChange={(e) => onVariableChange(e.target.value)}
              style={{
                background: 'transparent',
                color: '#f8fafc',
                border: 'none',
                fontSize: '0.75rem',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              {Object.entries(VariableMetadata).map(([key, meta]) => (
                <option key={key} value={key} style={{ background: '#0f172a', color: '#fff' }}>
                  {meta.label} ({meta.unit})
                </option>
              ))}
            </select>
          </div>

          {/* Lead Time Selector */}
          <div
            className="control-pill"
            style={{
              background: 'rgba(15, 23, 42, 0.85)',
              border: '1px solid var(--border-color)',
              padding: '4px 8px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
            }}
          >
            <CloudLightning size={13} color="#10b981" />
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Lead:</span>
            <select
              className="control-select"
              value={selectedLeadTime}
              onChange={(e) => onLeadTimeChange(Number(e.target.value))}
              style={{
                background: 'transparent',
                color: '#f8fafc',
                border: 'none',
                fontSize: '0.75rem',
                fontWeight: 600,
                outline: 'none',
                cursor: 'pointer',
              }}
            >
              <option value={6} style={{ background: '#0f172a', color: '#fff' }}>T+6h (Nowcast/Short)</option>
              <option value={12} style={{ background: '#0f172a', color: '#fff' }}>T+12h (Half-Day)</option>
              <option value={24} style={{ background: '#0f172a', color: '#fff' }}>T+24h (Day 1)</option>
              <option value={48} style={{ background: '#0f172a', color: '#fff' }}>T+48h (Day 2)</option>
              <option value={72} style={{ background: '#0f172a', color: '#fff' }}>T+72h (Day 3)</option>
              <option value={96} style={{ background: '#0f172a', color: '#fff' }}>T+96h (Day 4)</option>
              <option value={120} style={{ background: '#0f172a', color: '#fff' }}>T+120h (Day 5)</option>
              <option value={168} style={{ background: '#0f172a', color: '#fff' }}>T+168h (Day 7)</option>
            </select>
          </div>

          {/* Run Pipeline Button */}
          <button
            onClick={onRunPipeline}
            disabled={isRunningPipeline}
            style={{
              background: isRunningPipeline ? 'rgba(56, 189, 248, 0.2)' : 'linear-gradient(135deg, #0284c7, #2563eb)',
              color: '#fff',
              border: 'none',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '0.75rem',
              fontWeight: 700,
              cursor: isRunningPipeline ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              boxShadow: '0 2px 6px rgba(2, 132, 199, 0.4)',
            }}
          >
            {isRunningPipeline ? (
              <>
                <RotateCw size={13} className="spin-animation" />
                <span>Running...</span>
              </>
            ) : (
              <>
                <Play size={13} />
                <span>Execute Blend</span>
              </>
            )}
          </button>

          {/* Pipeline Simulation Button */}
          <button
            onClick={() => onSectionClick('demo-mode')}
            title="Open Operational Pipeline Simulation"
            style={{
              background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
              color: '#ffffff',
              border: 'none',
              padding: '6px 12px',
              borderRadius: '8px',
              fontSize: '0.74rem',
              fontWeight: 800,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              boxShadow: '0 2px 8px rgba(2, 132, 199, 0.4)',
              transition: 'all 0.2s ease',
            }}
          >
            <Play size={13} />
            <span>Simulation</span>
          </button>

          {/* Projector Mode Toggle */}
          <button
            onClick={onToggleProjectorMode}
            title="Toggle high-contrast large-format presentation mode for auditorium projectors"
            style={{
              background: projectorMode ? '#f59e0b' : 'rgba(30, 41, 59, 0.8)',
              color: projectorMode ? '#0f172a' : '#cbd5e1',
              border: `1px solid ${projectorMode ? '#f59e0b' : 'var(--border-color)'}`,
              padding: '6px 10px',
              borderRadius: '8px',
              fontSize: '0.72rem',
              fontWeight: 700,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              transition: 'all 0.2s ease',
            }}
          >
            <Monitor size={13} />
            <span>{projectorMode ? 'Projector Mode: ON' : 'Projector Mode'}</span>
          </button>
        </div>
      </div>

      {/* Presentation Section Tabs Sub-Header */}
      <nav
        style={{
          background: 'rgba(15, 23, 42, 0.95)',
          backdropFilter: 'blur(10px)',
          borderBottom: '1px solid var(--border-color)',
          padding: '0.35rem 1.25rem',
          display: 'flex',
          gap: '6px',
          overflowX: 'auto',
        }}
      >
        {navSections.map((sec) => {
          const Icon = sec.icon
          const isActive = activeSection === sec.id
          return (
            <button
              key={sec.id}
              onClick={() => onSectionClick(sec.id)}
              style={{
                background: isActive ? 'var(--accent-blue)' : 'transparent',
                color: isActive ? '#ffffff' : '#94a3b8',
                border: 'none',
                padding: '5px 10px',
                borderRadius: '6px',
                fontSize: '0.74rem',
                fontWeight: isActive ? 700 : 500,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                whiteSpace: 'nowrap',
                transition: 'all 0.15s ease',
              }}
            >
              <Icon size={12} color={isActive ? '#ffffff' : '#64748b'} />
              <span>{sec.label}</span>
            </button>
          )
        })}
      </nav>
    </header>
  )
}
