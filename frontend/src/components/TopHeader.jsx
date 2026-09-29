import React from 'react'
import {
  Menu,
  Activity,
  Sliders,
  CloudLightning,
  Play,
  RotateCw,
  Monitor,
  MapPin,
  ChevronRight,
  Layers,
  Sparkles,
  LogOut,
  User,
} from 'lucide-react'
import { WeatherVariables, VariableMetadata } from '../types'

export const SUB_OPTIONS_MAP = {
  overview: [
    { id: 'all', label: 'All Overview', targetId: 'overview' },
    { id: 'forecast-summary', label: 'Forecast & Consensus', targetId: 'overview-forecast' },
    { id: 'atmospheric', label: 'Atmospheric Indicators', targetId: 'overview-atmospheric' },
    { id: 'hazards-summary', label: 'Active Hazards', targetId: 'overview-hazards' },
    { id: 'verification', label: 'Verification & Skill', targetId: 'overview-verification' },
    { id: 'pipeline', label: 'Pipeline Telemetry', targetId: 'overview-pipeline' },
  ],
  forecast: [
    { id: 'all', label: 'All Forecast Views', targetId: 'live-forecast' },
    { id: 'timeline', label: 'Lead-Time Scrubber', targetId: 'forecast-timeline' },
    { id: 'meteograms', label: 'Multi-Variable Meteograms', targetId: 'forecast-meteograms' },
    { id: 'contributions', label: 'Itemized Model Math (Wᵢ × Fᵢ)', targetId: 'forecast-contributions' },
    { id: 'wind-vector', label: 'Yamartino Wind Vector', targetId: 'forecast-wind' },
    { id: 'pipeline', label: '12-Step Pipeline Telemetry', targetId: 'forecast-pipeline' },
  ],
  models: [
    { id: 'all', label: 'All Model Analytics', targetId: 'comparison' },
    { id: 'architecture-flow', label: 'Blending Architecture Flow', targetId: 'models-flow' },
    { id: 'skill-matrix', label: 'Skill Scorecards & Matrix', targetId: 'models-skill' },
    { id: 'adaptive-weights', label: 'Adaptive Softmax Weights', targetId: 'models-weights' },
    { id: 'explainability', label: 'Explainability & Audit', targetId: 'models-explain' },
  ],
  'weight-map': [
    { id: 'all', label: 'Interactive GIS Map', targetId: 'geo-map' },
    { id: 'dominant', label: 'Dominant Model Layer', mapLayer: 'dominant_model' },
    { id: 'weights-layer', label: 'Model Weights Layer', mapLayer: 'weight_distribution' },
    { id: 'forecast-layer', label: 'Forecast Values Layer', mapLayer: 'forecast_values' },
    { id: 'hazards-layer', label: 'Extreme Hazard Layer', mapLayer: 'extreme_weather' },
  ],
  hazards: [
    { id: 'all', label: 'All Hazard Guidance', targetId: 'extreme-weather' },
    { id: 'active-alerts', label: 'Active IMD Warnings', targetId: 'hazards-active' },
    { id: 'thresholds', label: 'Threshold Criteria & Protocols', targetId: 'hazards-thresholds' },
  ],
  verify: [
    { id: 'all', label: 'All Verification', targetId: 'backtesting' },
    { id: 'backtest', label: 'Rolling-Origin Backtest', targetId: 'verify-backtest' },
    { id: 'errors', label: 'Historical Error Curves', targetId: 'verify-errors' },
    { id: 'provenance', label: 'Data Provenance & Zero Leakage', targetId: 'verify-provenance' },
  ],
  'demo-mode': [
    { id: 'all', label: '7-Stage Pipeline Flow', targetId: 'demo-mode' },
    { id: 'scenario1', label: 'Scenario 1: Monsoon Convective' },
    { id: 'scenario2', label: 'Scenario 2: Heatwave Subsidence' },
  ],
}

const SECTION_LABELS = {
  overview: 'Overview',
  forecast: 'Forecast',
  models: 'Models',
  'weight-map': 'Weight Map',
  hazards: 'Hazards',
  verify: 'Verify',
  'demo-mode': 'Pipeline Simulation',
}

