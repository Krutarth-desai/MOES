import React from 'react'
import { Server, Cpu, Database, CpuIcon, ArrowDown, ShieldCheck, Zap } from 'lucide-react'

export default function BlendingArchitectureFlow({
  weights = {
    'NWP Model A': 0.24,
    'NWP Model B': 0.38,
    'Ensemble Forecast': 0.20,
    'AI/ML Forecast': 0.18,
  },
  dominantModel = 'NWP Model B',
  entropy = 0.88,
  leadTime = 24,
}) {
  return (
    <div className="glass-card blending-flow-container" style={{ padding: '1.25rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Zap size={16} color="#4D91C9" />
          <h4 style={{ fontSize: '0.95rem', fontWeight: 800, color: '#243746', margin: 0 }}>
            Operational Forecast Fusion Pipeline Architecture
          </h4>
        </div>
        <div style={{ fontSize: '0.72rem', color: '#657886', fontWeight: 500 }}>
          Dynamic Softmax Simplex Calibration · Lead Time: T+{leadTime}h
        </div>
      </div>

      <div className="flow-diagram-grid">
        {/* Tier 1: Input Forecast Feeds */}
        <div className="flow-tier-box">
          <div className="flow-tier-header">
            <span className="flow-tier-badge">TIER 1 · INPUT STREAMS</span>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#243746' }}>Heterogeneous Model Feeds</span>
          </div>

          <div className="flow-sources-list">
            <div className="flow-source-item" style={{ borderLeft: '3px solid #2563EB' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#243746' }}>NWP Model A (GFS-like)</span>
                <span style={{ fontSize: '0.72rem', color: '#2563EB', fontWeight: 700, fontFamily: 'monospace' }}>
                  {Math.round((weights['NWP Model A'] || 0.24) * 100)}%
                </span>
              </div>
              <span style={{ fontSize: '0.66rem', color: '#657886' }}>Global Spectral Dynamical Equations</span>
            </div>

            <div className="flow-source-item" style={{ borderLeft: '3px solid #1E3A8A' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#243746' }}>NWP Model B (ECMWF-like)</span>
                <span style={{ fontSize: '0.72rem', color: '#1E3A8A', fontWeight: 700, fontFamily: 'monospace' }}>
                  {Math.round((weights['NWP Model B'] || 0.38) * 100)}%
                </span>
              </div>
              <span style={{ fontSize: '0.66rem', color: '#657886' }}>Semi-Lagrangian Atmospheric Dynamics</span>
            </div>

            <div className="flow-source-item" style={{ borderLeft: '3px solid #0284C7' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#243746' }}>Ensemble Forecast (GEFS/EPS)</span>
                <span style={{ fontSize: '0.72rem', color: '#0284C7', fontWeight: 700, fontFamily: 'monospace' }}>
                  {Math.round((weights['Ensemble Forecast'] || 0.20) * 100)}%
                </span>
              </div>
              <span style={{ fontSize: '0.66rem', color: '#657886' }}>Perturbed Initial Conditions Monte-Carlo</span>
            </div>

            <div className="flow-source-item" style={{ borderLeft: '3px solid #38BDF8' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#243746' }}>AI Neural Forecast (GraphCast)</span>
                <span style={{ fontSize: '0.72rem', color: '#38BDF8', fontWeight: 700, fontFamily: 'monospace' }}>
                  {Math.round((weights['AI/ML Forecast'] || 0.18) * 100)}%
                </span>
              </div>
              <span style={{ fontSize: '0.66rem', color: '#657886' }}>Auto-regressive Spherical Graph Neural Network</span>
            </div>
          </div>
        </div>

        {/* Tier 2: Adaptive Weight Engine (Core Mathematical Simplex) */}
        <div className="flow-core-box">
          <div className="flow-tier-header">
            <span className="flow-tier-badge" style={{ background: 'rgba(77, 145, 201, 0.15)', color: '#294E6B' }}>
              TIER 2 · ADAPTIVE BLENDING ENGINE
            </span>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#294E6B' }}>
              Softmax Simplex Weight Engine
            </span>
          </div>

          <div style={{ padding: '8px 10px', background: 'rgba(77, 145, 201, 0.08)', borderRadius: '6px', border: '1px solid rgba(77, 145, 201, 0.22)', margin: '8px 0' }}>
            <div style={{ fontSize: '0.68rem', color: '#657886', marginBottom: '2px', fontWeight: 600 }}>Reliability Optimization Metric:</div>
            <div style={{ fontFamily: 'monospace', fontSize: '0.76rem', color: '#294E6B', fontWeight: 700 }}>
              w_i = exp(Skill_i / T) / Σ exp(Skill_k / T)
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.72rem', color: '#405565' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ color: '#2563EB', fontWeight: 700 }}>✓</span>
              <span><strong>Consensus Entropy:</strong> {entropy} / 1.0 (High Agreement)</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ color: '#2563EB', fontWeight: 700 }}>✓</span>
              <span><strong>Lead-Time Decay α:</strong> High-res NWP leads at 0–24h; AI advection gains at 48–168h</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
              <span style={{ color: '#2563EB', fontWeight: 700 }}>✓</span>
              <span><strong>Governance Floor:</strong> Strict w_i ≥ 0.05 to prevent single-model lock</span>
            </div>
          </div>
        </div>

        {/* Tier 3: Operational Consensus Product */}
        <div className="flow-output-box">
          <div className="flow-tier-header">
            <span className="flow-tier-badge" style={{ background: 'rgba(37, 99, 235, 0.12)', color: '#2563EB' }}>
              TIER 3 · OPERATIONAL OUTPUT
            </span>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#2563EB' }}>
              Consensus Blended Forecast
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '6px' }}>
            <div style={{ background: 'rgba(234, 242, 247, 0.65)', padding: '8px 10px', borderRadius: '6px', border: '1px solid rgba(37, 99, 235, 0.25)' }}>
              <div style={{ fontSize: '0.68rem', color: '#657886' }}>Scalar Consensus & Bounding:</div>
              <div style={{ fontSize: '0.76rem', color: '#243746', fontWeight: 700 }}>
                F_blended = Σ (w_i · F_i) (Tweedie bounded R ≥ 0.0)
              </div>
            </div>

            <div style={{ background: 'rgba(234, 242, 247, 0.65)', padding: '8px 10px', borderRadius: '6px', border: '1px solid rgba(77, 145, 201, 0.25)' }}>
              <div style={{ fontSize: '0.68rem', color: '#657886' }}>Yamartino Directional Vector:</div>
              <div style={{ fontSize: '0.76rem', color: '#243746', fontWeight: 700 }}>
                θ_blended = atan2(Σ w_i sin θ_i, Σ w_i cos θ_i)
              </div>
            </div>

            <div style={{ background: 'rgba(234, 242, 247, 0.65)', padding: '8px 10px', borderRadius: '6px', border: '1px solid rgba(37, 99, 235, 0.25)' }}>
              <div style={{ fontSize: '0.68rem', color: '#657886' }}>Uncertainty Envelope:</div>
              <div style={{ fontSize: '0.76rem', color: '#243746', fontWeight: 700 }}>
                10th–90th Percentile Confidence Interval
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
