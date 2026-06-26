import React from 'react';
import Skeleton from './Skeleton';

/**
 * StatCard component for displaying key metrics
 * Pure minimalist design with centered content
 */
function StatCard({
  title,
  value,
  unit = '',
  color = 'var(--primary)',
  isLoading = false,
  isLiveData = false,
  style = {}
}) {
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
          position: 'relative',
          zIndex: 1,
          textAlign: 'center',
          marginBottom: '1.25rem'
        }}>
          {/* Number-shaped placeholder matching the resolved value block. */}
          <div style={{ marginBottom: '0.75rem', display: 'flex', justifyContent: 'center' }}>
            <Skeleton width="55%" height="2.5rem" radius="0.5rem" ariaLabel={`Loading ${title}`} />
          </div>
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
