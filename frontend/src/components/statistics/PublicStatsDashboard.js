import React, { useState, useEffect, useRef, useCallback } from 'react';
import { publicStatsApi, statisticsErrorMessage } from '../../utils/statisticsApi';
import { formatChartDate } from '../../utils/dateUtils';
import StatCard from '../ui/StatCard';
import Skeleton from '../ui/Skeleton';
import TimeSeriesChart from '../ui/TimeSeriesChart';
import PieChart from '../ui/PieChart';
import Alert from '../ui/Alert';
import {
  Database,
  Users,
  Server
} from 'lucide-react';
import { useResponsiveGrid } from '../../hooks/useMediaQuery';

/**
 * PublicStatsDashboard component for external users to view registry statistics
 * Features real-time auto-refresh every 60 seconds with manual controls
 */
function PublicStatsDashboard() {
  const { isMobile, isTablet, getGridColumns } = useResponsiveGrid();
  const [overviewStats, setOverviewStats] = useState(null);
  const [providerStats, setProviderStats] = useState([]);
  const [timelineData, setTimelineData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [, setIsRefreshing] = useState(false);
  const [, setLastUpdated] = useState(null);
  const [autoRefreshEnabled] = useState(true);
  const [, setNextRefreshIn] = useState(60);

  const intervalRef = useRef(null);
  const countdownRef = useRef(null);
  const REFRESH_INTERVAL = 60000; // 60 seconds for public dashboard

  // Auto-refresh backoff (FR-16, REQ-FE-POLL-3): after BACKOFF_THRESHOLD
  // consecutive failures the effective cadence widens — the 60s interval keeps
  // firing but the callback skips all but every BACKOFF_FACTOR-th tick, until a
  // success resets the cadence to 60s.
  const BACKOFF_THRESHOLD = 3;
  const BACKOFF_FACTOR = 4;
  const failuresRef = useRef(0);
  const backoffTicksRef = useRef(0);
  // Overlap guard + abort (FR-17, REQ-FE-POLL-4): skip a tick while a batch is in
  // flight, and abort the in-flight batch on unmount.
  const isFetchingRef = useRef(false);
  const abortControllerRef = useRef(null);

  const fetchAllStats = useCallback(async (isAutoRefresh = false) => {
    // Overlap guard: skip this tick if a batch is still in flight.
    if (isFetchingRef.current) {
      return;
    }
    isFetchingRef.current = true;
    // Capture THIS batch's signal up front, so the catch/finally test the
    // controller that owns this batch — not a newer one a remount installed into
    // the ref (which would mis-attribute this batch's abort as a real failure).
    const signal = abortControllerRef.current?.signal;
    try {
      if (!isAutoRefresh) {
        setIsLoading(true);
      } else {
        setIsRefreshing(true);
      }
      setError('');

      const [overview, providers, timeline] = await Promise.all([
        publicStatsApi.getOverview({ signal }),
        publicStatsApi.getProviders({ signal }),
        publicStatsApi.getTimeline({ period: 'monthly', months: 12 }, { signal })
      ]);

      // Aborted mid-flight (unmount): do not touch state.
      if (signal?.aborted) {
        return;
      }

      setOverviewStats(overview);

      // Transform provider stats data for compatibility with charts
      // Only update if data has actually changed to prevent chart re-renders
      const transformedProviders = {
        ...providers,
        // Transform and sort datacenter data for PieChart component (largest to smallest)
        datacenters: (() => {
          const sorted = (providers.datacenters || [])
            .map(dc => ({
              name: dc.datacenter,
              value: dc.dataset_count,
              provider_count: dc.provider_count
            }))
            .sort((a, b) => b.value - a.value); // Sort by dataset count, descending

          // If more than 7 data centers, group the smallest ones into "Other"
          if (sorted.length > 7) {
            const topProviders = sorted.slice(0, 6); // Take top 6
            const otherProviders = sorted.slice(6); // All the rest

            const otherTotal = otherProviders.reduce((sum, dc) => sum + dc.value, 0);
            const otherCount = otherProviders.length;

            return [
              ...topProviders,
              {
                name: `Other (${otherCount} centers)`,
                value: otherTotal,
                provider_count: otherProviders.reduce((sum, dc) => sum + (dc.provider_count || 0), 0),
                details: otherProviders // Keep details for tooltip if needed
              }
            ];
          }

          return sorted;
        })()
      };

      // Only update providerStats if the data has actually changed
      setProviderStats(prev => {
        const prevDatacentersStr = JSON.stringify(prev?.datacenters || []);
        const newDatacentersStr = JSON.stringify(transformedProviders.datacenters);
        if (prevDatacentersStr !== newDatacentersStr) {
          return transformedProviders;
        }
        return prev;
      });

      // Format timeline data for the chart
      const formattedTimeline = (timeline.datasets_timeline || []).map(point => ({
        date: formatChartDate(point.date),
        value: point.value,
        fullDate: point.date,
        ...point.extra_data
      }));

      // Only update timelineData if the data has actually changed
      setTimelineData(prev => {
        const prevTimelineStr = JSON.stringify(prev);
        const newTimelineStr = JSON.stringify(formattedTimeline);
        if (prevTimelineStr !== newTimelineStr) {
          return formattedTimeline;
        }
        return prev;
      });

      // Update last refreshed timestamp
      setLastUpdated(new Date());

      // Success: reset the failure backoff to the normal 60s cadence.
      failuresRef.current = 0;
      backoffTicksRef.current = 0;

    } catch (err) {
      // This batch was aborted (unmount/remount): not a real failure — bail
      // without surfacing an error or counting it against the backoff.
      if (signal?.aborted) {
        return;
      }
      // Count consecutive failures so the auto-refresh cadence can widen.
      failuresRef.current += 1;
      console.error('Error fetching public statistics:', err);
      // Only show prominent error for manual refresh, not auto-refresh
      if (!isAutoRefresh) {
        setError(statisticsErrorMessage(err, 'Failed to load statistics: ' + err.message));
      } else {
        // For auto-refresh failures, just log and continue silently
        console.warn('Auto-refresh failed, will retry on next interval:', err.message);
      }
    } finally {
      // Only this batch's owner releases the loading flags / in-flight guard. A
      // batch cancelled by unmount/remount leaves them to whoever owns them now.
      if (!signal?.aborted) {
        isFetchingRef.current = false;
        setIsLoading(false);
        setIsRefreshing(false);
      }
    }
  }, []);

  // Auto-refresh functionality
  const startAutoRefresh = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);

    setNextRefreshIn(60);

    // Start countdown timer
    countdownRef.current = setInterval(() => {
      setNextRefreshIn(prev => {
        if (prev <= 1) {
          return 60; // Reset countdown
        }
        return prev - 1;
      });
    }, 1000);

    // Start auto-refresh interval
    intervalRef.current = setInterval(() => {
      if (!autoRefreshEnabled) {
        return;
      }
      // Backoff: while in the failure state, skip ticks so the effective cadence
      // widens (retry only every BACKOFF_FACTOR-th tick) instead of hammering a
      // backend that is already down.
      if (failuresRef.current >= BACKOFF_THRESHOLD) {
        backoffTicksRef.current += 1;
        if (backoffTicksRef.current < BACKOFF_FACTOR) {
          return;
        }
        backoffTicksRef.current = 0; // due for a retry
      }
      fetchAllStats(true);
    }, REFRESH_INTERVAL);
  }, [autoRefreshEnabled, fetchAllStats]);

  const stopAutoRefresh = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    abortControllerRef.current = controller;

    fetchAllStats();
    if (autoRefreshEnabled) {
      startAutoRefresh();
    }

    return () => {
      // Abort the in-flight batch and stop the timers on unmount. Release the
      // overlap guard too, so a remount (e.g. React StrictMode's dev
      // double-mount) is not blocked by the aborted batch's lingering flag.
      controller.abort();
      isFetchingRef.current = false;
      stopAutoRefresh();
    };
  }, [fetchAllStats, autoRefreshEnabled, startAutoRefresh, stopAutoRefresh]);

  if (isLoading) {
    return (
      <div
        style={{ flexGrow: 1, padding: '2rem 1rem', maxWidth: '1200px', margin: '0 auto', width: '100%' }}
        className="content-container"
      >
        {/* Header silhouette */}
        <div style={{
          textAlign: 'center',
          marginBottom: '4rem',
          padding: '2rem 0',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '1.25rem',
        }}>
          <Skeleton width="min(440px, 70%)" height="2.5rem" />
          <Skeleton variant="text" count={2} width="min(640px, 90%)" />
        </div>

        {/* Key metrics: reuse StatCard's own loading state with the known titles */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: getGridColumns(300),
          gap: '2rem',
          marginBottom: '4rem',
        }}>
          <StatCard title="Data Providers" value={0} isLoading color="var(--success)" />
          <StatCard title="Data Centers" value={0} isLoading color="var(--warning)" />
          <StatCard title="Total Datasets" value={0} isLoading color="var(--primary)" />
        </div>

        {/* Charts row silhouette */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile || isTablet ? '1fr' : 'minmax(0, 2fr) minmax(0, 1fr)',
          gap: '2.5rem',
          marginBottom: '4rem',
        }}>
          {Array.from({ length: 2 }).map((_, i) => (
            <div key={i} style={{
              backgroundColor: 'var(--card-bg)',
              border: '1px solid var(--border)',
              borderRadius: '0.75rem',
              padding: '1.5rem',
            }}>
              <Skeleton width="55%" height="1.25rem" style={{ marginBottom: '0.5rem' }} />
              <Skeleton width="40%" height="0.875rem" style={{ marginBottom: '1.5rem' }} />
              <Skeleton width="100%" height={300} radius="0.5rem" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error && !overviewStats) {
    return (
      <div style={{ padding: '1.5rem' }}>
        <Alert type="error">{error}</Alert>
      </div>
    );
  }

  return (
    <div
      style={{
        flexGrow: 1,
        padding: '2rem 1rem',
        maxWidth: '1200px',
        margin: '0 auto',
        width: '100%',
      }}
      className="content-container"
    >
      {/* Header */}
      <div style={{
        textAlign: 'center',
        marginBottom: '4rem',
        position: 'relative',
        padding: '2rem 0'
      }}>
        {/* Background decoration */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: '50%',
          transform: 'translateX(-50%)',
          width: '200px',
          height: '200px',
          background: 'radial-gradient(circle, var(--primary)08 0%, transparent 70%)',
          borderRadius: '50%',
          zIndex: -1
        }} />

        <h1 style={{
          fontSize: 'clamp(2rem, 4vw, 2.75rem)',
          fontWeight: 700,
          color: 'var(--text)',
          letterSpacing: '-0.025em',
          margin: '0 0 1.5rem 0'
        }}>
          GFBio Registry Statistics
        </h1>
        <p style={{
          fontSize: '1.25rem',
          color: 'var(--text-light)',
          maxWidth: '700px',
          margin: '0 auto',
          lineHeight: '1.6',
          fontWeight: 400
        }}>
          Explore comprehensive statistics about biological datasets and data providers
          in the German Federation for Biological Data registry.
        </p>
      </div>

      {error && (
        <Alert type="warning" style={{ marginBottom: '1.5rem' }}>
          Some data may be outdated: {error}
        </Alert>
      )}

      {/* Key Metrics Overview */}
      {overviewStats && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: getGridColumns(300),
          gap: '2rem',
          marginBottom: '4rem'
        }}>
          <StatCard
            title="Data Providers"
            value={overviewStats.total_providers}
            icon={<Users size={20} />}
            color="var(--success)"
            isLiveData={autoRefreshEnabled}
          />

          <StatCard
            title="Data Centers"
            value={overviewStats.total_datacenters}
            icon={<Server size={20} />}
            color="var(--warning)"
            isLiveData={autoRefreshEnabled}
          />

          <StatCard
            title="Total Datasets"
            value={overviewStats.total_datasets}
            icon={<Database size={20} />}
            color="var(--primary)"
            isLiveData={autoRefreshEnabled}
          />

        </div>
      )}


      {/* Charts Section */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile || isTablet ? '1fr' : 'minmax(0, 2fr) minmax(0, 1fr)',
        gap: '2.5rem',
        marginBottom: '4rem'
      }}>
        {/* Registry Growth Timeline */}
        <TimeSeriesChart
          data={timelineData}
          title="Dataset Registration Timeline"
          subtitle="Growth in total datasets over time"
          color="var(--primary)"
          height={400}
          integerOnly={true}
        />

        {/* Data Center Distribution */}
        <PieChart
          data={providerStats.datacenters || []}
          title="Data Center Distribution"
          subtitle="Datasets by data center"
          height={400}
          colors={[
            '#3B82F6', // Blue
            '#10B981', // Green
            '#F59E0B', // Amber
            '#EF4444', // Red
            '#8B5CF6', // Purple
            '#EC4899', // Pink
            '#14B8A6', // Teal
            '#F97316', // Orange
            '#6366F1', // Indigo
            '#84CC16', // Lime
            '#06B6D4', // Cyan
            '#FBBF24'  // Yellow
          ]}
        />
      </div>

    </div>
  );
}

export default PublicStatsDashboard;
