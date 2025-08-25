import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';

/**
 * MultiLineTimeSeriesChart component for displaying multi-provider time-series data
 * Supports multiple data series/lines with dynamic color assignment and enhanced tooltips
 */
function MultiLineTimeSeriesChart({ 
  data = [], 
  providers = [],
  xKey = 'date',
  colors = [
    'var(--primary)',
    'var(--success)', 
    'var(--warning)',
    'var(--error)',
    '#8B5CF6',
    '#F59E0B',
    '#EF4444',
    '#10B981',
    '#3B82F6',
    '#6366F1'
  ],
  height = 350,
  showGrid = true,
  showTooltip = true,
  showLegend = true,
  isLoading = false,
  error = null,
  title = '',
  subtitle = '',
  scaleType = 'linear',
  onScaleTypeChange = null
}) {
  // Memoize Y domain calculations
  const yDomain = useMemo(() => {
    if (!data || data.length === 0 || !providers || providers.length === 0) {
      return null;
    }
    
    // Calculate Y domain across all provider values
    const allValues = [];
    data.forEach(item => {
      providers.forEach(provider => {
        const value = item[provider.key];
        if (typeof value === 'number' && value > 0) {
          allValues.push(value);
        }
      });
    });
    
    if (allValues.length === 0) return null;
    
    const minY = Math.min(...allValues);
    const maxY = Math.max(...allValues);
    
    if (scaleType === 'log') {
      // For log scale, use actual min and max without padding
      // Ensure minimum is at least 1 for log scale
      return [Math.max(1, minY * 0.9), maxY * 1.1];
    } else {
      // Linear scale with padding
      const padding = (maxY - minY) * 0.1; // 10% padding
      return [Math.max(0, minY - padding), maxY + padding];
    }
  }, [data, providers, scaleType]);
  
  // Memoize processed data
  const memoizedData = useMemo(() => data, [data]);
  const memoizedProviders = useMemo(() => providers, [providers]);

  if (isLoading) {
    return (
      <div style={{
        height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.5rem',
        border: '1px solid var(--border)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: '32px',
            height: '32px',
            border: '3px solid var(--border)',
            borderRadius: '50%',
            borderTopColor: colors[0],
            animation: 'spin 1s linear infinite',
            margin: '0 auto 0.5rem'
          }} />
          <div style={{ color: 'var(--text-light)', fontSize: '0.875rem' }}>
            Loading chart...
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{
        height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.5rem',
        border: '1px solid var(--border)',
        color: 'var(--error)',
        textAlign: 'center',
        padding: '1rem'
      }}>
        <div>
          <div style={{ fontSize: '1.125rem', marginBottom: '0.5rem' }}>
            Failed to load chart
          </div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-light)' }}>
            {error}
          </div>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div style={{
        height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.5rem',
        border: '1px solid var(--border)',
        color: 'var(--text-light)',
        textAlign: 'center'
      }}>
        <div>
          <div style={{ fontSize: '1.125rem', marginBottom: '0.5rem' }}>
            No data available
          </div>
          <div style={{ fontSize: '0.875rem' }}>
            Data will appear here once statistics are collected
          </div>
        </div>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div style={{
          backgroundColor: 'var(--card-bg)',
          padding: '1rem 1.25rem',
          border: '1px solid var(--border)',
          borderRadius: '0.75rem',
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)',
          fontSize: '0.875rem',
          backdropFilter: 'blur(8px)',
          background: `linear-gradient(135deg, var(--card-bg) 0%, rgba(255, 255, 255, 0.1) 100%)`,
          position: 'relative',
          overflow: 'hidden',
          minWidth: '200px'
        }}>
          {/* Subtle gradient accent */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '3px',
            background: `linear-gradient(90deg, ${payload[0].color} 0%, transparent 100%)`,
            borderTopLeftRadius: '0.75rem',
            borderTopRightRadius: '0.75rem'
          }} />
          
          <p style={{ 
            margin: 0, 
            marginBottom: '0.75rem',
            color: 'var(--text-light)',
            fontWeight: 600,
            fontSize: '0.8rem',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}>
            {label}
          </p>
          
          {/* Show all providers' values */}
          {payload.map((entry, index) => (
            <div key={index} style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: index < payload.length - 1 ? '0.5rem' : 0,
              gap: '1rem'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem'
              }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: entry.color,
                  boxShadow: `0 0 0 2px ${entry.color}20`
                }} />
                <span style={{ 
                  color: 'var(--text)',
                  fontWeight: 500,
                  fontSize: '0.85rem'
                }}>
                  {entry.dataKey}
                </span>
              </div>
              <span style={{ 
                color: entry.color,
                fontWeight: 700,
                fontSize: '0.9rem'
              }}>
                {entry.value.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  const CustomLegend = ({ payload }) => {
    if (!payload || payload.length === 0) return null;
    
    // Determine if we need compact mode based on number of providers
    const needsCompactMode = payload.length > 6;
    
    return (
      <div style={{
        display: 'grid',
        gridTemplateColumns: needsCompactMode ? 'repeat(2, 1fr)' : 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: needsCompactMode ? '0.5rem' : '0.75rem',
        marginTop: '1rem',
        padding: needsCompactMode ? '0.5rem' : '0.75rem',
        backgroundColor: needsCompactMode ? 'transparent' : 'rgba(255, 255, 255, 0.02)',
        borderRadius: '0.5rem',
        border: needsCompactMode ? 'none' : '1px solid var(--border)',
        fontSize: needsCompactMode ? '0.75rem' : '0.875rem'
      }}>
        {payload.map((entry, index) => {
          // Truncate long provider names
          const displayName = entry.value.length > 40 
            ? entry.value.substring(0, 37) + '...' 
            : entry.value;
          
          return (
            <div 
              key={index} 
              title={entry.value} // Show full name on hover
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: needsCompactMode ? '0.375rem' : '0.5rem',
                padding: needsCompactMode ? '0.125rem 0.5rem' : '0.25rem 0.75rem',
                borderRadius: needsCompactMode ? '0.25rem' : '1rem',
                backgroundColor: needsCompactMode ? 'transparent' : 'rgba(255, 255, 255, 0.03)',
                overflow: 'hidden'
              }}
            >
              <div style={{
                width: needsCompactMode ? '8px' : '10px',
                height: needsCompactMode ? '8px' : '10px',
                borderRadius: '50%',
                backgroundColor: entry.color,
                flexShrink: 0,
                boxShadow: needsCompactMode ? 'none' : `0 0 0 2px ${entry.color}20`
              }} />
              <span style={{
                color: 'var(--text)',
                fontSize: 'inherit',
                fontWeight: needsCompactMode ? 400 : 500,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap'
              }}>
                {displayName}
              </span>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div style={{
      backgroundColor: 'var(--card-bg)',
      borderRadius: '1rem',
      padding: '2rem',
      border: '1px solid var(--border)',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
      background: `linear-gradient(135deg, var(--card-bg) 0%, rgba(255, 255, 255, 0.02) 100%)`,
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Subtle background decoration */}
      <div style={{
        position: 'absolute',
        top: 0,
        right: 0,
        width: '60%',
        height: '100%',
        background: `radial-gradient(ellipse at 100% 0%, ${colors[0]}05 0%, transparent 70%)`,
        pointerEvents: 'none'
      }} />
      
      {(title || subtitle) && (
        <div style={{ 
          marginBottom: '1.5rem', 
          position: 'relative', 
          zIndex: 1 
        }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start'
          }}>
            <div style={{ flex: 1 }}>
              {title && (
                <h3 style={{
                  margin: 0,
                  marginBottom: subtitle ? '0.5rem' : 0,
                  fontSize: '1.25rem',
                  fontWeight: 700,
                  color: 'var(--text)',
                  letterSpacing: '-0.5px'
                }}>
                  {title}
                </h3>
              )}
              {subtitle && (
                <p style={{
                  margin: 0,
                  fontSize: '0.9rem',
                  color: 'var(--text-light)',
                  lineHeight: '1.5'
                }}>
                  {subtitle}
                </p>
              )}
            </div>
            {onScaleTypeChange && (
              <div style={{
                display: 'flex',
                gap: '0.5rem',
                marginLeft: '1rem'
              }}>
                <button
                  onClick={() => onScaleTypeChange('linear')}
                  style={{
                    padding: '0.375rem 0.75rem',
                    fontSize: '0.8rem',
                    fontWeight: 500,
                    border: '1px solid var(--border)',
                    borderRadius: '0.375rem',
                    backgroundColor: scaleType === 'linear' ? 'var(--primary)' : 'var(--card-bg)',
                    color: scaleType === 'linear' ? 'white' : 'var(--text)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    outline: 'none'
                  }}
                  title="Linear scale shows absolute values"
                >
                  Linear
                </button>
                <button
                  onClick={() => onScaleTypeChange('log')}
                  style={{
                    padding: '0.375rem 0.75rem',
                    fontSize: '0.8rem',
                    fontWeight: 500,
                    border: '1px solid var(--border)',
                    borderRadius: '0.375rem',
                    backgroundColor: scaleType === 'log' ? 'var(--primary)' : 'var(--card-bg)',
                    color: scaleType === 'log' ? 'white' : 'var(--text)',
                    cursor: 'pointer',
                    transition: 'all 0.2s ease',
                    outline: 'none'
                  }}
                  title="Logarithmic scale helps visualize data with large differences"
                >
                  Log
                </button>
              </div>
            )}
          </div>
        </div>
      )}
      
      <div style={{ position: 'relative', zIndex: 1 }}>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart 
            data={memoizedData} 
            margin={{ top: 10, right: 30, left: 20, bottom: 10 }}
          >
            {showGrid && (
              <CartesianGrid 
                strokeDasharray="2 4" 
                stroke="var(--border)"
                opacity={0.3}
                vertical={false}
              />
            )}
            <XAxis 
              dataKey={xKey}
              stroke="var(--text-light)"
              fontSize={11}
              fontWeight={500}
              tickLine={false}
              axisLine={false}
              tick={{ fill: 'var(--text-light)' }}
            />
            <YAxis 
              stroke="var(--text-light)"
              fontSize={11}
              fontWeight={500}
              tickLine={false}
              axisLine={false}
              tick={{ fill: 'var(--text-light)' }}
              scale={scaleType}
              domain={yDomain}
              allowDataOverflow={scaleType === 'log'}
              tickFormatter={(value) => {
                // For very small values, show them as is
                if (value < 1) {
                  return value.toFixed(2);
                }
                // Format large numbers with K/M suffixes
                if (value >= 1000000) {
                  return `${(value / 1000000).toFixed(1)}M`;
                } else if (value >= 1000) {
                  return `${(value / 1000).toFixed(1)}K`;
                }
                return Math.round(value).toString();
              }}
            />
            {showTooltip && <Tooltip content={<CustomTooltip />} />}
            {showLegend && <Legend content={<CustomLegend />} />}
            
            {/* Render a Line component for each provider */}
            {memoizedProviders.map((provider, index) => (
              <Line 
                key={provider.key}
                type="monotone" 
                dataKey={provider.key} 
                stroke={colors[index % colors.length]}
                strokeWidth={2.5}
                dot={{ 
                  fill: 'var(--card-bg)', 
                  stroke: colors[index % colors.length], 
                  strokeWidth: 2, 
                  r: 4,
                  filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))'
                }}
                activeDot={{ 
                  r: 6, 
                  stroke: colors[index % colors.length], 
                  strokeWidth: 2.5,
                  fill: 'var(--card-bg)',
                  filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.15))'
                }}
                strokeLinecap="round"
                strokeLinejoin="round"
                isAnimationActive={false}
                animationDuration={0}
                name={provider.name}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Memoize component to prevent unnecessary re-renders
export default React.memo(MultiLineTimeSeriesChart, (prevProps, nextProps) => {
  // Deep comparison for data arrays and providers
  const shallowDataEqual = (prev, next) => {
    if (prev === next) return true;
    if (!prev || !next) return prev === next;
    if (prev.length !== next.length) return false;
    
    return prev.every((item, index) => {
      const nextItem = next[index];
      if (!nextItem) return false;
      
      // Compare date and all provider values
      if (item[prevProps.xKey] !== nextItem[nextProps.xKey]) return false;
      
      return prevProps.providers?.every(provider => 
        item[provider.key] === nextItem[provider.key]
      ) ?? true;
    });
  };
  
  const providersEqual = (prev, next) => {
    if (prev === next) return true;
    if (!prev || !next) return prev === next;
    if (prev.length !== next.length) return false;
    
    return prev.every((provider, index) => {
      const nextProvider = next[index];
      return provider?.key === nextProvider?.key && 
             provider?.name === nextProvider?.name;
    });
  };
  
  return (
    shallowDataEqual(prevProps.data, nextProps.data) &&
    providersEqual(prevProps.providers, nextProps.providers) &&
    prevProps.xKey === nextProps.xKey &&
    JSON.stringify(prevProps.colors) === JSON.stringify(nextProps.colors) &&
    prevProps.height === nextProps.height &&
    prevProps.showGrid === nextProps.showGrid &&
    prevProps.showTooltip === nextProps.showTooltip &&
    prevProps.showLegend === nextProps.showLegend &&
    prevProps.isLoading === nextProps.isLoading &&
    prevProps.error === nextProps.error &&
    prevProps.title === nextProps.title &&
    prevProps.subtitle === nextProps.subtitle &&
    prevProps.scaleType === nextProps.scaleType &&
    prevProps.onScaleTypeChange === nextProps.onScaleTypeChange
  );
});