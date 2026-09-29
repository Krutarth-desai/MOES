import React from 'react'
import {
  Activity,
  Sliders,
  CloudLightning,
  Play,
  RotateCw,
  MapPin,
  Layers,
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
  sidebarCollapsed,
}) {
  const currentSubOptions = SUB_OPTIONS_MAP[activeSection] || []
  const sectionTitle = SECTION_LABELS[activeSection] || 'Overview'

  return (
    <header className="top-header-wrapper">
      <style>{`
        .th-grid-container {
          display: grid;
          width: 100%;
          gap: 12px;
          align-items: center;
          /* Desktop layout: 3 main column areas */
          grid-template-columns: auto 1fr auto;
          grid-template-areas: 
            "brand spacer top-controls"
            "brand spacer bottom-controls";
        }
        
        .th-brand { grid-area: brand; display: flex; flex-direction: column; gap: 2px; padding-left: 4px; }
        .th-spacer { grid-area: spacer; }
        
        /* Desktop Rows */
        .th-top-controls {
          grid-area: top-controls;
          display: flex;
          align-items: center;
          gap: 12px;
          justify-content: flex-end;
        }
        .th-bottom-controls {
          grid-area: bottom-controls;
          display: flex;
          align-items: center;
          gap: 12px;
          justify-content: flex-end;
        }

        /* Mobile/Collapsed Layout (width < 1100px) */
        @media (max-width: 1100px) {
          .th-grid-container {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-end;
          }
          .th-brand {
            margin-right: auto;
          }
          .th-top-controls, .th-bottom-controls {
            display: contents; /* Flattens them so their children participate in the main flex container */
          }
          /* Control the order on mobile to match user request */
          .th-item-mumbai { order: 1; }
          .th-item-precip { order: 2; }
          .th-item-horizon { order: 3; }
          .th-item-regime { order: 4; }
          .th-item-execute { order: 5; }
          .th-item-operational { order: 6; }
        }
      `}</style>
      <div className="top-header-main-content th-grid-container">
        
        <div className="th-brand">
            <div className="gradient-brand-text" style={{
              fontFamily: "'Outfit', sans-serif",
              fontSize: '2rem',
              fontWeight: 900,
              lineHeight: 1.1,
              letterSpacing: '-0.02em',
            }}>AtmoCast</div>
            <div style={{
              fontFamily: "'Outfit', sans-serif",
              fontSize: '0.7rem',
              color: '#64748B',
              fontWeight: 700,
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              marginTop: '2px',
            }}>Forecast Blending System</div>
        </div>
        
        <div className="th-spacer"></div>

        {/* TOP ROW CONTROLS (Desktop) */}
        <div className="th-top-controls">
          {activeRegime && (
            <div className="control-pill regime-pill th-item-regime" title={activeRegime.synoptic_summary || activeRegime.atmospheric_situation}>
              <Activity size={16} color="#3B82F6" />
              <span style={{ color: '#64748B' }}>Regime:</span>
              <strong style={{ color: '#0F172A' }}>{activeRegime.regime_name || activeRegime.diagnosed_regime}</strong>
            </div>
          )}
          
          <div className="control-pill station-pill th-item-mumbai">
            <MapPin size={16} color="#3B82F6" />
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
                  {st.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* BOTTOM ROW CONTROLS (Desktop) */}
        <div className="th-bottom-controls">
          <div className="control-pill th-item-precip">
            <Sliders size={16} color="#3B82F6" />
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
          
          <div className="control-pill th-item-horizon">
            <CloudLightning size={16} color="#3B82F6" />
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

          <button
            onClick={onRunPipeline}
            disabled={isRunningPipeline}
            className="action-btn-primary th-item-execute"
            style={{ padding: '8px 20px', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '8px', height: '36px', transition: 'all 0.2s ease', boxShadow: '0 2px 4px rgba(37, 99, 235, 0.1)' }}
            title="Execute automated 12-step meteorological forecast blending pipeline"
          >
            {isRunningPipeline ? (
              <>
                <RotateCw size={16} className="spin-animation" />
                <span>Running...</span>
              </>
            ) : (
              <>
                <Play size={16} />
                <span>Execute Blend</span>
              </>
            )}
          </button>

          <div className="status-chip-small th-item-operational" style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '0 10px', height: '32px', background: 'rgba(16, 185, 129, 0.08)', border: '1px solid rgba(16, 185, 129, 0.2)', borderRadius: '6px', fontSize: '11px', fontWeight: 700, color: '#047857', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
            <span className="status-dot" style={{ width: '6px', height: '6px', background: '#10B981', borderRadius: '50%', boxShadow: '0 0 6px rgba(16, 185, 129, 0.5)' }}></span>
            Operational
          </div>
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
