import React from 'react';
import { formatCompactNumber } from '../../utils/numberFormat';
import {
  BarChart as RechartsBarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

/**
 * BarChart component for displaying bar chart data
 */
function BarChart({
  data = [],
  dataKey = 'value',
  nameKey = 'name',
  color = 'var(--primary)',
  height = 300,
  showGrid = true,
  showTooltip = true,
  isLoading = false,
  error = null,
  title = '',
  subtitle = '',
  horizontal = false
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
            Data will appear here once available
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
          padding: '0.75rem',
          border: '1px solid var(--border)',
          borderRadius: '0.5rem',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          fontSize: '0.875rem'
        }}>
          <p style={{
            margin: 0,
            marginBottom: '0.25rem',
            color: 'var(--text-light)',
            fontWeight: 500
          }}>
            {label}
          </p>
          <p style={{
            margin: 0,
            color: payload[0].fill,
            fontWeight: 600
          }}>
            {`${payload[0].name || 'Value'}: ${payload[0].value.toLocaleString()}`}
          </p>
        </div>
      );
    }
    return null;
  };

  const ChartComponent = horizontal ? RechartsBarChart : RechartsBarChart;
  const layout = horizontal ? 'horizontal' : 'vertical';

  // Resolve CSS variables to actual colors
  const resolveColor = (colorValue) => {
    const colorMap = {
      'var(--primary)': '#3b82f6',
      'var(--success)': '#22c55e',
      'var(--warning)': '#f59e0b',
      'var(--error)': '#ef4444',
      'var(--text)': '#1f2937',
      'var(--text-light)': '#6b7280'
    };
    return colorMap[colorValue] || colorValue;
  };

  const resolvedColor = resolveColor(color);


  return (
    <div style={{
      backgroundColor: 'var(--card-bg)',
      borderRadius: '0.75rem',
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
        left: 0,
        width: '60%',
        height: '100%',
        background: `radial-gradient(ellipse at 0% 0%, ${color}05 0%, transparent 70%)`,
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
          <ChartComponent
            data={data}
            margin={{ top: 10, right: 30, left: 20, bottom: 10 }}
            layout={layout}
          >
            {showGrid && (
              <CartesianGrid
                strokeDasharray="2 4"
                stroke="var(--border)"
                opacity={0.3}
                horizontal={!horizontal}
                vertical={horizontal}
              />
            )}
            {horizontal ? (
              <>
                <XAxis
                  type="number"
                  stroke="var(--text-light)"
                  fontSize={11}
                  fontWeight={500}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: 'var(--text-light)' }}
                  tickFormatter={(value) => formatCompactNumber(value)}
                />
                <YAxis
                  type="category"
                  dataKey={nameKey}
                  stroke="var(--text-light)"
                  fontSize={11}
                  fontWeight={500}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: 'var(--text-light)' }}
                  width={120}
                />
              </>
            ) : (
              <>
                <XAxis
                  dataKey={nameKey}
                  stroke="var(--text-light)"
                  fontSize={11}
                  fontWeight={500}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: 'var(--text-light)' }}
                  interval={0}
                  angle={data.length > 5 ? -45 : 0}
                  textAnchor={data.length > 5 ? 'end' : 'middle'}
                  height={data.length > 5 ? 60 : 30}
                />
                <YAxis
                  stroke="var(--text-light)"
                  fontSize={11}
                  fontWeight={500}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fill: 'var(--text-light)' }}
                  domain={[0, 'dataMax + 1']}
                  tickFormatter={(value) => formatCompactNumber(value)}
                />
              </>
            )}
            {showTooltip && <Tooltip content={<CustomTooltip />} />}
            <Bar
              dataKey={dataKey}
              fill={resolvedColor}
              radius={horizontal ? [0, 6, 6, 0] : [6, 6, 0, 0]}
              opacity={1}
              stroke="rgba(0,0,0,0.2)"
              strokeWidth={1}
            />
          </ChartComponent>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default BarChart;
