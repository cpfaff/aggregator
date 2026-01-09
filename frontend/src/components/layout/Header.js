import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Sun, Moon } from 'lucide-react';

const Header = ({ currentUser, activeView, navigate, logout, isDarkTheme, toggleTheme }) => {
  const isLoggedIn = !!currentUser;
  const location = useLocation();
  
  // Helper function to determine if a path is active
  const isActive = (path) => {
    if (path === '/providers' && location.pathname.startsWith('/provider/')) {
      return true;
    }
    if (path === '/statistics' && location.pathname === '/admin/statistics') {
      return false; // Don't highlight public stats when on admin stats
    }
    return location.pathname === path;
  };
  
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
        <Link 
          to={isLoggedIn ? '/providers' : '/'}
          style={{ 
            fontSize: '1.25rem', 
            fontWeight: 700, 
            margin: 0,
            color: 'var(--text)',
            letterSpacing: '-0.01em',
            textDecoration: 'none',
            flexShrink: 0,
          }}
        >
          Data Provider Manager
        </Link>
        
        <nav style={{ 
          display: 'flex',
          gap: '1.5rem',
          minWidth: 0,
          flex: 1,
        }}>
          {isLoggedIn && (
            <Link 
              to="/providers"
              style={{
                padding: '0.5rem 0',
                position: 'relative',
                color: isActive('/providers') ? 'var(--primary)' : 'var(--text-light)',
                textDecoration: 'none',
                fontWeight: 500,
                transition: 'all 0.2s ease',
              }}
            >
              Providers
              <span style={{
                content: '""',
                position: 'absolute',
                bottom: 0,
                left: 0,
                width: '100%',
                height: '2px',
                backgroundColor: 'var(--primary)',
                transform: isActive('/providers') ? 'scaleX(1)' : 'scaleX(0)',
                transformOrigin: 'left',
                transition: 'transform 0.2s ease',
              }}></span>
            </Link>
          )}
          
          <Link
            to={isLoggedIn ? '/admin/statistics' : '/statistics'}
            style={{
              padding: '0.5rem 0',
              position: 'relative',
              color: (isActive('/statistics') || isActive('/admin/statistics')) ? 'var(--primary)' : 'var(--text-light)',
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
              transform: (isActive('/statistics') || isActive('/admin/statistics')) ? 'scaleX(1)' : 'scaleX(0)',
              transformOrigin: 'left',
              transition: 'transform 0.2s ease',
            }}></span>
          </Link>
          
          {isLoggedIn && currentUser?.is_global_admin && (
            <Link 
              to="/users"
              style={{
                padding: '0.5rem 0',
                position: 'relative',
                color: isActive('/users') ? 'var(--primary)' : 'var(--text-light)',
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
                transform: isActive('/users') ? 'scaleX(1)' : 'scaleX(0)',
                transformOrigin: 'left',
                transition: 'transform 0.2s ease',
              }}></span>
            </Link>
          )}
          
          {isLoggedIn && (
            <Link 
              to="/changelog"
              style={{
                padding: '0.5rem 0',
                position: 'relative',
                color: isActive('/changelog') ? 'var(--primary)' : 'var(--text-light)',
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
                transform: isActive('/changelog') ? 'scaleX(1)' : 'scaleX(0)',
                transformOrigin: 'left',
                transition: 'transform 0.2s ease',
              }}></span>
            </Link>
          )}
          
          <Link 
            to="/about"
            style={{
              padding: '0.5rem 0',
              position: 'relative',
              color: isActive('/about') ? 'var(--primary)' : 'var(--text-light)',
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
              transform: isActive('/about') ? 'scaleX(1)' : 'scaleX(0)',
              transformOrigin: 'left',
              transition: 'transform 0.2s ease',
            }}></span>
          </Link>
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
                {currentUser?.username ? currentUser.username.charAt(0).toUpperCase() : 'A'}
              </div>
              <span style={{ 
                color: 'var(--text)', 
                fontWeight: 500, 
                fontSize: '0.875rem',
                letterSpacing: '-0.01em',
              }}>
                {currentUser?.is_global_admin ? 'Admin' : currentUser?.username}
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
          <Link
            to="/login"
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
              textDecoration: 'none',
              display: 'inline-block',
            }}
          >
            Sign In
          </Link>
        )}
        
        <button
          onClick={toggleTheme}
          style={{
            width: '38px',
            height: '38px',
            padding: '0',
            borderRadius: '0.375rem',
            border: '1px solid var(--border)',
            backgroundColor: 'var(--subtle-bg)',
            color: 'var(--text)',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
          onMouseEnter={e => e.target.style.backgroundColor = 'var(--hover-bg)'}
          onMouseLeave={e => e.target.style.backgroundColor = 'var(--subtle-bg)'}
          aria-label="Toggle theme"
        >
          {isDarkTheme ? <Sun size={18} /> : <Moon size={18} />}
        </button>
      </div>
    </header>
  );
};

export default Header;