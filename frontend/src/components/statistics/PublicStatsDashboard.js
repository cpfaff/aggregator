import React, { useState, useEffect } from 'react';
import { publicStatsApi, statsUtils } from '../../utils/statisticsApi';
import StatCard from '../ui/StatCard';
import TimeSeriesChart from '../ui/TimeSeriesChart';
import PieChart from '../ui/PieChart';
import Alert from '../ui/Alert';
import Button from '../ui/Button';
import { 
  Database, 
  Building, 
  FileText, 
  CheckCircle, 
  RefreshCw, 
  Activity,
  Users,
  Server,
  Globe
} from 'lucide-react';

/**
 * PublicStatsDashboard component for external users to view registry statistics
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

  const fetchAllStats = async () => {
    try {
      setIsLoading(true);
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
      const transformedProviders = {
        ...providers,
        // Transform datacenter data for PieChart component
        datacenters: (providers.datacenters || []).map(dc => ({
          name: dc.datacenter,
          value: dc.dataset_count,
          provider_count: dc.provider_count
        }))
      };
      setProviderStats(transformedProviders);
      
      // Format timeline data for the chart
      const formattedTimeline = (timeline.datasets_timeline || []).map(point => ({
        date: new Date(point.date).toLocaleDateString(),
        value: point.value,
        fullDate: point.date,
        ...point.extra_data
      }));
      setTimelineData(formattedTimeline);
      
      setRecentActivity(activity);
      setHealthStatus(health);
      
    } catch (err) {
      console.error('Error fetching public statistics:', err);
      setError('Failed to load statistics: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchAllStats();
  }, []);

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
        <Button onClick={fetchAllStats} style={{ marginTop: '1rem' }}>
          <RefreshCw size={16} />
          Retry
        </Button>
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
        
        <h1 style={{
          fontSize: 'clamp(2rem, 5vw, 3rem)',
          fontWeight: 800,
          background: 'linear-gradient(135deg, var(--text) 0%, var(--primary) 100%)',
          backgroundClip: 'text',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: '1.5rem',
          letterSpacing: '-2px'
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
            title="Total Datasets"
            value={overviewStats.total_datasets}
            icon={<Database size={20} />}
            color="var(--primary)"
          />
          
          <StatCard
            title="Data Providers"
            value={overviewStats.total_providers}
            icon={<Users size={20} />}
            color="var(--success)"
          />
          
          <StatCard
            title="Data Centers"
            value={overviewStats.total_datacenters}
            icon={<Server size={20} />}
            color="var(--warning)"
          />
          
          <StatCard
            title="XML Archives"
            value={overviewStats.total_xml_archives}
            icon={<FileText size={20} />}
            color="var(--error)"
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
            Data Quality & Validation
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
                  Avg Processing Time
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
        marginBottom: '4rem',
        '@media (max-width: 768px)': {
          gridTemplateColumns: '1fr',
        }
      }}>
        {/* Registry Growth Timeline */}
        <TimeSeriesChart
          data={timelineData}
          title="Registry Growth Over Time"
          subtitle="Historical growth in dataset registrations"
          color="var(--primary)"
          height={400}
        />

        {/* Data Center Distribution */}
        <PieChart
          data={providerStats.datacenters || []}
          title="Geographic Distribution"
          subtitle="Datasets by data center location"
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

      {/* Footer Information */}
      <div style={{
        textAlign: 'center',
        padding: '2rem',
        backgroundColor: 'var(--subtle-bg)',
        borderRadius: '1rem',
        marginTop: '3rem'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '0.5rem',
          marginBottom: '1rem'
        }}>
          <Globe size={20} color="var(--primary)" />
          <h3 style={{
            fontSize: '1.25rem',
            fontWeight: 600,
            color: 'var(--text)',
            margin: 0
          }}>
            About GFBio Registry
          </h3>
        </div>
        
        <p style={{
          color: 'var(--text-light)',
          maxWidth: '800px',
          margin: '0 auto 1rem',
          lineHeight: 1.6
        }}>
          The German Federation for Biological Data (GFBio) registry serves as a central 
          hub for biological datasets across Germany. Our platform enables researchers 
          to discover, access, and contribute high-quality biological data while maintaining 
          rigorous validation standards.
        </p>
        
        {overviewStats?.last_updated && (
          <div style={{
            color: 'var(--text-light)',
            fontSize: '0.875rem'
          }}>
            Statistics last updated: {new Date(overviewStats.last_updated).toLocaleString()}
          </div>
        )}
      </div>
    </div>
  );
}

export default PublicStatsDashboard;