import React, { useState, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { API_BASE, API_VERSION, initCsrfProtection } from '../../utils/apiUtils';
import Alert from '../ui/Alert';

// Login component
function Login({ sessionExpired, onViewPublicStats }) {
  const { login, isLoading, setIsLoading, sessionExpired: authSessionExpired, setSessionExpired } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  // Clear session expired message when user starts typing
  useEffect(() => {
    if ((sessionExpired || authSessionExpired) && (username || password)) {
      setError('');
      setSessionExpired(false);
    }
  }, [username, password, sessionExpired, authSessionExpired, setSessionExpired]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    
    try {
      // Get CSRF token first
      await initCsrfProtection();
      
      // We don't use apiRequest here because we're getting the token
      const res = await fetch(`${API_BASE}${API_VERSION}/auth-token`, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-CSRF-Token': localStorage.getItem('csrfToken')
        },
        body: new URLSearchParams({ username, password }),
        credentials: 'include', // Important for CSRF cookies
      });
      
      if (!res.ok) {
        setError('Invalid username or password');
        setIsLoading(false);
        return;
      }
      
      const data = await res.json();
      
      // Use the context's login function
      await login(data.access_token, data.refresh_token, data.expires_in);
      setIsLoading(false);
    } catch (err) {
      setError('Network error. Please check your connection');
      setIsLoading(false);
    }
  };

  return (
    <div style={{ 
      display: 'flex', 
      justifyContent: 'center', 
      alignItems: 'center', 
      minHeight: '100vh',
      padding: '24px',
      backgroundColor: 'var(--background)',
      transition: 'background-color 0.3s',
    }}>
      <div style={{
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.75rem',
        padding: '2rem',
        width: '400px',
        maxWidth: '100%',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        transition: 'background-color 0.3s',
      }}>
        <h1 style={{ 
          fontSize: '1.5rem', 
          fontWeight: 600, 
          marginTop: 0,
          marginBottom: '1.5rem',
          color: 'var(--text)',
        }}>
          Sign In
        </h1>
        
        {error && <Alert type="error">{error}</Alert>}
        {(sessionExpired || authSessionExpired) && <Alert type="error">Your session has expired. Please sign in again.</Alert>}
        
        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ 
              display: 'block', 
              fontSize: '0.875rem', 
              fontWeight: 500, 
              marginBottom: '0.5rem', 
              color: 'var(--text)',
            }} htmlFor="username">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="Enter your username"
              autoComplete="username"
              disabled={isLoading}
              style={{
                display: 'block',
                width: '100%',
                padding: '0.75rem 1rem',
                fontSize: '1rem',
                borderRadius: '0.5rem',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--card-bg)',
                color: 'var(--text)',
                transition: 'border-color 0.2s',
              }}
            />
          </div>
          
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ 
              display: 'block', 
              fontSize: '0.875rem', 
              fontWeight: 500, 
              marginBottom: '0.5rem', 
              color: 'var(--text)',
            }} htmlFor="password">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Enter your password"
              autoComplete="current-password"
              disabled={isLoading}
              style={{
                display: 'block',
                width: '100%',
                padding: '0.75rem 1rem',
                fontSize: '1rem',
                borderRadius: '0.5rem',
                border: '1px solid var(--border)',
                backgroundColor: 'var(--card-bg)',
                color: 'var(--text)',
                transition: 'border-color 0.2s',
              }}
            />
          </div>
          
          <button
            type="submit"
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '0.75rem 1rem',
              backgroundColor: 'var(--primary)',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              fontSize: '1rem',
              fontWeight: 500,
              cursor: 'pointer',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              gap: '0.5rem',
              transition: 'background 0.2s',
            }}
          >
            {isLoading && (
              <span style={{
                display: 'inline-block',
                width: '16px',
                height: '16px',
                border: '2px solid rgba(255, 255, 255, 0.3)',
                borderRadius: '50%',
                borderTopColor: '#fff',
                animation: 'spin 1s linear infinite',
              }}></span>
            )}
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}

export default Login;
