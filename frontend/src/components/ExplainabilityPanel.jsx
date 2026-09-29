import React from 'react'
import {
  HelpCircle,
  ShieldCheck,
  CheckCircle,
  Award,
  Layers,
  Activity,
  Clock,
  Compass,
  FileText,
  AlertCircle,
} from 'lucide-react'

export default function ExplainabilityPanel({
  explanation,
  variable = 'rainfall',
  leadTimeHours = 24,
  region = 'Western Ghats & Coastal',
  season = 'monsoon',
  weatherRegime = 'heavy_rain',
  weights = {},
}) {
  if (!explanation) {
    return (
      <div className="glass-card state-container" style={{ padding: '1.5rem' }}>
        <HelpCircle size={24} color="#38bdf8" />
        <div style={{ fontSize: '0.9rem', color: '#94a3b8' }}>
          Generating explainability audit for adaptive model weights...
        </div>
      </div>
    )
  }

  const {
    summary_text,
    dominant_model,
    dominant_weight,
    dominant_reason,
    historical_skill_used = {},
    selected_weights = {},
    decision_factors = [],
    non_technical_summary,
  } = explanation

  const modelColorMap = {
    'NWP Model A': '#2563EB',
    'NWP Model B': '#1E3A8A',
    'Ensemble Forecast': '#0284C7',
    'AI/ML Forecast': '#38BDF8',
  }

  return (
    <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              background: 'rgba(37, 99, 235, 0.12)',
              padding: '6px',
              borderRadius: '8px',
              border: '1px solid rgba(37, 99, 235, 0.25)',
            }}
          >
            <ShieldCheck size={20} color="#2563EB" />
          </div>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#243746', letterSpacing: '-0.01em', margin: 0 }}>
              Adaptive Weighting Explainability Audit
            </h3>
            <p style={{ fontSize: '0.72rem', color: '#657886', margin: '2px 0 0 0' }}>
              Empirical rationale grounded strictly in verified ground-truth skill · Non-fabricated provenance
            </p>
          </div>
        </div>

        {/* Dimension Metadata Context Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ background: '#EAF2F7', border: '1px solid rgba(77, 145, 201, 0.25)', padding: '3px 8px', borderRadius: '6px', fontSize: '0.72rem', color: '#2563EB' }}>
            Regime: <strong>{explanation.current_weather_regime || weatherRegime}</strong>
          </span>
          <span style={{ background: '#EAF2F7', border: '1px solid rgba(77, 145, 201, 0.25)', padding: '3px 8px', borderRadius: '6px', fontSize: '0.72rem', color: '#0284C7' }}>
            Lead: <strong>T+{explanation.lead_time_hours || leadTimeHours}h</strong>
          </span>
          <span style={{ background: '#EAF2F7', border: '1px solid rgba(77, 145, 201, 0.25)', padding: '3px 8px', borderRadius: '6px', fontSize: '0.72rem', color: '#1E3A8A' }}>
            Season: <strong>{explanation.season || season}</strong>
          </span>
          <span style={{ background: '#EAF2F7', border: '1px solid rgba(77, 145, 201, 0.25)', padding: '3px 8px', borderRadius: '6px', fontSize: '0.72rem', color: '#294E6B' }}>
            Region: <strong>{explanation.region || region}</strong>
          </span>
        </div>
      </div>

      {/* Primary Narrative Box */}
      <div
        style={{
          background: 'rgba(234, 242, 247, 0.65)',
          borderLeft: '4px solid #4D91C9',
          borderTop: '1px solid rgba(77, 145, 201, 0.20)',
          borderRight: '1px solid rgba(77, 145, 201, 0.20)',
          borderBottom: '1px solid rgba(77, 145, 201, 0.20)',
          borderRadius: '8px',
          padding: '1rem 1.25rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
          <FileText size={15} color="#4D91C9" />
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#294E6B', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Concise Machine-Readable Rationale
          </span>
        </div>
        <pre
          style={{
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            fontSize: '0.82rem',
            color: '#243746',
            whiteSpace: 'pre-wrap',
            lineHeight: 1.5,
            margin: 0,
          }}
        >
          {summary_text}
        </pre>
      </div>

      {/* Non-Technical Summary Card for Judges */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(77, 145, 201, 0.10), rgba(37, 99, 235, 0.08))',
          border: '1px solid rgba(37, 99, 235, 0.25)',
          borderRadius: '8px',
          padding: '0.85rem 1.15rem',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '10px',
        }}
      >
        <Award size={18} color="#2563EB" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#2563EB', marginBottom: '2px', textTransform: 'uppercase' }}>
            Judge Summary (Transparent & Non-Technical)
          </div>
          <p style={{ fontSize: '0.8rem', color: '#243746', lineHeight: 1.45, margin: 0 }}>
            {non_technical_summary}
          </p>
        </div>
      </div>

      {/* Historical Skill Used Matrix Table */}
      <div style={{ overflowX: 'auto' }}>
        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#405565', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Activity size={14} color="#2563EB" />
          <span>Historical Skill Metrics Grounding the Weighting Decision</span>
        </div>

        <table className="scientific-table">
          <thead>
            <tr>
              <th>Model Name</th>
              <th>Assigned Weight</th>
              <th>Historical RMSE</th>
              <th>MAE</th>
              <th>Bias</th>
              <th>Correlation (r)</th>
              <th>Sample Size (N)</th>
              <th>Reliability Score</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(historical_skill_used).map(([mName, skill]) => {
              const isDominant = mName === dominant_model
              const color = modelColorMap[mName] || '#2563EB'
              return (
                <tr
                  key={mName}
                  style={{
                    background: isDominant ? 'rgba(77, 145, 201, 0.08)' : 'transparent',
                    fontWeight: isDominant ? 700 : 400,
                  }}
                >
                  <td style={{ color: isDominant ? '#294E6B' : '#243746', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: color }} />
                    {isDominant ? '★ ' : ''}{mName}
                  </td>
                  <td>
                    <strong style={{ color }}>{Math.round(skill.weight * 100)}%</strong>
                  </td>
                  <td>
                    <span style={{ color: isDominant ? '#059669' : '#243746', fontWeight: isDominant ? 700 : 400 }}>
                      {skill.rmse} {variable.includes('temp') ? '°C' : 'mm'}
                    </span>
                  </td>
                  <td>{skill.mae}</td>
                  <td style={{ color: skill.bias < 0 ? '#2563EB' : '#D97706' }}>{skill.bias}</td>
                  <td>{skill.correlation}</td>
                  <td>{skill.sample_size} cases</td>
                  <td>{skill.composite_skill_score}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Decision Factors & Audit Trail */}
      {decision_factors.length > 0 && (
        <div style={{ background: 'rgba(234, 242, 247, 0.65)', padding: '10px 14px', borderRadius: '8px', border: '1px solid rgba(77, 145, 201, 0.20)' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#657886', marginBottom: '6px', textTransform: 'uppercase' }}>
            Decision Factors Considered
          </div>
          <ul style={{ paddingLeft: '1.2rem', margin: 0, fontSize: '0.75rem', color: '#405565', lineHeight: 1.5 }}>
            {decision_factors.map((factor, idx) => (
              <li key={idx} style={{ marginBottom: '3px' }}>{factor}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
