import React, { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import { supabase } from './lib/supabaseClient'
import { CloudLightning, RotateCw } from 'lucide-react'
import './styles/index.css'

export default function App() {
  const [session, setSession] = useState(null)
  const [user, setUser] = useState(null)
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [authError, setAuthError] = useState(null)

  // Handle profile syncing to Supabase DB (idempotent upsert)
  const syncUserProfile = async (authUser) => {
    if (!authUser) return null
    try {
      const full_name = authUser.user_metadata?.full_name || authUser.user_metadata?.name || authUser.email || ''
      const avatar_url = authUser.user_metadata?.avatar_url || authUser.user_metadata?.picture || ''

      const profileData = {
        id: authUser.id,
        email: authUser.email,
        full_name,
        avatar_url,
        updated_at: new Date().toISOString(),
      }

      // Upsert into Supabase profiles table
      const { data, error } = await supabase
        .from('profiles')
        .upsert(profileData, { onConflict: 'id' })
        .select()
        .maybeSingle()

      if (error) {
        console.warn('Profile upsert notice:', error.message)
      }
      return data || profileData
    } catch (err) {
      console.error('Failed to sync user profile:', err)
      return {
        id: authUser.id,
        email: authUser.email,
        full_name: authUser.user_metadata?.full_name || authUser.user_metadata?.name || authUser.email,
        avatar_url: authUser.user_metadata?.avatar_url || authUser.user_metadata?.picture || '',
      }
    }
  }

  useEffect(() => {
    let subscription = null

    async function initAuth() {
      try {
        setLoading(true)
        // 1. Fetch current session
        const { data: { session: currentSession }, error } = await supabase.auth.getSession()

        if (error) {
          console.error('Supabase getSession error:', error)
          setAuthError(error.message)
        } else if (currentSession?.user) {
          setSession(currentSession)
          setUser(currentSession.user)
          const prof = await syncUserProfile(currentSession.user)
          setProfile(prof)
        }
      } catch (err) {
        console.error('Session initialization error:', err)
        setAuthError(err.message || 'Supabase connection failed.')
      } finally {
        setLoading(false)
      }

      // 2. Set up auth state change listener
      const { data: authListener } = supabase.auth.onAuthStateChange(async (event, newSession) => {
        setSession(newSession)
        if (newSession?.user) {
          setUser(newSession.user)
          const prof = await syncUserProfile(newSession.user)
          setProfile(prof)
        } else {
          setUser(null)
          setProfile(null)
        }
        setLoading(false)
      })

      subscription = authListener?.subscription
    }

    initAuth()

    return () => {
      if (subscription) {
        subscription.unsubscribe()
      }
    }
  }, [])

  const handleLogout = async () => {
    try {
      setLoading(true)
      const { error } = await supabase.auth.signOut()
      if (error) {
        console.error('Logout error:', error)
        alert('Failed to log out: ' + error.message)
      } else {
        setSession(null)
        setUser(null)
        setProfile(null)
      }
    } catch (err) {
      console.error('Unexpected logout error:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: '#0b0f19',
          color: '#f8fafc',
          gap: '1rem',
          fontFamily: "'Inter', sans-serif",
        }}
      >
        <CloudLightning size={40} color="#38bdf8" />
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.9rem', color: '#94a3b8' }}>
          <RotateCw size={16} className="spin-animation" color="#38bdf8" />
          <span>Authenticating MOES Operational Session...</span>
        </div>
      </div>
    )
  }

  if (!session) {
    return <Login authError={authError} />
  }

  return <Dashboard user={user} profile={profile} onLogout={handleLogout} />
}
