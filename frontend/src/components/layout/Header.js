import React from 'react';
import { Sun, Moon } from 'lucide-react';

const Header = ({ currentUser, activeView, setActiveView, logout, isDarkTheme, toggleTheme }) => {
  const isLoggedIn = !!currentUser;
  
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
      <div style={{ display: 'flex', alignItems: 'center', gap: '2rem', flex: 1 }}>
        <h1 style={{ 
          fontSize: '1.25rem', 
          fontWeight: 700, 
          margin: 0,
          color: 'var(--text)',
          letterSpacing: '-0.01em',
          cursor: 'pointer',
          flexShrink: 0,
        }}
        onClick={() => setActiveView(isLoggedIn ? 'dashboard' : 'landing')}
        >
          Data Provider Manager
        </h1>
        
        <nav style={{ 
          display: 'flex',
          gap: '1.5rem',
          minWidth: 0,
          flex: 1,
        }}>
          {isLoggedIn && (
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
          )}
          
          <a 
            href="#" 
            onClick={(e) => { 
              e.preventDefault(); 
              setActiveView(isLoggedIn && currentUser?.is_global_admin ? 'adminStats' : 'publicStats'); 
            }}
            style={{
              padding: '0.5rem 0',
              position: 'relative',
              color: (activeView === 'adminStats' || activeView === 'publicStats') ? 'var(--primary)' : 'var(--text-light)',
              textDecoration: 'none',
              fontWeight: 500,
              transition: 'all 0.2s ease',
            }}
          >
            Statistics
            <span style={{
              content: '""',
              position: 'absolute',
              bottom: 0,
              left: 0,
              width: '100%',
              height: '2px',
              backgroundColor: 'var(--primary)',
              transform: (activeView === 'adminStats' || activeView === 'publicStats') ? 'scaleX(1)' : 'scaleX(0)',
              transformOrigin: 'left',
              transition: 'transform 0.2s ease',
            }}></span>
          </a>
          
          {isLoggedIn && currentUser?.is_global_admin && (
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
              Users
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
          
          {isLoggedIn && (
            <a 
              href="#" 
              onClick={(e) => { e.preventDefault(); setActiveView('changelog'); }}
              style={{
                padding: '0.5rem 0',
                position: 'relative',
                color: activeView === 'changelog' ? 'var(--primary)' : 'var(--text-light)',
                textDecoration: 'none',
                fontWeight: 500,
                transition: 'all 0.2s ease',
              }}
            >
              Changelog
              <span style={{
                content: '""',
                position: 'absolute',
                bottom: 0,
                left: 0,
                width: '100%',
                height: '2px',
                backgroundColor: 'var(--primary)',
                transform: activeView === 'changelog' ? 'scaleX(1)' : 'scaleX(0)',
                transformOrigin: 'left',
                transition: 'transform 0.2s ease',
              }}></span>
            </a>
          )}
          
          <a 
            href="#" 
            onClick={(e) => { e.preventDefault(); setActiveView('about'); }}
            style={{
              padding: '0.5rem 0',
              position: 'relative',
              color: activeView === 'about' ? 'var(--primary)' : 'var(--text-light)',
              textDecoration: 'none',
              fontWeight: 500,
              transition: 'all 0.2s ease',
            }}
          >
            About
            <span style={{
              content: '""',
              position: 'absolute',
              bottom: 0,
              left: 0,
              width: '100%',
              height: '2px',
              backgroundColor: 'var(--primary)',
              transform: activeView === 'about' ? 'scaleX(1)' : 'scaleX(0)',
              transformOrigin: 'left',
              transition: 'transform 0.2s ease',
            }}></span>
          </a>
        </nav>
      </div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexShrink: 0 }}>
        {isLoggedIn ? (
          <>
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
          </>
        ) : (
          <button
            onClick={() => setActiveView('login')}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: 'var(--primary)',
              color: 'white',
              border: 'none',
              borderRadius: '0.375rem',
              fontSize: '0.875rem',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={(e) => {
              e.target.style.opacity = '0.9';
            }}
            onMouseLeave={(e) => {
              e.target.style.opacity = '1';
            }}
          >
            Sign In
          </button>
        )}

        <button 
          onClick={toggleTheme}
          style={{
            width: '38px',
            height: '38px',
            padding: '0',
            backgroundColor: 'transparent',
            color: 'var(--text)',
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
          onMouseEnter={(e) => {
            e.target.style.backgroundColor = 'var(--subtle-bg)';
            e.target.style.borderColor = 'var(--primary)';
          }}
          onMouseLeave={(e) => {
            e.target.style.backgroundColor = 'transparent';
            e.target.style.borderColor = 'var(--border)';
          }}
          aria-label={`Switch to ${isDarkTheme ? 'light' : 'dark'} theme`}
        >
          {isDarkTheme ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </header>
  );
};

export default Header;
