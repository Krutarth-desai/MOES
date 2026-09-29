import React from 'react'
import {
  Sun,
  CloudRain,
  CloudLightning,
  Wind,
  Droplets,
  Gauge,
  Compass,
  ShieldCheck,
  MapPin,
  Calendar,
  Sparkles,
} from 'lucide-react'

export default function AuraMetHeroWeather({
  station,
  variable,
  blendedValue = 38.5,
  unit = 'mm',
  ci10 = 34.6,
  ci90 = 42.4,
  leadTime = 24,
  activeRegime,
  dominantModel = 'NWP Model B',
  entropy = 0.88,
}) {
  const stationName = station?.name || 'Mumbai (Santacruz)'
  const regionType = station?.region_type || 'Western Ghats & Coastal'
  const isRain = variable?.toLowerCase().includes('rain')
  const isTemp = variable?.toLowerCase().includes('temp')
  const isWind = variable?.toLowerCase().includes('wind')

  // Temperature and condition synthesis
  const displayTemp = isTemp ? blendedValue : 32.4
  const feelsLikeTemp = Math.round((displayTemp + 2.1) * 10) / 10
  const conditionLabel = activeRegime?.regime_name || (isRain ? 'Heavy Convective Rain' : isWind ? 'Coastal Gale Squall' : 'Partly Cloudy')

  // Weather icon selection
  const WeatherIcon = isRain ? CloudRain : isWind ? Wind : isTemp && displayTemp > 38 ? Sun : CloudLightning

  // Yamartino wind parameters
  const windSpeed = 24.5
  const windDeg = 245
  const humidity = 82
  const dewPoint = 24.8
  const pressureHpa = 1011.6
  const consensusSkill = Math.min(99, Math.max(75, Math.round((1 - entropy * 0.25) * 100)))

  return (
    <div className="auramet-hero-card">
      {/* Top Banner: Location, Live Telemetry Tag & Date */}
      <div className="auramet-hero-header">
        <div className="auramet-location-badge">
          <MapPin size={15} className="auramet-icon-glow" />
          <span className="auramet-station-title">{stationName}</span>
          <span className="auramet-region-tag">{regionType}</span>
        </div>

        <div className="auramet-header-meta">
          <div className="live-telemetry-tag">
            <span className="live-dot" />
            <span>OPERATIONAL RUN T+{leadTime}h</span>
          </div>
          <span className="auramet-date-chip">
            <Calendar size={13} />
            <span>Forecast Horizon: {leadTime} Hours</span>
          </span>
        </div>
      </div>

      {/* Hero Temperature & Condition Layout */}
      <div className="auramet-hero-body">
        {/* Left: Floating Icon, Temperature, Description */}
        <div className="auramet-main-temp-section">
          <div className="auramet-floating-weather-icon-wrapper">
            <WeatherIcon size={76} className="auramet-weather-icon-floating" />
          </div>

          <div className="auramet-temp-column">
            <div className="auramet-temp-row">
              <span className="auramet-temp-value">{displayTemp}</span>
              <span className="auramet-temp-unit">°C</span>
            </div>
            <div className="auramet-condition-text">{conditionLabel}</div>
            <div className="auramet-temp-sub">
              <span>Feels like <strong>{feelsLikeTemp}°C</strong></span>
              <span className="auramet-separator">·</span>
              <span>Min <strong>26.2°</strong></span>
              <span className="auramet-separator">·</span>
              <span>Max <strong>34.8°</strong></span>
            </div>
          </div>
        </div>

        {/* Center / Right: High-Priority Metric Pill */}
        <div className="auramet-hero-variable-pill">
          <div className="auramet-variable-title">
            <Sparkles size={14} />
            <span>Primary Blended Output ({variable.toUpperCase()})</span>
          </div>
          <div className="auramet-variable-value">
            <span className="auramet-metric-num">{blendedValue}</span>
            <span className="auramet-metric-unit">{unit}</span>
          </div>
          <div className="auramet-variable-envelope">
            90% Conformal Envelope: <strong>{ci10} – {ci90} {unit}</strong>
          </div>
        </div>
      </div>

      {/* 4 Telemetry Glass Chips */}
      <div className="auramet-telemetry-grid">
        {/* 1. Humidity & Dew Point */}
        <div className="auramet-telemetry-chip">
          <div className="auramet-chip-icon">
            <Droplets size={18} />
          </div>
          <div className="auramet-chip-content">
            <span className="auramet-chip-label">Humidity</span>
            <div className="auramet-chip-value">
              <span>{humidity}%</span>
            </div>
            <span className="auramet-chip-sub">Dew Point: {dewPoint}°C</span>
          </div>
        </div>

        {/* 2. Wind Flow & Yamartino Direction */}
        <div className="auramet-telemetry-chip">
          <div className="auramet-chip-icon">
            <Wind size={18} />
          </div>
          <div className="auramet-chip-content">
            <span className="auramet-chip-label">Surface Wind</span>
            <div className="auramet-chip-value">
              <span>{windSpeed}</span>
              <span className="auramet-chip-unit">km/h</span>
              <Compass
                size={16}
                style={{
                  transform: `rotate(${windDeg}deg)`,
                  transition: 'transform 0.6s ease',
                  marginLeft: '4px',
                }}
              />
            </div>
            <span className="auramet-chip-sub">{windDeg}° WSW (Yamartino)</span>
          </div>
        </div>

        {/* 3. Barometer Pressure */}
        <div className="auramet-telemetry-chip">
          <div className="auramet-chip-icon">
            <Gauge size={18} />
          </div>
          <div className="auramet-chip-content">
            <span className="auramet-chip-label">Pressure (MSL)</span>
            <div className="auramet-chip-value">
              <span>{pressureHpa}</span>
              <span className="auramet-chip-unit">hPa</span>
            </div>
            <span className="auramet-chip-sub">Stable Synoptic Field</span>
          </div>
        </div>

        {/* 4. Consensus Agreement Skill */}
        <div className="auramet-telemetry-chip">
          <div className="auramet-chip-icon">
            <ShieldCheck size={18} />
          </div>
          <div className="auramet-chip-content">
            <span className="auramet-chip-label">Model Consensus</span>
            <div className="auramet-chip-value">
              <span>{consensusSkill}%</span>
              <span className="auramet-chip-unit">Skill</span>
            </div>
            <span className="auramet-chip-sub">Lead Model: {dominantModel}</span>
          </div>
        </div>
      </div>
    </div>
  )
}
