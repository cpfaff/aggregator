import React, { useState, useEffect, useRef, useCallback } from 'react';
import { publicStatsApi } from '../../utils/statisticsApi';
import StatCard from '../ui/StatCard';
import TimeSeriesChart from '../ui/TimeSeriesChart';
import PieChart from '../ui/PieChart';
import Alert from '../ui/Alert';
import { 
  Database, 
  FileText, 
  Users,
  Server
} from 'lucide-react';

/**
 * PublicStatsDashboard component for external users to view registry statistics
 * Features real-time auto-refresh every 60 seconds with manual controls
 */
function PublicStatsDashboard() {
  const [overviewStats, setOverviewStats] = useState(null);
  const [qualityMetrics, setQualityMetrics] = useState(null);
  const [providerStats, setProviderStats] = useState([]);
  const [timelineData, setTimelineData] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [healthStatus, setHealthStatus] = useState(null);
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
      
      const [overview, quality, providers, timeline, activity, health] = await Promise.all([
        publicStatsApi.getOverview(),
        publicStatsApi.getQuality(),
        publicStatsApi.getProviders(),
        publicStatsApi.getTimeline({ period: 'daily', months: 1 }),
        publicStatsApi.getRecentActivity(),
        publicStatsApi.getHealth()
      ]);
      
      setOverviewStats(overview);
      setQualityMetrics(quality);
      
      // Transform provider stats data for compatibility with charts
      // Only update if data has actually changed to prevent chart re-renders
      const transformedProviders = {
        ...providers,
        // Transform datacenter data for PieChart component
        datacenters: (providers.datacenters || []).map(dc => ({
          name: dc.datacenter,
          value: dc.dataset_count,
          provider_count: dc.provider_count
        }))
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
      
      setRecentActivity(activity);
      setHealthStatus(health);
      
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
    <div style={{ 
      padding: '2rem 1.5rem 4rem', 
      maxWidth: '1400px', 
      margin: '0 auto',
      minHeight: '100vh'
    }}>
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
        
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.5rem'
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            flexWrap: 'wrap'
          }}>
            <h1 style={{
              fontSize: 'clamp(2rem, 5vw, 3rem)',
              fontWeight: 800,
              background: 'linear-gradient(135deg, var(--text) 0%, var(--primary) 100%)',
              backgroundClip: 'text',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '-2px',
              margin: 0
            }}>
              GFBio Registry Statistics
            </h1>
            {autoRefreshEnabled && (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.25rem',
                padding: '0.5rem 1rem',
                backgroundColor: 'var(--success)',
                color: 'white',
                borderRadius: '1.5rem',
                fontSize: '0.875rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                animation: 'pulse 3s infinite',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
              }}>
                <div style={{
                  width: '8px',
                  height: '8px',
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
          fontSize: '1.25rem',
          color: 'var(--text-light)',
          maxWidth: '700px',
          margin: '0 auto',
          lineHeight: '1.6',
          fontWeight: 400
        }}>
          Explore comprehensive statistics about biological datasets, data providers, 
          and quality metrics in the German Federation for Biological Data registry.
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
          
          <StatCard
            title="XML Archives"
            value={overviewStats.total_xml_archives}
            icon={<FileText size={20} />}
            color="var(--error)"
            isLiveData={autoRefreshEnabled}
          />
        </div>
      )}

      {/* Data Quality Section */}
      {qualityMetrics && (
        <div style={{
          backgroundColor: 'var(--card-bg)',
          borderRadius: '1.5rem',
          padding: '3rem 2rem',
          border: '1px solid var(--border)',
          marginBottom: '4rem',
          textAlign: 'center',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
          background: `linear-gradient(135deg, var(--card-bg) 0%, rgba(255, 255, 255, 0.02) 100%)`,
          position: 'relative',
          overflow: 'hidden'
        }}>
          {/* Background decoration */}
          <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'radial-gradient(ellipse at center, var(--success)05 0%, transparent 70%)',
            pointerEvents: 'none'
          }} />
          
          <h2 style={{
            fontSize: '2rem',
            fontWeight: 700,
            color: 'var(--text)',
            marginBottom: '1.5rem',
            letterSpacing: '-1px',
            position: 'relative',
            zIndex: 1
          }}>
            Data Quality Metrics
          </h2>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '3rem',
            marginTop: '2.5rem',
            position: 'relative',
            zIndex: 1
          }}>
            <div style={{
              padding: '1.5rem',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '1rem',
              border: '1px solid var(--border)',
              backdropFilter: 'blur(10px)'
            }}>
              <div style={{
                fontSize: '3rem',
                fontWeight: 800,
                background: 'linear-gradient(135deg, var(--primary) 0%, #3b82f6 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                marginBottom: '0.75rem',
                lineHeight: 1
              }}>
                {qualityMetrics.total_validations.toLocaleString()}
              </div>
              <div style={{
                fontSize: '1.1rem',
                color: 'var(--text-light)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Total Validations
              </div>
            </div>
            
            <div style={{
              padding: '1.5rem',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '1rem',
              border: '1px solid var(--border)',
              backdropFilter: 'blur(10px)'
            }}>
              <div style={{
                fontSize: '3rem',
                fontWeight: 800,
                background: 'linear-gradient(135deg, var(--success) 0%, #22c55e 100%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                marginBottom: '0.75rem',
                lineHeight: 1
              }}>
                {qualityMetrics.success_rate.toFixed(1)}%
              </div>
              <div style={{
                fontSize: '1.1rem',
                color: 'var(--text-light)',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Validation Success Rate
              </div>
            </div>
            
            {qualityMetrics.average_processing_time && (
              <div style={{
                padding: '1.5rem',
                backgroundColor: 'rgba(255, 255, 255, 0.03)',
                borderRadius: '1rem',
                border: '1px solid var(--border)',
                backdropFilter: 'blur(10px)'
              }}>
                <div style={{
                  fontSize: '3rem',
                  fontWeight: 800,
                  background: 'linear-gradient(135deg, var(--warning) 0%, #f59e0b 100%)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  marginBottom: '0.75rem',
                  lineHeight: 1
                }}>
                  {qualityMetrics.average_processing_time.toFixed(1)}s
                </div>
                <div style={{
                  fontSize: '1.1rem',
                  color: 'var(--text-light)',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  letterSpacing: '0.5px'
                }}>
                  Average Validation Time
                </div>
              </div>
            )}
          </div>
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
        />

        {/* Data Center Distribution */}
        <PieChart
          data={providerStats.datacenters || []}
          title="Data Center Distribution"
          subtitle="Datasets by data center"
          height={400}
          colors={['var(--primary)', 'var(--success)', 'var(--warning)', 'var(--error)']}
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

export default PublicStatsDashboard;