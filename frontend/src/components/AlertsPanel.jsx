import React from 'react'
import { AlertTriangle, ShieldAlert, CheckCircle, Clock } from 'lucide-react'

export default function AlertsPanel({ alerts }) {
  const getBadgeClass = (severity) => {
    switch (severity) {
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

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="card-header">
        <div className="card-title">
          <ShieldAlert size={18} color="#ef4444" />
          <span>IMD Severe Weather Warning Center</span>
        </div>
        <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
          {alerts.length} Active Advisories
        </span>
      </div>

      <div className="card-body" style={{ overflowY: 'auto', maxHeight: '420px', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {alerts.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: '#64748b' }}>
            <CheckCircle size={32} color="#10b981" style={{ margin: '0 auto 8px' }} />
            <p>No severe meteorological hazards detected for this lead time.</p>
          </div>
        ) : (
          alerts.map((alert) => (
            <div
              key={alert.id}
              style={{
                background: 'rgba(30, 41, 59, 0.6)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                padding: '0.75rem',
                borderLeft: `4px solid ${
                  alert.severity === 'red' ? '#ef4444' : alert.severity === 'orange' ? '#f97316' : '#eab308'
                }`,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span className={getBadgeClass(alert.severity)}>
                  {alert.severity.toUpperCase()} ALERT
                </span>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Clock size={12} />
                  Prob: {Math.round(alert.exceedance_probability * 100)}%
                </span>
              </div>

              <h4 style={{ fontSize: '0.88rem', fontWeight: 600, color: '#f1f5f9', marginBottom: '2px' }}>
                {alert.location_name}
              </h4>
              <p style={{ fontSize: '0.78rem', color: '#cbd5e1', marginBottom: '6px' }}>
                {alert.description}
              </p>

              <div style={{ fontSize: '0.72rem', color: '#94a3b8', background: 'rgba(15, 23, 42, 0.5)', padding: '4px 6px', borderRadius: '4px' }}>
                <strong>IMD Protocol:</strong> {alert.recommended_action}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
