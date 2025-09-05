import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import ProviderDetail from './components/providers/ProviderDetail';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import { API_BASE, API_VERSION, apiRequest, initCsrfProtection } from './utils/apiUtils';
import { useAuth } from './components/auth/AuthContext';
import { applyTheme } from './styles/theme';
import { addGlobalStyles } from './styles/globalStyles';
import Login from './components/auth/Login';
import Providers from './components/providers/Providers';
import UserManagement from './components/users/UserManagement';
import Changelog from './components/changelog/Changelog';
import About from './components/public/About';
import LandingPage from './components/public/LandingPage';
import { AdminDashboard, PublicStatsDashboard } from './components/statistics';
import { ToastContainer } from './components/ui/Toast';

// Protected Route wrapper component
function ProtectedRoute({ children }) {
  const { token, currentUser } = useAuth();
  const location = useLocation();
  
  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  
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
  
  return children;
}

// Admin-only Route wrapper
function AdminRoute({ children }) {
  const { currentUser } = useAuth();
  
  if (!currentUser?.is_global_admin) {
    return <Navigate to="/providers" replace />;
  }
  
  return children;
}

function App() {
  const { token, currentUser, logout, sessionExpired, handleTokenExpiration } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
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

  // Handle logout
  const handleLogout = () => {
    logout();
    navigate('/');
  };

  // Derive active view from location for Header component compatibility
  const getActiveView = () => {
    const path = location.pathname;
    if (path === '/') return 'landing';
    if (path === '/login') return 'login';
    if (path === '/providers' || path.startsWith('/provider/')) return 'providers';
    if (path === '/users') return 'userManagement';
    if (path === '/changelog') return 'changelog';
    if (path === '/statistics') return 'publicStats';
    if (path === '/admin/statistics') return 'adminStats';
    if (path === '/about') return 'about';
    return 'landing';
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
        activeView={getActiveView()}
        navigate={navigate}
        logout={handleLogout}
        isDarkTheme={isDarkTheme}
        toggleTheme={toggleTheme}
      />

      <div style={{ 
        flex: 1, 
        display: 'flex', 
        flexDirection: 'column',
        width: '100%',
        alignItems: ['/', '/about', '/statistics', '/login'].includes(location.pathname) ? 'stretch' : 'center',
      }}>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={
            <LandingPage 
              onGetStarted={() => navigate('/login')}
              onLearnMore={() => navigate('/about')}
              onViewStatistics={() => navigate('/statistics')}
            />
          } />
          
          <Route path="/about" element={
            <About currentUser={currentUser} />
          } />
          
          <Route path="/statistics" element={
            <PublicStatsDashboard />
          } />
          
          <Route path="/login" element={
            token ? <Navigate to="/providers" replace /> : 
            <Login sessionExpired={sessionExpired} />
          } />
          
          {/* Protected Routes */}
          <Route path="/providers" element={
            <ProtectedRoute>
              <div style={{
                width: '100%',
                maxWidth: '1200px',
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
              }}>
                <Providers 
                  currentUser={currentUser} 
                  onViewProviderDetails={(provider) => {
                    navigate(`/provider/${provider.id}`);
                  }}
                />
              </div>
            </ProtectedRoute>
          } />
          
          <Route path="/provider/:id" element={
            <ProtectedRoute>
              <div style={{
                width: '100%',
                maxWidth: '1200px',
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
              }}>
                <ProviderDetail 
                  currentUser={currentUser}
                />
              </div>
            </ProtectedRoute>
          } />
          
          <Route path="/changelog" element={
            <ProtectedRoute>
              <div style={{
                width: '100%',
                maxWidth: '1200px',
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
              }}>
                <Changelog />
              </div>
            </ProtectedRoute>
          } />
          
          {/* Admin Routes */}
          <Route path="/users" element={
            <ProtectedRoute>
              <AdminRoute>
                <div style={{
                  width: '100%',
                  maxWidth: '1200px',
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                }}>
                  <UserManagement />
                </div>
              </AdminRoute>
            </ProtectedRoute>
          } />
          
          <Route path="/admin/statistics" element={
            <ProtectedRoute>
              <AdminRoute>
                <div style={{
                  width: '100%',
                  maxWidth: '1200px',
                  flex: 1,
                  display: 'flex',
                  flexDirection: 'column',
                }}>
                  <AdminDashboard />
                </div>
              </AdminRoute>
            </ProtectedRoute>
          } />
          
          {/* Catch-all redirect */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>

      {location.pathname !== '/login' && <Footer />}
      <ToastContainer />
    </div>
  );
}

export default App;