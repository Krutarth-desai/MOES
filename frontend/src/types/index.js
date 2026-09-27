/**
 * Core Meteorological and Model Enums & Constants
 */

export const WeatherVariables = {
  PRECIPITATION: 'precipitation',
  TEMPERATURE_2M: 'temperature_2m',
  WIND_SPEED_10M: 'wind_speed_10m',
}

export const VariableMetadata = {
  [WeatherVariables.PRECIPITATION]: {
    id: 'precipitation',
    label: 'Precipitation',
    unit: 'mm/day',
    icon: 'CloudRain',
    colorScale: ['#e0f2fe', '#38bdf8', '#0284c7', '#1d4ed8', '#581c87'],
  },
  [WeatherVariables.TEMPERATURE_2M]: {
    id: 'temperature_2m',
    label: 'Temperature (2m)',
    unit: '°C',
    icon: 'Thermometer',
    colorScale: ['#22d3ee', '#facc15', '#f97316', '#ef4444', '#7f1d1d'],
  },
  [WeatherVariables.WIND_SPEED_10M]: {
    id: 'wind_speed_10m',
    label: 'Wind Speed (10m)',
    unit: 'km/h',
    icon: 'Wind',
    colorScale: ['#a7f3d0', '#34d399', '#059669', '#047857', '#064e3b'],
  },
}

export const ModelSources = {
  BLENDED: { id: 'blended', name: 'Hybrid Blended', type: 'ensemble', color: '#38bdf8' },
  GFS: { id: 'gfs', name: 'NOAA GFS', type: 'nwp', color: '#f59e0b' },
  ECMWF: { id: 'ecmwf', name: 'ECMWF IFS', type: 'nwp', color: '#10b981' },
  GRAPHCAST: { id: 'graphcast', name: 'DeepMind GraphCast', type: 'ai', color: '#8b5cf6' },
  PANGU: { id: 'pangu', name: 'Pangu-Weather', type: 'ai', color: '#ec4899' },
}

export const AlertSeverities = {
  GREEN: 'green',
  YELLOW: 'yellow',
  ORANGE: 'orange',
  RED: 'red',
}
