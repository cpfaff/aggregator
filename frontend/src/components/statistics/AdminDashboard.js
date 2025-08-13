import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../auth/AuthContext';
import { authStatsApi, publicStatsApi, statsUtils } from '../../utils/statisticsApi';
import StatCard from '../ui/StatCard';
import TimeSeriesChart from '../ui/TimeSeriesChart';
import PieChart from '../ui/PieChart';
import Alert from '../ui/Alert';
import { 
  Database, 
  FileText, 
  CheckCircle, 
  RefreshCw, 
  Users,
  Server
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
      
      // Fetch public stats for datacenter distribution
      const providers = await publicStatsApi.getProviders();
      
      // Transform datacenter data for PieChart component
      // Only update if data has actually changed to prevent chart re-renders
      const transformedDatacenters = (providers.datacenters || []).map(dc => ({
        name: dc.datacenter,
        value: dc.dataset_count,
        provider_count: dc.provider_count
      }));
      
      setDatacenterStats(prev => {
        const prevDataStr = JSON.stringify(prev);
        const newDataStr = JSON.stringify(transformedDatacenters);
        if (prevDataStr !== newDataStr) {
          return transformedDatacenters;
        }
        return prev;
      });
      
      // Fetch time-series data for system dataset count
      await fetchTimeSeries();
      
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
    <div style={{ padding: '1.5rem', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem'
      }}>
        <div>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            marginBottom: '0.5rem'
          }}>
            <h2 style={{
              fontSize: '1.75rem',
              fontWeight: 700,
              color: 'var(--text)',
              margin: 0
            }}>
              Admin Dashboard
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
          <p style={{
            color: 'var(--text-light)',
            margin: 0
          }}>
            Real-time system statistics and performance metrics
          </p>
          <p style={{
            color: 'var(--text-light)',
            fontSize: '0.875rem',
            margin: '0.25rem 0 0 0'
          }}>
            Data updates automatically every 30 seconds
          </p>
        </div>
        
      </div>

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
            title="Total Datasets"
            value={overviewStats.total_datasets}
            icon={<Database size={20} />}
            color="var(--primary)"
            isLiveData={autoRefreshEnabled}
          />
          
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
            title="XML Archives"
            value={overviewStats.total_xml_archives}
            icon={<FileText size={20} />}
            color="var(--error)"
            isLiveData={autoRefreshEnabled}
          />
          
          {overviewStats.validation_success_rate !== null && (
            <StatCard
              title="Validation Success Rate"
              value={`${overviewStats.validation_success_rate.toFixed(1)}`}
              unit="%"
              icon={<CheckCircle size={20} />}
              color="var(--success)"
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

      {/* Quality Metrics */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        marginBottom: '2rem'
      }}>
        {/* Quality Metrics */}
        {qualityMetrics && (
          <div style={{
            backgroundColor: 'var(--card-bg)',
            borderRadius: '0.75rem',
            padding: '1.5rem',
            border: '1px solid var(--border)'
          }}>
            <h3 style={{
              fontSize: '1.125rem',
              fontWeight: 600,
              color: 'var(--text)',
              marginBottom: '1.5rem'
            }}>
              Data Quality Metrics
            </h3>
            
            <div style={{ display: 'grid', gap: '1.5rem' }}>
              <div>
                <div style={{
                  fontSize: '0.875rem',
                  color: 'var(--text-light)',
                  marginBottom: '0.5rem'
                }}>
                  Total Validations
                </div>
                <div style={{
                  fontSize: '1.5rem',
                  fontWeight: 700,
                  color: 'var(--text)'
                }}>
                  {qualityMetrics.total_validations.toLocaleString()}
                </div>
              </div>
              
              <div>
                <div style={{
                  fontSize: '0.875rem',
                  color: 'var(--text-light)',
                  marginBottom: '0.5rem'
                }}>
                  Success Rate
                </div>
                <div style={{
                  fontSize: '1.5rem',
                  fontWeight: 700,
                  color: 'var(--success)'
                }}>
                  {qualityMetrics.success_rate.toFixed(1)}%
                </div>
                <div style={{
                  width: '100%',
                  height: '6px',
                  backgroundColor: 'var(--border)',
                  borderRadius: '3px',
                  marginTop: '0.5rem',
                  overflow: 'hidden'
                }}>
                  <div style={{
                    width: `${qualityMetrics.success_rate}%`,
                    height: '100%',
                    backgroundColor: 'var(--success)',
                    transition: 'width 0.3s ease'
                  }} />
                </div>
              </div>
              
              {qualityMetrics.average_processing_time && (
                <div>
                  <div style={{
                    fontSize: '0.875rem',
                    color: 'var(--text-light)',
                    marginBottom: '0.5rem'
                  }}>
                    Avg. Processing Time
                  </div>
                  <div style={{
                    fontSize: '1.25rem',
                    fontWeight: 600,
                    color: 'var(--text)'
                  }}>
                    {qualityMetrics.average_processing_time.toFixed(1)}s
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

    </div>
  );
}

export default AdminDashboard;