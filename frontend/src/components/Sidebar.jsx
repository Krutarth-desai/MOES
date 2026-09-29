import React from 'react'
import {
  Activity,
  CloudLightning,
  BarChart3,
  Map as MapIcon,
  AlertTriangle,
  History,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Server,
  X,
  LogOut,
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
  user,
  profile,
  onLogout,
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
        <div className="sidebar-brand">
          <div className="sidebar-brand-badge">
            MoES · IMD
          </div>
          {!collapsed && (
            <div className="sidebar-brand-text">
              <div className="sidebar-brand-title">Atmospheric AI</div>
              <div className="sidebar-brand-sub">Forecast Blending System</div>
            </div>
          )}
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
                      backgroundColor: item.id === 'hazards' ? 'rgba(30, 58, 138, 0.12)' : 'rgba(37, 99, 235, 0.12)',
                      color: item.id === 'hazards' ? '#1E3A8A' : '#1D4ED8',
                      borderColor: item.id === 'hazards' ? 'rgba(30, 58, 138, 0.3)' : 'rgba(37, 99, 235, 0.3)',
                    }}
                  >
                    {hazardBadge}
                  </span>
                )}
              </button>
            )
          })}
        </nav>

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
            <Sparkles size={16} color="#2563EB" />
            {!collapsed && (
              <div style={{ textAlign: 'left', flex: 1 }}>
                <div style={{ fontWeight: 800, fontSize: '0.78rem', color: '#1E3A8A', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span>Pipeline Simulation</span>
                  <span className="demo-live-dot" />
                </div>
                <div style={{ fontSize: '0.67rem', color: '#64748B' }}>7-Stage Blending Flow</div>
              </div>
            )}
          </button>
        </div>

        {/* Footer / Telemetry & Collapse Toggle */}
        <div className="sidebar-footer">
          {/* Authenticated User Account Box */}
          {(user || profile) && (
            <div
              className="sidebar-user-box"
              style={{
                padding: collapsed ? '6px' : '8px 10px',
                background: 'rgba(241, 245, 249, 0.8)',
                borderRadius: '8px',
                border: '1px solid rgba(203, 213, 225, 0.6)',
                marginBottom: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', justifyContent: collapsed ? 'center' : 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                  {profile?.avatar_url || user?.user_metadata?.avatar_url || user?.user_metadata?.picture ? (
                    <img
                      src={profile?.avatar_url || user?.user_metadata?.avatar_url || user?.user_metadata?.picture}
                      alt="User Avatar"
                      style={{
                        width: '24px',
                        height: '24px',
                        borderRadius: '50%',
                        objectFit: 'cover',
                        border: '1px solid #2563EB',
                        flexShrink: 0,
                      }}
                    />
                  ) : (
                    <div
                      style={{
                        width: '24px',
                        height: '24px',
                        borderRadius: '50%',
                        background: 'linear-gradient(135deg, #1E3A8A, #2563EB)',
                        color: '#ffffff',
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      {(profile?.full_name || user?.email || 'U').charAt(0).toUpperCase()}
                    </div>
                  )}
                  {!collapsed && (
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#1E3A8A', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={profile?.full_name || user?.email}>
                        {profile?.full_name || user?.email?.split('@')[0]}
                      </div>
                      <div style={{ fontSize: '0.65rem', color: '#64748B', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {user?.email}
                      </div>
                    </div>
                  )}
                </div>

                {!collapsed && onLogout && (
                  <button
                    onClick={onLogout}
                    title="Sign Out of MOES System"
                    style={{
                      background: 'rgba(239, 68, 68, 0.1)',
                      color: '#DC2626',
                      border: '1px solid rgba(239, 68, 68, 0.3)',
                      borderRadius: '6px',
                      padding: '3px 8px',
                      fontSize: '0.68rem',
                      fontWeight: 700,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '3px',
                      flexShrink: 0,
                    }}
                  >
                    <LogOut size={12} />
                    <span>Logout</span>
                  </button>
                )}
              </div>
            </div>
          )}

          {!collapsed && activeRegime && (
            <div className="sidebar-regime-box">
              <div style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '0.7rem', color: '#64748B' }}>
                <ShieldCheck size={12} color="#2563EB" />
                <span>Active Regime:</span>
              </div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#1E3A8A', marginTop: '2px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
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
