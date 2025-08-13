import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

/**
 * TimeSeriesChart component for displaying time-series data
 */
function TimeSeriesChart({ 
  data = [], 
  dataKey = 'value',
  xKey = 'date',
  color = 'var(--primary)',
  height = 300,
  showGrid = true,
  showTooltip = true,
  isLoading = false,
  error = null,
  title = '',
  subtitle = ''
}) {
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
            borderTopColor: color,
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
          overflow: 'hidden'
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
            marginBottom: '0.5rem',
            color: 'var(--text-light)',
            fontWeight: 600,
            fontSize: '0.8rem',
            textTransform: 'uppercase',
            letterSpacing: '0.5px'
          }}>
            {label}
          </p>
          <p style={{ 
            margin: 0, 
            color: payload[0].color,
            fontWeight: 700,
            fontSize: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <div style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: payload[0].color,
              boxShadow: `0 0 0 2px ${payload[0].color}20`
            }} />
            {payload[0].value.toLocaleString()}
          </p>
        </div>
      );
    }
    return null;
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
        background: `radial-gradient(ellipse at 100% 0%, ${color}05 0%, transparent 70%)`,
        pointerEvents: 'none'
      }} />
      
      {(title || subtitle) && (
        <div style={{ 
          marginBottom: '1.5rem', 
          position: 'relative', 
          zIndex: 1 
        }}>
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
      )}
      
      <div style={{ position: 'relative', zIndex: 1 }}>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart 
            data={data} 
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
              tickFormatter={(value) => {
                if (value >= 1000000) {
                  return `${(value / 1000000).toFixed(1)}M`;
                } else if (value >= 1000) {
                  return `${(value / 1000).toFixed(1)}K`;
                }
                return value;
              }}
            />
            {showTooltip && <Tooltip content={<CustomTooltip />} />}
            <Line 
              type="monotone" 
              dataKey={dataKey} 
              stroke={color}
              strokeWidth={3}
              dot={{ 
                fill: 'var(--card-bg)', 
                stroke: color, 
                strokeWidth: 3, 
                r: 5,
                filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.1))'
              }}
              activeDot={{ 
                r: 7, 
                stroke: color, 
                strokeWidth: 3,
                fill: 'var(--card-bg)',
                filter: 'drop-shadow(0 4px 8px rgba(0,0,0,0.15))'
              }}
              strokeLinecap="round"
              strokeLinejoin="round"
              isAnimationActive={false}
              animationDuration={0}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default TimeSeriesChart;