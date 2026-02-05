import React, { useMemo } from 'react';
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
 * Calculate a "nice" upper bound for the y-axis that prevents
 * small changes from appearing dramatic
 * @param {number} maxValue - The maximum value in the data
 * @returns {number} A "nice" round number for the upper bound
 */
function getNiceUpperBound(maxValue) {
  // For very small values, ensure minimum range
  if (maxValue <= 5) return 10;
  if (maxValue <= 10) return 15;
  if (maxValue <= 15) return 20;
  if (maxValue <= 20) return 25;
  if (maxValue <= 25) return 30;
  if (maxValue <= 30) return 40;
  if (maxValue <= 40) return 50;
  if (maxValue <= 50) return 60;
  if (maxValue <= 60) return 75;
  if (maxValue <= 75) return 100;

  // For larger values, round up to nearest nice number
  const magnitude = Math.pow(10, Math.floor(Math.log10(maxValue)));
  const normalized = maxValue / magnitude;

  let niceFactor;
  if (normalized <= 1.5) niceFactor = 1.5;
  else if (normalized <= 2) niceFactor = 2;
  else if (normalized <= 2.5) niceFactor = 2.5;
  else if (normalized <= 3) niceFactor = 3;
  else if (normalized <= 4) niceFactor = 4;
  else if (normalized <= 5) niceFactor = 5;
  else if (normalized <= 6) niceFactor = 6;
  else if (normalized <= 7.5) niceFactor = 7.5;
  else niceFactor = 10;

  return niceFactor * magnitude;
}

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
  subtitle = '',
  integerOnly = false
}) {
  // Always call hooks at the top level to avoid conditional hook calls
  // Memoize axis domain calculations to prevent flickering during refreshes
  const yDomain = useMemo(() => {
    if (!data || data.length === 0) {
      return null;
    }

    // Calculate stable Y domain with padding
    const yValues = data.map(item => item[dataKey]).filter(val => typeof val === 'number');
    const minY = Math.min(...yValues);
    const maxY = Math.max(...yValues);

    // For integer-only charts (like dataset counts), use nice bounds
    // to prevent small changes from appearing dramatic
    if (integerOnly) {
      const range = maxY - minY;
      const niceUpper = getNiceUpperBound(maxY);

      // For high baseline values (min > 50), start from a nice round number below min
      // This avoids wasting chart space when all values are high
      if (minY > 50) {
        // Find a nice lower bound that's below minY but not too far
        let niceLower = Math.floor(minY / 10) * 10 - 10; // Round down to nearest 10, then subtract 10
        if (niceLower < 0) niceLower = 0;

        // Ensure we have enough range to show variations
        const minRange = 20;
        if (niceUpper - niceLower < minRange) {
          niceUpper = niceLower + minRange;
        }

        return [niceLower, niceUpper];
      }

      // For smaller values or bigger ranges, start from 0 for clarity
      return [0, niceUpper];
    }

    // For continuous data, use padding approach
    const padding = (maxY - minY) * 0.1; // 10% padding
    return [Math.max(0, minY - padding), maxY + padding];
  }, [data, dataKey, integerOnly]);

  // Memoize processed data to ensure stable object references
  const memoizedData = useMemo(() => data, [data]);
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
          <div style={{
            margin: 0,
            color: payload[0].color,
            fontWeight: 700,
            fontSize: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <span style={{
              display: 'inline-block',
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              backgroundColor: payload[0].color,
              boxShadow: `0 0 0 2px ${payload[0].color}20`
            }} />
            {payload[0].value.toLocaleString()}
          </div>
        </div>
      );
    }
    return null;
  };

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
              domain={yDomain}
              allowDecimals={!integerOnly}
              tickFormatter={(value) => {
                // For integer-only mode, skip non-integer values
                if (integerOnly && !Number.isInteger(value)) {
                  return '';
                }
                if (value >= 1000000) {
                  return `${(value / 1000000).toFixed(integerOnly ? 0 : 1)}M`;
                } else if (value >= 1000) {
                  return `${(value / 1000).toFixed(integerOnly ? 0 : 1)}K`;
                }
                return integerOnly ? value.toString() : value;
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

// Memoize component to prevent unnecessary re-renders during refresh cycles
export default React.memo(TimeSeriesChart, (prevProps, nextProps) => {
  // Deep comparison for data arrays - only re-render if actual content changes
  const shallowDataEqual = (prev, next) => {
    if (prev === next) return true;
    if (!prev || !next) return prev === next;
    if (prev.length !== next.length) return false;

    return prev.every((item, index) => {
      const nextItem = next[index];
      if (!nextItem) return false;

      // Compare key properties that affect chart rendering
      return (
        item[prevProps.dataKey] === nextItem[nextProps.dataKey] &&
        item[prevProps.xKey] === nextItem[nextProps.xKey]
      );
    });
  };

  return (
    shallowDataEqual(prevProps.data, nextProps.data) &&
    prevProps.dataKey === nextProps.dataKey &&
    prevProps.xKey === nextProps.xKey &&
    prevProps.color === nextProps.color &&
    prevProps.height === nextProps.height &&
    prevProps.showGrid === nextProps.showGrid &&
    prevProps.showTooltip === nextProps.showTooltip &&
    prevProps.isLoading === nextProps.isLoading &&
    prevProps.error === nextProps.error &&
    prevProps.title === nextProps.title &&
    prevProps.subtitle === nextProps.subtitle &&
    prevProps.integerOnly === nextProps.integerOnly
  );
});
