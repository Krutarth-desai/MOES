import React, { useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, Circle } from 'react-leaflet'
import { Globe, Layers, AlertTriangle, PieChart, Info, MapPin } from 'lucide-react'

// Center coordinates for India
const INDIA_CENTER = [22.3, 79.5]

export default function WeatherMapView({
  stations = [],
  selectedStation,
  onStationSelect,
  alerts = [],
  variable = 'rainfall',
  gridData,
  weightGridData,
}) {
  // 4 Modes as requested:
  // 1. dominant_model: Dominant model by region
  // 2. weight_distribution: Model-weight distribution
  // 3. forecast_values: Forecast values
  // 4. extreme_weather: Extreme-weather regions
  const [mapLayer, setMapLayer] = useState('dominant_model')

  const modelColorMap = {
    'NWP Model A': '#0284c7',       // Sky Blue (GFS)
    'NWP Model B': '#10b981',       // Emerald Green (ECMWF)
    'Ensemble Forecast': '#f59e0b',  // Amber
    'AI/ML Forecast': '#8b5cf6',     // Violet (GraphCast)
  }

  const getMarkerColor = (station, isSelected) => {
    if (isSelected) return '#38bdf8'
    return '#94a3b8'
  }

  // Pre-configured extreme weather hazard regions across India for visual layer demonstration
  const extremeRegions = [
    {
      name: 'Konkan & Western Ghats',
      lat: 18.9,
      lon: 73.1,
      radiusKm: 120,
      severity: 'red',
      hazard: 'Extremely Heavy Rainfall',
      forecastVal: '142 mm',
      threshold: '≥ 115.5 mm (Red Alert)',
      alertCat: 'Take Immediate Action',
      contributingModels: 'NWP Model B (42%), AI/ML Forecast (28%)',
    },
    {
      name: 'Eastern Coastal Delta & Sundarbans',
      lat: 22.1,
      lon: 88.6,
      radiusKm: 140,
      severity: 'orange',
      hazard: 'High Coastal Squall & Heavy Rain',
      forecastVal: '88 mm / 65 km/h',
      threshold: '≥ 64.5 mm (Orange Alert)',
      alertCat: 'Be Prepared',
      contributingModels: 'NWP Model A (38%), Ensemble (32%)',
    },
    {
      name: 'Vidarbha & Central Deccan',
      lat: 21.1,
      lon: 79.1,
      radiusKm: 110,
      severity: 'yellow',
      hazard: 'Convective Gusty Winds',
      forecastVal: '48 km/h',
      threshold: '≥ 40 km/h (Yellow Watch)',
      alertCat: 'Be Updated',
      contributingModels: 'AI/ML Forecast (36%), NWP Model B (30%)',
    },
  ]

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="card-header" style={{ flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'space-between' }}>
        <div className="card-title">
          <Globe size={18} color="#38bdf8" />
          <span>Interactive Meteorological GIS & Spatial Weight Map</span>
        </div>

        {/* 4-Layer Mode Selector Tabs */}
        <div style={{ display: 'flex', background: '#0f172a', padding: '3px', borderRadius: '8px', gap: '3px' }}>
          <button
            onClick={() => setMapLayer('dominant_model')}
            style={{
              background: mapLayer === 'dominant_model' ? 'var(--accent-blue)' : 'transparent',
              color: mapLayer === 'dominant_model' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '5px 9px',
              fontSize: '0.72rem',
              borderRadius: '5px',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Layers size={12} />
            Dominant Model by Region
          </button>

          <button
            onClick={() => setMapLayer('weight_distribution')}
            style={{
              background: mapLayer === 'weight_distribution' ? 'var(--accent-blue)' : 'transparent',
              color: mapLayer === 'weight_distribution' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '5px 9px',
              fontSize: '0.72rem',
              borderRadius: '5px',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <PieChart size={12} />
            Model-Weight Distribution
          </button>

          <button
            onClick={() => setMapLayer('forecast_values')}
            style={{
              background: mapLayer === 'forecast_values' ? 'var(--accent-blue)' : 'transparent',
              color: mapLayer === 'forecast_values' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '5px 9px',
              fontSize: '0.72rem',
              borderRadius: '5px',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <Globe size={12} />
            Forecast Values
          </button>

          <button
            onClick={() => setMapLayer('extreme_weather')}
            style={{
              background: mapLayer === 'extreme_weather' ? '#dc2626' : 'transparent',
              color: mapLayer === 'extreme_weather' ? '#fff' : '#94a3b8',
              border: 'none',
              padding: '5px 9px',
              fontSize: '0.72rem',
              borderRadius: '5px',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '4px',
            }}
          >
            <AlertTriangle size={12} />
            Extreme-Weather Regions
          </button>
        </div>
      </div>

      <div className="map-view-wrapper" style={{ position: 'relative', height: '480px', width: '100%' }}>
        <MapContainer
          center={INDIA_CENTER}
          zoom={5}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%', borderRadius: '0 0 12px 12px' }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://stadia.maps.com">Stadia Maps</a>'
            url="https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png"
          />

          {/* LAYER 1: Dominant Model by Region */}
          {mapLayer === 'dominant_model' &&
            weightGridData?.grid_cells?.map((cell, idx) => {
              const cellColor = cell.color || modelColorMap[cell.dominant_model] || '#38bdf8'
              const fillOpacity = Math.min(0.9, Math.max(0.4, cell.dominant_weight * 1.6))

              return (
                <CircleMarker
                  key={`dominant-grid-${idx}`}
                  center={[cell.lat, cell.lon]}
                  radius={7}
                  pathOptions={{
                    fillColor: cellColor,
                    fillOpacity: fillOpacity,
                    color: '#ffffff',
                    weight: 1.2,
                  }}
                >
                  <Popup>
                    <div style={{ color: '#0f172a', padding: '4px', minWidth: '210px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '3px' }}>
                        <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
                          {cell.lat}°N, {cell.lon}°E
                        </span>
                        <span style={{ fontSize: '0.7rem', background: '#e2e8f0', padding: '1px 5px', borderRadius: '3px' }}>
                          {cell.elevation_m}m
                        </span>
                      </div>
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0f172a', marginBottom: '4px' }}>
                        {cell.region_name}
                      </h4>
                      <div
                        style={{
                          background: `${cellColor}22`,
                          borderLeft: `3px solid ${cellColor}`,
                          padding: '4px 6px',
                          borderRadius: '4px',
                          marginBottom: '6px',
                        }}
                      >
                        <div style={{ fontSize: '0.7rem', color: '#475569' }}>Dominant Contributing Model:</div>
                        <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#0f172a' }}>
                          {cell.dominant_model}: {Math.round(cell.dominant_weight * 100)}%
                        </div>
                      </div>
                      <div style={{ fontSize: '0.68rem', color: '#64748b' }}>
                        Context: Reliability calibrated using historical skill and terrain physics.
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              )
            })}

          {/* LAYER 2: Model-Weight Distribution */}
          {mapLayer === 'weight_distribution' &&
            weightGridData?.grid_cells?.map((cell, idx) => {
              const entropy = cell.weight_distribution?.entropy ?? 0.88
              const radius = 6 + Math.round(entropy * 5)
              return (
                <CircleMarker
                  key={`dist-grid-${idx}`}
                  center={[cell.lat, cell.lon]}
                  radius={radius}
                  pathOptions={{
                    fillColor: '#38bdf8',
                    fillOpacity: 0.75,
                    color: '#ffffff',
                    weight: 1.5,
                  }}
                >
                  <Popup>
                    <div style={{ color: '#0f172a', padding: '4px', minWidth: '220px' }}>
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 700, marginBottom: '2px' }}>
                        {cell.region_name} Weight Distribution
                      </h4>
                      <div style={{ fontSize: '0.72rem', color: '#64748b', marginBottom: '6px' }}>
                        Entropy: <strong>{entropy}</strong> / 1.0 (Sum: 100%)
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        {Object.entries(cell.weights || {}).map(([mName, w]) => (
                          <div key={mName} style={{ fontSize: '0.72rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
                              <span>{mName}</span>
                              <strong>{Math.round(w * 100)}%</strong>
                            </div>
                            <div style={{ width: '100%', height: '5px', background: '#e2e8f0', borderRadius: '3px', overflow: 'hidden' }}>
                              <div
                                style={{
                                  width: `${w * 100}%`,
                                  height: '100%',
                                  background: modelColorMap[mName] || '#0284c7',
                                }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              )
            })}

          {/* LAYER 3: Forecast Values (Spatial Intensity Heatmap) */}
          {mapLayer === 'forecast_values' &&
            gridData?.grid_cells?.map((cell, idx) => {
              let fillColor = 'rgba(56, 189, 248, 0.5)'
              let radius = 6
              if (variable.includes('rain') || variable.includes('precip')) {
                if (cell.value >= 100) { fillColor = '#a855f7'; radius = 8 }
                else if (cell.value >= 50) { fillColor = '#2563eb'; radius = 7 }
                else if (cell.value >= 15) { fillColor = '#38bdf8'; radius = 6 }
                else { fillColor = '#64748b'; radius = 4 }
              } else if (variable.includes('temp')) {
                if (cell.value >= 40) { fillColor = '#ef4444'; radius = 8 }
                else if (cell.value >= 35) { fillColor = '#f97316'; radius = 7 }
                else if (cell.value >= 28) { fillColor = '#eab308'; radius = 6 }
                else { fillColor = '#22c55e'; radius = 5 }
              } else {
                if (cell.value >= 50) { fillColor = '#ef4444'; radius = 8 }
                else if (cell.value >= 30) { fillColor = '#f59e0b'; radius = 6 }
                else { fillColor = '#10b981'; radius = 5 }
              }

              return (
                <CircleMarker
                  key={`forecast-val-${idx}`}
                  center={[cell.lat, cell.lon]}
                  radius={radius}
                  pathOptions={{
                    fillColor,
                    fillOpacity: 0.8,
                    color: '#ffffff',
                    weight: 1,
                  }}
                >
                  <Popup>
                    <div style={{ color: '#0f172a', padding: '4px' }}>
                      <div style={{ fontSize: '0.72rem', color: '#64748b' }}>
                        {cell.lat}°N, {cell.lon}°E
                      </div>
                      <h4 style={{ fontSize: '0.85rem', fontWeight: 700 }}>
                        {variable.toUpperCase()} Blended Value
                      </h4>
                      <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#0284c7', margin: '4px 0' }}>
                        {cell.value} {cell.unit || (variable.includes('temp') ? '°C' : variable.includes('rain') ? 'mm' : 'km/h')}
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              )
            })}

          {/* LAYER 4: Extreme Weather Regions */}
          {mapLayer === 'extreme_weather' &&
            extremeRegions.map((reg, idx) => (
              <React.Fragment key={`extreme-reg-${idx}`}>
                <Circle
                  center={[reg.lat, reg.lon]}
                  radius={reg.radiusKm * 1000}
                  pathOptions={{
                    fillColor: reg.severity === 'red' ? '#ef4444' : reg.severity === 'orange' ? '#f97316' : '#eab308',
                    fillOpacity: 0.25,
                    color: reg.severity === 'red' ? '#dc2626' : reg.severity === 'orange' ? '#ea580c' : '#ca8a04',
                    weight: 2,
                    dashArray: '6, 6',
                  }}
                />
                <CircleMarker
                  center={[reg.lat, reg.lon]}
                  radius={12}
                  pathOptions={{
                    fillColor: reg.severity === 'red' ? '#ef4444' : reg.severity === 'orange' ? '#f97316' : '#eab308',
                    fillOpacity: 0.9,
                    color: '#ffffff',
                    weight: 2,
                  }}
                >
                  <Popup>
                    <div style={{ color: '#0f172a', padding: '4px', minWidth: '220px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                        <span
                          style={{
                            background: reg.severity === 'red' ? '#fee2e2' : '#ffedd5',
                            color: reg.severity === 'red' ? '#b91c1c' : '#c2410c',
                            fontSize: '0.68rem',
                            fontWeight: 700,
                            padding: '2px 6px',
                            borderRadius: '4px',
                            textTransform: 'uppercase',
                          }}
                        >
                          IMD {reg.severity} Warning
                        </span>
                      </div>
                      <h4 style={{ fontSize: '0.9rem', fontWeight: 800, color: '#0f172a', marginBottom: '2px' }}>
                        {reg.name}
                      </h4>
                      <div style={{ fontSize: '0.78rem', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                        {reg.hazard}
                      </div>
                      <div style={{ background: '#f8fafc', padding: '6px', borderRadius: '4px', border: '1px solid #e2e8f0', fontSize: '0.72rem', marginBottom: '6px' }}>
                        <div><strong>Forecast Value:</strong> {reg.forecastVal}</div>
                        <div><strong>Threshold:</strong> {reg.threshold}</div>
                        <div><strong>Action:</strong> {reg.alertCat}</div>
                        <div style={{ marginTop: '2px', color: '#64748b' }}>
                          <strong>Contributing Models:</strong> {reg.contributingModels}
                        </div>
                      </div>
                      <div style={{ fontSize: '0.65rem', color: '#94a3b8', fontStyle: 'italic' }}>
                        Distinction: Risk score is probabilistic guidance, not guaranteed outcome.
                      </div>
                    </div>
                  </Popup>
                </CircleMarker>
              </React.Fragment>
            ))}

          {/* Meteorological Observation Stations (Always clickable pins) */}
          {stations.map((st) => {
            const isSelected = selectedStation && selectedStation.name === st.name
            return (
              <CircleMarker
                key={st.name}
                center={[st.lat, st.lon]}
                radius={isSelected ? 8 : 5}
                pathOptions={{
                  fillColor: getMarkerColor(st, isSelected),
                  fillOpacity: 0.9,
                  color: isSelected ? '#ffffff' : '#38bdf8',
                  weight: isSelected ? 2.5 : 1.5,
                }}
                eventHandlers={{
                  click: () => onStationSelect(st),
                }}
              >
                <Popup>
                  <div style={{ color: '#0f172a' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '2px' }}>
                      <MapPin size={12} color="#0284c7" />
                      <h4 style={{ fontWeight: 700, fontSize: '0.85rem' }}>{st.name}</h4>
                    </div>
                    <p style={{ fontSize: '0.75rem', color: '#64748b', margin: '2px 0 6px 0' }}>
                      Zone: {st.region_type} | Elev: {st.elevation_m}m
                    </p>
                    <button
                      onClick={() => onStationSelect(st)}
                      style={{
                        background: '#0284c7',
                        color: '#fff',
                        border: 'none',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '0.72rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        width: '100%',
                      }}
                    >
                      Inspect Point Forecast & Weights
                    </button>
                  </div>
                </Popup>
              </CircleMarker>
            )
          })}
        </MapContainer>

        {/* Dynamic Legend Overlay depending on active layer */}
        <div
          style={{
            position: 'absolute',
            bottom: '12px',
            left: '12px',
            zIndex: 1000,
            background: 'rgba(15, 23, 42, 0.92)',
            backdropFilter: 'blur(8px)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            padding: '8px 12px',
            display: 'flex',
            flexDirection: 'column',
            gap: '5px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.5)',
            maxWidth: '300px',
          }}
        >
          {mapLayer === 'dominant_model' && (
            <>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#f8fafc' }}>
                Dominant Forecast Model by Region
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '6px' }}>
                {Object.entries(modelColorMap).map(([mName, mColor]) => (
                  <div key={mName} style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: mColor }} />
                    <span style={{ fontSize: '0.68rem', color: '#cbd5e1' }}>{mName}</span>
                  </div>
                ))}
              </div>
              <div style={{ fontSize: '0.62rem', color: '#94a3b8', fontStyle: 'italic', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '3px' }}>
                <Info size={10} />
                No single model is globally best; weights adapt dynamically by context.
              </div>
            </>
          )}

          {mapLayer === 'weight_distribution' && (
            <>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#f8fafc' }}>
                Model Weight Distribution
              </div>
              <div style={{ fontSize: '0.68rem', color: '#cbd5e1' }}>
                Bubble radius indicates consensus entropy (diversity of model inputs).
              </div>
              <div style={{ fontSize: '0.62rem', color: '#38bdf8', fontStyle: 'italic' }}>
                Click any circle to view normalized percentage breakdown.
              </div>
            </>
          )}

          {mapLayer === 'forecast_values' && (
            <>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#f8fafc' }}>
                Forecast Values ({variable})
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#64748b' }} />
                <span style={{ fontSize: '0.68rem', color: '#cbd5e1' }}>Light</span>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#38bdf8' }} />
                <span style={{ fontSize: '0.68rem', color: '#cbd5e1' }}>Moderate</span>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#2563eb' }} />
                <span style={{ fontSize: '0.68rem', color: '#cbd5e1' }}>Heavy</span>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#a855f7' }} />
                <span style={{ fontSize: '0.68rem', color: '#cbd5e1' }}>Very Heavy</span>
              </div>
            </>
          )}

          {mapLayer === 'extreme_weather' && (
            <>
              <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#f8fafc' }}>
                IMD Multi-Tier Weather Alerts
              </div>
              <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444' }} />
                <span style={{ fontSize: '0.68rem', color: '#fca5a5' }}>Red (Take Action)</span>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#f97316' }} />
                <span style={{ fontSize: '0.68rem', color: '#fdba74' }}>Orange (Be Prepared)</span>
                <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#eab308' }} />
                <span style={{ fontSize: '0.68rem', color: '#fef08a' }}>Yellow (Be Updated)</span>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
