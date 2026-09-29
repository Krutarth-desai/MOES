import React from 'react'
import {
  Activity,
  CloudLightning,
  BarChart3,
  Map as MapIcon,
  AlertTriangle,
  History,
  Play,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Server,
  X,
} from 'lucide-react'

export const PRIMARY_SECTIONS = [
  {
    id: 'overview',
    label: 'Overview',
    subtitle: 'System KPIs & Regime',
    icon: Activity,
    badge: null,
  },
  {
    id: 'forecast',
    label: 'Forecast',
    subtitle: 'Meteograms & Vectors',
    icon: CloudLightning,
    badge: null,
  },
  {
    id: 'models',
    label: 'Models',
    subtitle: 'Skill & Softmax Weights',
    icon: BarChart3,
    badge: null,
  },
  {
    id: 'weight-map',
    label: 'Weight Map',
    subtitle: 'Spatial GIS Layers',
    icon: MapIcon,
    badge: '4 Layers',
  },
  {
    id: 'hazards',
    label: 'Hazards',
    subtitle: 'IMD Extreme Guidance',
    icon: AlertTriangle,
    badgeColor: '#1E3A8A',
  },
  {
    id: 'verify',
    label: 'Verify',
    subtitle: 'Rolling Backtest & Proof',
    icon: History,
    badge: 'Zero Leak',
  },
]

export default function Sidebar({
  activeSection,
  onSectionSelect,
  activeAlertsCount = 0,
  activeRegime,
  collapsed = false,
  onToggleCollapse,
  mobileOpen = false,
  onCloseMobile,
}) {
  return (
    <>
      {/* Mobile Backdrop Overlay */}
      {mobileOpen && (
        <div
          className="sidebar-mobile-backdrop"
          onClick={onCloseMobile}
          aria-hidden="true"
        />
      )}

      <aside
        className={`app-sidebar ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}
        aria-label="Primary Navigation"
      >
        {/* Brand / System Identity */}
        <div className="sidebar-brand" style={{ padding: collapsed ? '1rem 0' : '1rem 1.15rem', justifyContent: collapsed ? 'center' : 'flex-start' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: collapsed ? '0' : '14px', padding: '0' }}>
            <div style={{
              width: collapsed ? '44px' : '64px',
              height: collapsed ? '44px' : '64px',
              borderRadius: '50%',
              overflow: 'hidden',
              flexShrink: 0,
              boxShadow: '0 4px 12px rgba(0,0,0,0.4)', /* Only drop shadow, no CSS ring */
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              /* Premium Soft Ice/Sky gradient - extremely clean and complements orange/navy */
              background: 'linear-gradient(135deg, #F0F9FF 0%, #BAE6FD 100%)',
              boxShadow: 'inset 0 2px 4px rgba(255,255,255,0.5), 0 4px 12px rgba(0,0,0,0.3)'
            }}>
              <img
                src="/atmocast-logo-t.png"
                alt="AtmoCast Logo"
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'contain', 
                  transform: 'scale(1.15)', /* Slight zoom so the graphic feels powerful */
                  filter: 'contrast(1.1) drop-shadow(0px 6px 12px rgba(0,0,0,0.5))', /* Sharpness + heavy dynamic shadow so it pops off the background */
                  transition: 'all 0.3s ease',
                }}
              />
            </div>
            {!collapsed && (
              <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
                <span style={{ fontSize: '0.9rem', fontWeight: 900, color: '#F1F5F9', letterSpacing: '0.02em', fontFamily: "'Outfit', sans-serif" }}>MoES · IMD</span>
                <span style={{ fontSize: '0.62rem', color: '#38BDF8', fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', fontFamily: "'Outfit', sans-serif" }}>AI Forecast Engine</span>
              </div>
            )}
          </div>
          {mobileOpen && (
            <button
              onClick={onCloseMobile}
              className="sidebar-mobile-close-btn"
              title="Close Navigation"
            >
              <X size={18} />
            </button>
          )}
        </div>

        {/* Section Label */}
        {!collapsed && (
          <div className="sidebar-nav-header">
            <span>FORECAST WORKSTATION</span>
          </div>
        )}

        {/* Primary Navigation Items List */}
        <nav className="sidebar-nav-list">
          {PRIMARY_SECTIONS.map((item) => {
            const Icon = item.icon
            const isActive = activeSection === item.id
            const hazardBadge = item.id === 'hazards' && activeAlertsCount > 0
              ? `${activeAlertsCount} Alert${activeAlertsCount > 1 ? 's' : ''}`
              : item.badge

            return (
              <button
                key={item.id}
                onClick={() => {
                  onSectionSelect(item.id)
                  if (onCloseMobile) onCloseMobile()
                }}
                className={`sidebar-nav-item ${isActive ? 'active' : ''}`}
                title={collapsed ? `${item.label} — ${item.subtitle}` : undefined}
                aria-current={isActive ? 'page' : undefined}
              >
                <div className="sidebar-nav-icon-wrap">
                  <Icon size={18} className="sidebar-nav-icon" />
                  {isActive && <div className="sidebar-active-indicator" />}
                </div>

                {!collapsed && (
                  <div className="sidebar-nav-content">
                    <span className="sidebar-nav-label">{item.label}</span>
                    <span className="sidebar-nav-sub">{item.subtitle}</span>
                  </div>
                )}

                {!collapsed && hazardBadge && (
                  <span
                    className="sidebar-nav-badge"
                    style={{
                      backgroundColor: item.id === 'hazards' ? 'rgba(239, 68, 68, 0.12)' : 'rgba(59, 130, 246, 0.15)',
                      color: item.id === 'hazards' ? '#F87171' : '#60A5FA',
                      borderColor: item.id === 'hazards' ? 'rgba(239, 68, 68, 0.3)' : 'rgba(59, 130, 246, 0.3)',
                    }}
                  >
                    {hazardBadge}
                  </span>
                )}
              </button>
            )
          })}
          {/* Divider */}
          <div className="sidebar-divider" />

          {/* Operational 7-Stage Scenario Simulation Trigger */}
          <div className="sidebar-demo-wrapper">
            <button
              onClick={() => {
                onSectionSelect('demo-mode')
                if (onCloseMobile) onCloseMobile()
              }}
              className={`sidebar-demo-btn ${activeSection === 'demo-mode' ? 'active' : ''}`}
              title="Interactive 7-stage meteorological consensus simulation"
            >
              <Play size={16} color="#2563EB" />
              {!collapsed && (
                <div style={{ textAlign: 'left', flex: 1 }}>
                  <div style={{ fontWeight: 800, fontSize: '0.78rem', color: '#F8FAFC', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span>Pipeline Simulation</span>
                    <span className="demo-live-dot" />
                  </div>
                  <div style={{ fontSize: '0.67rem', color: '#94A3B8' }}>7-Stage Blending Flow</div>
                </div>
              )}
            </button>
          </div>
        </nav>

        {/* Footer / Telemetry & Collapse Toggle */}
        <div className="sidebar-footer">
          {!collapsed && activeRegime && (
            <div className="sidebar-regime-box">
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.7rem', color: '#94A3B8' }}>
                <ShieldCheck size={12} color="#60A5FA" />
                <span>Active Regime:</span>
              </div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#F8FAFC', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {activeRegime.regime_name || activeRegime.diagnosed_regime || 'Heavy Rain'}
              </div>
            </div>
          )}

          <button
            onClick={onToggleCollapse}
            className="sidebar-collapse-btn"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
            {!collapsed && <span>Collapse Sidebar</span>}
          </button>
        </div>
      </aside>
    </>
  )
}
