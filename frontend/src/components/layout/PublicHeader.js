import React from 'react';
import { Sun, Moon } from 'lucide-react';

const PublicHeader = ({ activeView, setActiveView, isDarkTheme, toggleTheme }) => {
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
            onClick={(e) => { e.preventDefault(); setActiveView('landing'); }}
            style={{
              padding: '0.5rem 0',
              position: 'relative',
              color: activeView === 'landing' ? 'var(--primary)' : 'var(--text-light)',
              textDecoration: 'none',
              fontWeight: 500,
              transition: 'all 0.2s ease',
            }}
          >
            Home
            <span style={{
              content: '""',
              position: 'absolute',
              bottom: 0,
              left: 0,
              width: '100%',
              height: '2px',
              backgroundColor: 'var(--primary)',
              transform: activeView === 'landing' ? 'scaleX(1)' : 'scaleX(0)',
              transformOrigin: 'left',
              transition: 'transform 0.2s ease',
            }}></span>
          </a>
          
          <a 
            href="#" 
            onClick={(e) => { e.preventDefault(); setActiveView('publicStats'); }}
            style={{
              padding: '0.5rem 0',
              position: 'relative',
              color: activeView === 'publicStats' ? 'var(--primary)' : 'var(--text-light)',
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
              transform: activeView === 'publicStats' ? 'scaleX(1)' : 'scaleX(0)',
              transformOrigin: 'left',
              transition: 'transform 0.2s ease',
            }}></span>
          </a>
          
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
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
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

export default PublicHeader;