export default function TopHeader({
  activeSection,
  activeSubOption = 'all',
  onSubOptionSelect,
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
  onRunPipeline,
  isRunningPipeline,
  onOpenMobileSidebar,
  user,
  profile,
  onLogout,
}) {
  const currentSubOptions = SUB_OPTIONS_MAP[activeSection] || []
  const sectionTitle = SECTION_LABELS[activeSection] || 'Overview'

  return (
    <header className="top-header-wrapper">
      {/* Upper Control Bar: Global Telemetry & Filters */}
      <div className="top-header-controls-bar">
        {/* Left: Mobile Menu Trigger & Section Title Crumb */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            onClick={onOpenMobileSidebar}
            className="mobile-menu-btn"
            title="Open navigation menu"
            aria-label="Open navigation menu"
          >
            <Menu size={20} />
          </button>

          <div className="header-breadcrumbs">
            <span className="crumb-system">MoES / IMD</span>
            <ChevronRight size={13} color="#64748b" />
            <span className="crumb-section">{sectionTitle}</span>
          </div>
        </div>

        {/* Right: Global Operational Filters & Triggers */}
        <div className="header-controls">
          {/* Active Regime Pill */}
          {activeRegime && (
            <div
              className="control-pill regime-pill"
              title={activeRegime.synoptic_summary || activeRegime.atmospheric_situation}
            >
              <Activity size={13} color="#2563EB" />
              <span style={{ fontSize: '0.74rem', color: '#64748B' }}>Regime:</span>
              <strong style={{ fontSize: '0.78rem', color: '#1E3A8A' }}>
                {activeRegime.regime_name || activeRegime.diagnosed_regime}
              </strong>
            </div>
          )}

          {/* Station / Location Filter */}
          <div className="control-pill">
            <MapPin size={13} color="#2563EB" />
            <span style={{ fontSize: '0.74rem', color: '#64748B' }}>Station:</span>
            <select
              className="control-select"
              value={selectedStation?.name || ''}
              onChange={(e) => {
                const found = stations.find((s) => s.name === e.target.value)
                if (found) onStationChange(found)
              }}
            >
              {stations.map((st) => (
                <option key={st.name} value={st.name}>
                  {st.name} ({st.region_type?.split(' ')[0] || 'Zone'})
                </option>
              ))}
            </select>
          </div>

          {/* Variable Selector */}
          <div className="control-pill">
            <Sliders size={13} color="#2563EB" />
            <span style={{ fontSize: '0.74rem', color: '#64748B' }}>Variable:</span>
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
            <CloudLightning size={13} color="#0284C7" />
            <span style={{ fontSize: '0.74rem', color: '#657886' }}>Lead:</span>
            <select
              className="control-select"
              value={selectedLeadTime}
              onChange={(e) => onLeadTimeChange(Number(e.target.value))}
            >
              <option value={6}>T+6h (Nowcast/Short)</option>
              <option value={12}>T+12h (Half-Day)</option>
              <option value={24}>T+24h (Day 1)</option>
              <option value={48}>T+48h (Day 2)</option>
              <option value={72}>T+72h (Day 3)</option>
              <option value={96}>T+96h (Day 4)</option>
              <option value={120}>T+120h (Day 5)</option>
              <option value={168}>T+168h (Day 7)</option>
            </select>
          </div>

          {/* Run Pipeline Button */}
          <button
            onClick={onRunPipeline}
            disabled={isRunningPipeline}
            className="action-btn-primary"
            title="Execute automated 12-step meteorological forecast blending pipeline"
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

          {/* Projector Mode Toggle */}
          <button
            onClick={onToggleProjectorMode}
            className={`action-btn-secondary ${projectorMode ? 'active' : ''}`}
            title="Toggle high-contrast large-format presentation mode for auditorium projectors"
          >
            <Monitor size={13} />
            <span>{projectorMode ? 'Projector: ON' : 'Projector'}</span>
          </button>

          {/* User Profile & Logout Pill */}
          {(user || profile) && (
            <div
              className="control-pill user-profile-pill"
              style={{
                background: 'rgba(255, 255, 255, 0.85)',
                border: '1px solid rgba(203, 213, 225, 0.8)',
                padding: '3px 8px 3px 6px',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                marginLeft: '4px',
              }}
            >
              {profile?.avatar_url || user?.user_metadata?.avatar_url || user?.user_metadata?.picture ? (
                <img
                  src={profile?.avatar_url || user?.user_metadata?.avatar_url || user?.user_metadata?.picture}
                  alt="User Avatar"
                  style={{
                    width: '22px',
                    height: '22px',
                    borderRadius: '50%',
                    objectFit: 'cover',
                    border: '1px solid #2563EB',
                  }}
                />
              ) : (
                <div
                  style={{
                    width: '22px',
                    height: '22px',
                    borderRadius: '50%',
                    background: 'linear-gradient(135deg, #1E3A8A, #2563EB)',
                    color: '#ffffff',
                    fontSize: '0.7rem',
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {(profile?.full_name || user?.email || 'U').charAt(0).toUpperCase()}
                </div>
              )}
              <span
                style={{
                  fontSize: '0.74rem',
                  fontWeight: 600,
                  color: '#1E293B',
                  maxWidth: '110px',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                title={profile?.full_name || user?.email}
              >
                {profile?.full_name || user?.email?.split('@')[0]}
              </span>
              {onLogout && (
                <button
                  onClick={onLogout}
                  title="Sign Out of MOES System"
                  style={{
                    background: 'rgba(239, 68, 68, 0.1)',
                    color: '#DC2626',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    borderRadius: '5px',
                    padding: '2px 6px',
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '3px',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <LogOut size={11} />
                  <span>Logout</span>
                </button>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Secondary Horizontal Sub-Navigation Bar (Directly below Global Controls) */}
      <nav className="top-subnav-bar" aria-label="Secondary Navigation">
        <div className="subnav-indicator-label">
          <Layers size={13} color="#2563EB" />
          <span>{sectionTitle.toUpperCase()} VIEWS:</span>
        </div>

        <div className="subnav-pills-list">
          {currentSubOptions.map((sub) => {
            const isActive = activeSubOption === sub.id
            return (
              <button
                key={sub.id}
                onClick={() => onSubOptionSelect(sub.id, sub.targetId, sub.mapLayer)}
                className={`subnav-pill ${isActive ? 'active' : ''}`}
              >
                <span>{sub.label}</span>
              </button>
            )
          })}
        </div>
      </nav>
    </header>
  )
}
