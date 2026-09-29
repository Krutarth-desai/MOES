import React, { useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Circle, Polyline, Polygon, Tooltip } from 'react-leaflet'
import {
  Globe,
  Layers,
  AlertTriangle,
  PieChart,
  MapPin,
  Wind,
  Compass,
  Eye,
  Sliders,
  Maximize2,
  Info,
  CheckCircle,
} from 'lucide-react'

// Center coordinates for India & Subcontinent
const INDIA_CENTER = [22.8, 79.5]

export default function WeatherMapView({
  stations = [],
  selectedStation,
  onStationSelect,
  alerts = [],
  variable = 'rainfall',
  gridData,
  weightGridData,
  selectedLeadTime = 24,
  onLeadTimeChange,
  isHeroMode = false,
}) {
  // Map visualization layers:
  // 1. dominant_model: Regional model allocation
  // 2. weight_distribution: Spatial model entropy & weights
  // 3. forecast_values: Forecast intensity field (rain/temp/wind)
  // 4. wind_streamlines: Directional wind vector field & streamlines
  // 5. extreme_weather: IMD active hazard impact zones
  const [mapLayer, setMapLayer] = useState('dominant_model')
  const [showStations, setShowStations] = useState(true)
  const [showRadarGrid, setShowRadarGrid] = useState(true)
  const [basemap, setBasemap] = useState('osm') // Default to vibrant full-color OpenStreetMap
  const [hoveredFeature, setHoveredFeature] = useState(null)

  const basemapUrls = {
    osm: {
      url: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      name: 'OpenStreetMap (Full Color)',
      maxZoom: 19,
    },
    topo: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}',
      attribution: '&copy; Esri &mdash; Esri, DeLorme, NAVTEQ, TomTom',
      name: 'World Topography & Terrain',
      maxZoom: 18,
    },
    satellite: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      attribution: '&copy; Esri, Maxar, Earthstar Geographics, USDA, USGS',
      name: 'Satellite True Color',
      maxZoom: 18,
    },
    ocean: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}',
      attribution: '&copy; Esri, GEBCO, NOAA, DeLorme',
      name: 'Maritime & Ocean Bathymetry',
      maxZoom: 13,
    },
    canvas: {
      url: 'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      attribution: '&copy; Esri &mdash; Esri, DeLorme, NAVTEQ',
      name: 'Muted Light Gray Canvas',
      maxZoom: 16,
    },
  }

  const modelColorMap = {
    'NWP Model A': '#2563EB',       // Vivid Royal Blue (GFS / Physical NWP)
    'NWP Model B': '#10B981',       // Vivid Emerald Green (ECMWF IFS)
    'Ensemble Forecast': '#F59E0B',  // Vibrant Amber / Gold (GEFS Multi-Ensemble)
    'AI/ML Forecast': '#8B5CF6',     // Neon Violet / Purple (GraphCast Neural)
  }

  // Meteorological Regional Boundaries across India with dominant models
  const meteorologicalRegions = [
    {
      id: 'reg-west-ghats',
      name: 'Western Ghats & Konkan Coast',
      dominantModel: 'NWP Model B',
      weight: 0.38,
      coords: [
        [14.2, 73.8], [17.5, 72.8], [20.2, 72.6], [20.5, 74.2], [17.0, 75.2], [14.0, 75.0]
      ],
      forecastVal: '44.8 mm / 28 km/h',
      reason: 'ECMWF high-resolution orographic precipitation physics',
    },
    {
      id: 'reg-indo-gangetic',
      name: 'Indo-Gangetic Plains & North',
      dominantModel: 'NWP Model A',
      weight: 0.36,
      coords: [
        [25.5, 75.5], [29.5, 75.2], [30.8, 77.5], [27.8, 84.5], [24.8, 83.5]
      ],
      forecastVal: '18.2 mm / 18 km/h',
      reason: 'GFS global thermal boundary layer skill',
    },
    {
      id: 'reg-central-deccan',
      name: 'Central Deccan & Plateau',
      dominantModel: 'AI/ML Forecast',
      weight: 0.34,
      coords: [
        [17.8, 76.2], [22.8, 76.5], [23.2, 82.2], [18.2, 81.5]
      ],
      forecastVal: '34.2°C / 22 km/h',
      reason: 'GraphCast non-linear multi-level geopotential skill',
    },
    {
      id: 'reg-eastern-delta',
      name: 'Eastern Coastal Delta & Bengal',
      dominantModel: 'Ensemble Forecast',
      weight: 0.35,
      coords: [
        [20.5, 84.5], [24.5, 86.0], [25.0, 90.5], [21.5, 89.2]
      ],
      forecastVal: '68.4 mm / 42 km/h',
      reason: 'Multi-ensemble dispersion captures convective cyclogenesis',
    },
    {
      id: 'reg-thar-desert',
      name: 'Thar Desert & Northwest Fringe',
      dominantModel: 'NWP Model A',
      weight: 0.40,
      coords: [
        [24.0, 69.8], [28.8, 70.2], [28.2, 74.8], [24.2, 73.2]
      ],
      forecastVal: '41.5°C / 26 km/h',
      reason: 'Dry-line radiation balance and thermal advection',
    },
    {
      id: 'reg-south-peninsula',
      name: 'Southern Peninsula & Coromandel',
      dominantModel: 'NWP Model B',
      weight: 0.35,
      coords: [
        [8.2, 77.0], [13.8, 74.8], [14.2, 80.2], [9.2, 79.2]
      ],
      forecastVal: '28.5 mm / 34 km/h',
      reason: 'Equatorial maritime boundary friction calibration',
    },
  ]

  // Pre-configured extreme weather hazard regions across India
  const extremeRegions = [
    {
      name: 'Konkan & Western Ghats',
      lat: 18.9,
      lon: 73.1,
      radiusKm: 130,
      severity: 'red',
      hazard: 'Extremely Heavy Rainfall & Gale Squall',
      forecastVal: '142.5 mm / 68 km/h',
      threshold: '≥ 115.5 mm (Red Alert)',
      alertCat: 'Take Immediate Action',
      contributingModels: 'NWP Model B (38%), AI Model (32%)',
    },
    {
      name: 'Eastern Coastal Delta & Sundarbans',
      lat: 22.1,
      lon: 88.6,
      radiusKm: 145,
      severity: 'orange',
      hazard: 'High Coastal Squall & Heavy Rain',
      forecastVal: '88.0 mm / 62 km/h',
      threshold: '≥ 64.5 mm (Orange Alert)',
      alertCat: 'Be Prepared',
      contributingModels: 'NWP Model A (36%), Ensemble (34%)',
    },
    {
      name: 'Vidarbha & Central Deccan',
      lat: 21.1,
      lon: 79.1,
      radiusKm: 115,
      severity: 'yellow',
      hazard: 'Convective Gusts & Subsidence Heat',
      forecastVal: '44.2°C / 48 km/h',
      threshold: '≥ 40.0°C (Yellow Watch)',
      alertCat: 'Be Updated',
      contributingModels: 'AI Model (36%), NWP Model B (30%)',
    },
  ]

  // Synthesized synoptic wind vector field across India
  const windVectorGrid = [
    { lat: 18.9, lon: 72.8, deg: 245, speed: 44, region: 'Arabian Sea / West Coast' },
    { lat: 15.3, lon: 73.8, deg: 240, speed: 48, region: 'Goa Coastal' },
    { lat: 13.0, lon: 80.2, deg: 190, speed: 28, region: 'Coromandel Coast' },
    { lat: 22.5, lon: 88.3, deg: 160, speed: 38, region: 'Bay of Bengal Head' },
    { lat: 28.6, lon: 77.2, deg: 310, speed: 22, region: 'Indo-Gangetic Plain' },
    { lat: 26.9, lon: 75.8, deg: 320, speed: 26, region: 'Thar Desert Fringe' },
    { lat: 21.1, lon: 79.0, deg: 260, speed: 32, region: 'Central Plateau' },
    { lat: 12.9, lon: 77.6, deg: 250, speed: 35, region: 'Southern Peninsula' },
    { lat: 25.5, lon: 85.1, deg: 120, speed: 20, region: 'Middle Ganges Valley' },
    { lat: 26.1, lon: 91.7, deg: 90, speed: 18, region: 'Brahmaputra Basin' },
    { lat: 31.1, lon: 77.1, deg: 330, speed: 30, region: 'Western Himalayan Ridge' },
    { lat: 17.3, lon: 78.4, deg: 245, speed: 31, region: 'Telangana Plateau' },
  ]

  // Helper to draw wind streamline line segment
  const getWindLine = (lat, lon, deg, lengthKm = 75) => {
    const rad = ((deg + 180) % 360) * (Math.PI / 180)
    const dLat = (lengthKm / 111) * Math.cos(rad)
    const dLon = (lengthKm / (111 * Math.cos(lat * (Math.PI / 180)))) * Math.sin(rad)
    return [
      [lat, lon],
      [lat + dLat, lon + dLon],
    ]
  }

  // Active basemap config
  const activeBasemap = basemapUrls[basemap] || basemapUrls.canvas

  return (
    <div className="weather-card gis-command-card" style={{ padding: 0, overflow: 'hidden' }}>
      {/* Top GIS Command Bar */}
      <div className="gis-command-header">
        <div className="gis-title-group">
          <div className="weather-icon-badge" style={{ background: 'rgba(37, 99, 235, 0.15)', color: '#2563EB' }}>
            <Globe size={18} />
          </div>
          <div>
            <div className="gis-title">
              <span>National Meteorological GIS Command Canvas</span>
              <span className="live-telemetry-tag">
                <span className="live-dot" />
                OPERATIONAL GIS
              </span>
            </div>
            <span className="gis-subtitle">
              India Subcontinent Domain · Ground Truth Calibration · T+{selectedLeadTime}h Horizon
            </span>
          </div>
        </div>

        {/* Layer Selector & Controls */}
        <div className="gis-controls-cluster">
          {/* 5 Layer Switcher */}
          <div className="gis-layer-tabs">
            <button
              onClick={() => setMapLayer('dominant_model')}
              className={`gis-tab-btn ${mapLayer === 'dominant_model' ? 'active' : ''}`}
              title="Regional dominant model allocation"
            >
              <Layers size={13} />
              <span>Dominant Model</span>
            </button>

            <button
              onClick={() => setMapLayer('weight_distribution')}
              className={`gis-tab-btn ${mapLayer === 'weight_distribution' ? 'active' : ''}`}
              title="Consensus entropy & weight balance"
            >
              <PieChart size={13} />
              <span>Weight Dispersion</span>
            </button>

            <button
              onClick={() => setMapLayer('forecast_values')}
              className={`gis-tab-btn ${mapLayer === 'forecast_values' ? 'active' : ''}`}
              title="Continuous forecast intensity field"
            >
              <Globe size={13} />
              <span>Forecast Field</span>
            </button>

            <button
              onClick={() => setMapLayer('wind_streamlines')}
              className={`gis-tab-btn ${mapLayer === 'wind_streamlines' ? 'active' : ''}`}
              title="Yamartino wind streamlines & vectors"
            >
              <Wind size={13} />
              <span>Wind Vectors</span>
            </button>

            <button
              onClick={() => setMapLayer('extreme_weather')}
              className={`gis-tab-btn hazard-tab ${mapLayer === 'extreme_weather' ? 'active' : ''}`}
              title="IMD active hazard warnings"
            >
              <AlertTriangle size={13} />
              <span>Hazard Zones</span>
            </button>
          </div>

          {/* Basemap Switcher & Overlays */}
          <div className="gis-aux-controls">
            <select
              value={basemap}
              onChange={(e) => setBasemap(e.target.value)}
              className="gis-basemap-select"
              title="Select GIS Basemap"
            >
              <option value="osm">Basemap: OpenStreetMap (Full Color)</option>
              <option value="topo">Basemap: World Topography & Terrain</option>
              <option value="satellite">Basemap: High-Res Satellite True Color</option>
              <option value="ocean">Basemap: Maritime Ocean Bathymetry</option>
              <option value="canvas">Basemap: Muted Light Gray Canvas</option>
            </select>

            <button
              onClick={() => setShowStations(!showStations)}
              className={`gis-pill-btn ${showStations ? 'active' : ''}`}
              title="Toggle IMD AWS observation stations"
            >
              <MapPin size={12} />
              <span>AWS Stations</span>
            </button>
          </div>
        </div>
      </div>

      {/* Map View Canvas Container */}
      <div className="gis-canvas-wrapper" style={{ height: isHeroMode ? '540px' : '680px', width: '100%', position: 'relative' }}>
        <MapContainer
          center={INDIA_CENTER}
          zoom={5}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%', background: '#EAF2F7' }}
        >
          {/* Scientific Esri / OpenStreetMap Basemap (Zero Watermarks, 100% Free) */}
          <TileLayer
            key={activeBasemap.url}
            attribution={activeBasemap.attribution}
            url={activeBasemap.url}
            maxZoom={activeBasemap.maxZoom || 18}
          />

          {/* LAYER 1: Dominant Model Regional Polygons & Grid */}
          {mapLayer === 'dominant_model' && (
            <>
              {/* Regional Meteorological Sectors */}
              {meteorologicalRegions.map((reg) => {
                const color = modelColorMap[reg.dominantModel] || '#2563EB'
                return (
                  <Polygon
                    key={reg.id}
                    positions={reg.coords}
                    pathOptions={{
                      fillColor: color,
                      fillOpacity: 0.28,
                      color: color,
                      weight: 2.2,
                      dashArray: '5, 5',
                    }}
                    eventHandlers={{
                      mouseover: () => setHoveredFeature({
                        title: reg.name,
                        dominant: `${reg.dominantModel} (${Math.round(reg.weight * 100)}%)`,
                        forecast: reg.forecastVal,
                        note: reg.reason,
                      }),
                      mouseout: () => setHoveredFeature(null),
                    }}
                  >
                    <Tooltip direction="center" permanent={false}>
                      <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#0F172A' }}>
                        {reg.name}
                        <div style={{ color, fontSize: '0.72rem', fontWeight: 800 }}>
                          Dominant: {reg.dominantModel} ({Math.round(reg.weight * 100)}%)
                        </div>
                      </div>
                    </Tooltip>
                  </Polygon>
                )
              })}

              {/* Grid cell nodes with high-contrast color pins */}
              {weightGridData?.grid_cells?.map((cell, idx) => {
                const cellColor = modelColorMap[cell.dominant_model] || cell.color || '#2563EB'
                const fillOpacity = Math.min(0.95, Math.max(0.65, cell.dominant_weight * 1.5))

                return (
                  <CircleMarker
                    key={`dom-cell-${idx}`}
                    center={[cell.lat, cell.lon]}
                    radius={8}
                    pathOptions={{
                      fillColor: cellColor,
                      fillOpacity: fillOpacity,
                      color: '#ffffff',
                      weight: 2,
                    }}
                  >
                    <Tooltip direction="top" offset={[0, -6]}>
                      <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A' }}>
                        {cell.region_name}: <span style={{ color: cellColor, fontWeight: 800 }}>{cell.dominant_model} ({Math.round(cell.dominant_weight * 100)}%)</span>
                      </div>
                    </Tooltip>
                  </CircleMarker>
                )
              })}
            </>
          )}

          {/* LAYER 2: Model Weight Dispersion (Entropy Heat Nodes - Vibrant Traffic Spectrum) */}
          {mapLayer === 'weight_distribution' &&
            weightGridData?.grid_cells?.map((cell, idx) => {
              const entropy = cell.weight_distribution?.entropy ?? 0.88
              const radius = 7 + Math.round(entropy * 7)
              
              // Multi-color consensus spectrum: High Agreement (Green) -> Moderate Spread (Amber) -> High Dispersion (Red)
              let nodeColor = '#10B981'
              let labelText = 'High Consensus'
              if (entropy >= 0.90) {
                nodeColor = '#EF4444'
                labelText = 'High Dispersion (Disagreement)'
              } else if (entropy >= 0.78) {
                nodeColor = '#F59E0B'
                labelText = 'Moderate Spread'
              }

              return (
                <CircleMarker
                  key={`dist-cell-${idx}`}
                  center={[cell.lat, cell.lon]}
                  radius={radius}
                  pathOptions={{
                    fillColor: nodeColor,
                    fillOpacity: 0.85,
                    color: '#ffffff',
                    weight: 2,
                  }}
                >
                  <Tooltip direction="top">
                    <div style={{ fontSize: '0.74rem', color: '#0F172A' }}>
                      <strong>{cell.region_name}</strong>
                      <div>Status: <span style={{ color: nodeColor, fontWeight: 700 }}>{labelText}</span></div>
                      <div>Entropy: <strong>{entropy}</strong> / 1.0</div>
                    </div>
                  </Tooltip>
                </CircleMarker>
              )
            })}

          {/* LAYER 3: Continuous Forecast Field (Rainfall / Temp / Wind Rainbow Spectrum) */}
          {mapLayer === 'forecast_values' &&
            gridData?.cells?.map((cell, idx) => {
              let fillColor = '#06B6D4'
              let radius = 6

              if (variable.includes('temp')) {
                // Thermal Rainbow Spectrum
                if (cell.value >= 42) { fillColor = '#DC2626'; radius = 10 }
                else if (cell.value >= 38) { fillColor = '#EA580C'; radius = 8.5 }
                else if (cell.value >= 32) { fillColor = '#F59E0B'; radius = 7.5 }
                else if (cell.value >= 25) { fillColor = '#10B981'; radius = 6.5 }
                else { fillColor = '#06B6D4'; radius = 5.5 }
              } else if (variable.includes('wind') || variable.includes('gust')) {
                // Wind Speed Spectrum
                if (cell.value >= 55) { fillColor = '#DC2626'; radius = 10 }
                else if (cell.value >= 40) { fillColor = '#F59E0B'; radius = 8.5 }
                else if (cell.value >= 25) { fillColor = '#10B981'; radius = 7 }
                else { fillColor = '#06B6D4'; radius = 5.5 }
              } else {
                // WMO Meteorological Precipitation Reflectivity Spectrum
                if (cell.value >= 75) { fillColor = '#7C3AED'; radius = 10 }       // Extreme Purple / Violet
                else if (cell.value >= 45) { fillColor = '#EF4444'; radius = 8.5 }  // Heavy Orange-Red
                else if (cell.value >= 25) { fillColor = '#F59E0B'; radius = 7.5 }  // Moderate Amber
                else if (cell.value >= 10) { fillColor = '#10B981'; radius = 6.5 }  // Light Green
                else { fillColor = '#06B6D4'; radius = 5.5 }                        // Trace Cyan
              }

              return (
                <CircleMarker
                  key={`forecast-cell-${idx}`}
                  center={[cell.lat, cell.lon]}
                  radius={radius}
                  pathOptions={{
                    fillColor,
                    fillOpacity: 0.90,
                    color: '#ffffff',
                    weight: 1.8,
                  }}
                >
                  <Tooltip direction="top">
                    <div style={{ fontSize: '0.74rem', color: '#0F172A' }}>
                      <strong>{variable.toUpperCase()}</strong>: <span style={{ color: fillColor, fontWeight: 800 }}>{cell.value} {cell.unit || (variable.includes('temp') ? '°C' : 'mm')}</span>
                    </div>
                  </Tooltip>
                </CircleMarker>
              )
            })}

          {/* LAYER 4: Directional Wind Streamlines (Color-graded by Velocity) */}
          {mapLayer === 'wind_streamlines' &&
            windVectorGrid.map((wv, idx) => {
              const lineCoords = getWindLine(wv.lat, wv.lon, wv.deg, 85)
              let lineColor = '#06B6D4' // Moderate Cyan (<30 km/h)
              let lineWeight = 2.4
              let markerRadius = 5.5

              if (wv.speed >= 45) {
                lineColor = '#EF4444' // Gale Red
                lineWeight = 3.8
                markerRadius = 7.5
              } else if (wv.speed >= 30) {
                lineColor = '#F59E0B' // Strong Amber
                lineWeight = 3.0
                markerRadius = 6.5
              }

              return (
                <React.Fragment key={`wind-stream-${idx}`}>
                  <Polyline
                    positions={lineCoords}
                    pathOptions={{
                      color: lineColor,
                      weight: lineWeight,
                      dashArray: '6, 6',
                      opacity: 0.95,
                    }}
                  />
                  <CircleMarker
                    center={[wv.lat, wv.lon]}
                    radius={markerRadius}
                    pathOptions={{
                      fillColor: lineColor,
                      fillOpacity: 0.95,
                      color: '#ffffff',
                      weight: 2,
                    }}
                  >
                    <Tooltip direction="top">
                      <div style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A' }}>
                        {wv.region}: <span style={{ color: lineColor }}>{wv.speed} km/h @ {wv.deg}°</span>
                      </div>
                    </Tooltip>
                  </CircleMarker>
                </React.Fragment>
              )
            })}

          {/* LAYER 5: Extreme Weather Hazard Halo Zones (Official IMD Warning Colors) */}
          {mapLayer === 'extreme_weather' &&
            extremeRegions.map((reg, idx) => {
              const warningColor = reg.severity === 'red' ? '#EF4444' : reg.severity === 'orange' ? '#F97316' : '#EAB308'

              return (
                <React.Fragment key={`extreme-reg-${idx}`}>
                  <Circle
                    center={[reg.lat, reg.lon]}
                    radius={reg.radiusKm * 1000}
                    pathOptions={{
                      fillColor: warningColor,
                      fillOpacity: 0.25,
                      color: warningColor,
                      weight: 2.5,
                      dashArray: '5, 5',
                    }}
                  />
                  <CircleMarker
                    center={[reg.lat, reg.lon]}
                    radius={10}
                    pathOptions={{
                      fillColor: warningColor,
                      fillOpacity: 0.95,
                      color: '#ffffff',
                      weight: 2.5,
                    }}
                  >
                    <Popup>
                      <div style={{ color: '#0F172A', padding: '6px', maxWidth: '250px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                          <span style={{ fontSize: '0.70rem', fontWeight: 800, color: '#ffffff', background: warningColor, padding: '3px 8px', borderRadius: '4px' }}>
                            IMD {reg.severity.toUpperCase()} ALERT
                          </span>
                        </div>
                        <h4 style={{ fontSize: '0.90rem', fontWeight: 800, marginBottom: '3px' }}>{reg.name}</h4>
                        <div style={{ fontSize: '0.76rem', fontWeight: 600, color: warningColor, marginBottom: '6px' }}>{reg.hazard}</div>
                        <div style={{ fontSize: '0.73rem', background: '#F8FAFC', border: '1px solid #E2E8F0', padding: '8px', borderRadius: '6px' }}>
                          <div><strong>Forecast:</strong> {reg.forecastVal}</div>
                          <div><strong>Threshold:</strong> {reg.threshold}</div>
                          <div><strong>Protocol:</strong> {reg.alertCat}</div>
                          <div style={{ marginTop: '4px', fontSize: '0.68rem', color: '#64748B' }}>{reg.contributingModels}</div>
                        </div>
                      </div>
                    </Popup>
                  </CircleMarker>
                </React.Fragment>
              )
            })}

          {/* Observation AWS Stations */}
          {showStations &&
            stations.map((st) => {
              const isSelected = selectedStation && selectedStation.name === st.name
              return (
                <CircleMarker
                  key={st.name}
                  center={[st.lat, st.lon]}
                  radius={isSelected ? 9 : 5.5}
                  pathOptions={{
                    fillColor: isSelected ? '#EF4444' : '#0284C7',
                    fillOpacity: 0.95,
                    color: '#ffffff',
                    weight: isSelected ? 3 : 1.8,
                  }}
                  eventHandlers={{
                    click: () => onStationSelect(st),
                    mouseover: () => setHoveredFeature({
                      title: st.name,
                      dominant: `AWS Station (${st.region_type})`,
                      forecast: `Elev: ${st.elevation_m}m ASL`,
                      note: `${st.lat.toFixed(2)}°N, ${st.lon.toFixed(2)}°E`,
                    }),
                    mouseout: () => setHoveredFeature(null),
                  }}
                >
                  <Tooltip direction="top" offset={[0, -6]}>
                    <span style={{ fontSize: '0.74rem', fontWeight: 700, color: '#0F172A' }}>{st.name}</span>
                  </Tooltip>
                  <Popup>
                    <div style={{ color: '#0F172A', padding: '4px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '5px', marginBottom: '3px' }}>
                        <MapPin size={14} color={isSelected ? '#EF4444' : '#0284C7'} />
                        <h4 style={{ fontWeight: 800, fontSize: '0.88rem' }}>{st.name}</h4>
                      </div>
                      <p style={{ fontSize: '0.73rem', color: '#64748B', margin: '2px 0 6px 0' }}>
                        Zone: {st.region_type} | Elev: {st.elevation_m}m ASL
                      </p>
                      <button
                        onClick={() => onStationSelect(st)}
                        className="gis-popup-action-btn"
                        style={{
                          background: isSelected ? '#EF4444' : '#0284C7',
                          color: '#ffffff',
                          border: 'none',
                          padding: '4px 10px',
                          borderRadius: '4px',
                          fontWeight: 600,
                          cursor: 'pointer',
                        }}
                      >
                        Inspect Station Telemetry
                      </button>
                    </div>
                  </Popup>
                </CircleMarker>
              )
            })}
        </MapContainer>

        {/* Dynamic Scientific Legend Box */}
        <div className="gis-map-legend">
          {mapLayer === 'dominant_model' && (
            <>
              <div className="legend-title">Dominant Forecast Model</div>
              <div className="legend-items-grid">
                {Object.entries(modelColorMap).map(([mName, mColor]) => (
                  <div key={mName} className="legend-item">
                    <span className="legend-color-dot" style={{ background: mColor, boxShadow: `0 0 6px ${mColor}80` }} />
                    <span className="legend-label" style={{ fontWeight: 600 }}>{mName.replace(' Forecast', '').replace('Model ', '')}</span>
                  </div>
                ))}
              </div>
              <div className="legend-note">Calculated via localized Softmax simplex residuals.</div>
            </>
          )}

          {mapLayer === 'wind_streamlines' && (
            <>
              <div className="legend-title">Yamartino Wind Vectors</div>
              <div className="legend-items-row" style={{ display: 'flex', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
                <span className="legend-line" style={{ background: '#06B6D4', width: '20px', height: '3px', display: 'inline-block' }} />
                <span className="legend-label">&lt;30 km/h (Moderate)</span>
                <span className="legend-line" style={{ background: '#F59E0B', width: '20px', height: '3px', display: 'inline-block' }} />
                <span className="legend-label">30–45 km/h (Fresh)</span>
                <span className="legend-line" style={{ background: '#EF4444', width: '20px', height: '3px', display: 'inline-block' }} />
                <span className="legend-label">≥45 km/h (Gale / Squall)</span>
              </div>
            </>
          )}

          {mapLayer === 'forecast_values' && (
            <>
              <div className="legend-title">Consensus Scalar Field ({variable})</div>
              <div className="legend-gradient-bar">
                <span>Low</span>
                <div className="gradient-track" />
                <span>Extreme</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.66rem', color: '#64748B', marginTop: '2px' }}>
                <span>Cyan (Trace)</span>
                <span>Green</span>
                <span>Amber</span>
                <span>Red</span>
                <span>Violet (Peak)</span>
              </div>
            </>
          )}

          {mapLayer === 'extreme_weather' && (
            <>
              <div className="legend-title">IMD Severe Warning Criteria</div>
              <div className="legend-items-row" style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span className="legend-color-dot" style={{ background: '#EF4444', boxShadow: '0 0 6px #EF444480' }} />
                  <span className="legend-label" style={{ color: '#EF4444', fontWeight: 700 }}>Red Alert</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span className="legend-color-dot" style={{ background: '#F97316', boxShadow: '0 0 6px #F9731680' }} />
                  <span className="legend-label" style={{ color: '#F97316', fontWeight: 700 }}>Orange Alert</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span className="legend-color-dot" style={{ background: '#EAB308', boxShadow: '0 0 6px #EAB30880' }} />
                  <span className="legend-label" style={{ color: '#CA8A04', fontWeight: 700 }}>Yellow Watch</span>
                </div>
              </div>
            </>
          )}

          {mapLayer === 'weight_distribution' && (
            <>
              <div className="legend-title">Model Weight Dispersion (Entropy)</div>
              <div className="legend-items-row" style={{ display: 'flex', gap: '12px', alignItems: 'center', margin: '4px 0' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span className="legend-color-dot" style={{ background: '#10B981' }} />
                  <span className="legend-label">Consensus (&lt;0.78)</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span className="legend-color-dot" style={{ background: '#F59E0B' }} />
                  <span className="legend-label">Moderate Spread</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <span className="legend-color-dot" style={{ background: '#EF4444' }} />
                  <span className="legend-label">High Dispersion (≥0.90)</span>
                </div>
              </div>
              <div className="legend-note">Radius and color indicate prediction consensus vs multi-model divergence.</div>
            </>
          )}
        </div>

        {/* Live Hover Location Information Card */}
        {hoveredFeature && (
          <div className="gis-hover-card">
            <div className="gis-hover-header">
              <Info size={13} color="#4D91C9" />
              <strong>{hoveredFeature.title}</strong>
            </div>
            <div className="gis-hover-row">
              <span className="gis-hover-label">Consensus:</span>
              <span className="gis-hover-val">{hoveredFeature.dominant}</span>
            </div>
            <div className="gis-hover-row">
              <span className="gis-hover-label">Forecast:</span>
              <span className="gis-hover-val">{hoveredFeature.forecast}</span>
            </div>
            {hoveredFeature.note && (
              <div className="gis-hover-note">{hoveredFeature.note}</div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
