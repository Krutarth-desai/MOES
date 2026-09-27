import React, { useState, useEffect } from 'react'
import Navbar from '../components/Navbar'
import RegimeBanner from '../components/RegimeBanner'
import AlertsPanel from '../components/AlertsPanel'
import WeatherMapView from '../maps/WeatherMapView'
import MeteogramChart from '../charts/MeteogramChart'
import SkillChart from '../charts/SkillChart'
import WeightRadar from '../charts/WeightRadar'
import apiService from '../services/api'
import { WeatherVariables } from '../types'

export default function Dashboard() {
  const [selectedVariable, setSelectedVariable] = useState(WeatherVariables.PRECIPITATION)
  const [selectedLeadTime, setSelectedLeadTime] = useState(48)
  const [stations, setStations] = useState([])
  const [selectedStation, setSelectedStation] = useState(null)
  const [pointData, setPointData] = useState(null)
  const [gridData, setGridData] = useState(null)
  const [weightsData, setWeightsData] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [metricsData, setMetricsData] = useState(null)
  const [activeRegime, setActiveRegime] = useState(null)
  const [loading, setLoading] = useState(true)

  // 1. Initial Load: Stations & Regime
  useEffect(() => {
    async function init() {
      try {
        const [stList, regime] = await Promise.all([
          apiService.getStations(),
          apiService.getCurrentRegime(),
        ])
        setStations(stList)
        setActiveRegime(regime)
        // Default to Mumbai (Santacruz)
        const defaultSt = stList.find((s) => s.name.includes('Mumbai')) || stList[0]
        setSelectedStation(defaultSt)
      } catch (err) {
        console.error('Initialization error:', err)
      }
    }
    init()
  }, [])

  // 2. Fetch Point Forecast when Station or Variable changes
  useEffect(() => {
    if (!selectedStation) return
    async function loadPoint() {
      try {
        const data = await apiService.getPointForecast({
          lat: selectedStation.lat,
          lon: selectedStation.lon,
          variable: selectedVariable,
        })
        setPointData(data)
      } catch (err) {
        console.error('Error fetching point forecast:', err)
      }
    }
    loadPoint()
  }, [selectedStation, selectedVariable])

  // 3. Fetch Gridded Slice, Weights, Alerts, and Metrics when Variable/LeadTime changes
  useEffect(() => {
    async function loadData() {
      setLoading(true)
      try {
        const [grid, weights, alts, metrics] = await Promise.all([
          apiService.getGriddedForecast({
            variable: selectedVariable,
            leadTimeHours: selectedLeadTime,
            modelId: 'blended',
          }),
          apiService.getWeightsMap({
            variable: selectedVariable,
            leadTimeHours: selectedLeadTime,
          }),
          apiService.getExtremeAlerts({ leadTimeHours: selectedLeadTime }),
          apiService.getSkillMetrics({
            variable: selectedVariable,
            leadTimeHours: selectedLeadTime,
          }),
        ])
        setGridData(grid)
        setWeightsData(weights)
        setAlerts(alts)
        setMetricsData(metrics)
      } catch (err) {
        console.error('Error loading dashboard data:', err)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [selectedVariable, selectedLeadTime])

  return (
    <div>
      <Navbar
        selectedVariable={selectedVariable}
        onVariableChange={setSelectedVariable}
        selectedLeadTime={selectedLeadTime}
        onLeadTimeChange={setSelectedLeadTime}
        activeRegime={activeRegime}
      />

      <main className="dashboard-container">
        {/* Synoptic Weather Regime & Blending Logic Context */}
        <RegimeBanner regimeData={activeRegime} leadTimeHours={selectedLeadTime} />

        {/* Primary Row: Spatial GIS Map + Severe Hazard Alert Center */}
        <div className="grid-main">
          <WeatherMapView
            stations={stations}
            selectedStation={selectedStation}
            onStationSelect={(st) => setSelectedStation(st)}
            alerts={alerts}
            variable={selectedVariable}
            gridData={gridData}
          />
          <AlertsPanel alerts={alerts} />
        </div>

        {/* Secondary Row: 7-Day Point Meteogram with Ensemble Envelope */}
        <div>
          <MeteogramChart pointData={pointData} />
        </div>

        {/* Tertiary Row: Regional Weight Inspector & Quantitative Skill Scorecard */}
        <div className="grid-secondary">
          <WeightRadar weightsData={weightsData} />
          <SkillChart metricsData={metricsData} />
        </div>
      </main>
    </div>
  )
}
