import React from 'react'
import { Info, Wind, Layers } from 'lucide-react'

export default function RegimeBanner({ regimeData, leadTimeHours }) {
  if (!regimeData) return null

  return (
    <div className="glass-card" style={{ padding: '0.85rem 1.25rem', borderLeft: '4px solid #38bdf8' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <Wind size={16} color="#38bdf8" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, color: '#f8fafc' }}>
              Synoptic Atmospheric Regime: {regimeData.regime_name}
            </h3>
            <span style={{ fontSize: '0.75rem', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', padding: '1px 6px', borderRadius: '4px' }}>
              Model Confidence: {Math.round(regimeData.confidence * 100)}%
            </span>
          </div>
          <p style={{ fontSize: '0.82rem', color: '#94a3b8', lineHeight: 1.4 }}>
            {regimeData.synoptic_summary}
          </p>
        </div>

        <div style={{ minWidth: '280px', borderLeft: '1px solid var(--border-color)', paddingLeft: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: '#cbd5e1', fontWeight: 500, marginBottom: '4px' }}>
            <Layers size={14} color="#f59e0b" />
            <span>Adaptive Blending Logic (T+{leadTimeHours}h)</span>
          </div>
          <p style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
            {leadTimeHours <= 48
              ? 'Short lead horizon: AI models (GraphCast/Pangu) receive elevated weight for rapid dynamic skill.'
              : 'Extended lead horizon: Physics-based NWP (ECMWF/GFS) prioritized to enforce conservation laws.'}
          </p>
        </div>
      </div>
    </div>
  )
}
