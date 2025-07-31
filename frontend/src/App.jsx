import React, { useState, useEffect } from 'react'

const API_BASE = 'http://localhost:8003'

function App() {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const [token, setToken] = useState(localStorage.getItem('auth_token'))

  // Check auth on mount
  useEffect(() => {
    const checkAuth = async () => {
      if (token) {
        try {
          const response = await fetch(`${API_BASE}/auth/user`, {
            headers: { Authorization: `Bearer ${token}` }
          })
          
          if (response.ok) {
            const userData = await response.json()
            setUser(userData)
          } else {
            localStorage.removeItem('auth_token')
            setToken(null)
          }
        } catch (error) {
          console.error('Auth check failed:', error)
          localStorage.removeItem('auth_token')
          setToken(null)
        }
      }
      setLoading(false)
    }

    checkAuth()
  }, [token])

  // Handle auth success callback
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const urlToken = urlParams.get('token')
    
    if (urlToken && window.location.pathname === '/auth/success') {
      localStorage.setItem('auth_token', urlToken)
      setToken(urlToken)
      window.history.replaceState({}, document.title, '/')
    }
  }, [])

  const login = async () => {
    try {
      const response = await fetch(`${API_BASE}/auth/login`)
      const data = await response.json()
      window.location.href = data.auth_url
    } catch (error) {
      console.error('Login failed:', error)
    }
  }

  const logout = () => {
    localStorage.removeItem('auth_token')
    setToken(null)
    setUser(null)
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <h1 className="text-3xl font-bold mb-8">Microsoft OAuth Demo</h1>
          <button
            onClick={login}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg"
          >
            Sign in with Microsoft
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-xl font-semibold">OAuth Demo</h1>
          <button
            onClick={logout}
            className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded"
          >
            Sign out
          </button>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto p-4">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-bold mb-4">Welcome, {user.name}!</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700">Name</label>
              <p className="mt-1 text-sm text-gray-900">{user.name}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">Email</label>
              <p className="mt-1 text-sm text-gray-900">{user.email}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700">User ID</label>
              <p className="mt-1 text-sm text-gray-900 font-mono text-xs">{user.user_id}</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App