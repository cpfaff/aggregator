import React, { useState, useEffect } from 'react';
import ProviderDetail from './ProviderDetail';
import Header from './Header';
import Footer from './Footer';
import { API_BASE, API_VERSION, apiRequest, initCsrfProtection } from './apiUtils';
import { useAuth } from './AuthContext';
import { applyTheme } from './styles/theme';
import { addGlobalStyles } from './styles/globalStyles';
import Login from './components/auth/Login';
import Dashboard from './components/dashboard/Dashboard';
import UserManagement from './components/users/UserManagement';
import Changelog from './components/changelog/Changelog';

function App() {
  const { token, currentUser, logout, sessionExpired, handleTokenExpiration } = useAuth();
  const [activeView, setActiveView] = useState('dashboard'); // 'dashboard', 'userManagement', 'changelog', or 'providerDetail'
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [isDarkTheme, setIsDarkTheme] = useState(() => {
    const savedTheme = localStorage.getItem('isDarkTheme');
    return savedTheme ? JSON.parse(savedTheme) : false;
  });
  
  // Toggle theme function
  const toggleTheme = () => {
    const newTheme = !isDarkTheme;
    setIsDarkTheme(newTheme);
    localStorage.setItem('isDarkTheme', JSON.stringify(newTheme));
  };

  // Apply theme variables to root element when theme changes
  useEffect(() => {
    applyTheme(isDarkTheme);
  }, [isDarkTheme]);

  // Add global styles on first render
  useEffect(() => {
    addGlobalStyles();
  }, []);
  
  // Initialize CSRF protection on first render
  useEffect(() => {
    const initCsrf = async () => {
      try {
        await initCsrfProtection();
        console.log('CSRF protection initialized');
      } catch (error) {
        console.error('Failed to initialize CSRF protection:', error);
      }
    };
    
    initCsrf();
  }, []);

  // Reset view to dashboard when user logs in
  useEffect(() => {
    if (token) {
      setActiveView('dashboard');
      setSelectedProvider(null);
    }
  }, [token]);

  // Render appropriate view based on whether user data is fully loaded
  const renderContent = () => {
    // Don't render content until we have both token and user data
    if (!token) {
      return <Login sessionExpired={sessionExpired} />;
    }
    
    // If token exists but user data isn't loaded yet, show a loading state
    if (!currentUser) {
      return (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          flex: 1 
        }}>
          <div>Loading user data...</div>
        </div>
      );
    }
    
    // Only render content when we have both token and user data
    return (
      <>
        {activeView === 'dashboard' && (
          <Dashboard 
            currentUser={currentUser} 
            onViewProviderDetails={(provider) => {
              setSelectedProvider(provider);
              setActiveView('providerDetail');
            }}
          />
        )}
        
        {activeView === 'userManagement' && currentUser && currentUser.is_global_admin && (
          <UserManagement />
        )}
        
        {activeView === 'changelog' && (
          <Changelog />
        )}
        
        {activeView === 'providerDetail' && selectedProvider && (
          <ProviderDetail 
            provider={selectedProvider}
            currentUser={currentUser}
            onBack={() => {
              setActiveView('dashboard');
              setSelectedProvider(null);
            }}
          />
        )}
      </>
    );
  };

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      minHeight: '100vh',
      backgroundColor: 'var(--background)',
      color: 'var(--text)',
      transition: 'background-color 0.3s, color 0.3s',
    }}>
      {token && currentUser && (
        <Header 
          currentUser={currentUser} 
          activeView={activeView}
          setActiveView={(view) => {
            setActiveView(view);
            // Reset provider detail view when navigating away
            if (view !== 'providerDetail') {
              setSelectedProvider(null);
            }
          }}
          logout={logout}
          isDarkTheme={isDarkTheme}
          toggleTheme={toggleTheme}
        />
      )}

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {renderContent()}
      </div>

      {token && currentUser && <Footer />}
    </div>
  );
}

export default App;
