import React from 'react';

const Header = ({ currentUser, activeView, setActiveView, logout, isDarkTheme, toggleTheme }) => {
  return (
    <header style={{
      backgroundColor: 'var(--card-bg)',
      borderBottom: '1px solid var(--border)',
      padding: '1rem 2rem',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      transition: 'all 0.3s ease',
      position: 'sticky',
      top: 0,
      zIndex: 100,
      backdropFilter: 'blur(10px)',
      WebkitBackdropFilter: 'blur(10px)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
        <h1 style={{ 
          fontSize: '1.25rem', 
          fontWeight: 700, 
          margin: 0,
          color: 'var(--text)',
          letterSpacing: '-0.01em',
        }}>
          Data Provider Manager
        </h1>
        
        <nav style={{ 
          display: 'flex',
          gap: '1.5rem'
        }}>
          <a 
            href="#" 
            onClick={(e) => { e.preventDefault(); setActiveView('dashboard'); }}
            style={{
              padding: '0.5rem 0',
              position: 'relative',
              color: activeView === 'dashboard' ? 'var(--primary)' : 'var(--text-light)',
              textDecoration: 'none',
              fontWeight: 500,
              transition: 'all 0.2s ease',
            }}
          >
            Dashboard
            <span style={{
              content: '""',
              position: 'absolute',
              bottom: 0,
              left: 0,
              width: '100%',
              height: '2px',
              backgroundColor: 'var(--primary)',
              transform: activeView === 'dashboard' ? 'scaleX(1)' : 'scaleX(0)',
              transformOrigin: 'left',
              transition: 'transform 0.2s ease',
            }}></span>
          </a>
          {currentUser?.is_global_admin && (
            <a 
              href="#" 
              onClick={(e) => { e.preventDefault(); setActiveView('userManagement'); }}
              style={{
                padding: '0.5rem 0',
                position: 'relative',
                color: activeView === 'userManagement' ? 'var(--primary)' : 'var(--text-light)',
                textDecoration: 'none',
                fontWeight: 500,
                transition: 'all 0.2s ease',
              }}
            >
              User Management
              <span style={{
                content: '""',
                position: 'absolute',
                bottom: 0,
                left: 0,
                width: '100%',
                height: '2px',
                backgroundColor: 'var(--primary)',
                transform: activeView === 'userManagement' ? 'scaleX(1)' : 'scaleX(0)',
                transformOrigin: 'left',
                transition: 'transform 0.2s ease',
              }}></span>
            </a>
          )}
        </nav>
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {currentUser && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            padding: '0.375rem 0.75rem',
            borderRadius: '0.375rem',
            border: '1px solid var(--border)',
            backgroundColor: 'var(--subtle-bg)',
            transition: 'all 0.2s ease',
          }}>
            <div style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              backgroundColor: 'var(--primary)',
              color: 'white',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginRight: '0.5rem',
              fontWeight: 600,
              fontSize: '0.75rem',
            }}>
              {currentUser.username ? currentUser.username.charAt(0).toUpperCase() : 'A'}
            </div>
            <span style={{ 
              color: 'var(--text)', 
              fontWeight: 500, 
              fontSize: '0.875rem',
              letterSpacing: '-0.01em',
            }}>
              {currentUser.is_global_admin ? 'Admin' : currentUser.username}
            </span>
          </div>
        )}
        
        <button
          onClick={logout}
          style={{
            padding: '0.5rem 0.75rem',
            backgroundColor: 'transparent',
            color: 'var(--text-light)',
            border: '1px solid var(--border)',
            borderRadius: '0.375rem',
            fontSize: '0.875rem',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
        >
          Logout
        </button>

        <button 
          onClick={toggleTheme}
          style={{
            width: '38px',
            height: '38px',
            padding: '0',
            backgroundColor: 'transparent',
            color: 'var(--text-light)',
            border: '1px solid var(--border)',
            borderRadius: '0.375rem',
            fontSize: '0.875rem',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          aria-label={`Switch to ${isDarkTheme ? 'light' : 'dark'} theme`}
        >
          {isDarkTheme ? '☀️' : '🌙'}
        </button>
      </div>
    </header>
  );
};

export default Header;
