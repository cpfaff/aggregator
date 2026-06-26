import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { authStatsApi, statsUtils } from '../../utils/statisticsApi';
import { formatRelativeTime } from '../../utils/dateUtils';
import TimeSeriesChart from '../ui/TimeSeriesChart';
import Skeleton from '../ui/Skeleton';
import Alert from '../ui/Alert';
import { Clock } from 'lucide-react';

/**
 * ProviderStatistics component for displaying provider trend data
 */
function ProviderStatistics({ providerId, providerName }) {
  const { handleTokenExpiration } = useAuth();
  const [stats, setStats] = useState(null);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [biologicalUnitsTimeSeriesData, setBiologicalUnitsTimeSeriesData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isTimeSeriesLoading, setIsTimeSeriesLoading] = useState(false);
  const [isBiologicalUnitsTimeSeriesLoading, setIsBiologicalUnitsTimeSeriesLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchProviderStats = async () => {
    try {
      setIsLoading(true);
      setError('');

      const data = await authStatsApi.getProviderStats(providerId, handleTokenExpiration);
      setStats(data);

      // Fetch time-series data for this provider's dataset count
      await fetchTimeSeries();

      // Fetch biological units time-series data
      await fetchBiologicalUnitsTimeSeries();

    } catch (err) {
      console.error('Error fetching provider trends:', err);
      setError('Failed to load provider trends: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchTimeSeries = async () => {
    try {
      setIsTimeSeriesLoading(true);

      const params = {
        period: 'monthly',
        months: 12
      };

      const data = await authStatsApi.getProviderDatasetsTimeline(providerId, params, handleTokenExpiration);
      const formattedData = statsUtils.toChartSeries(data);

      // Only update if data has actually changed to prevent chart re-renders
      setTimeSeriesData(prev => {
        const prevDataStr = JSON.stringify(prev);
        const newDataStr = JSON.stringify(formattedData);
        if (prevDataStr !== newDataStr) {
          return formattedData;
        }
        return prev;
      });

    } catch (err) {
      console.error('Error fetching provider time-series:', err);
      // Don't set error for time-series failure, just log it
    } finally {
      setIsTimeSeriesLoading(false);
    }
  };

  const fetchBiologicalUnitsTimeSeries = async () => {
    try {
      setIsBiologicalUnitsTimeSeriesLoading(true);

      const params = {
        period: 'daily',
        limit: 30
      };

      const data = await authStatsApi.getProviderBiologicalUnitsTimeline(providerId, params, handleTokenExpiration);
      const formattedData = statsUtils.toChartSeries(data);

      // Only update if data has actually changed to prevent chart re-renders
      setBiologicalUnitsTimeSeriesData(prev => {
        const prevDataStr = JSON.stringify(prev);
        const newDataStr = JSON.stringify(formattedData);
        if (prevDataStr !== newDataStr) {
          return formattedData;
        }
        return prev;
      });

    } catch (err) {
      console.error('Error fetching biological units time-series:', err);
      // Don't set error for time-series failure, just log it
    } finally {
      setIsBiologicalUnitsTimeSeriesLoading(false);
    }
  };

  useEffect(() => {
    if (providerId) {
      fetchProviderStats();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [providerId]);

  if (isLoading) {
    return (
      <div style={{ padding: '0 1.5rem 2rem', maxWidth: '1200px', margin: '0 auto' }}>
        {/* Header silhouette */}
        <div style={{
          marginBottom: '3rem',
          padding: '0.5rem 0 1.5rem',
          borderBottom: '1px solid var(--border-light)',
        }}>
          <Skeleton width="40%" height="1.625rem" style={{ marginBottom: '1rem' }} />
          <Skeleton width="30%" height="0.875rem" style={{ marginBottom: '1rem' }} />
          <Skeleton width="min(700px, 80%)" height="1rem" />
        </div>

        {/* Two timeline-chart silhouettes */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '3rem' }}>
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} style={{
              backgroundColor: 'var(--card-bg)',
              border: '1px solid var(--border)',
              borderRadius: '0.5rem',
              padding: '1.5rem',
            }}>
              <Skeleton width="45%" height="1.125rem" style={{ marginBottom: '0.4rem' }} />
              <Skeleton width="60%" height="0.8125rem" style={{ marginBottom: '1.25rem' }} />
              <Skeleton width="100%" height={300} radius="0.5rem" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: '1.5rem' }}>
        <Alert type="error">{error}</Alert>
      </div>
    );
  }

  if (!stats) {
    return (
      <div style={{ padding: '1.5rem' }}>
        <Alert type="info">No trend data available for this provider.</Alert>
      </div>
    );
  }


  return (
    <div style={{
      padding: '0 1.5rem 2rem',
      maxWidth: '1200px',
      margin: '0 auto',
      position: 'relative'
    }}>
      {/* Background decoration */}
      <div style={{
        position: 'absolute',
        top: '0',
        right: '2rem',
        width: '120px',
        height: '120px',
        background: 'radial-gradient(circle, var(--primary)08 0%, transparent 70%)',
        borderRadius: '50%',
        zIndex: -1
      }} />

      {/* Header */}
      <div style={{
        marginBottom: '3rem',
        textAlign: 'left',
        position: 'relative',
        padding: '0.5rem 0 1.5rem',
        borderBottom: '1px solid var(--border-light)'
      }}>
        {/* Provider name as primary heading */}
        <h2 style={{
          fontSize: 'clamp(1.25rem, 3vw, 1.625rem)',
          fontWeight: 700,
          color: 'var(--text)',
          marginBottom: '1rem',
          letterSpacing: '-0.5px',
          lineHeight: '1.3'
        }}>
          {providerName || 'Provider Trends'}
        </h2>

        {/* Meta information row */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1rem'
        }}>
          {/* Last Activity */}
          {stats.last_activity && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontSize: '0.875rem',
              color: 'var(--text-light)',
              fontWeight: 500
            }}>
              <Clock size={16} style={{ color: 'var(--primary)' }} />
              Last activity: {formatRelativeTime(stats.last_activity)}
            </div>
          )}
        </div>

        <p style={{
          color: 'var(--text-light)',
          margin: 0,
          fontSize: '1rem',
          lineHeight: '1.6',
          maxWidth: '700px'
        }}>
          Historical growth and activity trends for this provider
        </p>
      </div>

      {/* Timeline Charts Section */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr',
        gap: '3rem'
      }}>
        {/* Dataset Count Timeline */}
        <TimeSeriesChart
          data={timeSeriesData}
          title="Dataset Registration Timeline"
          subtitle="Growth in total datasets over time"
          color="var(--primary)"
          height={300}
          isLoading={isTimeSeriesLoading}
          error={timeSeriesData.length === 0 ? 'No historical data available' : null}
          integerOnly={true}
        />

        {/* Biological Units Timeline */}
        <TimeSeriesChart
          data={biologicalUnitsTimeSeriesData}
          title="Biological Units Over Time"
          subtitle="Total biological units across all datasets in this provider"
          color="var(--success)"
          height={300}
          isLoading={isBiologicalUnitsTimeSeriesLoading}
          error={biologicalUnitsTimeSeriesData.length === 0 ? 'No biological units data available' : null}
          integerOnly={true}
        />
      </div>
    </div>
  );
}

export default ProviderStatistics;
