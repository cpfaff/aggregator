import React, { useState, useEffect } from 'react';
import ProviderDetail from './components/providers/ProviderDetail';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import { API_BASE, API_VERSION, apiRequest, initCsrfProtection } from './utils/apiUtils';
import { useAuth } from './components/auth/AuthContext';
import { applyTheme } from './styles/theme';
import { addGlobalStyles } from './styles/globalStyles';
import Login from './components/auth/Login';
import Dashboard from './components/dashboard/Dashboard';
import UserManagement from './components/users/UserManagement';
import Changelog from './components/changelog/Changelog';
import About from './components/public/About';
import LandingPage from './components/public/LandingPage';
import { AdminDashboard, PublicStatsDashboard } from './components/statistics';

function App() {
  const { token, currentUser, logout, sessionExpired, handleTokenExpiration } = useAuth();
  const [activeView, setActiveView] = useState('landing'); // 'landing', 'login', 'dashboard', 'userManagement', 'changelog', 'providerDetail', 'adminStats', 'publicStats', or 'about'
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
    // Public views can be accessed without authentication
    if (activeView === 'landing') {
      return <LandingPage 
        onGetStarted={() => setActiveView('login')}
        onLearnMore={() => setActiveView('about')}
        onViewStatistics={() => setActiveView('publicStats')}
      />;
    }
    
    if (activeView === 'publicStats') {
      return <PublicStatsDashboard />;
    }
    
    if (activeView === 'about') {
      return <About currentUser={currentUser} />;
    }
    
    // Login view - don't render content until we have both token and user data
    if (!token || activeView === 'login') {
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
        
        {activeView === 'adminStats' && currentUser && currentUser.is_global_admin && (
          <AdminDashboard />
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
      <Header 
        currentUser={token ? currentUser : null} 
        activeView={activeView}
        setActiveView={(view) => {
          setActiveView(view);
          // Reset provider detail view when navigating away
          if (view !== 'providerDetail') {
            setSelectedProvider(null);
          }
        }}
        logout={() => {
          logout();
          setActiveView('landing');
        }}
        isDarkTheme={isDarkTheme}
        toggleTheme={toggleTheme}
      />

      <div style={{ 
        flex: 1, 
        display: 'flex', 
        flexDirection: 'column',
        width: '100%',
        alignItems: activeView === 'landing' || activeView === 'about' || activeView === 'publicStats' || activeView === 'login' ? 'stretch' : 'center',
      }}>
        {(activeView === 'landing' || activeView === 'about' || activeView === 'publicStats' || activeView === 'login') ? (
          renderContent()
        ) : (
          <div style={{
            width: '100%',
            maxWidth: '1200px',
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
          }}>
            {renderContent()}
          </div>
        )}
      </div>

      <Footer />
    </div>
  );
}

export default App;
