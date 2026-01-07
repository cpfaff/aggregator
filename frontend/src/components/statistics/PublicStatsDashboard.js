import React, { useState, useEffect, useRef, useCallback } from 'react';
import { publicStatsApi } from '../../utils/statisticsApi';
import StatCard from '../ui/StatCard';
import TimeSeriesChart from '../ui/TimeSeriesChart';
import PieChart from '../ui/PieChart';
import Alert from '../ui/Alert';
import { 
  Database, 
  Users,
  Server
} from 'lucide-react';

/**
 * PublicStatsDashboard component for external users to view registry statistics
 * Features real-time auto-refresh every 60 seconds with manual controls
 */
function PublicStatsDashboard() {
  const [overviewStats, setOverviewStats] = useState(null);
  const [providerStats, setProviderStats] = useState([]);
  const [timelineData, setTimelineData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const [nextRefreshIn, setNextRefreshIn] = useState(60);
  
  const intervalRef = useRef(null);
  const countdownRef = useRef(null);
  const REFRESH_INTERVAL = 60000; // 60 seconds for public dashboard

  const fetchAllStats = useCallback(async (isAutoRefresh = false) => {
    try {
      if (!isAutoRefresh) {
        setIsLoading(true);
      } else {
        setIsRefreshing(true);
      }
      setError('');
      
      const [overview, providers, timeline] = await Promise.all([
        publicStatsApi.getOverview(),
        publicStatsApi.getProviders(),
        publicStatsApi.getTimeline({ period: 'monthly', months: 12 })
      ]);
      
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
        date: new Date(point.date).toLocaleDateString(),
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
      
    } catch (err) {
      console.error('Error fetching public statistics:', err);
      // Only show prominent error for manual refresh, not auto-refresh
      if (!isAutoRefresh) {
        setError('Failed to load statistics: ' + err.message);
      } else {
        // For auto-refresh failures, just log and continue silently
        console.warn('Auto-refresh failed, will retry on next interval:', err.message);
      }
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
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
      if (autoRefreshEnabled) {
        fetchAllStats(true);
      }
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
  
  const toggleAutoRefresh = () => {
    setAutoRefreshEnabled(prev => {
      const newValue = !prev;
      if (newValue) {
        startAutoRefresh();
      } else {
        stopAutoRefresh();
        setNextRefreshIn(0);
      }
      return newValue;
    });
  };
  
  const handleManualRefresh = () => {
    fetchAllStats(false);
    if (autoRefreshEnabled) {
      startAutoRefresh(); // Reset the auto-refresh timer
    }
  };
  
  useEffect(() => {
    fetchAllStats();
    if (autoRefreshEnabled) {
      startAutoRefresh();
    }
    
    return () => {
      stopAutoRefresh();
    };
  }, [fetchAllStats, autoRefreshEnabled, startAutoRefresh, stopAutoRefresh]);

  if (isLoading) {
    return (
      <div style={{ padding: '1.5rem' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '4rem 0'
        }}>
          <div style={{
            width: '32px',
            height: '32px',
            border: '3px solid var(--border)',
            borderRadius: '50%',
            borderTopColor: 'var(--primary)',
            animation: 'spin 1s linear infinite',
          }}></div>
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
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
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
        gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)',
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