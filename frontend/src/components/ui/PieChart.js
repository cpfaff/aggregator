import React, { useMemo } from 'react';
import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend
} from 'recharts';
import Skeleton from './Skeleton';

/**
 * PieChart component for displaying pie chart data
 */
function PieChart({
  data = [],
  dataKey = 'value',
  nameKey = 'name',
  colors = ['var(--primary)', 'var(--success)', 'var(--warning)', 'var(--error)'],
  height = 300,
  showTooltip = true,
  showLegend = true,
  isLoading = false,
  error = null,
  title = '',
  subtitle = '',
  innerRadius = 0,
  outerRadius = 80
}) {
  // Always call hooks at the top level to avoid conditional hook calls
  // Add total to each data point for percentage calculation
  // Use useMemo to prevent unnecessary recalculations during refreshes
  const enhancedData = useMemo(() => {
    if (!data || data.length === 0) return [];
    const total = data.reduce((sum, item) => sum + item[dataKey], 0);
    return data.map(item => ({
      ...item,
      total
    }));
  }, [data, dataKey]);
  if (isLoading) {
    return (
      <div style={{
        height,
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.5rem',
        border: '1px solid var(--border)',
        padding: '1.5rem',
      }}>
        {title && <Skeleton width="45%" height="1.125rem" style={{ marginBottom: '0.4rem' }} />}
        {subtitle && <Skeleton width="60%" height="0.8125rem" style={{ marginBottom: '1.25rem' }} />}
        {/* Pie plate placeholder — a centred circle echoes the chart shape. */}
        <div style={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Skeleton variant="circle" width={140} />
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

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      const percentage = ((data.value / data.payload.total) * 100).toFixed(1);
      const isOther = data.name && data.name.includes('Other');
      const details = data.payload.details;

      return (
        <div style={{
          backgroundColor: 'var(--card-bg)',
          padding: '0.75rem',
          border: '1px solid var(--border)',
          borderRadius: '0.5rem',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
          fontSize: '0.875rem',
          maxWidth: isOther && details ? '250px' : 'auto'
        }}>
          <p style={{
            margin: 0,
            marginBottom: '0.25rem',
            color: 'var(--text-light)',
            fontWeight: 500
          }}>
            {data.name}
          </p>
          <p style={{
            margin: 0,
            color: data.fill,
            fontWeight: 600,
            marginBottom: isOther && details ? '0.5rem' : 0
          }}>
            {`${data.value.toLocaleString()} datasets (${percentage}%)`}
          </p>
          {isOther && details && (
            <div style={{
              borderTop: '1px solid var(--border)',
              paddingTop: '0.5rem',
              fontSize: '0.75rem',
              color: 'var(--text-light)'
            }}>
              <p style={{ margin: 0, marginBottom: '0.25rem', fontWeight: 500 }}>
                Includes:
              </p>
              {details.slice(0, 5).map((dc, idx) => (
                <p key={idx} style={{ margin: 0, marginLeft: '0.5rem' }}>
                  • {dc.name}: {dc.value}
                </p>
              ))}
              {details.length > 5 && (
                <p style={{ margin: 0, marginLeft: '0.5rem', fontStyle: 'italic' }}>
                  • and {details.length - 5} more...
                </p>
              )}
            </div>
          )}
        </div>
      );
    }
    return null;
  };

  const CustomLegend = ({ payload }) => {
    // Determine if we need compact mode based on number of items
    const needsCompactMode = payload.length > 6;

    return (
      <div style={{
        display: 'grid',
        gridTemplateColumns: needsCompactMode ? 'repeat(2, 1fr)' : 'repeat(auto-fit, minmax(140px, 1fr))',
        gap: needsCompactMode ? '0.5rem' : '0.75rem',
        marginTop: '1.5rem',
        maxWidth: '100%'
      }}>
        {payload.map((entry, index) => {
          // Truncate long names for display
          const displayName = entry.value.length > 25
            ? entry.value.substring(0, 22) + '...'
            : entry.value;

          return (
            <div
              key={index}
              title={entry.value} // Show full name on hover
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                fontSize: needsCompactMode ? '0.75rem' : '0.875rem',
                padding: needsCompactMode ? '0.25rem 0.5rem' : '0.5rem 0.75rem',
                borderRadius: '0.25rem',
                backgroundColor: needsCompactMode ? 'transparent' : `${entry.color}10`,
                border: needsCompactMode ? 'none' : `1px solid ${entry.color}20`,
                transition: 'all 0.2s ease',
                cursor: 'default',
                minWidth: 0, // Allow content to shrink
                overflow: 'hidden'
              }}
            >
              <div style={{
                width: needsCompactMode ? '10px' : '12px',
                height: needsCompactMode ? '10px' : '12px',
                backgroundColor: entry.color,
                borderRadius: '50%',
                flexShrink: 0,
                boxShadow: needsCompactMode ? 'none' : `0 0 0 2px ${entry.color}20`
              }} />
              <span style={{
                color: 'var(--text)',
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
        width: '50%',
        height: '100%',
        background: `radial-gradient(circle at 100% 50%, ${colors[0]}03 0%, transparent 70%)`,
        pointerEvents: 'none'
      }} />

      {(title || subtitle) && (
        <div style={{
          marginBottom: '1.5rem',
          textAlign: 'center',
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
          <RechartsPieChart>
            <Pie
              data={enhancedData}
              cx="50%"
              cy="50%"
              innerRadius={innerRadius}
              outerRadius={outerRadius}
              paddingAngle={3}
              dataKey={dataKey}
              nameKey={nameKey}
              stroke="rgba(255, 255, 255, 0.2)"
              strokeWidth={2}
              isAnimationActive={false}
              animationDuration={0}
            >
              {enhancedData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={colors[index % colors.length]}
                />
              ))}
            </Pie>
            {showTooltip && <Tooltip content={<CustomTooltip />} />}
            {showLegend && <Legend content={<CustomLegend />} />}
          </RechartsPieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Memoize component to prevent unnecessary re-renders during refresh cycles
export default React.memo(PieChart, (prevProps, nextProps) => {
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
        item[prevProps.nameKey] === nextItem[nextProps.nameKey]
      );
    });
  };

  // Array comparison for colors
  const arraysEqual = (a, b) => {
    if (a === b) return true;
    if (!a || !b) return a === b;
    return a.length === b.length && a.every((val, i) => val === b[i]);
  };

  return (
    shallowDataEqual(prevProps.data, nextProps.data) &&
    prevProps.dataKey === nextProps.dataKey &&
    prevProps.nameKey === nextProps.nameKey &&
    prevProps.height === nextProps.height &&
    prevProps.isLoading === nextProps.isLoading &&
    prevProps.error === nextProps.error &&
    prevProps.title === nextProps.title &&
    prevProps.subtitle === nextProps.subtitle &&
    prevProps.innerRadius === nextProps.innerRadius &&
    prevProps.outerRadius === nextProps.outerRadius &&
    prevProps.showTooltip === nextProps.showTooltip &&
    prevProps.showLegend === nextProps.showLegend &&
    arraysEqual(prevProps.colors, nextProps.colors)
  );
});
