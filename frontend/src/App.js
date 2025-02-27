import React, { useState, useEffect } from 'react';
import { Database, Globe, Server, Edit, Trash2 } from 'lucide-react';
import ProviderCard from './ProviderCard';
import Header from './Header';
import Footer from './Footer';
import { API_BASE, apiRequest } from './apiUtils';

// Theme variables using CSS variables approach (from Design Playground)
const themeVariables = {
  light: {
    '--primary': '#2563eb',
    '--success': '#16a34a',
    '--error': '#dc2626',
    '--warning': '#ea580c',
    '--background': '#f8fafc',      // page background
    '--card-bg': '#ffffff',         // main card/container background
    // '--subtle-bg': '#f1f5f9',       // smaller sub-panels or highlight sections
    '--subtle-bg': '#f1f5f9',       // smaller sub-panels or highlight sections
    '--text': '#1e293b',
    '--text-light': '#64748b',
    '--border': '#e2e8f0',
  },
  dark: {
    '--primary': '#3b82f6',
    '--success': '#22c55e',
    '--error': '#ef4444',
    '--warning': '#f97316',
    '--background': '#1e293b',
    '--card-bg': '#273444',
    '--subtle-bg': '#2f3e4e',
    '--text': '#f8fafc',
    '--text-light': '#cbd5e1',
    '--border': '#3b4a63',
  }
};

// Add global styles with CSS variables support
const addGlobalStyles = () => {
  const style = document.createElement('style');
  style.innerHTML = `
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    html, body { 
      margin: 0; 
      padding: 0;
      scrollbar-width: thin;
      scrollbar-color: var(--border) var(--card-bg);
    }
    * { box-sizing: border-box; }
    button:focus, input:focus, textarea:focus, select:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }
    input:disabled, textarea:disabled, select:disabled, button:disabled {
      background-color: var(--subtle-bg);
      cursor: not-allowed;
    }
    html::-webkit-scrollbar,
    body::-webkit-scrollbar,
    .modal-content-scrollable::-webkit-scrollbar {
      width: 6px;
    }
    html::-webkit-scrollbar-track,
    body::-webkit-scrollbar-track,
    .modal-content-scrollable::-webkit-scrollbar-track {
      background: var(--card-bg);
    }
    html::-webkit-scrollbar-thumb,
    body::-webkit-scrollbar-thumb,
    .modal-content-scrollable::-webkit-scrollbar-thumb {
      background-color: var(--border);
      border-radius: 3px;
    }
    html::-webkit-scrollbar-thumb:hover,
    body::-webkit-scrollbar-thumb:hover,
    .modal-content-scrollable::-webkit-scrollbar-thumb:hover {
      background-color: var(--text-light);
    }
  `;
  document.head.appendChild(style);
};

