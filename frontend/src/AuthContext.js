// src/AuthContext.js
import React, { createContext, useState, useContext, useEffect } from 'react';
import { refreshAccessToken, apiRequest } from './apiUtils';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [refreshToken, setRefreshToken] = useState(localStorage.getItem('refreshToken'));
  const [tokenExpiry, setTokenExpiry] = useState(localStorage.getItem('tokenExpiry'));
  const [currentUser, setCurrentUser] = useState(() => {
    const savedUser = localStorage.getItem('currentUser');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [isLoading, setIsLoading] = useState(false);
  const [sessionExpired, setSessionExpired] = useState(false);
  
  // Fetch user data when token changes
  useEffect(() => {
    const fetchUserData = async () => {
      if (!token) return;
      
      try {
        const response = await apiRequest('/me/permissions', {}, handleTokenExpiration);
        
        if (response.ok) {
          const userData = await response.json();
          setCurrentUser(userData);
          localStorage.setItem('currentUser', JSON.stringify(userData));
        }
      } catch (error) {
        console.error('Error fetching user data:', error);
      }
    };
    
    fetchUserData();
  }, [token]);
  
  // Set up automatic token refresh
  useEffect(() => {
    if (!token || !refreshToken || !tokenExpiry) return;
    
    const timeUntilExpiry = parseInt(tokenExpiry) - Date.now() - 60000; // 1 minute buffer
    
    if (timeUntilExpiry <= 0) {
      // Token is already expired, try to refresh now
      refreshAccessToken().catch(() => logout());
      return;
    }
    
    // Set up timer to refresh before expiry
    const refreshTimer = setTimeout(() => {
      refreshAccessToken().catch(() => logout());
    }, timeUntilExpiry);
    
    return () => clearTimeout(refreshTimer);
  }, [token, refreshToken, tokenExpiry]);
  
  // Listen for token updates from apiUtils
  useEffect(() => {
    const handleTokensUpdated = (event) => {
      const { access_token, refresh_token, expires_in } = event.detail;
      setToken(access_token);
      setRefreshToken(refresh_token);
      setTokenExpiry(Date.now() + (expires_in * 1000));
    };

    window.addEventListener('auth:tokens-updated', handleTokensUpdated);
    return () => window.removeEventListener('auth:tokens-updated', handleTokensUpdated);
  }, []);
  
  const login = async (accessToken, newRefreshToken, expiresIn) => {
    localStorage.setItem('token', accessToken);
    localStorage.setItem('refreshToken', newRefreshToken);
    localStorage.setItem('tokenExpiry', Date.now() + (expiresIn * 1000));
    
    setToken(accessToken);
    setRefreshToken(newRefreshToken);
    setTokenExpiry(Date.now() + (expiresIn * 1000));
    setSessionExpired(false);
  };
  
  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('tokenExpiry');
    localStorage.removeItem('currentUser');
    
    setToken(null);
    setRefreshToken(null);
    setTokenExpiry(null);
    setCurrentUser(null);
  };
  
  const handleTokenExpiration = () => {
    logout();
    setSessionExpired(true);
  };
  
  return (
    <AuthContext.Provider 
      value={{ 
        token, 
        currentUser, 
        isLoading, 
        setIsLoading,
        sessionExpired,
        setSessionExpired,
        login, 
        logout, 
        handleTokenExpiration 
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
