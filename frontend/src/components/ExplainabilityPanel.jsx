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
    'NWP Model A': '#0284c7',
    'NWP Model B': '#10b981',
    'Ensemble Forecast': '#f59e0b',
    'AI/ML Forecast': '#8b5cf6',
  }

  return (
    <div className="glass-card" style={{ padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {/* Header Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div
            style={{
              background: 'rgba(56, 189, 248, 0.15)',
              padding: '6px',
              borderRadius: '8px',
              border: '1px solid rgba(56, 189, 248, 0.3)',
            }}
          >
            <ShieldCheck size={20} color="#38bdf8" />
          </div>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 800, color: '#f8fafc', letterSpacing: '-0.01em' }}>
              Adaptive Weighting Explainability Audit
            </h3>
            <p style={{ fontSize: '0.72rem', color: '#94a3b8' }}>
              Empirical rationale grounded strictly in verified ground-truth skill · Non-fabricated provenance
            </p>
          </div>
        </div>

        {/* Dimension Metadata Context Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ background: '#0f172a', border: '1px solid var(--border-color)', padding: '3px 8px', borderRadius: '6px', fontSize: '0.72rem', color: '#38bdf8' }}>
            Regime: <strong>{explanation.current_weather_regime || weatherRegime}</strong>
          </span>
          <span style={{ background: '#0f172a', border: '1px solid var(--border-color)', padding: '3px 8px', borderRadius: '6px', fontSize: '0.72rem', color: '#10b981' }}>
            Lead: <strong>T+{explanation.lead_time_hours || leadTimeHours}h</strong>
          </span>
          <span style={{ background: '#0f172a', border: '1px solid var(--border-color)', padding: '3px 8px', borderRadius: '6px', fontSize: '0.72rem', color: '#f59e0b' }}>
            Season: <strong>{explanation.season || season}</strong>
          </span>
          <span style={{ background: '#0f172a', border: '1px solid var(--border-color)', padding: '3px 8px', borderRadius: '6px', fontSize: '0.72rem', color: '#cbd5e1' }}>
            Region: <strong>{explanation.region || region}</strong>
          </span>
        </div>
      </div>

      {/* Primary Narrative Box (Format requested in specification) */}
      <div
        style={{
          background: 'rgba(15, 23, 42, 0.85)',
          borderLeft: '4px solid #38bdf8',
          borderTop: '1px solid var(--border-color)',
          borderRight: '1px solid var(--border-color)',
          borderBottom: '1px solid var(--border-color)',
          borderRadius: '8px',
          padding: '1rem 1.25rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
          <FileText size={15} color="#38bdf8" />
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Concise Machine-Readable Rationale
          </span>
        </div>
        <pre
          style={{
            fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
            fontSize: '0.82rem',
            color: '#e2e8f0',
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
          background: 'linear-gradient(135deg, rgba(2, 132, 199, 0.12), rgba(16, 185, 129, 0.08))',
          border: '1px solid rgba(56, 189, 248, 0.3)',
          borderRadius: '8px',
          padding: '0.85rem 1.15rem',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '10px',
        }}
      >
        <Award size={18} color="#10b981" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#10b981', marginBottom: '2px', textTransform: 'uppercase' }}>
            Judge Summary (Transparent & Non-Technical)
          </div>
          <p style={{ fontSize: '0.8rem', color: '#f1f5f9', lineHeight: 1.45, margin: 0 }}>
            {non_technical_summary}
          </p>
        </div>
      </div>

      {/* Historical Skill Used Matrix Table */}
      <div style={{ overflowX: 'auto' }}>
        <div style={{ fontSize: '0.8rem', fontWeight: 700, color: '#cbd5e1', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Activity size={14} color="#f59e0b" />
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
              const color = modelColorMap[mName] || '#0284c7'
              return (
                <tr
                  key={mName}
                  style={{
                    background: isDominant ? 'rgba(56, 189, 248, 0.10)' : 'transparent',
                    fontWeight: isDominant ? 700 : 400,
                  }}
                >
                  <td style={{ color: isDominant ? '#38bdf8' : '#f8fafc', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: color }} />
                    {isDominant ? '★ ' : ''}{mName}
                  </td>
                  <td>
                    <strong style={{ color }}>{Math.round(skill.weight * 100)}%</strong>
                  </td>
                  <td>
                    <span style={{ color: isDominant ? '#10b981' : '#e2e8f0', fontWeight: isDominant ? 700 : 400 }}>
                      {skill.rmse} {variable.includes('temp') ? '°C' : 'mm'}
                    </span>
                  </td>
                  <td>{skill.mae}</td>
                  <td style={{ color: skill.bias < 0 ? '#38bdf8' : '#f59e0b' }}>{skill.bias}</td>
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
        <div style={{ background: 'rgba(15, 23, 42, 0.6)', padding: '10px 14px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', marginBottom: '6px', textTransform: 'uppercase' }}>
            Decision Factors Considered
          </div>
          <ul style={{ paddingLeft: '1.2rem', margin: 0, fontSize: '0.75rem', color: '#cbd5e1', lineHeight: 1.5 }}>
            {decision_factors.map((factor, idx) => (
              <li key={idx} style={{ marginBottom: '3px' }}>{factor}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
