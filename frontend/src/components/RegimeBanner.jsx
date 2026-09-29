import React from 'react'
import { Info, Wind, Layers } from 'lucide-react'

export default function RegimeBanner({ regimeData, leadTimeHours }) {
  if (!regimeData) return null

  return (
    <div className="glass-card" style={{ padding: '0.85rem 1.25rem', borderLeft: '4px solid #4D91C9', background: '#FFFFFF' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: '280px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <Wind size={16} color="#4D91C9" />
            <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#243746', margin: 0 }}>
              Synoptic Atmospheric Regime: {regimeData.regime_name}
            </h3>
            <span style={{ fontSize: '0.72rem', background: 'rgba(77, 145, 201, 0.12)', color: '#2563EB', border: '1px solid rgba(77, 145, 201, 0.28)', padding: '2px 8px', borderRadius: '4px', fontWeight: 700 }}>
              Model Confidence: {Math.round(regimeData.confidence * 100)}%
            </span>
          </div>
          <p style={{ fontSize: '0.82rem', color: '#405565', lineHeight: 1.4, margin: '4px 0 0 0' }}>
            {regimeData.synoptic_summary}
          </p>
        </div>

        <div style={{ minWidth: '280px', borderLeft: '1px solid rgba(77, 145, 201, 0.2)', paddingLeft: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: '#243746', fontWeight: 700, marginBottom: '4px' }}>
            <Layers size={14} color="#2563EB" />
            <span>Adaptive Blending Logic (T+{leadTimeHours}h)</span>
          </div>
          <p style={{ fontSize: '0.75rem', color: '#405565', margin: 0, lineHeight: 1.4 }}>
            {leadTimeHours <= 48
              ? 'Short lead horizon: AI models (GraphCast/Pangu) receive elevated weight for rapid dynamic skill.'
              : 'Extended lead horizon: Physics-based NWP (ECMWF/GFS) prioritized to enforce conservation laws.'}
          </p>
        </div>
      </div>
    </div>
  )
}
