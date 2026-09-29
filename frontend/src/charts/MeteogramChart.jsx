import React from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'
import { TrendingUp } from 'lucide-react'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

export default function MeteogramChart({ pointData }) {
  if (!pointData || !pointData.time_series) {
    return (
      <div className="glass-card" style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
        Loading point meteogram...
      </div>
    )
  }

  const labels = pointData.time_series.map((item) => `T+${item.lead_time_hours}h`)

  const data = {
    labels,
    datasets: [
      // 1. Shaded 10th-90th Percentile Confidence Envelope
      {
        label: '90th Percentile Upper Bound',
        data: pointData.time_series.map((item) => item.confidence_interval_90th),
        borderColor: 'transparent',
        backgroundColor: 'rgba(56, 189, 248, 0.12)',
        fill: '+1',
        pointRadius: 0,
      },
      {
        label: '10th Percentile Lower Bound',
        data: pointData.time_series.map((item) => item.confidence_interval_10th),
        borderColor: 'transparent',
        backgroundColor: 'transparent',
        fill: false,
        pointRadius: 0,
      },
      // 2. Hybrid Blended Consensus (Bold Solid Luminous Line)
      {
        label: '★ Hybrid Blended Consensus',
        data: pointData.time_series.map((item) => item.blended_value),
        borderColor: '#38bdf8',
        backgroundColor: '#38bdf8',
        borderWidth: 3.5,
        pointRadius: 4,
        pointHoverRadius: 6,
        tension: 0.3,
      },
      // 3. Individual Models (Dashed Lines)
      {
        label: 'NOAA GFS (NWP)',
        data: pointData.time_series.map((item) => item.raw_predictions.gfs),
        borderColor: '#0284C7',
        borderDash: [5, 4],
        borderWidth: 1.8,
        pointRadius: 2,
        tension: 0.25,
      },
      {
        label: 'ECMWF IFS (NWP)',
        data: pointData.time_series.map((item) => item.raw_predictions.ecmwf),
        borderColor: '#1E3A8A',
        borderDash: [4, 4],
        borderWidth: 1.8,
        pointRadius: 2,
        tension: 0.25,
      },
      {
        label: 'GraphCast (AI)',
        data: pointData.time_series.map((item) => item.raw_predictions.graphcast),
        borderColor: '#38BDF8',
        borderDash: [3, 3],
        borderWidth: 1.8,
        pointRadius: 2,
        tension: 0.25,
      },
      {
        label: 'Pangu-Weather (AI)',
        data: pointData.time_series.map((item) => item.raw_predictions.pangu),
        borderColor: '#60A5FA',
        borderDash: [2, 2],
        borderWidth: 1.8,
        pointRadius: 2,
        tension: 0.25,
      },
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: '#cbd5e1',
          boxWidth: 12,
          font: { size: 11 },
          filter: (item) => !item.text.includes('Bound'), // Hide envelope bounds from legend list
        },
      },
      tooltip: {
        mode: 'index',
        intersect: false,
        backgroundColor: 'rgba(15, 23, 42, 0.95)',
        titleColor: '#38bdf8',
        bodyColor: '#f1f5f9',
        borderColor: 'rgba(255,255,255,0.1)',
        borderWidth: 1,
      },
    },
    scales: {
      x: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#94a3b8' },
      },
      y: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#94a3b8' },
        title: {
          display: true,
          text: `${pointData.variable} (${pointData.unit})`,
          color: '#94a3b8',
        },
      },
    },
  }

  return (
    <div className="glass-card">
      <div className="card-header">
        <div className="card-title">
          <TrendingUp size={18} color="#38bdf8" />
          <span>Point Meteogram · {pointData.station_name}</span>
        </div>
        <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
          Lat: {pointData.lat.toFixed(2)}°N · Lon: {pointData.lon.toFixed(2)}°E
        </span>
      </div>
      <div className="card-body" style={{ height: '340px' }}>
        <Line data={data} options={options} />
      </div>
    </div>
  )
}
