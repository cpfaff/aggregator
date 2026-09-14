import React, { useState, useEffect, useLayoutEffect } from 'react';
import { Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import ProviderDetail from './components/providers/ProviderDetail';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import { initCsrfProtection } from './utils/apiUtils';
import { useAuth } from './components/auth/AuthContext';
import {
  applyTheme,
  resolveInitialTheme,
  storeThemeChoice,
  subscribeToSystemTheme,
} from './styles/theme';
import Login from './components/auth/Login';
import Providers from './components/providers/Providers';
import UserManagement from './components/users/UserManagement';
import Changelog from './components/changelog/Changelog';
import About from './components/public/About';
import LandingPage from './components/public/LandingPage';
import { AdminDashboard, PublicStatsDashboard } from './components/statistics';
import { ToastContainer } from './components/ui/Toast';
import ErrorBoundary from './components/ui/ErrorBoundary';

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
  const { token, currentUser, logout, sessionExpired } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  // Mirrors the boot script in public/index.html, which has already stamped
  // data-theme on <html> before this ever runs. Resolving it the same way here
  // keeps React's first render in agreement with what is already painted.
  const [isDarkTheme, setIsDarkTheme] = useState(resolveInitialTheme);

  // Toggle theme function
  const toggleTheme = () => {
    const newTheme = !isDarkTheme;
    setIsDarkTheme(newTheme);
    storeThemeChoice(newTheme);
  };

  // Keep <html data-theme> in sync with React's view of the theme. A layout
  // effect, not a passive one: passive effects are scheduled as a separate
  // task, which lets a frame paint in between — that gap was the theme flash.
  // On first load this is a no-op, because the boot script already set it.
  useLayoutEffect(() => {
    applyTheme(isDarkTheme);
  }, [isDarkTheme]);

  // Follow the OS while the user has made no explicit choice.
  useEffect(() => subscribeToSystemTheme(setIsDarkTheme), []);

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
        alignItems: ['/', '/about', '/statistics', '/login', '/changelog'].includes(location.pathname) ? 'stretch' : 'center',
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
            <About currentUser={currentUser} isDarkTheme={isDarkTheme} />
          } />

          <Route path="/statistics" element={
            <ErrorBoundary>
              <PublicStatsDashboard />
            </ErrorBoundary>
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
                <ErrorBoundary>
                  <ProviderDetail
                    currentUser={currentUser}
                  />
                </ErrorBoundary>
              </div>
            </ProtectedRoute>
          } />

          <Route path="/changelog" element={
            <Changelog currentUser={currentUser} />
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
              <div style={{
                width: '100%',
                maxWidth: '1200px',
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
              }}>
                <ErrorBoundary>
                  <AdminDashboard />
                </ErrorBoundary>
              </div>
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
