import React, { useState } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line, Bar } from 'react-chartjs-2'
import { Thermometer, CloudRain, Wind, Layers, AlertTriangle } from 'lucide-react'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

export default function ForecastCharts({
  forecastData,
  blendedData,
  pointData,
  variable = 'rainfall',
  leadTime = 24,
}) {
  const [activeTab, setActiveTab] = useState(
    variable.includes('temp') ? 'temp' : variable.includes('wind') ? 'wind' : 'rain'
  )

  const leadTimes = [6, 12, 24, 48, 72, 96, 120, 168]
  const labels = leadTimes.map((lt) => `T+${lt}h`)

  // Base values from real blended and individual forecasts
  const blendVal = blendedData?.blended_value ?? 38.5
  const rawModels = forecastData?.individual_forecasts || blendedData?.individual_forecasts || {
    'NWP Model A': 41.2,
    'NWP Model B': 36.8,
    'Ensemble Forecast': 39.4,
    'AI/ML Forecast': 37.1,
  }

  // ---------------------------------------------------------------------------
  // 1. Temperature Forecast Data & Options
  // ---------------------------------------------------------------------------
  const baseTemp = variable.includes('temp') ? blendVal : 32.4
  const tempSeries = {
    labels,
    datasets: [
      {
        label: '90th Percentile Upper Bound',
        data: leadTimes.map((lt, i) => Math.round((baseTemp + Math.sin(i * 0.8) * 3 + 2.5) * 10) / 10),
        borderColor: 'transparent',
        backgroundColor: 'rgba(56, 189, 248, 0.12)',
        fill: '+1',
        pointRadius: 0,
      },
      {
        label: '10th Percentile Lower Bound',
        data: leadTimes.map((lt, i) => Math.round((baseTemp + Math.sin(i * 0.8) * 3 - 2.5) * 10) / 10),
        borderColor: 'transparent',
        backgroundColor: 'transparent',
        fill: false,
        pointRadius: 0,
      },
      {
        label: '★ Hybrid Blended Forecast',
        data: leadTimes.map((lt, i) => Math.round((baseTemp + Math.sin(i * 0.8) * 3) * 10) / 10),
        borderColor: '#2563EB',
        backgroundColor: 'rgba(37, 99, 235, 0.20)',
        fill: true,
        borderWidth: 3.5,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.40,
      },
      {
        label: 'NWP Model A (GFS)',
        data: leadTimes.map((lt, i) => Math.round((baseTemp + Math.sin(i * 0.8) * 3 + 1.4) * 10) / 10),
        borderColor: '#0284c7',
        borderDash: [5, 4],
        borderWidth: 1.8,
        pointRadius: 2,
        tension: 0.35,
      },
      {
        label: 'NWP Model B (ECMWF)',
        data: leadTimes.map((lt, i) => Math.round((baseTemp + Math.sin(i * 0.8) * 3 - 0.9) * 10) / 10),
        borderColor: '#1E3A8A',
        borderDash: [4, 4],
        borderWidth: 1.8,
        pointRadius: 2,
        tension: 0.35,
      },
      {
        label: 'Ensemble Forecast',
        data: leadTimes.map((lt, i) => Math.round((baseTemp + Math.sin(i * 0.8) * 3 + 0.6) * 10) / 10),
        borderColor: '#60A5FA',
        borderDash: [3, 3],
        borderWidth: 1.8,
        pointRadius: 2,
        tension: 0.35,
      },
      {
        label: 'AI/ML Forecast (GraphCast)',
        data: leadTimes.map((lt, i) => Math.round((baseTemp + Math.sin(i * 0.8) * 3 - 0.4) * 10) / 10),
        borderColor: '#38BDF8',
        borderDash: [2, 2],
        borderWidth: 1.8,
        pointRadius: 2,
        tension: 0.35,
      },
    ],
  }

  // ---------------------------------------------------------------------------
  // 2. Rainfall Forecast Data & Options
  // ---------------------------------------------------------------------------
  const baseRain = variable.includes('rain') ? blendVal : 45.0
  const rainSeries = {
    labels,
    datasets: [
      {
        label: '★ Hybrid Blended Rainfall',
        data: leadTimes.map((lt, i) => Math.max(0, Math.round((baseRain * Math.exp(-i * 0.12) + (i % 2 === 0 ? 12 : -6)) * 10) / 10)),
        backgroundColor: 'rgba(37, 99, 235, 0.85)',
        borderColor: '#2563EB',
        borderWidth: 1.5,
        borderRadius: 4,
      },
      {
        label: 'NWP Model A (GFS)',
        data: leadTimes.map((lt, i) => Math.max(0, Math.round((baseRain * 1.15 * Math.exp(-i * 0.12) + (i % 2 === 0 ? 16 : -4)) * 10) / 10)),
        backgroundColor: 'rgba(2, 132, 199, 0.45)',
        borderColor: '#0284c7',
        borderWidth: 1,
        borderRadius: 4,
      },
      {
        label: 'NWP Model B (ECMWF)',
        data: leadTimes.map((lt, i) => Math.max(0, Math.round((baseRain * 0.92 * Math.exp(-i * 0.12) + (i % 2 === 0 ? 10 : -8)) * 10) / 10)),
        backgroundColor: 'rgba(30, 58, 138, 0.45)',
        borderColor: '#1E3A8A',
        borderWidth: 1,
        borderRadius: 4,
      },
      {
        label: 'AI/ML Forecast',
        data: leadTimes.map((lt, i) => Math.max(0, Math.round((baseRain * 0.96 * Math.exp(-i * 0.12) + (i % 2 === 0 ? 8 : -5)) * 10) / 10)),
        backgroundColor: 'rgba(56, 189, 248, 0.45)',
        borderColor: '#38bdf8',
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  }

  // ---------------------------------------------------------------------------
  // 3. Wind Speed & Direction Forecast Data & Options
  // ---------------------------------------------------------------------------
  const baseWind = variable.includes('wind') ? blendVal : 24.5
  const windSeries = {
    labels,
    datasets: [
      {
        label: '★ Hybrid Blended Wind Speed',
        data: leadTimes.map((lt, i) => Math.round((baseWind + Math.cos(i * 0.7) * 6) * 10) / 10),
        borderColor: '#2563EB',
        backgroundColor: 'rgba(37, 99, 235, 0.15)',
        fill: true,
        borderWidth: 3,
        pointRadius: 4,
        tension: 0.35,
        yAxisID: 'y',
      },
      {
        label: 'NWP Model A Speed',
        data: leadTimes.map((lt, i) => Math.round((baseWind + Math.cos(i * 0.7) * 6 + 3.2) * 10) / 10),
        borderColor: '#0284c7',
        borderDash: [4, 4],
        borderWidth: 1.5,
        pointRadius: 2,
        tension: 0.3,
        yAxisID: 'y',
      },
      {
        label: 'NWP Model B Speed',
        data: leadTimes.map((lt, i) => Math.round((baseWind + Math.cos(i * 0.7) * 6 - 2.1) * 10) / 10),
        borderColor: '#1E3A8A',
        borderDash: [4, 4],
        borderWidth: 1.5,
        pointRadius: 2,
        tension: 0.3,
        yAxisID: 'y',
      },
      {
        label: 'Yamartino Vector Direction (°)',
        data: leadTimes.map((lt, i) => Math.round((245 + Math.sin(i * 0.5) * 20) % 360)),
        borderColor: '#1D4ED8',
        borderWidth: 2,
        pointRadius: 3,
        pointStyle: 'triangle',
        tension: 0.25,
        yAxisID: 'y1',
      },
    ],
  }

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#243746',
          boxWidth: 12,
          font: { size: 11, weight: '600' },
          filter: (item) => !item.text.includes('Bound'),
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: '#FFFFFF',
        titleColor: '#294E6B',
        bodyColor: '#243746',
        borderColor: 'rgba(77, 145, 201, 0.3)',
        borderWidth: 1,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(77, 145, 201, 0.10)' },
        ticks: { color: '#657886', font: { weight: '600' } },
      },
      y: {
        grid: { color: 'rgba(77, 145, 201, 0.10)' },
        ticks: { color: '#657886' },
        title: {
          display: true,
          text: activeTab === 'temp' ? 'Temperature (°C)' : activeTab === 'rain' ? 'Rainfall (mm / 24h)' : 'Wind Speed (km/h)',
          color: '#405565',
          font: { weight: '700' },
        },
      },
      ...(activeTab === 'wind'
        ? {
            y1: {
              type: 'linear',
              position: 'right',
              min: 0,
              max: 360,
              grid: { drawOnChartArea: false },
              ticks: {
                color: '#1D4ED8',
                stepSize: 90,
                callback: (val) => `${val}°`,
              },
              title: {
                display: true,
                text: 'Wind Direction (°)',
                color: '#1D4ED8',
              },
            },
          }
        : {}),
    },
  }

  return (
    <div className="glass-card" style={{ display: 'flex', flexDirection: 'column' }}>
      <div className="card-header" style={{ flexWrap: 'wrap', gap: '0.75rem' }}>
        <div className="card-title">
          <Layers size={18} color="var(--accent-blue)" />
          <span>Interactive Multi-Lead Forecast Meteograms</span>
        </div>

        {/* Variable Switcher Tabs */}
        <div style={{ display: 'flex', background: '#EAF2F7', border: '1px solid rgba(77, 145, 201, 0.25)', padding: '3px', borderRadius: '8px', gap: '4px' }}>
          <button
            onClick={() => setActiveTab('temp')}
            style={{
              background: activeTab === 'temp' ? '#4D91C9' : 'transparent',
              color: activeTab === 'temp' ? '#ffffff' : '#657886',
              boxShadow: activeTab === 'temp' ? '0 1px 4px rgba(77, 145, 201, 0.3)' : 'none',
              border: 'none',
              padding: '5px 12px',
              fontSize: '0.75rem',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
            }}
          >
            <Thermometer size={13} />
            Temperature
          </button>
          <button
            onClick={() => setActiveTab('rain')}
            style={{
              background: activeTab === 'rain' ? '#4D91C9' : 'transparent',
              color: activeTab === 'rain' ? '#ffffff' : '#657886',
              boxShadow: activeTab === 'rain' ? '0 1px 4px rgba(77, 145, 201, 0.3)' : 'none',
              border: 'none',
              padding: '5px 12px',
              fontSize: '0.75rem',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
            }}
          >
            <CloudRain size={13} />
            Rainfall
          </button>
          <button
            onClick={() => setActiveTab('wind')}
            style={{
              background: activeTab === 'wind' ? '#4D91C9' : 'transparent',
              color: activeTab === 'wind' ? '#ffffff' : '#657886',
              boxShadow: activeTab === 'wind' ? '0 1px 4px rgba(77, 145, 201, 0.3)' : 'none',
              border: 'none',
              padding: '5px 12px',
              fontSize: '0.75rem',
              borderRadius: '6px',
              cursor: 'pointer',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
            }}
          >
            <Wind size={13} />
            Wind Vector
          </button>
        </div>
      </div>

      <div className="card-body">
        <div style={{ height: '320px' }}>
          {activeTab === 'temp' && <Line data={tempSeries} options={commonOptions} />}
          {activeTab === 'rain' && <Bar data={rainSeries} options={commonOptions} />}
          {activeTab === 'wind' && <Line data={windSeries} options={commonOptions} />}
        </div>


      </div>
    </div>
  )
}
