import React from 'react'
import { MapContainer, TileLayer, CircleMarker, Marker, Popup, useMap } from 'react-leaflet'
import { Globe, MapPin, AlertCircle } from 'lucide-react'

// Center of India
const INDIA_CENTER = [22.3, 79.5]
const DEFAULT_ZOOM = 4.5

export default function WeatherMapView({
  stations,
  selectedStation,
  onStationSelect,
  alerts,
  variable,
  gridData,
}) {
  const getMarkerColor = (station, isSelected) => {
    if (isSelected) return '#38bdf8'
    return '#94a3b8'
  }

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="card-header">
        <div className="card-title">
          <Globe size={18} color="#38bdf8" />
          <span>Spatial Blended Forecast & Observatories Map</span>
        </div>
        <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
          Click an observatory to inspect point meteogram
        </span>
      </div>

      <div className="map-view-wrapper">
        <MapContainer
          center={INDIA_CENTER}
          zoom={5}
          scrollWheelZoom={true}
          style={{ height: '100%', width: '100%' }}
        >
          {/* High-contrast CartoDB Dark Matter tiles */}
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          />

          {/* Gridded Forecast Spatial Mesh Points */}
          {gridData &&
            gridData.grid_cells &&
            gridData.grid_cells.map((cell, idx) => {
              // Color based on variable value
              let fillColor = 'rgba(56, 189, 248, 0.4)'
              if (variable === 'precipitation') {
                if (cell.value > 100) fillColor = 'rgba(168, 85, 247, 0.7)'
                else if (cell.value > 50) fillColor = 'rgba(37, 99, 235, 0.6)'
                else if (cell.value > 15) fillColor = 'rgba(56, 189, 248, 0.5)'
                else fillColor = 'rgba(148, 163, 184, 0.2)'
              } else if (variable === 'temperature_2m') {
                if (cell.value >= 42) fillColor = 'rgba(239, 68, 68, 0.7)'
                else if (cell.value >= 35) fillColor = 'rgba(249, 115, 22, 0.6)'
                else if (cell.value >= 28) fillColor = 'rgba(234, 179, 8, 0.5)'
                else fillColor = 'rgba(34, 197, 94, 0.4)'
              }

              return (
                <CircleMarker
                  key={`grid-${idx}`}
                  center={[cell.lat, cell.lon]}
                  radius={5}
                  pathOptions={{
                    fillColor,
                    fillOpacity: 0.6,
                    stroke: false,
                  }}
                />
              )
            })}

          {/* Severe Weather Hazard Alert Indicators */}
          {alerts &&
            alerts.map((alert) => (
              <CircleMarker
                key={alert.id}
                center={[alert.lat, alert.lon]}
                radius={14}
                pathOptions={{
                  fillColor: alert.severity === 'red' ? '#ef4444' : '#f97316',
                  fillOpacity: 0.35,
                  color: alert.severity === 'red' ? '#ef4444' : '#f97316',
                  weight: 2,
                }}
              >
                <Popup>
                  <div style={{ color: '#0f172a', padding: '4px' }}>
                    <h4 style={{ fontWeight: 700, color: alert.severity === 'red' ? '#dc2626' : '#ea580c' }}>
                      {alert.title}
                    </h4>
                    <p style={{ fontSize: '0.8rem', margin: '4px 0' }}>{alert.description}</p>
                    <p style={{ fontSize: '0.75rem', color: '#475569' }}>
                      <strong>Protocol:</strong> {alert.recommended_action}
                    </p>
                  </div>
                </Popup>
              </CircleMarker>
            ))}

          {/* Meteorological Stations */}
          {stations &&
            stations.map((st) => {
              const isSelected = selectedStation && selectedStation.name === st.name
              return (
                <CircleMarker
                  key={st.name}
                  center={[st.lat, st.lon]}
                  radius={isSelected ? 8 : 6}
                  pathOptions={{
                    fillColor: getMarkerColor(st, isSelected),
                    fillOpacity: 0.9,
                    color: '#ffffff',
                    weight: isSelected ? 2.5 : 1.5,
                  }}
                  eventHandlers={{
                    click: () => onStationSelect(st),
                  }}
                >
                  <Popup>
                    <div style={{ color: '#0f172a' }}>
                      <h4 style={{ fontWeight: 600 }}>{st.name}</h4>
                      <p style={{ fontSize: '0.8rem', color: '#64748b' }}>
                        Zone: {st.region_type} | Elev: {st.elevation_m}m
                      </p>
                      <button
                        onClick={() => onStationSelect(st)}
                        style={{
                          marginTop: '6px',
                          background: '#0284c7',
                          color: '#fff',
                          border: 'none',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          fontSize: '0.75rem',
                          cursor: 'pointer',
                        }}
                      >
                        Inspect Meteogram
                      </button>
                    </div>
                  </Popup>
                </CircleMarker>
              )
            })}
        </MapContainer>
      </div>
    </div>
  )
}
