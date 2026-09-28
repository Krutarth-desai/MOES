import React, { useState, useEffect } from 'react'
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle,
  Clock,
  Gauge,
  Sliders,
  Sparkles,
  Info,
  MapPin,
  TrendingUp,
} from 'lucide-react'
import apiService from '../services/api'

export default function AlertsPanel({ alerts = [], leadTimeHours = 24 }) {
  const [activeTab, setActiveTab] = useState('scenarios') // 'scenarios' | 'operational'
  const [scenarios, setScenarios] = useState([])
  const [selectedScenarioKey, setSelectedScenarioKey] = useState('heavy_rainfall')
  const [activeScenario, setActiveScenario] = useState(null)
  const [guidanceList, setGuidanceList] = useState([])
  const [loading, setLoading] = useState(false)

  // Load scenarios on mount
  useEffect(() => {
    async function loadScenarios() {
      try {
        const data = await apiService.getScenarios()
        setScenarios(data)
        if (data.length > 0) {
          const defaultSc = data.find((s) => s.category === 'heavy_rainfall') || data[0]
          setSelectedScenarioKey(defaultSc.category)
          setActiveScenario(defaultSc)
        }
      } catch (err) {
        console.warn('Could not load scenarios from API, fallback to default', err)
      }
    }
    loadScenarios()
  }, [])

  // Load operational structured guidance when leadTimeHours changes
  useEffect(() => {
    async function loadGuidance() {
      setLoading(true)
      try {
        const data = await apiService.getExtremeGuidance({ leadTimeHours })
        setGuidanceList(data)
      } catch (err) {
        console.warn('Could not load structured guidance from API', err)
      } finally {
        setLoading(false)
      }
    }
    loadGuidance()
  }, [leadTimeHours])

  const handleSelectScenario = async (catKey) => {
    setSelectedScenarioKey(catKey)
    try {
      const sc = await apiService.getScenarioByName(catKey)
      setActiveScenario(sc)
    } catch (err) {
      console.error('Failed to load scenario:', err)
      const found = scenarios.find((s) => s.category === catKey)
      if (found) setActiveScenario(found)
    }
  }

  const getBadgeClass = (category) => {
    const c = (category || '').toLowerCase()
    switch (c) {
      case 'red':
        return 'badge-red'
      case 'orange':
        return 'badge-orange'
      case 'yellow':
        return 'badge-yellow'
      default:
        return 'badge-green'
    }
  }

  const getBorderColor = (category) => {
    const c = (category || '').toLowerCase()
    switch (c) {
      case 'red':
        return '#ef4444'
      case 'orange':
        return '#f97316'
      case 'yellow':
        return '#eab308'
      default:
        return '#22c55e'
    }
  }

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Header */}
      <div className="card-header" style={{ flexWrap: 'wrap', gap: '0.5rem' }}>
        <div className="card-title">
          <ShieldAlert size={18} color="#ef4444" />
          <span>Extreme Weather Guidance Engine</span>
        </div>
        <div style={{ display: 'flex', gap: '4px', background: '#0f172a', padding: '2px', borderRadius: '6px' }}>
          <button
            onClick={() => setActiveTab('scenarios')}
            style={{
              background: activeTab === 'scenarios' ? 'var(--accent-blue)' : 'transparent',
              color: activeTab === 'scenarios' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '4px 8px',
              fontSize: '0.72rem',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Sparkles size={12} />
            Test Scenarios
          </button>
          <button
            onClick={() => setActiveTab('operational')}
            style={{
              background: activeTab === 'operational' ? 'var(--accent-blue)' : 'transparent',
              color: activeTab === 'operational' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '4px 8px',
              fontSize: '0.72rem',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Sliders size={12} />
            Live Stations ({guidanceList.length})
          </button>
        </div>
      </div>

      <div className="card-body" style={{ overflowY: 'auto', maxHeight: '460px', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {/* TAB 1: DEMONSTRATION SCENARIOS */}
        {activeTab === 'scenarios' && (
          <div>
            {/* Scenario Buttons */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px', marginBottom: '0.75rem' }}>
              {[
                { id: 'heavy_rainfall', label: '🌧️ Heavy Rainfall', sub: 'Mumbai (135.5 mm)' },
                { id: 'heat_wave', label: '🔥 Heat Wave', sub: 'Nagpur (46.3 °C)' },
                { id: 'high_wind', label: '💨 High Wind', sub: 'Bhubaneswar (78.2 km/h)' },
                { id: 'normal_conditions', label: '🌤️ Normal Weather', sub: 'Bengaluru (3.1 mm)' },
              ].map((btn) => (
                <button
                  key={btn.id}
                  onClick={() => handleSelectScenario(btn.id)}
                  style={{
                    background: selectedScenarioKey === btn.id ? 'rgba(56, 189, 248, 0.15)' : 'rgba(30, 41, 59, 0.6)',
                    border: `1px solid ${selectedScenarioKey === btn.id ? 'var(--accent-cyan)' : 'var(--border-color)'}`,
                    borderRadius: '6px',
                    padding: '6px 8px',
                    textAlign: 'left',
                    cursor: 'pointer',
                    color: '#fff',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ fontSize: '0.76rem', fontWeight: 600 }}>{btn.label}</div>
                  <div style={{ fontSize: '0.68rem', color: '#94a3b8' }}>{btn.sub}</div>
                </button>
              ))}
            </div>

            {/* Active Scenario Card */}
            {activeScenario && activeScenario.guidance ? (
              <GuidanceCard guidance={activeScenario.guidance} description={activeScenario.description} />
            ) : (
              <div style={{ textAlign: 'center', padding: '1rem', color: '#94a3b8', fontSize: '0.8rem' }}>
                Loading scenario guidance...
              </div>
            )}
          </div>
        )}

        {/* TAB 2: LIVE OPERATIONAL GUIDANCES */}
        {activeTab === 'operational' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {guidanceList.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
                <CheckCircle size={32} color="#10b981" style={{ margin: '0 auto 8px' }} />
                <p>No active severe meteorological advisories at +{leadTimeHours}h lead time.</p>
              </div>
            ) : (
              guidanceList.map((g) => (
                <GuidanceCard key={g.event_id} guidance={g} />
              ))
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function GuidanceCard({ guidance, description }) {
  const cat = (guidance.recommended_alert_category || 'green').toLowerCase()
  const borderColor = cat === 'red' ? '#ef4444' : cat === 'orange' ? '#f97316' : cat === 'yellow' ? '#eab308' : '#22c55e'
  const risk = guidance.derived_risk_indicator || {}
  const thresh = guidance.alert_threshold || {}

  return (
    <div
      style={{
        background: 'rgba(30, 41, 59, 0.6)',
        border: '1px solid var(--border-color)',
        borderRadius: '8px',
        padding: '0.85rem',
        borderLeft: `4px solid ${borderColor}`,
        display: 'flex',
        flexDirection: 'column',
        gap: '0.6rem',
      }}
    >
      {/* Top Banner: Alert Category, Severity, Lead Time */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '4px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span className={`badge-${cat}`}>
            {cat.toUpperCase()} {cat === 'green' ? 'CONDITION' : 'ALERT'}
          </span>
          <span style={{ fontSize: '0.72rem', color: '#94a3b8', background: '#0f172a', padding: '2px 6px', borderRadius: '4px' }}>
            Severity: <strong>{(guidance.severity_level || 'NONE').toUpperCase()}</strong>
          </span>
        </div>
        <span style={{ fontSize: '0.72rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '3px' }}>
          <Clock size={12} />
          +{guidance.lead_time_hours}h ({guidance.expected_start_time ? guidance.expected_start_time.slice(5, 16).replace('T', ' ') : ''})
        </span>
      </div>

      {/* Location & Headline */}
      <div>
        <h4 style={{ fontSize: '0.88rem', fontWeight: 600, color: '#f8fafc', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <MapPin size={13} color="var(--accent-cyan)" />
          {guidance.location_name}
          <span style={{ fontSize: '0.72rem', color: '#94a3b8', fontWeight: 400 }}>
            ({guidance.affected_region})
          </span>
        </h4>
        {description && (
          <p style={{ fontSize: '0.73rem', color: '#cbd5e1', marginTop: '2px', fontStyle: 'italic' }}>
            {description}
          </p>
        )}
      </div>

      {/* THREE EXPLICIT SECTORS: FORECAST VALUE vs RISK INDICATOR vs ALERT THRESHOLD */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px', marginTop: '2px' }}>
        {/* 1. Forecast Value */}
        <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '6px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
            1. Forecast Value
          </div>
          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: 'var(--accent-cyan)' }}>
            {guidance.forecast_value} <span style={{ fontSize: '0.7rem', fontWeight: 500 }}>{guidance.forecast_unit}</span>
          </div>
          <div style={{ fontSize: '0.65rem', color: '#64748b' }}>
            Multi-model blend
          </div>
        </div>

        {/* 2. Derived Risk Indicator */}
        <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '6px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
            2. Risk Score
          </div>
          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: borderColor }}>
            {Math.round((risk.probability_score || 0) * 100)}%
            <span style={{ fontSize: '0.68rem', fontWeight: 500, color: '#94a3b8', marginLeft: '4px' }}>
              ({risk.composite_risk_score || 0}/100)
            </span>
          </div>
          <div style={{ fontSize: '0.65rem', color: '#94a3b8' }}>
            {risk.risk_level || 'Low'} Risk
          </div>
        </div>

        {/* 3. Alert Threshold */}
        <div style={{ background: 'rgba(15, 23, 42, 0.7)', padding: '6px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.05)' }}>
          <div style={{ fontSize: '0.65rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.4px' }}>
            3. Alert Cutoff
          </div>
          <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#f8fafc' }}>
            ≥ {thresh.applied_threshold || '--'} <span style={{ fontSize: '0.7rem', fontWeight: 500 }}>{thresh.threshold_unit || ''}</span>
          </div>
          <div style={{ fontSize: '0.65rem', color: '#64748b', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {thresh.threshold_source || 'IMD Standard'}
          </div>
        </div>
      </div>

      {/* Consensus Confidence & Contributing Models */}
      <div style={{ fontSize: '0.7rem', color: '#94a3b8', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '4px' }}>
        <span>
          <strong>Consensus Agreement:</strong> {Math.round((guidance.confidence || 0.8) * 100)}%
        </span>
        <span style={{ display: 'flex', gap: '3px' }}>
          {(guidance.contributing_models || []).map((m) => (
            <span key={m} style={{ background: '#1e293b', padding: '1px 5px', borderRadius: '3px', fontSize: '0.65rem', color: '#cbd5e1' }}>
              {m.replace(' Forecast', '')}
            </span>
          ))}
        </span>
      </div>

      {/* Mandatory Non-deterministic Disclaimer */}
      {risk.disclaimer && (
        <div style={{ fontSize: '0.65rem', color: '#64748b', fontStyle: 'italic', display: 'flex', alignItems: 'flex-start', gap: '4px' }}>
          <Info size={11} style={{ flexShrink: 0, marginTop: '2px' }} />
          <span>{risk.disclaimer}</span>
        </div>
      )}

      {/* IMD Protocol Action Guidance */}
      {guidance.recommended_actions && guidance.recommended_actions.length > 0 && (
        <div style={{ fontSize: '0.72rem', color: '#cbd5e1', background: 'rgba(15, 23, 42, 0.5)', padding: '5px 8px', borderRadius: '5px', borderLeft: '2px solid var(--accent-cyan)' }}>
          <strong>IMD Protocol Guidance:</strong> {guidance.recommended_actions.join(' ')}
        </div>
      )}
    </div>
  )
}
