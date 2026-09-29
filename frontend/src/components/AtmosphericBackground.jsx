import React, { useEffect, useRef } from 'react'

/**
 * AtmosphericBackground
 * Realistic dynamic sky simulation inspired by AuraMet.
 * Generates layered drifting cumulus cloud puffs and atmospheric moisture haze
 * rendered to an HTML5 canvas over a deep atmospheric sky gradient.
 */
export default function AtmosphericBackground() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationFrameId
    let width = (canvas.width = window.innerWidth)
    let height = (canvas.height = window.innerHeight)

    const handleResize = () => {
      if (!canvas) return
      width = canvas.width = window.innerWidth
      height = canvas.height = window.innerHeight
      initAtmosphere()
    }
    window.addEventListener('resize', handleResize)

    // Realistic cumulus cloud clusters
    let cloudClusters = []

    const initAtmosphere = () => {
      cloudClusters = []
      // 4-6 large cloud clusters across different depth layers
      const clusterCount = Math.max(5, Math.floor(width / 280))

      for (let i = 0; i < clusterCount; i++) {
        const baseX = (i / clusterCount) * (width + 500) - 250 + (Math.random() - 0.5) * 150
        const baseY = Math.random() * (height * 0.55) + 30
        const speed = (0.04 + Math.random() * 0.06) * (1 + (baseY / height) * 0.5)
        const scale = 0.8 + Math.random() * 0.7

        // Each cluster consists of 5-8 overlapping circular puffs to form a natural cloud shape
        const puffs = []
        const puffCount = 6 + Math.floor(Math.random() * 4)
        for (let p = 0; p < puffCount; p++) {
          puffs.push({
            offsetX: (Math.random() - 0.5) * 220 * scale,
            offsetY: (Math.random() - 0.5) * 70 * scale,
            radiusX: (80 + Math.random() * 90) * scale,
            radiusY: (45 + Math.random() * 55) * scale,
            opacity: 0.10 + Math.random() * 0.12,
          })
        }

        cloudClusters.push({
          x: baseX,
          y: baseY,
          speedX: speed,
          scale,
          puffs,
        })
      }
    }

    initAtmosphere()

    // Soft atmospheric micro-particles / humidity shimmer
    const particles = []
    const particleCount = Math.min(30, Math.floor(width / 50))
    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * width,
        y: Math.random() * height,
        radius: Math.random() * 1.8 + 0.6,
        speedX: Math.random() * 0.18 + 0.05,
        speedY: (Math.random() - 0.5) * 0.06,
        opacity: Math.random() * 0.20 + 0.08,
      })
    }

    const render = () => {
      ctx.clearRect(0, 0, width, height)

      // Draw each cloud cluster
      for (let i = 0; i < cloudClusters.length; i++) {
        const cluster = cloudClusters[i]

        if (!prefersReducedMotion) {
          cluster.x += cluster.speedX
          // Wrap around horizontally
          if (cluster.x - 300 * cluster.scale > width) {
            cluster.x = -350 * cluster.scale
            cluster.y = Math.random() * (height * 0.55) + 30
          }
        }

        // Render each puff in the cluster
        for (let p = 0; p < cluster.puffs.length; p++) {
          const puff = cluster.puffs[p]
          const puffX = cluster.x + puff.offsetX
          const puffY = cluster.y + puff.offsetY

          const gradient = ctx.createRadialGradient(
            puffX,
            puffY - puff.radiusY * 0.2,
            0,
            puffX,
            puffY,
            puff.radiusX
          )

          // White sunlight scattering on top, soft light-blue shading below
          gradient.addColorStop(0, `rgba(255, 255, 255, ${puff.opacity * 1.2})`)
          gradient.addColorStop(0.45, `rgba(240, 248, 255, ${puff.opacity * 0.85})`)
          gradient.addColorStop(0.8, `rgba(215, 235, 252, ${puff.opacity * 0.35})`)
          gradient.addColorStop(1, 'rgba(215, 235, 252, 0)')

          ctx.save()
          ctx.beginPath()
          ctx.ellipse(puffX, puffY, puff.radiusX, puff.radiusY, 0, 0, Math.PI * 2)
          ctx.fillStyle = gradient
          ctx.fill()
          ctx.restore()
        }
      }

      // Draw faint drifting moisture particles
      for (let i = 0; i < particles.length; i++) {
        const pt = particles[i]
        if (!prefersReducedMotion) {
          pt.x += pt.speedX
          pt.y += pt.speedY

          if (pt.x > width + 10) pt.x = -10
          if (pt.x < -10) pt.x = width + 10
          if (pt.y > height + 10) pt.y = -10
          if (pt.y < -10) pt.y = height + 10
        }

        ctx.beginPath()
        ctx.arc(pt.x, pt.y, pt.radius, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(186, 230, 253, ${pt.opacity})`
        ctx.fill()
      }

      if (!prefersReducedMotion) {
        animationFrameId = requestAnimationFrame(render)
      }
    }

    render()

    return () => {
      window.removeEventListener('resize', handleResize)
      if (animationFrameId) cancelAnimationFrame(animationFrameId)
    }
  }, [])

  return (
    <div className="atmospheric-bg-container" aria-hidden="true">
      {/* Deep, natural blue atmospheric sky backdrop matching AuraMet */}
      <div className="atmospheric-sky-gradient" />
      {/* HTML5 canvas with realistic smooth cloud drift */}
      <canvas ref={canvasRef} className="atmospheric-particle-canvas" />
    </div>
  )
}
