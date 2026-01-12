import React from 'react';

/**
 * StatCard component for displaying key metrics
 * Pure minimalist design with centered content
 */
function StatCard({ 
  title, 
  value, 
  previousValue, 
  unit = '', 
  color = 'var(--primary)',
  isLoading = false,
  isLiveData = false,
  style = {}
}) {
  // Calculate percentage change
  const calculateChange = () => {
    if (previousValue === null || previousValue === undefined || previousValue === 0) {
      return null;
    }
    return ((value - previousValue) / previousValue) * 100;
  };

  const change = calculateChange();

  return (
    <div style={{
      backgroundColor: 'var(--card-bg)',
      borderRadius: '0.75rem',
      padding: '2rem',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
      border: '1px solid var(--border)',
      position: 'relative',
      overflow: 'hidden',
      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      cursor: 'default',
      ...style
    }}
    onMouseEnter={(e) => {
      e.currentTarget.style.transform = 'translateY(-2px)';
      e.currentTarget.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)';
    }}
    onMouseLeave={(e) => {
      e.currentTarget.style.transform = 'translateY(0)';
      e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)';
    }}
    >
      {isLoading ? (
        <div style={{ 
          display: 'flex', 
          flexDirection: 'column',
          alignItems: 'center', 
          gap: '0.75rem',
          position: 'relative', 
          zIndex: 1,
          padding: '1rem 0',
          textAlign: 'center',
          marginBottom: '1.25rem'
        }}>
          <div style={{
            width: '40px',
            height: '40px',
            border: '3px solid var(--border)',
            borderRadius: '50%',
            borderTopColor: color,
            borderRightColor: 'transparent',
            animation: 'spin 1s linear infinite',
            boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)'
          }} />
          <span style={{ 
            color: 'var(--text-light)', 
            fontSize: '0.875rem',
            fontWeight: 500,
            letterSpacing: '0.25px'
          }}>
            Loading...
          </span>
        </div>
      ) : (
        <div style={{ position: 'relative', zIndex: 1, textAlign: 'center', marginBottom: '1.25rem' }}>
          <div style={{
            marginBottom: '0.75rem'
          }}>
            <div style={{
              fontSize: '2.5rem',
              fontWeight: 800,
              color: 'var(--text)',
              lineHeight: '1'
            }}>
              {typeof value === 'number' ? value.toLocaleString() : value}
              {unit && (
                <span style={{
                  fontSize: '1.125rem',
                  fontWeight: 600,
                  color: 'var(--text-light)',
                  marginLeft: '0.375rem',
                  background: 'var(--text-light)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}>
                  {unit}
                </span>
              )}
            </div>
          </div>

          {change !== null && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem',
              fontSize: '0.8rem',
              color: change >= 0 ? 'var(--success)' : 'var(--error)',
              backgroundColor: change >= 0 ? 'var(--success)10' : 'var(--error)10',
              padding: '0.375rem 0.75rem',
              borderRadius: '2rem',
              border: `1px solid ${change >= 0 ? 'var(--success)' : 'var(--error)'}20`,
              fontWeight: 600,
              margin: '0 auto',
              width: 'fit-content'
            }}>
              <span style={{
                fontSize: '0.875rem',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '16px',
                height: '16px',
                borderRadius: '50%',
                backgroundColor: change >= 0 ? 'var(--success)' : 'var(--error)',
                color: 'white'
              }}>
                {change >= 0 ? '↗' : '↘'}
              </span>
              <span>{Math.abs(change).toFixed(1)}%</span>
              <span style={{ color: 'var(--text-light)', fontSize: '0.75rem' }}>vs previous</span>
            </div>
          )}
        </div>
      )}

      <div style={{
        position: 'relative',
        zIndex: 1,
        textAlign: 'center'
      }}>
        <div style={{
          color: 'var(--text-light)',
          fontSize: '0.875rem',
          fontWeight: 600,
          lineHeight: '1.2',
          textTransform: 'uppercase',
          letterSpacing: '0.5px'
        }}>
          {title}
        </div>
      </div>
    </div>
  );
}

export default StatCard;