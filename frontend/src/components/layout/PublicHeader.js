import React, { useState, useEffect, useRef } from 'react';
import { Sun, Moon, Menu, X } from 'lucide-react';
import { useIsMobileOrSmallTablet } from '../../hooks/useMediaQuery';

const PublicHeader = ({ activeView, setActiveView, isDarkTheme, toggleTheme }) => {
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
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isMobileMenuOpen]);

  // Navigation items
  const navItems = [
    { view: 'landing', label: 'Home' },
    { view: 'publicStats', label: 'Statistics' },
    { view: 'about', label: 'About' },
  ];

  // Common link style for desktop nav
  const getNavLinkStyle = (view) => ({
    padding: '0.75rem 0',
    minHeight: '44px',
    position: 'relative',
    color: activeView === view ? 'var(--primary)' : 'var(--text-light)',
    textDecoration: 'none',
    fontWeight: 500,
    transition: 'all 0.2s ease',
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
    background: 'none',
    border: 'none',
    font: 'inherit',
  });

  // Mobile nav link style
  const getMobileNavLinkStyle = (view) => ({
    padding: '0.75rem 1rem',
    minHeight: '48px',
    color: activeView === view ? 'var(--primary)' : 'var(--text)',
    textDecoration: 'none',
    fontWeight: 500,
    transition: 'all 0.2s ease',
    display: 'flex',
    alignItems: 'center',
    borderRadius: '0.5rem',
    backgroundColor: activeView === view ? 'var(--subtle-bg)' : 'transparent',
    cursor: 'pointer',
    background: activeView === view ? 'var(--subtle-bg)' : 'none',
    border: 'none',
    font: 'inherit',
    width: '100%',
  });

  const getUnderlineStyle = (view) => ({
    content: '""',
    position: 'absolute',
    bottom: 0,
    left: 0,
    width: '100%',
    height: '2px',
    backgroundColor: 'var(--primary)',
    transform: activeView === view ? 'scaleX(1)' : 'scaleX(0)',
    transformOrigin: 'left',
    transition: 'transform 0.2s ease',
  });

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
        <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '1rem' : '2rem' }}>
          <h1 style={{
            fontSize: isMobile ? '1rem' : '1.25rem',
            fontWeight: 700,
            margin: 0,
            color: 'var(--text)',
            letterSpacing: '-0.01em',
          }}>
            {isMobile ? 'DPM' : 'Data Provider Manager'}
          </h1>

          {/* Desktop Navigation */}
          {!isMobile && (
            <nav style={{
              display: 'flex',
              gap: '1.5rem'
            }}>
              {navItems.map((item) => (
                <button
                  key={item.view}
                  onClick={() => setActiveView(item.view)}
                  style={getNavLinkStyle(item.view)}
                >
                  {item.label}
                  <span style={getUnderlineStyle(item.view)}></span>
                </button>
              ))}
            </nav>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? '0.5rem' : '1rem' }}>
          {/* Sign In button - desktop only */}
          {!isMobile && (
            <button
              onClick={() => setActiveView('login')}
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
                display: 'flex',
                alignItems: 'center',
              }}
            >
              Sign In
            </button>
          )}

          {/* Theme toggle */}
          <button
            onClick={toggleTheme}
            style={{
              width: '44px',
              height: '44px',
              padding: '0',
              backgroundColor: 'var(--subtle-bg)',
              color: 'var(--text)',
              border: '1px solid var(--border)',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
            onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--hover-bg)'}
            onMouseLeave={e => e.currentTarget.style.backgroundColor = 'var(--subtle-bg)'}
            aria-label={`Switch to ${isDarkTheme ? 'light' : 'dark'} theme`}
          >
            {isDarkTheme ? <Sun size={20} /> : <Moon size={20} />}
          </button>

          {/* Hamburger menu - mobile only */}
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
            {/* Close button */}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '1rem',
              paddingBottom: '1rem',
              borderBottom: '1px solid var(--border)',
            }}>
              <span style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text)' }}>
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

            {/* Navigation links */}
            {navItems.map((item) => (
              <button
                key={item.view}
                onClick={() => {
                  setActiveView(item.view);
                  setIsMobileMenuOpen(false);
                }}
                style={getMobileNavLinkStyle(item.view)}
              >
                {item.label}
              </button>
            ))}

            {/* Divider */}
            <div style={{ height: '1px', backgroundColor: 'var(--border)', margin: '0.5rem 0' }} />

            {/* Sign In button */}
            <button
              onClick={() => {
                setActiveView('login');
                setIsMobileMenuOpen(false);
              }}
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
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              Sign In
            </button>
          </nav>
        </div>
      )}
    </>
  );
};

export default PublicHeader;
