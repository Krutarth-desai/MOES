import React, { useState, useEffect } from 'react'
import {
  CloudLightning,
  AlertCircle,
  ShieldCheck,
  CheckCircle2,
  RotateCw,
  Mail,
  Lock,
  User as UserIcon,
  Activity,
  Layers,
  Compass,
  AlertTriangle,
} from 'lucide-react'
import { supabase } from '../lib/supabaseClient'
import AtmosphericBackground from '../components/AtmosphericBackground'

export default function Login({ authError }) {
  const [isSignUp, setIsSignUp] = useState(false)
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState(authError || null)
  const [successMessage, setSuccessMessage] = useState(null)

  useEffect(() => {
    // Check URL parameters for OAuth error responses (e.g. error_description)
    const hash = window.location.hash
    const search = window.location.search
    if (hash.includes('error_description=') || search.includes('error_description=')) {
      const params = new URLSearchParams(hash.replace('#', '?') || search)
      const desc = params.get('error_description') || params.get('error')
      if (desc) {
        setErrorMessage(decodeURIComponent(desc))
      }
    }
  }, [])

  // 1. Google OAuth Sign-In
  const handleGoogleLogin = async () => {
    try {
      setLoading(true)
      setErrorMessage(null)
      setSuccessMessage(null)

      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: window.location.origin,
        },
      })

      if (error) {
        console.error('Supabase Google OAuth error:', error)
        setErrorMessage(error.message || 'Failed to initialize Google authentication. Please try again.')
        setLoading(false)
      }
    } catch (err) {
      console.error('Unexpected Google OAuth error:', err)
      setErrorMessage(err.message || 'An unexpected error occurred during sign-in. Check your connection.')
      setLoading(false)
    }
  }

  // 2. Email/Password Sign-In
  const handleEmailSignIn = async (e) => {
    e.preventDefault()
    setErrorMessage(null)
    setSuccessMessage(null)

    if (!email || !password) {
      setErrorMessage('Please enter both email and password.')
      return
    }

    try {
      setLoading(true)
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })

      if (error) {
        console.error('Supabase Sign-In error:', error)
        if (error.message.toLowerCase().includes('invalid login credentials')) {
          setErrorMessage('Invalid email or password. Please verify your credentials and try again.')
        } else if (error.message.toLowerCase().includes('email not confirmed')) {
          setErrorMessage('Your email address has not been confirmed. Please check your inbox.')
        } else {
          setErrorMessage(error.message || 'Failed to sign in. Please check your email and password.')
        }
      }
    } catch (err) {
      console.error('Unexpected Sign-In error:', err)
      setErrorMessage('Network or authentication error occurred. Please check your connection.')
    } finally {
      setLoading(false)
    }
  }

  // 3. Email/Password Sign-Up
  const handleEmailSignUp = async (e) => {
    e.preventDefault()
    setErrorMessage(null)
    setSuccessMessage(null)

    if (!fullName.trim()) {
      setErrorMessage('Please enter your full name.')
      return
    }
    if (!email) {
      setErrorMessage('Please enter a valid email address.')
      return
    }
    if (password.length < 6) {
      setErrorMessage('Password must be at least 6 characters long.')
      return
    }
    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match. Please re-enter your password.')
      return
    }

    try {
      setLoading(true)
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName.trim(),
          },
        },
      })

      if (error) {
        console.error('Supabase Sign-Up error:', error)
        if (error.message.toLowerCase().includes('already registered')) {
          setErrorMessage('An account with this email already exists. Please sign in instead.')
        } else {
          setErrorMessage(error.message || 'Failed to create account. Please try again.')
        }
      } else if (data?.user) {
        if (data?.session) {
          setSuccessMessage('Account created successfully! Directing to MOES Dashboard...')
        } else {
          setSuccessMessage('Account created successfully! Please check your email inbox to confirm your account.')
        }
      }
    } catch (err) {
      console.error('Unexpected Sign-Up error:', err)
      setErrorMessage('Network or authentication error occurred. Please check your connection.')
    } finally {
      setLoading(false)
    }
  }

  const toggleMode = (signUpState) => {
    setIsSignUp(signUpState)
    setErrorMessage(null)
    setSuccessMessage(null)
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100%',
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem 1.5rem',
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        overflowX: 'hidden',
      }}
    >
      {/* 1. Dynamic Atmospheric Cloud & Sky Background */}
      <AtmosphericBackground />

      {/* 2. Main 2-Column Institutional Entry Layout */}
      <div
        style={{
          width: '100%',
          maxWidth: '1080px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '3rem',
          alignItems: 'center',
          position: 'relative',
          zIndex: 2,
        }}
      >
        {/* ========================================================================= */}
        {/* LEFT COLUMN: INSTITUTIONAL & PROJECT IDENTITY                             */}
        {/* ========================================================================= */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {/* Header Institutional Badges */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <div
              style={{
                background: '#1E3A8A',
                color: '#ffffff',
                fontSize: '0.82rem',
                fontWeight: 800,
                padding: '6px 14px',
                borderRadius: '8px',
                letterSpacing: '1px',
                boxShadow: '0 4px 14px rgba(30, 58, 138, 0.25)',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <span>SIH · MoES</span>
            </div>
            <div
              style={{
                background: 'rgba(255, 255, 255, 0.75)',
                color: '#1E3A8A',
                border: '1px solid rgba(56, 145, 218, 0.3)',
                fontSize: '0.72rem',
                fontWeight: 700,
                padding: '5px 10px',
                borderRadius: '8px',
                letterSpacing: '0.04em',
                backdropFilter: 'blur(8px)',
              }}
            >
              MINISTRY OF EARTH SCIENCES · GOVT. OF INDIA
            </div>
          </div>

          {/* Main System Title */}
          <div>
            <h1
              style={{
                fontSize: '2.3rem',
                fontWeight: 800,
                color: '#0F2942',
                letterSpacing: '-0.025em',
                lineHeight: 1.18,
                marginBottom: '0.75rem',
              }}
            >
              Hybrid AI–NWP Multi-Model Forecast Blending System
            </h1>
            <p
              style={{
                fontSize: '0.95rem',
                color: '#1E3A8A',
                lineHeight: 1.55,
                fontWeight: 500,
                maxWidth: '520px',
              }}
            >
              High-resolution operational consensus engine synthesizing ECMWF, GFS, NCUM, and GraphCast Neural models to produce dynamic skill-weighted meteorological predictions.
            </p>
          </div>

          {/* Subtle Scientific Operational Capabilities Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
              gap: '10px',
              marginTop: '0.5rem',
            }}
          >
            <div
              style={{
                background: 'rgba(255, 255, 255, 0.72)',
                backdropFilter: 'blur(12px)',
                border: '1px solid rgba(56, 145, 218, 0.22)',
                borderRadius: '10px',
                padding: '10px 12px',
                boxShadow: '0 4px 14px rgba(15, 41, 77, 0.05)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem', fontWeight: 700, color: '#1E3A8A' }}>
                <Layers size={14} color="#2563EB" />
                <span>4-Model Dynamic Blend</span>
              </div>
              <div style={{ fontSize: '0.7rem', color: '#475569', marginTop: '2px' }}>
                ECMWF · GFS · GEFS · GraphCast AI
              </div>
            </div>

            <div
              style={{
                background: 'rgba(255, 255, 255, 0.72)',
                backdropFilter: 'blur(12px)',
                border: '1px solid rgba(56, 145, 218, 0.22)',
                borderRadius: '10px',
                padding: '10px 12px',
                boxShadow: '0 4px 14px rgba(15, 41, 77, 0.05)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem', fontWeight: 700, color: '#1E3A8A' }}>
                <Activity size={14} color="#2563EB" />
                <span>Softmax Skill Weighting</span>
              </div>
              <div style={{ fontSize: '0.7rem', color: '#475569', marginTop: '2px' }}>
                Rolling RMSE & MAE performance metrics
              </div>
            </div>

            <div
              style={{
                background: 'rgba(255, 255, 255, 0.72)',
                backdropFilter: 'blur(12px)',
                border: '1px solid rgba(56, 145, 218, 0.22)',
                borderRadius: '10px',
                padding: '10px 12px',
                boxShadow: '0 4px 14px rgba(15, 41, 77, 0.05)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem', fontWeight: 700, color: '#1E3A8A' }}>
                <Compass size={14} color="#2563EB" />
                <span>Yamartino Wind Vectors</span>
              </div>
              <div style={{ fontSize: '0.7rem', color: '#475569', marginTop: '2px' }}>
                WMO-compliant circular vector math
              </div>
            </div>

            <div
              style={{
                background: 'rgba(255, 255, 255, 0.72)',
                backdropFilter: 'blur(12px)',
                border: '1px solid rgba(56, 145, 218, 0.22)',
                borderRadius: '10px',
                padding: '10px 12px',
                boxShadow: '0 4px 14px rgba(15, 41, 77, 0.05)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.76rem', fontWeight: 700, color: '#1E3A8A' }}>
                <AlertTriangle size={14} color="#2563EB" />
                <span>IMD Extreme Hazards</span>
              </div>
              <div style={{ fontSize: '0.7rem', color: '#475569', marginTop: '2px' }}>
                Heavy rain, heatwave & gale protocols
              </div>
            </div>
          </div>
        </div>

        {/* ========================================================================= */}
        {/* RIGHT COLUMN: REFINED ELEVATED AUTHENTICATION PANEL                       */}
        {/* ========================================================================= */}
        <div
          style={{
            background: 'rgba(255, 255, 255, 0.92)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            border: '1px solid rgba(56, 145, 218, 0.25)',
            borderRadius: '20px',
            padding: '2.25rem 2rem',
            boxShadow: '0 16px 48px rgba(15, 41, 77, 0.14)',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {/* Form Header */}
          <div style={{ marginBottom: '1.25rem' }}>
            <h2
              style={{
                fontSize: '1.35rem',
                fontWeight: 800,
                color: '#0F2942',
                letterSpacing: '-0.01em',
                marginBottom: '4px',
              }}
            >
              {isSignUp ? 'Create an Account' : 'Sign in to MoES'}
            </h2>
            <p style={{ fontSize: '0.82rem', color: '#475569' }}>
              {isSignUp ? 'Register for operational forecasting access.' : 'Access the operational forecasting workspace.'}
            </p>
          </div>

          {/* Success Notification Banner */}
          {successMessage && (
            <div
              style={{
                width: '100%',
                background: 'rgba(37, 99, 235, 0.08)',
                border: '1px solid rgba(37, 99, 235, 0.3)',
                color: '#1E3A8A',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                fontSize: '0.8rem',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
                marginBottom: '1.25rem',
              }}
            >
              <CheckCircle2 size={16} color="#2563EB" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ lineHeight: 1.4 }}>{successMessage}</div>
            </div>
          )}

          {/* Error Notification Banner */}
          {errorMessage && (
            <div
              style={{
                width: '100%',
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: '#991B1B',
                padding: '0.75rem 1rem',
                borderRadius: '8px',
                fontSize: '0.8rem',
                display: 'flex',
                alignItems: 'flex-start',
                gap: '8px',
                marginBottom: '1.25rem',
              }}
            >
              <AlertCircle size={16} color="#DC2626" style={{ flexShrink: 0, marginTop: '2px' }} />
              <div style={{ lineHeight: 1.4 }}>
                <strong>Authentication Notice:</strong> {errorMessage}
              </div>
            </div>
          )}

          {/* Google OAuth Button */}
          <button
            type="button"
            onClick={handleGoogleLogin}
            disabled={loading}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '12px',
              backgroundColor: '#ffffff',
              color: '#1E293B',
              border: '1px solid rgba(203, 213, 225, 0.9)',
              borderRadius: '10px',
              padding: '0.75rem 1.25rem',
              fontSize: '0.88rem',
              fontWeight: 700,
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.15s ease',
              boxShadow: '0 2px 8px rgba(15, 41, 77, 0.06)',
              opacity: loading ? 0.8 : 1,
            }}
          >
            {loading ? (
              <>
                <RotateCw size={18} className="spin-animation" color="#2563EB" />
                <span>Connecting to Google...</span>
              </>
            ) : (
              <>
                <svg width="18" height="18" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    fill="#4285F4"
                  />
                  <path
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    fill="#34A853"
                  />
                  <path
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                    fill="#FBBC05"
                  />
                  <path
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                    fill="#EA4335"
                  />
                </svg>
                <span>Continue with Google</span>
              </>
            )}
          </button>

          {/* Visual Divider */}
          <div style={{ display: 'flex', alignItems: 'center', margin: '1.25rem 0', width: '100%' }}>
            <div style={{ flex: 1, height: '1px', background: 'rgba(203, 213, 225, 0.8)' }} />
            <span style={{ padding: '0 12px', fontSize: '0.72rem', color: '#64748B', fontWeight: 700, letterSpacing: '1px' }}>
              OR
            </span>
            <div style={{ flex: 1, height: '1px', background: 'rgba(203, 213, 225, 0.8)' }} />
          </div>

          {/* Email & Password Form */}
          <form
            onSubmit={isSignUp ? handleEmailSignUp : handleEmailSignIn}
            style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '0.9rem' }}
          >
            {isSignUp && (
              <div>
                <label style={{ display: 'block', fontSize: '0.76rem', fontWeight: 700, color: '#1E3A8A', marginBottom: '0.35rem' }}>
                  Full Name
                </label>
                <div style={{ position: 'relative' }}>
                  <UserIcon size={16} color="#2563EB" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                  <input
                    type="text"
                    required
                    placeholder="Enter your full name"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.65rem 0.85rem 0.65rem 2.35rem',
                      background: '#FFFFFF',
                      border: '1px solid rgba(56, 145, 218, 0.3)',
                      borderRadius: '8px',
                      color: '#0F2942',
                      fontSize: '0.88rem',
                      outline: 'none',
                      boxShadow: 'inset 0 1px 2px rgba(15, 41, 77, 0.04)',
                    }}
                  />
                </div>
              </div>
            )}

            <div>
              <label style={{ display: 'block', fontSize: '0.76rem', fontWeight: 700, color: '#1E3A8A', marginBottom: '0.35rem' }}>
                Email Address
              </label>
              <div style={{ position: 'relative' }}>
                <Mail size={16} color="#2563EB" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="email"
                  required
                  placeholder="Enter your email address"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.85rem 0.65rem 2.35rem',
                    background: '#FFFFFF',
                    border: '1px solid rgba(56, 145, 218, 0.3)',
                    borderRadius: '8px',
                    color: '#0F2942',
                    fontSize: '0.88rem',
                    outline: 'none',
                    boxShadow: 'inset 0 1px 2px rgba(15, 41, 77, 0.04)',
                  }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.76rem', fontWeight: 700, color: '#1E3A8A', marginBottom: '0.35rem' }}>
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <Lock size={16} color="#2563EB" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                <input
                  type="password"
                  required
                  placeholder={isSignUp ? 'Create a password (min. 6 chars)' : 'Enter your password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '0.65rem 0.85rem 0.65rem 2.35rem',
                    background: '#FFFFFF',
                    border: '1px solid rgba(56, 145, 218, 0.3)',
                    borderRadius: '8px',
                    color: '#0F2942',
                    fontSize: '0.88rem',
                    outline: 'none',
                    boxShadow: 'inset 0 1px 2px rgba(15, 41, 77, 0.04)',
                  }}
                />
              </div>
            </div>

            {isSignUp && (
              <div>
                <label style={{ display: 'block', fontSize: '0.76rem', fontWeight: 700, color: '#1E3A8A', marginBottom: '0.35rem' }}>
                  Confirm Password
                </label>
                <div style={{ position: 'relative' }}>
                  <Lock size={16} color="#2563EB" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                  <input
                    type="password"
                    required
                    placeholder="Confirm your password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '0.65rem 0.85rem 0.65rem 2.35rem',
                      background: '#FFFFFF',
                      border: '1px solid rgba(56, 145, 218, 0.3)',
                      borderRadius: '8px',
                      color: '#0F2942',
                      fontSize: '0.88rem',
                      outline: 'none',
                      boxShadow: 'inset 0 1px 2px rgba(15, 41, 77, 0.04)',
                    }}
                  />
                </div>
              </div>
            )}

            {/* Submit Action Button */}
            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: '0.5rem',
                width: '100%',
                background: '#2563EB',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                padding: '0.75rem 1.25rem',
                fontSize: '0.9rem',
                fontWeight: 800,
                cursor: loading ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                boxShadow: '0 4px 14px rgba(37, 99, 235, 0.3)',
                opacity: loading ? 0.8 : 1,
                transition: 'all 0.15s ease',
              }}
            >
              {loading ? (
                <>
                  <RotateCw size={16} className="spin-animation" />
                  <span>{isSignUp ? 'Creating Account...' : 'Signing In...'}</span>
                </>
              ) : (
                <span>{isSignUp ? 'Create Account' : 'Sign In'}</span>
              )}
            </button>
          </form>

          {/* Toggle between Sign In and Sign Up */}
          <div style={{ marginTop: '1.25rem', textAlign: 'center', fontSize: '0.8rem', color: '#475569' }}>
            {isSignUp ? (
              <span>
                Already have an account?{' '}
                <button
                  type="button"
                  onClick={() => toggleMode(false)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#2563EB',
                    fontWeight: 700,
                    cursor: 'pointer',
                    padding: 0,
                    fontSize: 'inherit',
                    textDecoration: 'underline',
                  }}
                >
                  Sign in
                </button>
              </span>
            ) : (
              <span>
                Don't have an account?{' '}
                <button
                  type="button"
                  onClick={() => toggleMode(true)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#2563EB',
                    fontWeight: 700,
                    cursor: 'pointer',
                    padding: 0,
                    fontSize: 'inherit',
                    textDecoration: 'underline',
                  }}
                >
                  Create account
                </button>
              </span>
            )}
          </div>

          {/* Footer Security Guarantee */}
          <div style={{ marginTop: '1.5rem', borderTop: '1px solid rgba(203, 213, 225, 0.6)', paddingTop: '1rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', fontSize: '0.72rem', color: '#64748B' }}>
              <ShieldCheck size={14} color="#2563EB" />
              <span>Protected by Supabase Authentication Engine</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