// Alert component for notifications
function Alert({ type = 'error', children }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      padding: '1rem',
      borderRadius: '0.5rem',
      marginBottom: '1rem',
      gap: '0.75rem',
      backgroundColor: type === 'error' ? '#fee2e2' : '#dcfce7',
      color: type === 'error' ? 'var(--error)' : 'var(--success)',
      borderLeft: `4px solid ${type === 'error' ? 'var(--error)' : 'var(--success)'}`,
    }}>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        {type === 'error' ? (
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
        ) : (
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
        )}
      </svg>
      {children}
    </div>
  );
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [currentUser, setCurrentUser] = useState(() => {
    const savedUser = localStorage.getItem('currentUser');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [activeView, setActiveView] = useState('dashboard'); // 'dashboard' or 'userManagement'
  const [isDarkTheme, setIsDarkTheme] = useState(() => {
    const savedTheme = localStorage.getItem('isDarkTheme');
    return savedTheme ? JSON.parse(savedTheme) : false;
  });
  const [sessionExpired, setSessionExpired] = useState(false);
  
  // Toggle theme function
  const toggleTheme = () => {
    const newTheme = !isDarkTheme;
    setIsDarkTheme(newTheme);
    localStorage.setItem('isDarkTheme', JSON.stringify(newTheme));
  };

  // Apply theme variables to root element when theme changes
  useEffect(() => {
    const theme = isDarkTheme ? themeVariables.dark : themeVariables.light;
    Object.entries(theme).forEach(([property, value]) => {
      document.documentElement.style.setProperty(property, value);
    });
  }, [isDarkTheme]);

  // Add global styles on first render
  useEffect(() => {
    addGlobalStyles();
  }, []);

  // Check token validity on mount and after token changes
  useEffect(() => {
    const validateToken = async () => {
      if (!token) return;
      
      try {
        const response = await apiRequest('/me/permissions', {}, () => {
          // This callback will be called if token is expired
          logout();
          setSessionExpired(true);
        });
        
        if (!response.ok) {
          // Token is invalid for some other reason
          logout();
          return;
        }
        
        const userData = await response.json();
        setCurrentUser(userData);
        localStorage.setItem('currentUser', JSON.stringify(userData));
      } catch (error) {
        console.error('Failed to validate token:', error);
        // Don't logout here as the error might be temporary
        // The apiRequest will handle token expiration
      }
    };

    validateToken();
  }, [token]);

  const logout = () => {
    setToken(null);
    setCurrentUser(null);
    setActiveView('dashboard');
    localStorage.removeItem('token');
    localStorage.removeItem('currentUser');
  };

  return (
    <div style={{
      fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      backgroundColor: 'var(--background)',
      color: 'var(--text)',
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      lineHeight: 1.5,
      transition: 'background-color 0.3s, color 0.3s',
    }}>
      {token && currentUser && (
        <Header 
          currentUser={currentUser} 
          activeView={activeView}
          setView={setActiveView} 
          logout={logout}
          isDarkTheme={isDarkTheme}
          toggleTheme={toggleTheme}
        />
      )}
      
      {!token ? (
        <Login setToken={setToken} setCurrentUser={setCurrentUser} sessionExpired={sessionExpired} setSessionExpired={setSessionExpired} />
      ) : (
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
          {activeView === 'dashboard' && <Dashboard token={token} currentUser={currentUser} onTokenExpired={() => { logout(); setSessionExpired(true); }} />}
          {activeView === 'userManagement' && currentUser.is_global_admin && <UserManagement token={token} onTokenExpired={() => { logout(); setSessionExpired(true); }} />}
          
          <Footer />
        </div>
      )}
    </div>
  );
}

export default App;

// Enhanced Modal component with proper scrollbar styling
function Modal({ isOpen, onClose, title, children, footer }) {
  React.useEffect(() => {
    if (isOpen) {
      // Save the current body overflow style
      const originalStyle = window.getComputedStyle(document.body).overflow;
      // Disable scrolling on body
      document.body.style.overflow = 'hidden';
      
      // Restore original overflow style when modal is closed
      return () => {
        document.body.style.overflow = originalStyle;
      };
    }
  }, [isOpen]); // Only re-run when isOpen changes

  if (!isOpen) return null;
  
  return (
    <div 
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.1)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000,
      }} 
      onClick={onClose}
    >
      <div 
        style={{
          backgroundColor: 'var(--card-bg)',
          padding: '2rem',
          borderRadius: '0.75rem',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          width: '90%',
          maxWidth: '800px',
          maxHeight: '90vh',
          position: 'relative',
          transition: 'background-color 0.3s',
          display: 'flex',
          flexDirection: 'column',
        }} 
        onClick={e => e.stopPropagation()}
      >
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center',
          marginBottom: '1.5rem',
        }}>
          <h3 style={{ 
            margin: 0, 
            fontSize: '1.25rem', 
            fontWeight: 600,
            color: 'var(--text)',
          }}>
            {title}
          </h3>
          <button 
            onClick={onClose}
            style={{
              backgroundColor: 'transparent',
              border: 'none',
              fontSize: '1.5rem',
              lineHeight: 1,
              padding: '0.25rem',
              cursor: 'pointer',
              color: 'var(--text-light)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>
        
        <div 
          className="modal-content-scrollable"
          style={{ 
            flex: 1,
            overflowY: 'auto',
            marginRight: '-0.5rem',
            paddingRight: '0.5rem',
          }}
          onWheel={(e) => e.stopPropagation()}
        >
          {children}
        </div>
        
        {footer && (
          <div style={{ 
            display: 'flex', 
            justifyContent: 'flex-end', 
            gap: '0.75rem',
            marginTop: '1.5rem',
            borderTop: '1px solid var(--border)',
            paddingTop: '1.5rem',
          }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

// Enhanced confirm modal for deletion confirmations
function ConfirmModal({ message, onConfirm, onCancel, title = 'Confirm Action' }) {
  return (
    <Modal 
      isOpen={true} 
      onClose={onCancel}
      title={title}
      footer={
        <>
          <button 
            onClick={onCancel}
            style={{
              padding: '0.75rem 1rem',
              backgroundColor: 'transparent',
              color: 'var(--text-light)',
              border: '1px solid var(--border)',
              borderRadius: '0.5rem',
              fontSize: '1rem',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'background-color 0.3s',
            }}
          >
            Cancel
          </button>
          <button 
            onClick={onConfirm}
            style={{
              padding: '0.75rem 1rem',
              backgroundColor: 'var(--error)',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              fontSize: '1rem',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'background-color 0.3s',
            }}
          >
            Confirm
          </button>
        </>
      }
    >
      <p style={{ color: 'var(--text)', marginBottom: '1rem' }}>{message}</p>
    </Modal>
  );
}

// Button component
function Button({ children, onClick, variant = 'primary', isLoading, disabled, style, ...props }) {
  const getButtonStyle = () => {
    const baseStyle = {
      height: '2.75rem',
      padding: '0 1.5rem',
      borderRadius: '0.5rem',
      fontWeight: 500,
      fontSize: '1rem',
      cursor: 'pointer',
      transition: 'background 0.2s, transform 0.1s',
      display: 'flex',
      alignItems: 'center',
      gap: '0.5rem',
    };

    if (variant === 'primary') {
      return {
        ...baseStyle,
        backgroundColor: 'var(--primary)',
        color: 'white',
        border: 'none',
      };
    } else if (variant === 'danger') {
      return {
        ...baseStyle,
        backgroundColor: 'transparent',
        color: 'var(--error)',
        border: '1px solid var(--border)',
      };
    } else {
      return {
        ...baseStyle,
        backgroundColor: 'transparent',
        color: 'var(--text-light)',
        border: '1px solid var(--border)',
      };
    }
  };
  
  return (
    <button 
      style={{...getButtonStyle(), ...(style || {})}} 
      onClick={onClick}
      disabled={isLoading || disabled}
      {...props}
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
      {children}
    </button>
  );
}

// Login component
function Login({ setToken, setCurrentUser, sessionExpired, setSessionExpired }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Clear session expired message when user starts typing
  useEffect(() => {
    if (sessionExpired && (username || password)) {
      setSessionExpired(false);
    }
  }, [username, password, sessionExpired, setSessionExpired]);

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);
    
    try {
      // We don't use apiRequest here because we're getting the token
      const res = await fetch(`${API_BASE}/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ username, password }),
      });
      
      if (!res.ok) {
        setError('Invalid username or password');
        setIsLoading(false);
        return;
      }
      
      const data = await res.json();
      localStorage.setItem('token', data.access_token);
      setToken(data.access_token);
      
      // Now we have a token, we can use apiRequest
      const permRes = await apiRequest('/me/permissions', {}, () => {
        // This callback will only be called if token is expired
        setError('Failed to authenticate. Please try again.');
        setIsLoading(false);
        localStorage.removeItem('token');
        setToken(null);
      });
      
      if (!permRes.ok) {
        setError('Failed to fetch user permissions');
        setIsLoading(false);
        return;
      }
      
      const permData = await permRes.json();
      localStorage.setItem('currentUser', JSON.stringify(permData));
      setCurrentUser(permData);
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
        {sessionExpired && <Alert type="error">Your session has expired. Please sign in again.</Alert>}
        
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

// Dashboard component with improved nested form integration
function Dashboard({ token, currentUser, onTokenExpired }) {
  const [providers, setProviders] = useState([]);
  const [editingProvider, setEditingProvider] = useState(null);
  const [addingProvider, setAddingProvider] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchProviders = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const res = await apiRequest('/providers', {}, onTokenExpired);
      
      if (!res.ok) {
        if (res.status === 403) {
          setError('You do not have permission to view providers');
        } else {
          setError('Failed to fetch providers');
        }
        setIsLoading(false);
        return;
      }
      
      const data = await res.json();
      setProviders(data);
      setIsLoading(false);
    } catch (err) {
      setError('Error fetching providers: ' + err.message);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProviders();
  }, [token]);

  const deleteProvider = async (id) => {
    setIsLoading(true);
    setError('');
    
    try {
      const res = await apiRequest(`/providers/${id}`, {
        method: 'DELETE'
      }, onTokenExpired);
      
      if (!res.ok) {
        let errorMessage = 'Failed to delete provider';
        try {
          const errorData = await res.json();
          if (res.status === 403) {
            errorMessage = 'You do not have permission to delete this provider';
          } else {
            errorMessage = errorData.detail || errorMessage;
          }
        } catch (e) {
          // If we can't parse the error response, use the default message
        }
        setError(errorMessage);
        setIsLoading(false);
        return;
      }
      
      // Remove from local state
      setProviders(providers.filter(p => p.id !== id));
      setConfirmDelete(null);
      setIsLoading(false);
    } catch (err) {
      // Only set error if it's not a token expiration error
      // Token expiration is handled by the onTokenExpired callback
      if (!err.message || !err.message.includes('Session expired')) {
        setError('Error deleting provider: ' + err.message);
      }
      setIsLoading(false);
    }
  };

  const closeModals = () => {
    setEditingProvider(null);
    setAddingProvider(false);
  };

  const handleProviderUpdate = (updatedProvider) => {
    if (!updatedProvider) {
      closeModals();
      return;
    }
    
    // Update the local state immediately with the new data
    if (editingProvider) {
      setProviders(providers.map(p => 
        p.id === updatedProvider.id ? updatedProvider : p
      ));
    } else {
      setProviders([...providers, updatedProvider]);
    }
    
    closeModals();
  };

  return (
    <div style={{ 
      flexGrow: 1,
      padding: '2rem 1rem',
      maxWidth: '1200px',
      margin: '0 auto',
      width: '100%',
    }}>
      {/* Page title and actions */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '1.5rem',
      }}>
        <h2 style={{ 
          fontSize: '1.5rem', 
          fontWeight: 600, 
          margin: 0,
          color: 'var(--text)',
        }}>
          Data Providers
        </h2>
        
        {currentUser?.is_global_admin && (
          <Button 
            onClick={() => { setAddingProvider(true); setEditingProvider(null); }}
          >
            <span style={{ fontSize: '1.25rem' }}>+</span>
            <span>Add Provider</span>
          </Button>
        )}
      </div>
      
      {error && <Alert type="error">{error}</Alert>}
      
      {isLoading && !addingProvider && !editingProvider ? (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          padding: '4rem 0' 
        }}>
          <div style={{
            width: '32px',
            height: '32px',
            border: '3px solid var(--border)',
            borderRadius: '50%',
            borderTopColor: 'var(--primary)',
            animation: 'spin 1s linear infinite',
          }}></div>
        </div>
      ) : providers.length === 0 && !addingProvider ? (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          backgroundColor: 'var(--card-bg)',
          borderRadius: '0.75rem',
          color: 'var(--text-light)',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        }}>
          <h3 style={{ marginTop: 0, color: 'var(--text)' }}>No providers found</h3>
          <p style={{ marginBottom: '1.5rem' }}>Get started by adding your first data provider</p>
          {currentUser?.is_global_admin && (
            <Button onClick={() => { setAddingProvider(true); setEditingProvider(null); }}>
              Add Provider
            </Button>
          )}
        </div>
      ) : (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', 
          gap: '1.5rem',
          marginBottom: '2rem',
        }}>
        {providers.map((provider) => (
  <ProviderCard 
    key={provider.id}
    provider={provider}
    currentUser={currentUser}
    onEdit={(provider) => { setEditingProvider(provider); setAddingProvider(true); }}
    onDelete={(provider) => setConfirmDelete(provider)}
  />
))}
        </div>
      )}
      
      {confirmDelete && (
        <ConfirmModal
          title="Delete Provider"
          message={`Are you sure you want to delete "${confirmDelete.name}"? This will remove all associated datasets.`}
          onConfirm={() => { 
            deleteProvider(confirmDelete.id); 
            setConfirmDelete(null); 
          }}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
      
      <Modal
        isOpen={addingProvider}
        onClose={closeModals}
        title={editingProvider ? `Edit Provider: ${editingProvider.name}` : 'Add Provider'}
      >
        <ProviderForm
          token={token}
          provider={editingProvider}
          onClose={handleProviderUpdate}
          onTokenExpired={onTokenExpired}
        />
      </Modal>
    </div>
  );
}

// Enhanced ProviderForm component with fixed delete confirmation for all items
function ProviderForm({ token, provider, onClose, onTokenExpired }) {
  const isEditing = provider != null;
  const [formState, setFormState] = useState({
    name: provider ? provider.name : '',
    shortName: provider ? provider.shortName : '',
    datacenter: provider ? provider.datacenter : '',
    url: provider ? provider.url : '',
    biocaseUrl: provider ? provider.biocaseUrl : '',
    datasets: provider ? provider.datasets || [] : [],
  });
  const [validationErrors, setValidationErrors] = useState({});
  const [confirmAction, setConfirmAction] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  // Helper to update form state with validation
  const updateFormField = (field, value) => {
    setFormState(prev => ({
      ...prev,
      [field]: value
    }));
    
    // Clear validation error when field is updated
    if (validationErrors[field]) {
      setValidationErrors(prev => ({
        ...prev,
        [field]: null
      }));
    }
  };

  // Dataset operations
  const addDataset = () => {
    setFormState(prev => ({
      ...prev,
      datasets: [
        ...prev.datasets, 
        { 
          id: null, 
          source: '', 
          title: '', 
          landingPageUrl: '', 
          xmlArchives: [], 
          usefulLinks: [] 
        }
      ]
    }));
  };

  const updateDataset = (index, field, value) => {
    setFormState(prev => {
      const updatedDatasets = [...prev.datasets];
      updatedDatasets[index] = {
        ...updatedDatasets[index],
        [field]: value
      };
      return {
        ...prev,
        datasets: updatedDatasets
      };
    });
    
    // Clear validation errors
    const errorKey = `dataset_${index}_${field}`;
    if (validationErrors[errorKey]) {
      setValidationErrors(prev => ({
        ...prev,
        [errorKey]: null
      }));
    }
  };

  const removeDataset = (index) => {
    const dataset = formState.datasets[index];
    const displayName = dataset.title || `Dataset ${index + 1}`;
    
    // Ensure we set the confirmAction state regardless of whether it's a new or existing item
    setConfirmAction({
      message: `Are you sure you want to remove "${displayName}"? This will remove all associated datasets.`,
      onConfirm: () => {
        setFormState(prev => ({
          ...prev,
          datasets: prev.datasets.filter((_, idx) => idx !== index)
        }));
        setConfirmAction(null);
      },
      onCancel: () => setConfirmAction(null),
    });
  };

  // XML Archive operations
  const addXmlArchive = (dsIndex) => {
    setFormState(prev => {
      const updatedDatasets = [...prev.datasets];
      updatedDatasets[dsIndex] = {
        ...updatedDatasets[dsIndex],
        xmlArchives: [
          ...updatedDatasets[dsIndex].xmlArchives,
          { id: null, url: '', isLatest: false }
        ]
      };
      return {
        ...prev,
        datasets: updatedDatasets
      };
    });
  };

  const updateXmlArchive = (dsIndex, archIndex, field, value) => {
    setFormState(prev => {
      const updatedDatasets = [...prev.datasets];
      const updatedArchives = [...updatedDatasets[dsIndex].xmlArchives];
      updatedArchives[archIndex] = {
        ...updatedArchives[archIndex],
        [field]: value
      };
      updatedDatasets[dsIndex] = {
        ...updatedDatasets[dsIndex],
        xmlArchives: updatedArchives
      };
      return {
        ...prev,
        datasets: updatedDatasets
      };
    });
    
    // Clear validation errors
    const errorKey = `dataset_${dsIndex}_xml_${archIndex}_${field}`;
    if (validationErrors[errorKey]) {
      setValidationErrors(prev => ({
        ...prev,
        [errorKey]: null
      }));
    }
  };

  const removeXmlArchive = (dsIndex, archIndex) => {
    const dataset = formState.datasets[dsIndex];
    const archive = dataset.xmlArchives[archIndex];
    const displayUrl = archive.url || `Archive ${archIndex + 1}`;
    
    // Force the confirmAction state to update
    setConfirmAction(null);  // First clear it
    
    // Then set it with a slight delay to ensure state update
    setTimeout(() => {
      setConfirmAction({
        message: `Are you sure you want to remove XML Archive "${displayUrl}"? This action cannot be undone.`,
        onConfirm: () => {
          setFormState(prev => {
            const updatedDatasets = [...prev.datasets];
            const updatedArchives = updatedDatasets[dsIndex].xmlArchives.filter(
              (_, idx) => idx !== archIndex
            );
            updatedDatasets[dsIndex] = {
              ...updatedDatasets[dsIndex],
              xmlArchives: updatedArchives
            };
            return {
              ...prev,
              datasets: updatedDatasets
            };
          });
          setConfirmAction(null);
        },
        onCancel: () => setConfirmAction(null),
      });
    }, 10);
  };

  // Useful Links operations
  const addUsefulLink = (dsIndex) => {
    setFormState(prev => {
      const updatedDatasets = [...prev.datasets];
      updatedDatasets[dsIndex] = {
        ...updatedDatasets[dsIndex],
        usefulLinks: [
          ...updatedDatasets[dsIndex].usefulLinks,
          { id: null, title: '', url: '', isLatest: false }
        ]
      };
      return {
        ...prev,
        datasets: updatedDatasets
      };
    });
  };

  const updateUsefulLink = (dsIndex, linkIndex, field, value) => {
    setFormState(prev => {
      const updatedDatasets = [...prev.datasets];
      const updatedLinks = [...updatedDatasets[dsIndex].usefulLinks];
      updatedLinks[linkIndex] = {
        ...updatedLinks[linkIndex],
        [field]: value
      };
      updatedDatasets[dsIndex] = {
        ...updatedDatasets[dsIndex],
        usefulLinks: updatedLinks
      };
      return {
        ...prev,
        datasets: updatedDatasets
      };
    });
    
    // Clear validation errors
    const errorKey = `dataset_${dsIndex}_link_${linkIndex}_${field}`;
    if (validationErrors[errorKey]) {
      setValidationErrors(prev => ({
        ...prev,
        [errorKey]: null
      }));
    }
  };

  const removeUsefulLink = (dsIndex, linkIndex) => {
    const dataset = formState.datasets[dsIndex];
    const link = dataset.usefulLinks[linkIndex];
    const displayName = link.title || `Link ${linkIndex + 1}`;
    
    // Force the confirmAction state to update
    setConfirmAction(null);  // First clear it
    
    // Then set it with a slight delay to ensure state update
    setTimeout(() => {
      setConfirmAction({
        message: `Are you sure you want to remove Useful Link "${displayName}"? This action cannot be undone.`,
        onConfirm: () => {
          setFormState(prev => {
            const updatedDatasets = [...prev.datasets];
            const updatedLinks = updatedDatasets[dsIndex].usefulLinks.filter(
              (_, idx) => idx !== linkIndex
            );
            updatedDatasets[dsIndex] = {
              ...updatedDatasets[dsIndex],
              usefulLinks: updatedLinks
            };
            return {
              ...prev,
              datasets: updatedDatasets
            };
          });
          setConfirmAction(null);
        },
        onCancel: () => setConfirmAction(null),
      });
    }, 10);
  };

  // Form validation
  const validateForm = () => {
    const errors = {};
    
    // Validate provider fields
    if (!formState.datacenter.trim()) {
      errors.datacenter = 'Datacenter is required';
    }
    if (!formState.shortName.trim()) {
      errors.shortName = 'Short Name is required';
    }
    if (!formState.name.trim()) {
      errors.name = 'Full Name is required';
    }
    
    // Validate datasets
    formState.datasets.forEach((dataset, dsIndex) => {
      if (!dataset.source.trim()) {
        errors[`dataset_${dsIndex}_source`] = 'Source is required';
      }
      if (!dataset.title.trim()) {
        errors[`dataset_${dsIndex}_title`] = 'Title is required';
      }
      
      // Validate XML archives
      dataset.xmlArchives.forEach((archive, archIndex) => {
        if (!archive.url.trim()) {
          errors[`dataset_${dsIndex}_xml_${archIndex}_url`] = 'URL is required';
        }
      });
      
      // Validate useful links
      dataset.usefulLinks.forEach((link, linkIndex) => {
        if (!link.title.trim()) {
          errors[`dataset_${dsIndex}_link_${linkIndex}_title`] = 'Title is required';
        }
        if (!link.url.trim()) {
          errors[`dataset_${dsIndex}_link_${linkIndex}_url`] = 'URL is required';
        }
      });
    });
    
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    
    if (!validateForm()) {
      setError('Please fix the validation errors before submitting.');
      setIsLoading(false);
      return;
    }
    
    try {
      // Clone the form state to avoid mutating the state directly
      const sanitizedFormData = {
        ...formState,
        // Filter out empty datasets
        datasets: formState.datasets.filter(ds => 
          ds.source.trim() !== '' && 
          ds.title.trim() !== ''
        ).map(ds => ({
          ...ds,
          // Filter out empty XML archives
          xmlArchives: ds.xmlArchives.filter(archive => 
            archive.url.trim() !== ''
          ),
          // Filter out empty useful links
          usefulLinks: ds.usefulLinks.filter(link => 
            link.title.trim() !== '' && 
            link.url.trim() !== ''
          )
        }))
      };
      
      // Remove any empty strings for optional URL fields
      if (sanitizedFormData.url && sanitizedFormData.url.trim() === '') {
        sanitizedFormData.url = null;
      }
      
      if (sanitizedFormData.biocaseUrl && sanitizedFormData.biocaseUrl.trim() === '') {
        sanitizedFormData.biocaseUrl = null;
      }
      
      let res;
      if (isEditing) {
        res = await apiRequest(`/providers/${provider.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(sanitizedFormData)
        }, onTokenExpired);
      } else {
        res = await apiRequest('/providers', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(sanitizedFormData)
        }, onTokenExpired);
      }
      
      if (!res.ok) {
        let errorMessage = 'Failed to save provider';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          // If we can't parse the error response, use the default message
        }
        setError(errorMessage);
        setIsLoading(false);
        return;
      }
      
      const updatedProvider = await res.json();
      setIsLoading(false);
      onClose(updatedProvider);
    } catch (err) {
      // Only set error if it's not a token expiration error
      // Token expiration is handled by the onTokenExpired callback
      if (!err.message || !err.message.includes('Session expired')) {
        setError('Error saving provider: ' + err.message);
      }
      setIsLoading(false);
    }
  };

  // Field error display helper
  const getFieldErrorMessage = (fieldName) => {
    return validationErrors[fieldName] ? (
      <div style={{
        fontSize: '0.75rem',
        color: 'var(--error)',
        marginTop: '0.25rem',
      }}>
        {validationErrors[fieldName]}
      </div>
    ) : null;
  };

  // Check if there's a confirmation action in progress
  const hasConfirmAction = confirmAction !== null;

  return (
    <div>
      {error && <Alert type="error">{error}</Alert>}
      
      <form onSubmit={handleSubmit}>
        <div style={{
          backgroundColor: 'var(--card-bg)',
          borderRadius: '0.5rem',
          padding: '1.5rem',
          marginBottom: '1.5rem',
          border: '1px solid var(--border)',
        }}>
          <h3 style={{ 
            fontSize: '1.125rem', 
            fontWeight: 600, 
            marginTop: 0, 
            marginBottom: '1.5rem',
            color: 'var(--text)',
          }}>
            Provider Details
          </h3>
          
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ 
              display: 'block', 
              fontSize: '0.875rem', 
              fontWeight: 500, 
              marginBottom: '0.5rem', 
              color: 'var(--text)',
            }}>
              Datacenter
            </label>
            <input
              type="text"
              value={formState.datacenter || ''}
              onChange={(e) => updateFormField('datacenter', e.target.value)}
              required
              placeholder="Enter datacenter name"
              style={{
                display: 'block',
                width: '100%',
                padding: '0.625rem 0.75rem',
                fontSize: '0.875rem',
                borderRadius: '0.5rem',
                border: `1px solid ${validationErrors.datacenter ? 'var(--error)' : 'var(--border)'}`,
                backgroundColor: 'var(--card-bg)',
                color: 'var(--text)',
                transition: 'border-color 0.2s',
              }}
            />
            {getFieldErrorMessage('datacenter')}
          </div>
          
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ 
              display: 'block', 
              fontSize: '0.875rem', 
              fontWeight: 500, 
              marginBottom: '0.5rem', 
              color: 'var(--text)',
            }}>
              Short Name
            </label>
            <input
              type="text"
              value={formState.shortName || ''}
              onChange={(e) => updateFormField('shortName', e.target.value)}
              required
              placeholder="Enter short name"
              style={{
                display: 'block',
                width: '100%',
                padding: '0.625rem 0.75rem',
                fontSize: '0.875rem',
                borderRadius: '0.5rem',
                border: `1px solid ${validationErrors.shortName ? 'var(--error)' : 'var(--border)'}`,
                backgroundColor: 'var(--card-bg)',
                color: 'var(--text)',
                transition: 'border-color 0.2s',
              }}
            />
            {getFieldErrorMessage('shortName')}
            <div style={{
              fontSize: '0.75rem',
              color: 'var(--text-light)',
              marginTop: '0.25rem',
            }}>
              A brief identifier for this provider
            </div>
          </div>
          
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ 
              display: 'block', 
              fontSize: '0.875rem', 
              fontWeight: 500, 
              marginBottom: '0.5rem', 
              color: 'var(--text)',
            }}>
              Full Name
            </label>
            <input
              type="text"
              value={formState.name || ''}
              onChange={(e) => updateFormField('name', e.target.value)}
              required
              placeholder="Enter full provider name"
              style={{
                display: 'block',
                width: '100%',
                padding: '0.625rem 0.75rem',
                fontSize: '0.875rem',
                borderRadius: '0.5rem',
                border: `1px solid ${validationErrors.name ? 'var(--error)' : 'var(--border)'}`,
                backgroundColor: 'var(--card-bg)',
                color: 'var(--text)',
                transition: 'border-color 0.2s',
              }}
            />
            {getFieldErrorMessage('name')}
          </div>
          
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ 
              display: 'block', 
              fontSize: '0.875rem', 
              fontWeight: 500, 
              marginBottom: '0.5rem', 
              color: 'var(--text)',
            }}>
              URL
            </label>
            <input
              type="url"
              value={formState.url || ''}
              onChange={(e) => updateFormField('url', e.target.value)}
              placeholder="https://example.com"
              style={{
                display: 'block',
                width: '100%',
                padding: '0.625rem 0.75rem',
                fontSize: '0.875rem',
                borderRadius: '0.5rem',
                border: `1px solid ${validationErrors.url ? 'var(--error)' : 'var(--border)'}`,
                backgroundColor: 'var(--card-bg)',
                color: 'var(--text)',
                transition: 'border-color 0.2s',
              }}
            />
            {getFieldErrorMessage('url')}
          </div>
          
          <div style={{ marginBottom: '1rem' }}>
            <label style={{ 
              display: 'block', 
              fontSize: '0.875rem', 
              fontWeight: 500, 
              marginBottom: '0.5rem', 
              color: 'var(--text)',
            }}>
              Biocase URL
            </label>
            <input
              type="url"
              value={formState.biocaseUrl || ''}
              onChange={(e) => updateFormField('biocaseUrl', e.target.value)}
              placeholder="https://biocase.example.com"
              style={{
                display: 'block',
                width: '100%',
                padding: '0.625rem 0.75rem',
                fontSize: '0.875rem',
                borderRadius: '0.5rem',
                border: `1px solid ${validationErrors.biocaseUrl ? 'var(--error)' : 'var(--border)'}`,
                backgroundColor: 'var(--card-bg)',
                color: 'var(--text)',
                transition: 'border-color 0.2s',
              }}
            />
            {getFieldErrorMessage('biocaseUrl')}
          </div>
        </div>
        
        <h3 style={{ 
          fontSize: '1.125rem', 
          fontWeight: 600, 
          marginTop: '1.5rem', 
          marginBottom: '1rem',
          color: 'var(--text)',
        }}>
          Datasets
        </h3>
        
        {formState.datasets.length === 0 ? (
          <div style={{
            textAlign: 'center',
            padding: '2rem',
            backgroundColor: 'var(--card-bg)',
            borderRadius: '0.5rem',
            fontSize: '0.875rem',
            color: 'var(--text-light)',
            textAlign: 'center',
            marginBottom: '1.5rem',
            border: '1px solid var(--border)',
          }}>
            <p style={{ marginBottom: '1rem' }}>No datasets added yet</p>
            <Button variant="secondary" onClick={addDataset}>
              Add First Dataset
            </Button>
          </div>
        ) : (
          formState.datasets.map((dataset, dsIndex) => (
            <div 
              key={dsIndex} 
              style={{
                backgroundColor: 'var(--card-bg)',
                borderRadius: '0.5rem',
                padding: '1.5rem',
                marginBottom: '1.5rem',
                border: '1px solid var(--border)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h4 style={{ 
                  fontSize: '1rem', 
                  fontWeight: 600, 
                  margin: 0,
                  color: 'var(--text)',
                }}>
                  Dataset {dsIndex + 1}{dataset.title ? `: ${dataset.title}` : ''}
                </h4>
                <button
                  onClick={(e) => {
                    e.preventDefault(); // Prevent form submission
                    e.stopPropagation(); // Prevent event bubbling
                    removeDataset(dsIndex);
                  }}
                  style={{
                    width: '36px',
                    height: '36px',
                    backgroundColor: 'var(--subtle-bg)',
                    color: 'var(--error)',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.2s',
                    padding: 0
                  }}
                  aria-label="Remove dataset"
                >
                  <Trash2 size={18} />
                </button>
              </div>
              
              <div style={{ 
                height: '1px', 
                backgroundColor: 'var(--border)', 
                margin: '1rem 0',
              }} />
              
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ 
                  display: 'block', 
                  fontSize: '0.875rem', 
                  fontWeight: 500, 
                  marginBottom: '0.5rem', 
                  color: 'var(--text)',
                }}>
                  Source
                </label>
                <input
                  type="text"
                  value={dataset.source || ''}
                  onChange={(e) => updateDataset(dsIndex, 'source', e.target.value)}
                  placeholder="Enter dataset source"
                  style={{
                    display: 'block',
                    width: '100%',
                    padding: '0.625rem 0.75rem',
                    fontSize: '0.875rem',
                    borderRadius: '0.5rem',
                    border: `1px solid ${validationErrors[`dataset_${dsIndex}_source`] ? 'var(--error)' : 'var(--border)'}`,
                    backgroundColor: 'var(--card-bg)',
                    color: 'var(--text)',
                    transition: 'border-color 0.2s',
                  }}
                />
                {getFieldErrorMessage(`dataset_${dsIndex}_source`)}
              </div>
              
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ 
                  display: 'block', 
                  fontSize: '0.875rem', 
                  fontWeight: 500, 
                  marginBottom: '0.5rem', 
                  color: 'var(--text)',
                }}>
                  Title
                </label>
                <input
                  type="text"
                  value={dataset.title || ''}
                  onChange={(e) => updateDataset(dsIndex, 'title', e.target.value)}
                  placeholder="Enter dataset title"
                  style={{
                    display: 'block',
                    width: '100%',
                    padding: '0.625rem 0.75rem',
                    fontSize: '0.875rem',
                    borderRadius: '0.5rem',
                    border: `1px solid ${validationErrors[`dataset_${dsIndex}_title`] ? 'var(--error)' : 'var(--border)'}`,
                    backgroundColor: 'var(--card-bg)',
                    color: 'var(--text)',
                    transition: 'border-color 0.2s',
                  }}
                />
                {getFieldErrorMessage(`dataset_${dsIndex}_title`)}
              </div>
              
              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ 
                  display: 'block', 
                  fontSize: '0.875rem', 
                  fontWeight: 500, 
                  marginBottom: '0.5rem', 
                  color: 'var(--text)',
                }}>
                  Landing Page URL
                </label>
                <input
                  type="url"
                  value={dataset.landingPageUrl || ''}
                  onChange={(e) => updateDataset(dsIndex, 'landingPageUrl', e.target.value)}
                  placeholder="https://example.com/dataset"
                  style={{
                    display: 'block',
                    width: '100%',
                    padding: '0.625rem 0.75rem',
                    fontSize: '0.875rem',
                    borderRadius: '0.5rem',
                    border: `1px solid ${validationErrors[`dataset_${dsIndex}_landingPageUrl`] ? 'var(--error)' : 'var(--border)'}`,
                    backgroundColor: 'var(--card-bg)',
                    color: 'var(--text)',
                    transition: 'border-color 0.2s',
                  }}
                />
                {getFieldErrorMessage(`dataset_${dsIndex}_landingPageUrl`)}
              </div>
              
              {/* XML Archives Section */}
              <div style={{ margin: '1rem 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <h5 style={{ 
                    fontSize: '0.875rem', 
                    fontWeight: 600, 
                    margin: 0,
                    color: 'var(--text)',
                  }}>
                    XML Archives
                  </h5>
                  <Button 
                    variant="primary" 
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      addXmlArchive(dsIndex);
                    }} 
                    style={{
                      padding: '0.375rem 0.75rem',
                      height: 'auto',
                      fontSize: '0.75rem',
                      backgroundColor: 'var(--card-bg)',
                      color: 'var(--primary)',
                      border: '1.5px solid var(--primary)',
                      fontWeight: 500,
                    }}
                  >
                    Add Archive
                  </Button>
                </div>
                
                {dataset.xmlArchives.length === 0 ? (
                  <div style={{ 
                    padding: '1rem', 
                    backgroundColor: 'var(--subtle-bg)', 
                    borderRadius: '0.5rem', 
                    fontSize: '0.875rem', 
                    color: 'var(--text-light)', 
                    textAlign: 'center',
                    marginBottom: '1rem',
                  }}>
                    No XML archives added
                  </div>
                ) : (
                  dataset.xmlArchives.map((archive, archIndex) => (
                    <div 
                      key={archIndex} 
                      style={{ 
                        padding: '1rem', 
                        backgroundColor: 'var(--subtle-bg)', 
                        borderRadius: '0.5rem', 
                        marginBottom: '0.75rem',
                      }}
                    >
                      <div style={{ marginBottom: '0.75rem' }}>
                        <label style={{ 
                          display: 'block', 
                          fontSize: '0.875rem', 
                          fontWeight: 500, 
                          marginBottom: '0.5rem', 
                          color: 'var(--text)',
                        }}>
                          URL
                        </label>
                        <input
                          type="url"
                          value={archive.url || ''}
                          onChange={(e) => updateXmlArchive(dsIndex, archIndex, 'url', e.target.value)}
                          placeholder="https://example.com/archive.xml"
                          style={{
                            display: 'block',
                            width: '100%',
                            padding: '0.625rem 0.75rem',
                            fontSize: '0.875rem',
                            borderRadius: '0.5rem',
                            border: `1px solid ${validationErrors[`dataset_${dsIndex}_xml_${archIndex}_url`] ? 'var(--error)' : 'var(--border)'}`,
                            backgroundColor: 'var(--card-bg)',
                            color: 'var(--text)',
                            transition: 'border-color 0.2s',
                          }}
                        />
                        {getFieldErrorMessage(`dataset_${dsIndex}_xml_${archIndex}_url`)}
                      </div>
                      
                      <div style={{ marginBottom: '0.75rem' }}>
                        <label style={{ 
                          display: 'flex', 
                          paddingLeft: '0.2rem',
                          alignItems: 'center',
                          fontSize: '0.875rem', 
                          fontWeight: 500, 
                          color: 'var(--text)',
                        }}>
                          <input
                            type="checkbox"
                            checked={archive.isLatest}
                            onChange={(e) => updateXmlArchive(dsIndex, archIndex, 'isLatest', e.target.checked)}
                            style={{
                              width: '1rem',
                              height: '1rem',
                              borderRadius: '0.25rem',
                              marginRight: '0.5rem',
                              accentColor: 'var(--primary)',
                            }}
                          />
                          Is Latest Version
                        </label>
                      </div>
                      
                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            removeXmlArchive(dsIndex, archIndex);
                          }}
                          style={{
                            width: '36px',
                            height: '36px',
                            backgroundColor: 'var(--card-bg)',
                            color: 'var(--error)',
                            border: 'none',
                            borderRadius: '0.375rem',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'all 0.2s',
                            padding: 0
                          }}
                          aria-label="Remove XML Archive"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
              
              {/* Useful Links Section */}
              <div style={{ margin: '1rem 0' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                  <h5 style={{ 
                    fontSize: '0.875rem', 
                    fontWeight: 600, 
                    margin: 0,
                    color: 'var(--text)',
                  }}>
                    Useful Links
                  </h5>
                  <Button 
                    variant="primary" 
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      addUsefulLink(dsIndex);
                    }} 
                    style={{
                      padding: '0.375rem 0.75rem',
                      height: 'auto',
                      fontSize: '0.75rem',
                      backgroundColor: 'var(--card-bg)',
                      color: 'var(--primary)',
                      border: '1.5px solid var(--primary)',
                      fontWeight: 500,
                    }}
                  >
                    Add Link
                  </Button>
                </div>
                
                {dataset.usefulLinks.length === 0 ? (
                  <div style={{ 
                    padding: '1rem', 
                    backgroundColor: 'var(--subtle-bg)', 
                    borderRadius: '0.5rem', 
                    fontSize: '0.875rem', 
                    color: 'var(--text-light)', 
                    textAlign: 'center',
                    marginBottom: '1rem',
                  }}>
                    No useful links added
                  </div>
                ) : (
                  dataset.usefulLinks.map((link, linkIndex) => (
                    <div 
                      key={linkIndex} 
                      style={{ 
                        padding: '1rem', 
                        backgroundColor: 'var(--subtle-bg)', 
                        borderRadius: '0.5rem', 
                        marginBottom: '0.75rem',
                      }}
                    >
                      <div style={{ marginBottom: '0.75rem' }}>
                        <label style={{ 
                          display: 'block', 
                          fontSize: '0.875rem', 
                          fontWeight: 500, 
                          marginBottom: '0.5rem', 
                          color: 'var(--text)',
                        }}>
                          Title
                        </label>
                        <input
                          type="text"
                          value={link.title || ''}
                          onChange={(e) => updateUsefulLink(dsIndex, linkIndex, 'title', e.target.value)}
                          placeholder="Enter link title"
                          style={{
                            display: 'block',
                            width: '100%',
                            padding: '0.625rem 0.75rem',
                            fontSize: '0.875rem',
                            borderRadius: '0.5rem',
                            border: `1px solid ${validationErrors[`dataset_${dsIndex}_link_${linkIndex}_title`] ? 'var(--error)' : 'var(--border)'}`,
                            backgroundColor: 'var(--card-bg)',
                            color: 'var(--text)',
                            transition: 'border-color 0.2s',
                          }}
                        />
                        {getFieldErrorMessage(`dataset_${dsIndex}_link_${linkIndex}_title`)}
                      </div>
                      
                      <div style={{ marginBottom: '0.75rem' }}>
                        <label style={{ 
                          display: 'block', 
                          fontSize: '0.875rem', 
                          fontWeight: 500, 
                          marginBottom: '0.5rem', 
                          color: 'var(--text)',
                        }}>
                          URL
                        </label>
                        <input
                          type="url"
                          value={link.url || ''}
                          onChange={(e) => updateUsefulLink(dsIndex, linkIndex, 'url', e.target.value)}
                          placeholder="https://example.com/resource"
                          style={{
                            display: 'block',
                            width: '100%',
                            padding: '0.625rem 0.75rem',
                            fontSize: '0.875rem',
                            borderRadius: '0.5rem',
                            border: `1px solid ${validationErrors[`dataset_${dsIndex}_link_${linkIndex}_url`] ? 'var(--error)' : 'var(--border)'}`,
                            backgroundColor: 'var(--card-bg)',
                            color: 'var(--text)',
                            transition: 'border-color 0.2s',
                          }}
                        />
                        {getFieldErrorMessage(`dataset_${dsIndex}_link_${linkIndex}_url`)}
                      </div>
                      
                      <div style={{ marginBottom: '0.75rem' }}>
                        <label style={{ 
                          display: 'flex', 
                          paddingLeft: '0.2rem',
                          alignItems: 'center',
                          fontSize: '0.875rem', 
                          fontWeight: 500, 
                          color: 'var(--text)',
                        }}>
                          <input
                            type="checkbox"
                            checked={link.isLatest}
                            onChange={(e) => updateUsefulLink(dsIndex, linkIndex, 'isLatest', e.target.checked)}
                            style={{
                              width: '1rem',
                              height: '1rem',
                              borderRadius: '0.25rem',
                              marginRight: '0.5rem',
                              accentColor: 'var(--primary)',
                            }}
                          />
                          Is Latest Version
                        </label>
                      </div>
                      
                      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem' }}>
                        <button
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            removeUsefulLink(dsIndex, linkIndex);
                          }}
                          style={{
                            width: '36px',
                            height: '36px',
                            backgroundColor: 'var(--card-bg)',
                            color: 'var(--error)',
                            border: 'none',
                            borderRadius: '0.375rem',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'all 0.2s',
                            padding: 0
                          }}
                          aria-label="Remove Useful Link"
                        >
                          <Trash2 size={18} />
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          ))
        )}
        
        <div style={{ marginTop: '1rem', marginBottom: '1.5rem' }}>
          <Button
            variant="secondary"
            onClick={(e) => {
              e.preventDefault();
              addDataset();
            }}
            style={{ 
              width: '99%',
              backgroundColor: 'var(--card-bg)',
              color: 'var(--primary)',
              border: '1.5px solid var(--primary)',
              textAlign: 'center',
              fontWeight: 500,
              justifyContent: 'center',
             }}
          >
            Add Dataset
          </Button>
        </div>
        
        <div style={{ 
          display: 'flex', 
          justifyContent: 'flex-end', 
          gap: '0.75rem',
          marginTop: '1.5rem', 
        }}>
          <Button
            variant="secondary"
            onClick={() => onClose(null)}
            type="button"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            isLoading={isLoading}
            disabled={isLoading}
          >
            {isEditing ? (isLoading ? 'Updating...' : 'Update Provider') : (isLoading ? 'Creating...' : 'Create Provider')}
          </Button>
        </div>
      </form>
      
      {/* The confirmation modal must be rendered at the top level */}
      {hasConfirmAction && (
        <ConfirmModal
          title="Confirm Removal"
          message={confirmAction.message}
          onConfirm={confirmAction.onConfirm}
          onCancel={confirmAction.onCancel}
        />
      )}
    </div>
  );
}

