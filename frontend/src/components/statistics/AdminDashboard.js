import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../auth/AuthContext';
import { authStatsApi, publicStatsApi, statsUtils } from '../../utils/statisticsApi';
import StatCard from '../ui/StatCard';
import TimeSeriesChart from '../ui/TimeSeriesChart';
import PieChart from '../ui/PieChart';
import Alert from '../ui/Alert';
import Breadcrumbs from '../ui/Breadcrumbs';
import ActionMenu from '../ui/ActionMenu';
import { 
  RefreshCw, 
  RotateCcw
} from 'lucide-react';

/**
 * AdminDashboard component for comprehensive system statistics
 * Features real-time auto-refresh every 30 seconds with manual controls
 */
function AdminDashboard() {
  const { handleTokenExpiration } = useAuth();
  const [overviewStats, setOverviewStats] = useState(null);
  const [qualityMetrics, setQualityMetrics] = useState(null);
  const [datacenterStats, setDatacenterStats] = useState([]);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [biologicalUnitsData, setBiologicalUnitsData] = useState([]);
  const [providerStats, setProviderStats] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [healthStatus, setHealthStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [isCollecting, setIsCollecting] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [autoRefreshEnabled, setAutoRefreshEnabled] = useState(true);
  const [nextRefreshIn, setNextRefreshIn] = useState(30);
  
  const intervalRef = useRef(null);
  const countdownRef = useRef(null);
  const REFRESH_INTERVAL = 30000; // 30 seconds

  // Breadcrumb navigation items
  const breadcrumbItems = [
    { label: 'Home', onClick: () => window.location.href = '/' },
    { label: 'Statistics', onClick: null }
  ];

  const fetchAllStats = useCallback(async (isAutoRefresh = false) => {
    try {
      if (!isAutoRefresh) {
        setIsLoading(true);
      } else {
        setIsRefreshing(true);
      }
      setError('');
      
      // Fetch overview statistics
      const overview = await authStatsApi.getOverview(handleTokenExpiration);
      setOverviewStats(overview);
      
      // Fetch quality metrics
      const quality = await authStatsApi.getQualityMetrics(handleTokenExpiration);
      setQualityMetrics(quality);
      
      // Fetch public stats for datacenter distribution and provider stats
      const [providers, activity, health] = await Promise.all([
        publicStatsApi.getProviders(),
        publicStatsApi.getRecentActivity(),
        publicStatsApi.getHealth()
      ]);
      
      // Transform datacenter data for PieChart component
      // Sort by dataset count (descending) to ensure largest gets primary color
      // Only update if data has actually changed to prevent chart re-renders
      const transformedDatacenters = (providers.datacenters || [])
        .map(dc => ({
          name: dc.datacenter,
          value: dc.dataset_count,
          provider_count: dc.provider_count
        }))
        .sort((a, b) => b.value - a.value); // Sort descending by dataset count
      
      setDatacenterStats(prev => {
        const prevDataStr = JSON.stringify(prev);
        const newDataStr = JSON.stringify(transformedDatacenters);
        if (prevDataStr !== newDataStr) {
          return transformedDatacenters;
        }
        return prev;
      });
      
      // Set provider stats, recent activity, and health status for Registry Activity
      setProviderStats(providers);
      setRecentActivity(activity);
      setHealthStatus(health);
      
      // Fetch time-series data for system dataset count and biological units
      await Promise.all([
        fetchTimeSeries(),
        fetchBiologicalUnitsTimeline()
      ]);
      
      // Update last refreshed timestamp
      setLastUpdated(new Date());
      
    } catch (err) {
      console.error('Error fetching admin statistics:', err);
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
  }, [handleTokenExpiration]);

  const fetchTimeSeries = async () => {
    try {
      const params = {
        metricType: 'dataset_count',
        entityType: 'system',
        period: 'daily',
        limit: 30
      };
      
      const data = await authStatsApi.getTimeSeries(params, handleTokenExpiration);
      const formattedData = statsUtils.formatTimeSeriesForChart(data.data_points);
      
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
      console.error('Error fetching time-series:', err);
      // Don't set error for time-series failure
    }
  };

  const fetchBiologicalUnitsTimeline = async () => {
    try {
      const params = {
        period: 'daily',
        limit: 30
      };
      
      const data = await authStatsApi.getBiologicalUnitsTimeline(params, handleTokenExpiration);
      const formattedData = statsUtils.formatTimeSeriesForChart(data.data_points);
      
      // Only update if data has actually changed to prevent chart re-renders
      setBiologicalUnitsData(prev => {
        const prevDataStr = JSON.stringify(prev);
        const newDataStr = JSON.stringify(formattedData);
        if (prevDataStr !== newDataStr) {
          return formattedData;
        }
        return prev;
      });
      
    } catch (err) {
      console.error('Error fetching biological units timeline:', err);
      // Don't set error for biological units timeline failure
    }
  };

  const triggerStatsCollection = async () => {
    try {
      setIsCollecting(true);
      await authStatsApi.triggerCollection(null, handleTokenExpiration);
      
      // Wait a moment then refresh data
      setTimeout(() => {
        fetchAllStats();
        setIsCollecting(false);
      }, 2000);
      
    } catch (err) {
      console.error('Error triggering collection:', err);
      setError('Failed to trigger statistics collection: ' + err.message);
      setIsCollecting(false);
    }
  };

  // Auto-refresh functionality
  const startAutoRefresh = useCallback(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);
    
    setNextRefreshIn(30);
    
    // Start countdown timer
    countdownRef.current = setInterval(() => {
      setNextRefreshIn(prev => {
        if (prev <= 1) {
          return 30; // Reset countdown
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
        <Breadcrumbs items={breadcrumbItems} />
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
        <Breadcrumbs items={breadcrumbItems} />
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
      <Breadcrumbs items={breadcrumbItems} />
      
      {/* Page title and actions */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '1rem',
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '1rem'
        }}>
          <h2 style={{
            fontSize: '1.5rem',
            fontWeight: 600,
            marginLeft: '0.1rem',
            color: 'var(--text)',
            margin: 0
          }}>
            Statistics
          </h2>
          {autoRefreshEnabled && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
              padding: '0.25rem 0.75rem',
              backgroundColor: 'var(--success)',
              color: 'white',
              borderRadius: '1rem',
              fontSize: '0.75rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
              animation: 'pulse 3s infinite'
            }}>
              <div style={{
                width: '6px',
                height: '6px',
                backgroundColor: 'white',
                borderRadius: '50%',
                animation: 'pulse 1s infinite'
              }} />
              Live Data
            </div>
          )}
        </div>
      </div>
      
      <p style={{
        color: 'var(--text-light)',
        margin: '0 0 2rem 0'
      }}>
        Real-time system statistics and performance metrics. Data updates automatically every 30 seconds.
      </p>

      {/* ActionMenu for admin controls */}
      <ActionMenu
        mode="content-relative"
        offset={16}
        actions={[
          {
            icon: <RefreshCw size={24} />,
            label: 'Manual Refresh',
            onClick: handleManualRefresh,
            color: 'var(--success)'
          },
          {
            icon: <RotateCcw size={24} />,
            label: autoRefreshEnabled ? 'Disable Auto-refresh' : 'Enable Auto-refresh',
            onClick: toggleAutoRefresh,
            color: autoRefreshEnabled ? 'var(--warning)' : 'var(--success)'
          }
        ]}
      />

      {error && (
        <Alert type="warning" style={{ marginBottom: '1.5rem' }}>
          {error}
        </Alert>
      )}

      {/* System Overview Cards */}
      {overviewStats && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem'
        }}>
          <StatCard
            title="Data Providers"
            value={overviewStats.total_providers}
            color="var(--success)"
            isLiveData={autoRefreshEnabled}
          />
          
          <StatCard
            title="Data Centers"
            value={overviewStats.total_datacenters}
            color="var(--warning)"
            isLiveData={autoRefreshEnabled}
          />
          
          <StatCard
            title="Total Datasets"
            value={overviewStats.total_datasets}
            color="var(--primary)"
            isLiveData={autoRefreshEnabled}
          />
          
          <StatCard
            title="XML Archives"
            value={overviewStats.total_xml_archives}
            color="var(--info)"
            isLiveData={autoRefreshEnabled}
          />
          
          {qualityMetrics && (
            <StatCard
              title="Total Validations"
              value={qualityMetrics.total_validations}
              color="var(--warning)"
              isLiveData={autoRefreshEnabled}
            />
          )}
          
          {overviewStats.validation_success_rate !== null && (
            <StatCard
              title="Validation Success Rate"
              value={`${overviewStats.validation_success_rate.toFixed(1)}`}
              unit="%"
              color="var(--success)"
              isLiveData={autoRefreshEnabled}
            />
          )}
          
          {qualityMetrics && qualityMetrics.average_processing_time && (
            <StatCard
              title="Average Validation Time"
              value={`${qualityMetrics.average_processing_time.toFixed(1)}`}
              unit="s"
              color="var(--warning)"
              isLiveData={autoRefreshEnabled}
            />
          )}
        </div>
      )}

      {/* Charts Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '2fr 1fr',
        gap: '1.5rem',
        marginBottom: '2rem'
      }}>
        {/* Dataset Growth Timeline */}
        <TimeSeriesChart
          data={timeSeriesData}
          title="Dataset Registration Timeline"
          subtitle="Growth in total datasets over time"
          color="var(--primary)"
          height={350}
        />

        {/* Data Center Distribution */}
        <PieChart
          data={datacenterStats}
          title="Data Center Distribution"
          subtitle="Datasets by data center"
          height={350}
          colors={['var(--primary)', 'var(--success)', 'var(--warning)', 'var(--error)']}
        />
      </div>

      {/* Biological Units Timeline - Full Width */}
      <div style={{
        marginBottom: '2rem'
      }}>
        <TimeSeriesChart
          data={biologicalUnitsData}
          title="Biological Units Timeline"
          subtitle="Total biological units across all providers over time"
          color="var(--success)"
          height={350}
        />
      </div>

      {/* Registry Activity */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        marginBottom: '4rem'
      }}>
        {/* Activity Metrics */}
        {healthStatus && (
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
              background: `radial-gradient(ellipse at 100% 0%, var(--primary)05 0%, transparent 70%)`,
              pointerEvents: 'none'
            }} />
            
            <h3 style={{
              fontSize: '1.5rem',
              fontWeight: 700,
              color: 'var(--text)',
              marginBottom: '2rem',
              letterSpacing: '-0.5px',
              position: 'relative',
              zIndex: 1
            }}>
              Registry Activity
            </h3>
            
            <div style={{ 
              display: 'grid', 
              gap: '2rem',
              position: 'relative',
              zIndex: 1
            }}>
              <div style={{
                textAlign: 'center',
                padding: '1rem',
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '0.75rem',
                border: '1px solid var(--border)'
              }}>
                <div style={{
                  fontSize: '0.9rem',
                  color: 'var(--text-light)',
                  marginBottom: '0.75rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  Recent Registrations (30 days)
                </div>
                <div style={{
                  fontSize: '2.5rem',
                  fontWeight: 800,
                  background: 'linear-gradient(135deg, var(--primary) 0%, #3b82f6 100%)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}>
                  {recentActivity?.length || 0}
                </div>
              </div>
              
              <div style={{
                textAlign: 'center',
                padding: '1rem',
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '0.75rem',
                border: '1px solid var(--border)'
              }}>
                <div style={{
                  fontSize: '0.9rem',
                  color: 'var(--text-light)',
                  marginBottom: '0.75rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  Active Providers
                </div>
                <div style={{
                  fontSize: '2.5rem',
                  fontWeight: 800,
                  background: 'linear-gradient(135deg, var(--success) 0%, #22c55e 100%)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}>
                  {providerStats.total_providers || 0}
                </div>
              </div>
              
              <div style={{
                textAlign: 'center',
                padding: '1rem',
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '0.75rem',
                border: '1px solid var(--border)'
              }}>
                <div style={{
                  fontSize: '0.9rem',
                  color: 'var(--text-light)',
                  marginBottom: '0.75rem',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  Processing Jobs
                </div>
                <div style={{
                  fontSize: '2.5rem',
                  fontWeight: 800,
                  background: 'linear-gradient(135deg, var(--warning) 0%, #f59e0b 100%)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent'
                }}>
                  {healthStatus.processing_jobs || 0}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>


    </div>
  );
}

export default AdminDashboard;