import React from 'react'
import {
  Sun,
  CloudRain,
  CloudLightning,
  Wind,
  Droplets,
  ChevronRight,
} from 'lucide-react'

export default function AuraMetDailyStrip({
  selectedLeadTime = 24,
  onSelectLeadTime,
  variable = 'rainfall',
}) {
  const daysForecast = [
    {
      day: 'Mon',
      date: 'Nowcast',
      leadTime: 6,
      icon: CloudRain,
      condition: 'Steady Showers',
      maxTemp: 31,
      minTemp: 26,
      rainProb: 85,
      rainfallMm: 32.4,
    },
    {
      day: 'Tue',
      date: 'Half-Day',
      leadTime: 12,
      icon: CloudLightning,
      condition: 'Thunderstorms',
      maxTemp: 32,
      minTemp: 25,
      rainProb: 92,
      rainfallMm: 46.2,
    },
    {
      day: 'Wed',
      date: 'Day 1 Peak',
      leadTime: 24,
      icon: CloudRain,
      condition: 'Heavy Monsoon',
      maxTemp: 30,
      minTemp: 24,
      rainProb: 95,
      rainfallMm: 58.5,
    },
    {
      day: 'Thu',
      date: 'Day 2',
      leadTime: 48,
      icon: Wind,
      condition: 'Squally Winds',
      maxTemp: 31,
      minTemp: 25,
      rainProb: 78,
      rainfallMm: 28.0,
    },
    {
      day: 'Fri',
      date: 'Day 3',
      leadTime: 72,
      icon: CloudRain,
      condition: 'Scattered Rain',
      maxTemp: 32,
      minTemp: 26,
      rainProb: 65,
      rainfallMm: 18.2,
    },
    {
      day: 'Sat',
      date: 'Day 4',
      leadTime: 96,
      icon: Sun,
      condition: 'Partly Sunny',
      maxTemp: 33,
      minTemp: 27,
      rainProb: 40,
      rainfallMm: 8.5,
    },
    {
      day: 'Sun',
      date: 'Day 5',
      leadTime: 120,
      icon: Sun,
      condition: 'Clear & Humid',
      maxTemp: 34,
      minTemp: 27,
      rainProb: 25,
      rainfallMm: 3.1,
    },
  ]

  return (
    <div className="auramet-daily-strip-container">
      <div className="auramet-strip-header">
        <div className="auramet-strip-title-group">
          <h4 className="auramet-strip-title">Multi-Horizon Synoptic Forecast Strip</h4>
          <span className="auramet-strip-subtitle">Ground-Truth Calibrated · Select Horizon to Update System</span>
        </div>
        <div className="auramet-strip-tag">
          <span>7-Day Synoptic Cycle</span>
        </div>
      </div>

      <div className="auramet-daily-cards-row">
        {daysForecast.map((item) => {
          const isSelected = selectedLeadTime === item.leadTime
          const Icon = item.icon

          return (
            <button
              key={item.leadTime}
              onClick={() => onSelectLeadTime && onSelectLeadTime(item.leadTime)}
              className={`auramet-day-card ${isSelected ? 'active-horizon' : ''}`}
              title={`Click to analyze T+${item.leadTime}h operational horizon`}
            >
              <div className="auramet-card-day-header">
                <span className="auramet-day-label">{item.day}</span>
                <span className="auramet-lead-pill">T+{item.leadTime}h</span>
              </div>

              {/* Animated Floating Weather Icon */}
              <div className="auramet-card-icon-container">
                <Icon size={34} className="auramet-card-floating-icon" />
              </div>

              <div className="auramet-card-temp-range">
                <span className="auramet-temp-high">{item.maxTemp}°</span>
                <span className="auramet-temp-divider">/</span>
                <span className="auramet-temp-low">{item.minTemp}°</span>
              </div>

              <div className="auramet-card-condition-label">
                {item.condition}
              </div>

              {/* Rain Probability / Tweedie Output Pill */}
              <div className="auramet-card-prob-pill">
                <Droplets size={11} />
                <span>{variable.includes('rain') ? `${item.rainfallMm}mm` : `${item.rainProb}%`}</span>
              </div>

              {isSelected && (
                <div className="auramet-active-indicator-dot" />
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