// UserManagement component
function UserManagement({ token, onTokenExpired }) {
  const [users, setUsers] = useState([]);
  const [editingUser, setEditingUser] = useState(null);
  const [addingUser, setAddingUser] = useState(false);
  const [formData, setFormData] = useState({ username: '', password: '', is_global_admin: false, provider_roles: {} });
  const [confirmDeleteUser, setConfirmDeleteUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedRole, setSelectedRole] = useState('admin');

  const fetchProviders = async () => {
    try {
      const res = await apiRequest('/providers', {}, onTokenExpired);
      
      if (!res.ok) {
        console.error('Failed to fetch providers:', res.status);
        return;
      }
      
      const data = await res.json();
      setProviders(data);
    } catch (err) {
      console.error('Error fetching providers:', err.message);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchProviders();
  }, [token]);

  const handleAddProviderRole = () => {
    if (selectedProvider && selectedRole) {
      setFormData(prev => ({
        ...prev,
        provider_roles: {
          ...prev.provider_roles,
          [selectedProvider]: selectedRole
        }
      }));
      setSelectedProvider('');
    }
  };

  const handleRemoveProviderRole = (providerId) => {
    setFormData(prev => {
      const newRoles = { ...prev.provider_roles };
      delete newRoles[providerId];
      return {
        ...prev,
        provider_roles: newRoles
      };
    });
  };

  const fetchUsers = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const res = await apiRequest('/users', {}, onTokenExpired);
      
      if (!res.ok) {
        setError('Failed to fetch users');
        setIsLoading(false);
        return;
      }
      
      const data = await res.json();
      setUsers(data);
      setIsLoading(false);
    } catch (err) {
      setError('Error fetching users: ' + err.message);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [token]);

  const handleSaveUser = async (formData) => {
    setIsLoading(true);
    setError('');
    
    try {
      let res;
      if (editingUser) {
        res = await apiRequest(`/users/${editingUser.username}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        }, onTokenExpired);
      } else {
        res = await apiRequest('/users', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        }, onTokenExpired);
      }
      
      if (!res.ok) {
        let errorMessage = 'Failed to save user';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          // If we can't parse the error response, use the default message
        }
        setError(errorMessage);
        setIsLoading(false);
        return;
      }
      
      setEditingUser(null);
      setAddingUser(false);
      fetchUsers();
      setIsLoading(false);
    } catch (err) {
      // Only set error if it's not a token expiration error
      // Token expiration is handled by the onTokenExpired callback
      if (!err.message || !err.message.includes('Session expired')) {
        setError('Error saving user: ' + err.message);
      }
      setIsLoading(false);
    }
  };

  const handleDeleteUser = async (username) => {
    setIsLoading(true);
    setError('');
    
    try {
      const res = await apiRequest(`/users/${username}`, {
        method: 'DELETE'
      }, onTokenExpired);
      
      if (!res.ok) {
        let errorMessage = 'Failed to delete user';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          // If we can't parse the error response, use the default message
        }
        setError(errorMessage);
        setIsLoading(false);
        return;
      }
      
      fetchUsers();
      setIsLoading(false);
    } catch (err) {
      setError('Error deleting user: ' + err.message);
      setIsLoading(false);
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    setFormData({ 
      username: user.username, 
      password: '', 
      is_global_admin: user.is_global_admin, 
      provider_roles: user.provider_roles || {} 
    });
    setAddingUser(true);
  };

  const handleDelete = (username) => {
    setConfirmDeleteUser({ username });
  };

  return (
    <div style={{ 
      flexGrow: 1,
      padding: '2rem 1rem',
      maxWidth: '1200px',
      margin: '0 auto',
      width: '100%',
    }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '1.5rem',
      }}>
        <h2 style={{ 
          fontSize: '1.5rem', 
          fontWeight: 600, 
          margin: 0,
          color: 'var(--text)',
        }}>
          User Management
        </h2>
        
        <Button onClick={() => { 
          setAddingUser(true); 
          setEditingUser(null); 
          setFormData({ username: '', password: '', is_global_admin: false, provider_roles: {} }); 
        }}>
          <span style={{ fontSize: '1.25rem' }}>+</span>
          <span>Add User</span>
        </Button>
      </div>
      
      {error && <Alert type="error">{error}</Alert>}
      
      {isLoading && !addingUser ? (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          padding: '4rem 0' 
        }}>
          <div style={{
            width: '32px',
            height: '32px',
            border: '3px solid var(--border)',
            borderRadius: '50%',
            borderTopColor: 'var(--primary)',
            animation: 'spin 1s linear infinite',
          }}></div>
        </div>
      ) : users.length === 0 && !addingUser ? (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          backgroundColor: 'var(--card-bg)',
          borderRadius: '0.75rem',
          color: 'var(--text-light)',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        }}>
          <h3 style={{ marginTop: 0, color: 'var(--text)' }}>No users found</h3>
          <p style={{ marginBottom: '1.5rem' }}>Get started by adding your first user</p>
          <Button onClick={() => { 
            setAddingUser(true); 
            setEditingUser(null); 
            setFormData({ username: '', password: '', is_global_admin: false, provider_roles: {} }); 
          }}>
            Add User
          </Button>
        </div>
      ) : (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', 
          gap: '1.5rem',
          marginBottom: '2rem',
        }}>
          {users.map((user) => (
            <div 
              key={user.username} 
              style={{
                backgroundColor: 'var(--card-bg)',
                borderRadius: '0.75rem',
                border: '1px solid var(--border)',
                overflow: 'hidden',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
                transition: 'all 0.3s',
                display: 'flex',
                flexDirection: 'column',
                height: '100%', // Make card fill its container height
              }}
            >
              <div style={{ 
                padding: '1.25rem', 
                flexGrow: 1, // Make body expand to fill available space
                display: 'flex',
                flexDirection: 'column',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2rem' }}>
                  <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--primary)',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: '0.75rem',
                    fontWeight: 600,
                    fontSize: '1rem',
                  }}>
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h3 style={{ 
                      margin: '0', 
                      fontSize: '1.125rem', 
                      fontWeight: 600,
                      color: 'var(--text)',
                    }}>
                      {user.username}
                    </h3>
                  </div>
                </div>
                
                {/* Flexible spacer to push roles to the center */}
                <div style={{ flexGrow: 1 }}></div>
                
                {/* Roles section with subtle heading */}
                <div style={{ marginBottom: '2rem' }}>
                  <div style={{ 
                    fontSize: '0.75rem', 
                    textTransform: 'uppercase', 
                    fontWeight: 500, 
                    color: 'var(--text-light)',
                    marginBottom: '0.5rem',
                    letterSpacing: '0.025em',
                  }}>
                    Roles
                  </div>
                  
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {/* Show Global Admin tag first if applicable */}
                    {user.is_global_admin && (
                      <div 
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '0.5rem',
                          backgroundColor: 'var(--subtle-bg)',
                          borderRadius: '0.375rem',
                          fontSize: '0.875rem',
                        }}
                      >
                        <div style={{ flex: 1 }}>
                          <strong>Global Admin</strong>
                        </div>
                      </div>
                    )}
                    
                    {Object.keys(user.provider_roles || {}).length === 0 && !user.is_global_admin ? (
                      <div style={{ 
                        color: 'var(--text-light)', 
                        fontSize: '0.875rem',
                        fontStyle: 'italic'
                      }}>
                        No roles assigned
                      </div>
                    ) : (
                      <>
                        {Object.entries(user.provider_roles).map(([providerId, role]) => {
                          const provider = providers.find(p => p.id.toString() === providerId);
                          return (
                            <div 
                              key={providerId}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                padding: '0.5rem',
                                backgroundColor: 'var(--subtle-bg)',
                                borderRadius: '0.375rem',
                                fontSize: '0.875rem',
                              }}
                            >
                              <div style={{ flex: 1 }}>
                                <strong>{provider ? provider.shortName : providerId}</strong>
                                <span style={{ marginLeft: '0.5rem', color: 'var(--text-light)' }}>
                                  {role}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </>
                    )}
                  </div>
                </div>
                
                {/* Flexible spacer to push roles to the center */}
                <div style={{ flexGrow: 1 }}></div>
              </div>
              
              {/* Footer with action buttons - fixed height, not affected by content */}
              <div style={{ 
                borderTop: '1px solid var(--border)',
                display: 'flex',
                justifyContent: 'flex-end',
                alignItems: 'center',
                padding: '0.75rem',
                gap: '0.5rem',
                height: '60px',
                flexShrink: 0, // Prevent footer from shrinking
                boxSizing: 'border-box'
              }}>
                <button 
                  onClick={() => handleEdit(user)}
                  style={{
                    width: '36px',
                    height: '36px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: '--var(subtle-bg)',
                    color: 'var(--text-light)',
                    border: '1px solid var(--border)',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                >
                  <Edit size={16} />
                </button>
                <button 
                  onClick={() => handleDelete(user.username)}
                  style={{
                    width: '36px',
                    height: '36px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: '--var(subtle-bg)',
                    color: 'var(--error)',
                    border: '1px solid var(--border)',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                  }}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {confirmDeleteUser && (
        <ConfirmModal
          title="Delete User"
          message={`Are you sure you want to delete "${confirmDeleteUser.username}"? This action cannot be undone.`}
          onConfirm={() => { handleDeleteUser(confirmDeleteUser.username); setConfirmDeleteUser(null); }}
          onCancel={() => setConfirmDeleteUser(null)}
        />
      )}
      
      <Modal
        isOpen={addingUser}
        onClose={() => { setAddingUser(false); setEditingUser(null); }}
        title={editingUser ? `Edit User: ${editingUser.username}` : 'Add User'}
      >
        <div>
          {error && <Alert type="error">{error}</Alert>}
          
          <form onSubmit={(e) => { e.preventDefault(); handleSaveUser(formData); }}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ 
                display: 'block', 
                fontSize: '0.875rem', 
                fontWeight: 500, 
                marginBottom: '0.5rem', 
                color: 'var(--text)',
              }}>
                Username
              </label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                required
                disabled={!!editingUser}
                placeholder="Enter username"
                autoComplete="username"
                style={{
                  display: 'block',
                  width: '100%',
                  padding: '0.625rem 0.75rem',
                  fontSize: '0.875rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--card-bg)',
                  color: 'var(--text)',
                  transition: 'border-color 0.2s',
                }}
              />
              {editingUser && (
                <div style={{
                  fontSize: '0.75rem',
                  color: 'var(--text-light)',
                  marginTop: '0.25rem',
                }}>
                  Username cannot be changed
                </div>
              )}
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ 
                display: 'block', 
                fontSize: '0.875rem', 
                fontWeight: 500, 
                marginBottom: '0.5rem', 
                color: 'var(--text)',
              }}>
                Password
              </label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required={!editingUser}
                placeholder={editingUser ? "Leave blank to keep current password" : "Enter password"}
                autoComplete="current-password"
                style={{
                  display: 'block',
                  width: '100%',
                  padding: '0.625rem 0.75rem',
                  fontSize: '0.875rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--card-bg)',
                  color: 'var(--text)',
                  transition: 'border-color 0.2s',
                }}
              />
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ 
                display: 'flex', 
                alignItems: 'center',
                fontSize: '0.875rem', 
                fontWeight: 500, 
                color: 'var(--text)',
              }}>
                <input
                  type="checkbox"
                  checked={formData.is_global_admin}
                  onChange={(e) => setFormData({ ...formData, is_global_admin: e.target.checked })}
                  style={{
                    width: '1rem',
                    height: '1rem',
                    borderRadius: '0.25rem',
                    marginRight: '0.5rem',
                    accentColor: 'var(--primary)',
                  }}
                />
                Global Admin
              </label>
              <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-light)',
                marginTop: '0.25rem',
                marginLeft: '1.5rem',
              }}>
                Global admins have full access to all providers and user management
              </div>
            </div>
            
            {!formData.is_global_admin && (
              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ 
                  display: 'block', 
                  fontSize: '0.875rem', 
                  fontWeight: 500, 
                  marginBottom: '0.5rem', 
                  color: 'var(--text)',
                }}>
                  Provider Roles
                </label>
                
                <div style={{ marginBottom: '1rem' }}>
                  {Object.entries(formData.provider_roles).map(([providerId, role]) => {
                    const provider = providers.find(p => p.id.toString() === providerId);
                    return (
                      <div 
                        key={providerId}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '0.5rem',
                          backgroundColor: 'var(--subtle-bg)',
                          borderRadius: '0.375rem',
                          marginBottom: '0.5rem',
                        }}
                      >
                        <div style={{ flex: 1 }}>
                          <strong>{provider ? provider.shortName : providerId}</strong>
                          <span style={{ marginLeft: '0.5rem', color: 'var(--text-light)' }}>
                            {role}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveProviderRole(providerId)}
                          style={{
                            padding: '0.25rem 0.5rem',
                            backgroundColor: 'transparent',
                            border: 'none',
                            color: 'var(--error)',
                            cursor: 'pointer',
                          }}
                        >
                          ×
                        </button>
                      </div>
                    );
                  })}
                </div>

                <div style={{ 
                  display: 'flex', 
                  gap: '0.5rem',
                  marginBottom: '0.5rem'
                }}>
                  <select
                    value={selectedProvider}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                    style={{
                      flex: '2',
                      padding: '0.625rem 0.75rem',
                      fontSize: '0.875rem',
                      borderRadius: '0.5rem',
                      border: '1px solid var(--border)',
                      backgroundColor: 'var(--card-bg)',
                      color: 'var(--text)',
                    }}
                  >
                    <option value="">Select Provider</option>
                    {providers.map(provider => (
                      <option key={provider.id} value={provider.id}>
                        {provider.shortName}
                      </option>
                    ))}
                  </select>
                  
                  <select
                    value={selectedRole}
                    onChange={(e) => setSelectedRole(e.target.value)}
                    style={{
                      flex: '1',
                      padding: '0.625rem 0.75rem',
                      fontSize: '0.875rem',
                      borderRadius: '0.5rem',
                      border: '1px solid var(--border)',
                      backgroundColor: 'var(--card-bg)',
                      color: 'var(--text)',
                    }}
                  >
                    <option value="admin">Admin</option>
                    <option value="curator">Curator</option>
                  </select>
                  
                  <button
                    type="button"
                    onClick={handleAddProviderRole}
                    disabled={!selectedProvider}
                    style={{
                      padding: '0.625rem 1rem',
                      backgroundColor: selectedProvider ? 'var(--primary)' : 'var(--border)',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.5rem',
                      cursor: selectedProvider ? 'pointer' : 'not-allowed',
                      fontSize: '0.875rem',
                    }}
                  >
                    Add
                  </button>
                </div>
              </div>
            )}
            
            <div style={{ 
              display: 'flex', 
              justifyContent: 'flex-end', 
              gap: '0.75rem'
            }}>
              <Button
                variant="secondary"
                type="button"
                onClick={() => { setEditingUser(null); setAddingUser(false); }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                isLoading={isLoading}
                disabled={isLoading}
              >
                {editingUser ? (isLoading ? 'Updating...' : 'Update User') : (isLoading ? 'Creating...' : 'Create User')}
              </Button>
            </div>
          </form>
        </div>
      </Modal>
    </div>
  );
}
