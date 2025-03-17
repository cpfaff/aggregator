import React from 'react';
import { ChevronRight, Home } from 'lucide-react';

/**
 * Breadcrumbs - A navigation component showing the current location in the application
 * 
 * @param {Object} props - Component props
 * @param {Array} props.items - Array of breadcrumb items 
 *   Each item should have: { label: string, onClick: function, active: boolean (optional) }
 * @param {boolean} props.showHomeIcon - Whether to show a home icon on the first item (default: true)
 * @param {Object} props.style - Additional styles to apply to the container
 */
function Breadcrumbs({ items = [], showHomeIcon = true, style = {} }) {
  if (!items || items.length === 0) return null;
  
  return (
    <nav 
      aria-label="Breadcrumb"
      style={{
        display: 'flex',
        alignItems: 'center',
        fontSize: '1.125rem',
        fontWeight: 500,
        marginBottom: '1.75rem',
        color: 'var(--text)',
        padding: 0,
        ...style
      }}
    >
      <ol 
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: 0,
          margin: 0,
          listStyle: 'none',
        }}
      >
        {items.map((item, index) => {
          return (
            <li 
              key={`breadcrumb-${index}`}
              style={{
                display: 'flex',
                alignItems: 'center',
              }}
            >
              {index > 0 && (
                <ChevronRight 
                  size={16} 
                  style={{ 
                    color: 'var(--text)', 
                    opacity: 0.7,
                    margin: '0 0.5rem',
                  }} 
                />
              )}
              
              <a
                onClick={item.onClick}
                style={{
                  cursor: item.onClick ? 'pointer' : 'default',
                  display: 'flex',
                  alignItems: 'center',
                  color: 'var(--text)',
                  fontWeight: 500,
                  textDecoration: 'none',
                  padding: '0.25rem 0',
                  transition: 'opacity 0.2s',
                }}
              >
                {index === 0 && showHomeIcon && (
                  <Home size={16} style={{ marginRight: '0.375rem', color: 'var(--text)', strokeWidth: 2.5 }} />
                )}
                {item.label}
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export default Breadcrumbs;
