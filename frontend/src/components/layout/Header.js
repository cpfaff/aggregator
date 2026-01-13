import React, { useState, useEffect, useRef } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Sun, Moon, Menu, X } from 'lucide-react';
import { useIsMobileOrSmallTablet } from '../../hooks/useMediaQuery';

const Header = ({ currentUser, activeView, navigate, logout, isDarkTheme, toggleTheme }) => {
  const isLoggedIn = !!currentUser;
  const location = useLocation();
  const isMobile = useIsMobileOrSmallTablet();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const mobileMenuRef = useRef(null);
  const hamburgerRef = useRef(null);

  // Close mobile menu when viewport becomes desktop
  useEffect(() => {
    if (!isMobile) {
      setIsMobileMenuOpen(false);
    }
  }, [isMobile]);

  // Close mobile menu when route changes
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  // Focus trapping and escape key handling for mobile menu
  useEffect(() => {
    if (!isMobileMenuOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setIsMobileMenuOpen(false);
        hamburgerRef.current?.focus();
        return;
      }

      if (e.key === 'Tab' && mobileMenuRef.current) {
        const focusableElements = mobileMenuRef.current.querySelectorAll(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (e.shiftKey && document.activeElement === firstElement) {
          e.preventDefault();
          lastElement?.focus();
        } else if (!e.shiftKey && document.activeElement === lastElement) {
          e.preventDefault();
          firstElement?.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    // Prevent body scroll when menu is open
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isMobileMenuOpen]);

  // Helper function to determine if a path is active
  const isActive = (path) => {
    if (path === '/providers' && location.pathname.startsWith('/provider/')) {
      return true;
    }
    if (path === '/statistics' && location.pathname === '/admin/statistics') {
      return false;
    }
    return location.pathname === path;
  };

  // Common link style for desktop nav
  const getNavLinkStyle = (path) => ({
    padding: '0.75rem 0',
    minHeight: '44px',
    position: 'relative',
    color: isActive(path) ? 'var(--primary)' : 'var(--text-light)',
    textDecoration: 'none',
    fontWeight: 500,
    transition: 'all 0.2s ease',
    display: 'flex',
    alignItems: 'center',
  });

  // Mobile nav link style
  const getMobileNavLinkStyle = (path) => ({
    padding: '0.75rem 1rem',
    minHeight: '48px',
    color: isActive(path) ? 'var(--primary)' : 'var(--text)',
    textDecoration: 'none',
    fontWeight: 500,
    transition: 'all 0.2s ease',
    display: 'flex',
    alignItems: 'center',
    borderRadius: '0.5rem',
    backgroundColor: isActive(path) ? 'var(--subtle-bg)' : 'transparent',
  });

  // Underline indicator for desktop nav
  const getUnderlineStyle = (path) => ({
    content: '""',
    position: 'absolute',
    bottom: 0,
    left: 0,
    width: '100%',
    height: '2px',
    backgroundColor: 'var(--primary)',
    transform: isActive(path) ? 'scaleX(1)' : 'scaleX(0)',
    transformOrigin: 'left',
    transition: 'transform 0.2s ease',
  });

  // Navigation items configuration
  const navItems = [
    { path: '/providers', label: 'Providers', show: isLoggedIn },
    {
      path: isLoggedIn ? '/admin/statistics' : '/statistics',
      label: 'Statistics',
      show: true,
      isActiveFn: () => isActive('/statistics') || isActive('/admin/statistics')
    },
    { path: '/users', label: 'Users', show: isLoggedIn && currentUser?.is_global_admin },
    { path: '/changelog', label: 'Changelog', show: true },
    { path: '/about', label: 'About', show: true },
  ].filter(item => item.show);

  return (
    <>
      <header style={{
        backgroundColor: 'var(--card-bg)',
        borderBottom: '1px solid var(--border)',
        padding: isMobile ? '0.75rem 1rem' : '1rem 2rem',
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
        <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '1rem' : '2rem', flex: 1 }}>
          <Link
            to={isLoggedIn ? '/providers' : '/'}
            style={{
              fontSize: isMobile ? '1rem' : '1.25rem',
              fontWeight: 700,
              margin: 0,
              color: 'var(--text)',
              letterSpacing: '-0.01em',
              textDecoration: 'none',
              flexShrink: 0,
            }}
          >
            {isMobile ? 'DPM' : 'Data Provider Manager'}
          </Link>

          {/* Desktop Navigation */}
          {!isMobile && (
            <nav style={{
              display: 'flex',
              gap: '1.5rem',
              minWidth: 0,
              flex: 1,
            }}>
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  style={getNavLinkStyle(item.path)}
                >
                  {item.label}
                  <span style={getUnderlineStyle(item.isActiveFn ? (item.isActiveFn() ? item.path : '') : item.path)}></span>
                </Link>
              ))}
            </nav>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '0.5rem' : '1rem', flexShrink: 0 }}>
          {/* Desktop auth controls */}
          {!isMobile && (
            <>
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
                      minHeight: '44px',
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
                    minHeight: '44px',
                    backgroundColor: 'var(--primary)',
                    color: 'white',
                    border: 'none',
                    borderRadius: '0.375rem',
                    fontSize: '0.875rem',
                    fontWeight: 500,
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    textDecoration: 'none',
                    display: 'inline-flex',
                    alignItems: 'center',
                  }}
                >
                  Sign In
                </Link>
              )}
            </>
          )}

          {/* Theme toggle - always visible */}
          <button
            onClick={toggleTheme}
            style={{
              width: '44px',
              height: '44px',
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
              flexShrink: 0,
            }}
            onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--hover-bg)'}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = 'var(--subtle-bg)'}
            aria-label="Toggle theme"
          >
            {isDarkTheme ? <Sun size={20} /> : <Moon size={20} />}
          </button>

          {/* Hamburger menu button - mobile only */}
          {isMobile && (
            <button
              ref={hamburgerRef}
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              style={{
                width: '44px',
                height: '44px',
                padding: '0',
                borderRadius: '0.375rem',
                border: '1px solid var(--border)',
                backgroundColor: isMobileMenuOpen ? 'var(--primary)' : 'var(--subtle-bg)',
                color: isMobileMenuOpen ? 'white' : 'var(--text)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
              aria-label={isMobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={isMobileMenuOpen}
              aria-controls="mobile-nav-menu"
            >
              {isMobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          )}
        </div>
      </header>

      {/* Mobile Navigation Overlay */}
      {isMobile && (
        <div
          className={`mobile-nav-overlay ${isMobileMenuOpen ? 'open' : ''}`}
          onClick={() => setIsMobileMenuOpen(false)}
          aria-hidden={!isMobileMenuOpen}
        >
          <nav
            ref={mobileMenuRef}
            id="mobile-nav-menu"
            className="mobile-nav-panel"
            onClick={(e) => e.stopPropagation()}
            role="navigation"
            aria-label="Mobile navigation"
            style={{
              padding: '1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem',
            }}
          >
            {/* Close button at top */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1rem',
              paddingBottom: '1rem',
              borderBottom: '1px solid var(--border)',
            }}>
              <span style={{
                fontWeight: 600,
                fontSize: '1rem',
                color: 'var(--text)',
              }}>
                Menu
              </span>
              <button
                onClick={() => setIsMobileMenuOpen(false)}
                style={{
                  width: '44px',
                  height: '44px',
                  padding: '0',
                  borderRadius: '0.375rem',
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--subtle-bg)',
                  color: 'var(--text)',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                aria-label="Close menu"
              >
                <X size={20} />
              </button>
            </div>

            {/* User info for logged in users */}
            {isLoggedIn && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                padding: '0.75rem 1rem',
                marginBottom: '0.5rem',
                borderRadius: '0.5rem',
                backgroundColor: 'var(--subtle-bg)',
              }}>
                <div style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--primary)',
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginRight: '0.75rem',
                  fontWeight: 600,
                  fontSize: '0.875rem',
                }}>
                  {currentUser?.username ? currentUser.username.charAt(0).toUpperCase() : 'A'}
                </div>
                <div>
                  <div style={{
                    fontWeight: 500,
                    fontSize: '0.875rem',
                    color: 'var(--text)',
                  }}>
                    {currentUser?.username}
                  </div>
                  {currentUser?.is_global_admin && (
                    <div style={{
                      fontSize: '0.75rem',
                      color: 'var(--text-light)',
                    }}>
                      Administrator
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Navigation links */}
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                style={getMobileNavLinkStyle(item.path)}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                {item.label}
              </Link>
            ))}

            {/* Divider */}
            <div style={{
              height: '1px',
              backgroundColor: 'var(--border)',
              margin: '0.5rem 0'
            }} />

            {/* Auth actions */}
            {isLoggedIn ? (
              <button
                onClick={() => {
                  setIsMobileMenuOpen(false);
                  logout();
                }}
                style={{
                  padding: '0.75rem 1rem',
                  minHeight: '48px',
                  backgroundColor: 'transparent',
                  color: 'var(--error)',
                  border: '1px solid var(--error)',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                Logout
              </button>
            ) : (
              <Link
                to="/login"
                style={{
                  padding: '0.75rem 1rem',
                  minHeight: '48px',
                  backgroundColor: 'var(--primary)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                  textDecoration: 'none',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                Sign In
              </Link>
            )}
          </nav>
        </div>
      )}
    </>
  );
};

export default Header;
