import React from 'react'
import { AlertTriangle, AlertCircle, ShieldAlert, CheckCircle } from 'lucide-react'

export default function HazardSeverityBadge({
  alerts = [],
  leadTime = 24,
}) {
  const alertCount = alerts.length

  // High-priority active threat
  const topAlert = alerts[0] || {
    event_type: 'heavy_rainfall',
    severity: 'red',
    location: 'Konkan & Western Ghats',
    threshold: '115.5 mm / 24h',
    action: 'Take Immediate Action / NDRF Alert',
    valid_from: 'T+0h',
    valid_to: `T+${leadTime}h`,
  }

  const severityConfigs = {
    red: {
      label: 'TIER 1 (CRITICAL WARNING)',
      action: 'Take Immediate Action',
      color: '#1E3A8A',
      bg: 'rgba(30, 58, 138, 0.12)',
      border: 'rgba(30, 58, 138, 0.35)',
      icon: ShieldAlert,
    },
    orange: {
      label: 'TIER 2 (SEVERE ALERT)',
      action: 'Be Prepared / Update Response',
      color: '#2563EB',
      bg: 'rgba(37, 99, 235, 0.12)',
      border: 'rgba(37, 99, 235, 0.35)',
      icon: AlertTriangle,
    },
    yellow: {
      label: 'TIER 3 (ADVISORY WATCH)',
      action: 'Be Updated / Monitor Forecast',
      color: '#0284C7',
      bg: 'rgba(2, 132, 199, 0.12)',
      border: 'rgba(2, 132, 199, 0.35)',
      icon: AlertCircle,
    },
    green: {
      label: 'ROUTINE MONITORING',
      action: 'Normal Routine Operations',
      color: '#38BDF8',
      bg: 'rgba(56, 189, 248, 0.12)',
      border: 'rgba(56, 189, 248, 0.30)',
      icon: CheckCircle,
    },
  }

  const currentSev = (topAlert.severity || 'orange').toLowerCase()
  const cfg = severityConfigs[currentSev] || severityConfigs.orange
  const Icon = cfg.icon

  return (
    <div className="weather-card">
      <div className="weather-card-header">
        <div className="weather-card-title-group">
          <div className="weather-icon-badge" style={{ background: cfg.bg, color: cfg.color }}>
            <Icon size={18} />
          </div>
          <div>
            <h4 className="weather-card-title">IMD Hazard & Severe Alert Guidance</h4>
            <span className="weather-card-subtitle">{alertCount} Active Warning Guidance Bulletins</span>
          </div>
        </div>

        <span
          className="weather-category-badge"
          style={{ background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}
        >
          {cfg.label}
        </span>
      </div>

      <div className="hazard-hero-box" style={{ borderLeft: `4px solid ${cfg.color}`, background: cfg.bg }}>
        <div className="hazard-hero-title">
          <Icon size={16} color={cfg.color} />
          <strong style={{ color: cfg.color }}>{topAlert.location}</strong>
          <span className="hazard-type-pill">{topAlert.event_type?.replace('_', ' ')?.toUpperCase()}</span>
        </div>
        <div className="hazard-hero-protocol">
          <strong>Protocol:</strong> {topAlert.action || cfg.action}
        </div>
      </div>

      <div className="hazard-threshold-row">
        <span>Trigger Threshold:</span>
        <strong>{topAlert.threshold || '≥ 115.5 mm/24h'}</strong>
        <span className="hazard-validity">Horizon: {topAlert.valid_from || 'T+0h'} to {topAlert.valid_to || `T+${leadTime}h`}</span>
      </div>

      <div className="weather-sub-metrics">
        <div className="weather-sub-item">
          <span className="sub-label">Active Advisories:</span>
          <span className="sub-value" style={{ color: cfg.color, fontWeight: 700 }}>
            {alertCount > 0 ? `${alertCount} Regional Bulletins` : '0 Critical Bulletins'}
          </span>
        </div>
        <div className="weather-sub-item">
          <span className="sub-label">Disaster Authority:</span>
          <span className="sub-value">MoES / IMD Automated Feed</span>
        </div>
      </div>
    </div>
  )
}
