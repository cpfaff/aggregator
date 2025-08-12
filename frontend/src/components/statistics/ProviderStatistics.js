import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { authStatsApi, statsUtils } from '../../utils/statisticsApi';
import StatCard from '../ui/StatCard';
import TimeSeriesChart from '../ui/TimeSeriesChart';
import Alert from '../ui/Alert';
import { Database, FileText, CheckCircle, Activity, TrendingUp } from 'lucide-react';

/**
 * ProviderStatistics component for displaying provider-specific statistics
 */
function ProviderStatistics({ providerId, providerName }) {
  const { handleTokenExpiration } = useAuth();
  const [stats, setStats] = useState(null);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isTimeSeriesLoading, setIsTimeSeriesLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchProviderStats = async () => {
    try {
      setIsLoading(true);
      setError('');
      
      const data = await authStatsApi.getProviderStats(providerId, handleTokenExpiration);
      setStats(data);
      
      // Fetch time-series data for this provider's dataset count
      await fetchTimeSeries();
      
    } catch (err) {
      console.error('Error fetching provider statistics:', err);
      setError('Failed to load provider statistics: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchTimeSeries = async () => {
    try {
      setIsTimeSeriesLoading(true);
      
      const params = {
        metricType: 'provider_dataset_count',
        entityType: 'provider',
        entityId: providerId,
        period: 'daily',
        limit: 30
      };
      
      const data = await authStatsApi.getTimeSeries(params, handleTokenExpiration);
      const formattedData = statsUtils.formatTimeSeriesForChart(data.data_points);
      setTimeSeriesData(formattedData);
      
    } catch (err) {
      console.error('Error fetching provider time-series:', err);
      // Don't set error for time-series failure, just log it
    } finally {
      setIsTimeSeriesLoading(false);
    }
  };

  useEffect(() => {
    if (providerId) {
      fetchProviderStats();
    }
  }, [providerId]);

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
        <Alert type="info">No statistics available for this provider.</Alert>
      </div>
    );
  }

  const getActivityStatus = (score) => {
    if (score === null || score === undefined) return 'Unknown';
    if (score >= 80) return 'Very Active';
    if (score >= 60) return 'Active';
    if (score >= 40) return 'Moderate';
    if (score >= 20) return 'Low';
    return 'Inactive';
  };

  const getActivityColor = (score) => {
    if (score === null || score === undefined) return 'var(--text-light)';
    if (score >= 80) return 'var(--success)';
    if (score >= 60) return 'var(--primary)';
    if (score >= 40) return 'var(--warning)';
    return 'var(--error)';
  };

  return (
    <div style={{ 
      padding: '2rem 1.5rem', 
      maxWidth: '1200px', 
      margin: '0 auto',
      position: 'relative'
    }}>
      {/* Background decoration */}
      <div style={{
        position: 'absolute',
        top: '2rem',
        right: '2rem',
        width: '150px',
        height: '150px',
        background: 'radial-gradient(circle, var(--primary)06 0%, transparent 70%)',
        borderRadius: '50%',
        zIndex: -1
      }} />
      
      {/* Header */}
      <div style={{ 
        marginBottom: '3rem', 
        textAlign: 'center',
        position: 'relative',
        padding: '1rem 0'
      }}>
        <h2 style={{
          fontSize: 'clamp(1.5rem, 4vw, 2rem)',
          fontWeight: 800,
          background: 'linear-gradient(135deg, var(--text) 0%, var(--primary) 100%)',
          backgroundClip: 'text',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: '1rem',
          letterSpacing: '-1px'
        }}>
          Statistics for {providerName || 'Provider'}
        </h2>
        <p style={{
          color: 'var(--text-light)',
          margin: 0,
          fontSize: '1.1rem',
          lineHeight: '1.6',
          maxWidth: '600px',
          marginLeft: 'auto',
          marginRight: 'auto'
        }}>
          Comprehensive overview of provider performance and data contributions
        </p>
      </div>

      {/* Key Metrics Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
        gap: '2rem',
        marginBottom: '3rem'
      }}>
        <StatCard
          title="Total Datasets"
          value={stats.dataset_count}
          icon={<Database size={20} />}
          color="var(--primary)"
        />
        
        <StatCard
          title="XML Archives"
          value={stats.xml_archive_count}
          icon={<FileText size={20} />}
          color="var(--warning)"
        />
        
        <StatCard
          title="Validation Success Rate"
          value={stats.validation_success_rate ? `${stats.validation_success_rate.toFixed(1)}` : 'N/A'}
          unit={stats.validation_success_rate ? '%' : ''}
          icon={<CheckCircle size={20} />}
          color="var(--success)"
        />
        
        <StatCard
          title="Activity Status"
          value={getActivityStatus(stats.activity_score)}
          icon={<Activity size={20} />}
          color={getActivityColor(stats.activity_score)}
        />
      </div>

      {/* Activity Details */}
      {stats.activity_score !== null && (
        <div style={{
          backgroundColor: 'var(--card-bg)',
          borderRadius: '1rem',
          padding: '2rem',
          border: '1px solid var(--border)',
          marginBottom: '3rem',
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
            background: `radial-gradient(ellipse at 0% 50%, ${getActivityColor(stats.activity_score)}08 0%, transparent 70%)`,
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
            Activity Details
          </h3>
          
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', 
            gap: '2rem',
            position: 'relative',
            zIndex: 1,
            '@media (max-width: 640px)': {
              gridTemplateColumns: '1fr'
            }
          }}>
            <div style={{
              padding: '1.5rem',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '0.75rem',
              border: '1px solid var(--border)',
              backdropFilter: 'blur(10px)'
            }}>
              <div style={{
                fontSize: '0.9rem',
                color: 'var(--text-light)',
                marginBottom: '1rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Activity Score
              </div>
              <div style={{
                fontSize: '2.5rem',
                fontWeight: 800,
                background: `linear-gradient(135deg, ${getActivityColor(stats.activity_score)} 0%, ${getActivityColor(stats.activity_score)}CC 100%)`,
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                marginBottom: '1rem'
              }}>
                {Math.round(stats.activity_score)}/100
              </div>
              <div style={{
                width: '100%',
                height: '8px',
                backgroundColor: 'var(--border)',
                borderRadius: '8px',
                overflow: 'hidden',
                position: 'relative'
              }}>
                <div style={{
                  width: `${Math.min(stats.activity_score, 100)}%`,
                  height: '100%',
                  background: `linear-gradient(90deg, ${getActivityColor(stats.activity_score)} 0%, ${getActivityColor(stats.activity_score)}AA 100%)`,
                  transition: 'width 0.8s cubic-bezier(0.4, 0, 0.2, 1)',
                  borderRadius: '8px',
                  boxShadow: `0 0 0 1px ${getActivityColor(stats.activity_score)}40`
                }} />
              </div>
            </div>
            
            <div style={{
              padding: '1.5rem',
              backgroundColor: 'rgba(255, 255, 255, 0.03)',
              borderRadius: '0.75rem',
              border: '1px solid var(--border)',
              backdropFilter: 'blur(10px)'
            }}>
              <div style={{
                fontSize: '0.9rem',
                color: 'var(--text-light)',
                marginBottom: '1rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px'
              }}>
                Last Activity
              </div>
              <div style={{
                fontSize: '1.25rem',
                fontWeight: 700,
                color: 'var(--text)',
                lineHeight: '1.3'
              }}>
                {stats.last_activity ? 
                  new Date(stats.last_activity).toLocaleDateString('en-US', {
                    year: 'numeric',
                    month: 'short',
                    day: 'numeric'
                  }) : 
                  'No recent activity'
                }
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Dataset Count Timeline */}
      <TimeSeriesChart
        data={timeSeriesData}
        title="Dataset Count Over Time"
        subtitle="Historical view of datasets registered by this provider"
        color="var(--primary)"
        height={300}
        isLoading={isTimeSeriesLoading}
        error={timeSeriesData.length === 0 ? 'No historical data available' : null}
      />
    </div>
  );
}

export default ProviderStatistics;