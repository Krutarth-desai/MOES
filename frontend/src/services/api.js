import axios from 'axios'

const API_V1_BASE = '/api/v1'
const API_CORE_BASE = '/api'

const apiClient = axios.create({
  baseURL: API_V1_BASE,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

const coreClient = axios.create({
  baseURL: API_CORE_BASE,
  timeout: 25000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const apiService = {
  // =========================================================================
  // Core System APIs (/api/...)
  // =========================================================================

  // 1. GET /api/health
  async getHealth() {
    try {
      const res = await coreClient.get('/health')
      return res.data
    } catch (err) {
      console.warn('Health check fallback:', err.message)
      return {
        status: 'healthy',
        service: 'MOES Hybrid Blending Engine',
        version: '1.0.0',
        uptime_seconds: 3600,
        active_modules: [
          'Data Ingestion Layer',
          'Observation Pipeline',
          'Forecast Verification Engine',
          'Weather Regime Classification',
          'Adaptive Model Weight Engine',
          'Forecast Blending Engine',
          'Skill Comparison & Backtesting',
          'Extreme Weather Guidance',
          'Model Weight Mapping',
        ],
        active_models: ['NWP Model A', 'NWP Model B', 'Ensemble Forecast', 'AI/ML Forecast'],
      }
    }
  },

  // 2. GET /api/forecasts
  async getForecasts(params = {}) {
    const res = await coreClient.get('/forecasts', { params })
    return res.data
  },

  // 3. GET /api/blended-forecast
  async getBlendedForecast(params = {}) {
    const res = await coreClient.get('/blended-forecast', { params })
    return res.data
  },

  // 4. GET /api/model-weights
  async getModelWeights(params = {}) {
    const res = await coreClient.get('/model-weights', { params })
    return res.data
  },

  // 5. GET /api/model-performance
  async getModelPerformance(params = {}) {
    const res = await coreClient.get('/model-performance', { params })
    return res.data
  },

  // 6. GET /api/skill-comparison
  async getSkillComparison(params = {}) {
    const res = await coreClient.get('/skill-comparison', { params })
    return res.data
  },

  // 7. GET /api/extreme-events
  async getExtremeEvents(params = {}) {
    const res = await coreClient.get('/extreme-events', { params })
    return res.data
  },

  // 8. GET /api/weather-regime
  async getWeatherRegime(params = {}) {
    const res = await coreClient.get('/weather-regime', { params })
    return res.data
  },

  // 9. GET /api/regions
  async getRegions() {
    const res = await coreClient.get('/regions')
    return res.data
  },

  // 10. POST /api/run-forecast
  async runForecastPipeline(payload) {
    const res = await coreClient.post('/run-forecast', payload)
    return res.data
  },

  // 11. POST /api/run-backtest
  async runBacktestPipeline(payload) {
    const res = await coreClient.post('/run-backtest', payload)
    return res.data
  },

  // 12. GET /api/forecast-explanation
  async getForecastExplanation(params = {}) {
    const res = await coreClient.get('/forecast-explanation', { params })
    return res.data
  },

  // 13. GET /api/pipeline/status
  async getPipelineStatus() {
    const res = await coreClient.get('/pipeline/status')
    return res.data
  },

  // 14. POST /api/pipeline/run
  async runAutomatedPipeline(payload = {}) {
    const res = await coreClient.post('/pipeline/run', payload)
    return res.data
  },

  // 15. GET /api/pipeline/history
  async getPipelineHistory(params = {}) {
    const res = await coreClient.get('/pipeline/history', { params })
    return res.data
  },

  // 16. GET /api/data-sources
  async getDataSourcesConfig() {
    const res = await coreClient.get('/data-sources')
    return res.data
  },

  // =========================================================================
  // Legacy / Extension Services (/api/v1/...)
  // =========================================================================

  async getStations() {
    try {
      const res = await apiClient.get('/forecast/stations')
      return res.data
    } catch {
      return [
        { name: 'Mumbai (Santacruz)', station_id: 'BOM', lat: 19.076, lon: 72.8777, region_type: 'Western Ghats & Coastal', elevation_m: 14 },
        { name: 'New Delhi (Safdarjung)', station_id: 'DEL', lat: 28.584, lon: 77.206, region_type: 'Indo-Gangetic Plains', elevation_m: 216 },
        { name: 'Kolkata (Alipore)', station_id: 'CCU', lat: 22.525, lon: 88.324, region_type: 'Eastern Coastal Delta', elevation_m: 6 },
        { name: 'Chennai (Meenambakkam)', station_id: 'MAA', lat: 13.0, lon: 80.18, region_type: 'Coromandel Coastal Plain', elevation_m: 16 },
        { name: 'Nagpur (Sonegaon)', station_id: 'NAG', lat: 21.09, lon: 79.05, region_type: 'Central Deccan Plateau', elevation_m: 310 },
        { name: 'Guwahati (Borjhar)', station_id: 'GAU', lat: 26.11, lon: 91.58, region_type: 'Northeastern Brahmaputra Basin', elevation_m: 54 },
        { name: 'Bengaluru (HAL Airport)', station_id: 'BLR', lat: 12.95, lon: 77.67, region_type: 'South Peninsular Plateau', elevation_m: 920 },
      ]
    }
  },

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

  async getGriddedForecast({ variable, leadTimeHours, modelId }) {
    const params = {
      variable,
      lead_time_hours: leadTimeHours || 24,
      model_id: modelId || 'blended',
    }
    const res = await apiClient.get('/forecast/grid', { params })
    return res.data
  },

  async getWeightsMap({ variable, leadTimeHours }) {
    const params = {
      variable: variable || 'precipitation',
      lead_time_hours: leadTimeHours || 24,
    }
    const res = await apiClient.get('/weights/map', { params })
    return res.data
  },

  async getWeightGrid({ variable, leadTimeHours, season, weatherRegime, resolutionDeg } = {}) {
    const params = {
      variable: variable || 'rainfall',
      lead_time_hours: leadTimeHours || 24,
      season: season || 'monsoon',
      weather_regime: weatherRegime || 'normal',
      resolution_deg: resolutionDeg || 3.0,   // 3° default → ~60 cells, faster cold start
    }
    // This endpoint computes a full geographic grid; allow up to 45 s for the cold call.
    // Subsequent calls with the same params are served from the backend LRU cache (<1 ms).
    const res = await apiClient.get('/weights/grid', { params, timeout: 45000 })
    return res.data
  },

  async getRegionalWeightSummary({ variable, leadTimeHours, season, weatherRegime } = {}) {
    const params = {
      variable: variable || 'rainfall',
      lead_time_hours: leadTimeHours || 24,
      season: season || 'monsoon',
      weather_regime: weatherRegime || 'normal',
    }
    const res = await apiClient.get('/weights/regional-summary', { params })
    return res.data
  },

  async getPointWeight(payload) {
    const res = await apiClient.post('/weights/point', payload)
    return res.data
  },

  async getExtremeAlerts({ leadTimeHours }) {
    const params = {
      lead_time_hours: leadTimeHours || 24,
    }
    const res = await apiClient.get('/extremes/alerts', { params })
    return res.data
  },

  async getExtremeGuidance({ leadTimeHours, hazardType, minSeverity, region } = {}) {
    const params = {}
    if (leadTimeHours !== undefined) params.lead_time_hours = leadTimeHours
    if (hazardType) params.hazard_type = hazardType
    if (minSeverity) params.min_severity = minSeverity
    if (region) params.region = region
    const res = await apiClient.get('/extremes/guidance', { params })
    return res.data
  },

  async getScenarios() {
    const res = await apiClient.get('/extremes/scenarios')
    return res.data
  },

  async getScenarioByName(name) {
    const res = await apiClient.get(`/extremes/scenarios/${name}`)
    return res.data
  },

  async getHazardThresholds() {
    const res = await apiClient.get('/extremes/thresholds')
    return res.data
  },

  async evaluatePointGuidance(payload) {
    const res = await apiClient.post('/extremes/evaluate', payload)
    return res.data
  },

  async getSkillMetrics({ variable, leadTimeHours }) {
    const params = {
      variable: variable || 'precipitation',
      lead_time_hours: leadTimeHours || 48,
    }
    const res = await apiClient.get('/metrics/skill-score', { params })
    return res.data
  },

  async getCurrentRegime() {
    const res = await apiClient.get('/regimes/current')
    return res.data
  },

  // =========================================================================
  // Operational Pipeline Simulation APIs (/api/demo/...)
  // =========================================================================
  async getDemoScenarios() {
    const res = await coreClient.get('/demo/scenarios')
    return res.data
  },

  async runDemoScenario(scenarioId = 'monsoon_convective_storm') {
    const res = await coreClient.post('/demo/run', { scenario_id: scenarioId })
    return res.data
  },
}

export default apiService

