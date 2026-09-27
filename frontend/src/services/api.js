import axios from 'axios'

const API_BASE = '/api/v1'

const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const apiService = {
  // Observatories / Stations
  async getStations() {
    const res = await apiClient.get('/forecast/stations')
    return res.data
  },

  // Point meteogram forecast
  async getPointForecast({ stationId, lat, lon, variable }) {
    const params = { variable }
    if (stationId) params.station_id = stationId
    if (lat !== undefined && lon !== undefined) {
      params.lat = lat
      params.lon = lon
    }
    const res = await apiClient.get('/forecast/point', { params })
    return res.data
  },

  // Gridded spatial forecast slice
  async getGriddedForecast({ variable, leadTimeHours, modelId }) {
    const params = {
      variable,
      lead_time_hours: leadTimeHours || 24,
      model_id: modelId || 'blended',
    }
    const res = await apiClient.get('/forecast/grid', { params })
    return res.data
  },

  // Regional adaptive weights
  async getWeightsMap({ variable, leadTimeHours }) {
    const params = {
      variable: variable || 'precipitation',
      lead_time_hours: leadTimeHours || 24,
    }
    const res = await apiClient.get('/weights/map', { params })
    return res.data
  },

  // IMD Extreme alerts
  async getExtremeAlerts({ leadTimeHours }) {
    const params = {
      lead_time_hours: leadTimeHours || 24,
    }
    const res = await apiClient.get('/extremes/alerts', { params })
    return res.data
  },

  // Comparative verification skill metrics
  async getSkillMetrics({ variable, leadTimeHours }) {
    const params = {
      variable: variable || 'precipitation',
      lead_time_hours: leadTimeHours || 48,
    }
    const res = await apiClient.get('/metrics/skill-score', { params })
    return res.data
  },

  // Current weather regime
  async getCurrentRegime() {
    const res = await apiClient.get('/regimes/current')
    return res.data
  },
}

export default apiService
