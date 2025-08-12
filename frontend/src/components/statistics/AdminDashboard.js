import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { authStatsApi, publicStatsApi, statsUtils } from '../../utils/statisticsApi';
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
  TrendingUp,
  Users,
  Server
} from 'lucide-react';

/**
 * AdminDashboard component for comprehensive system statistics
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

  const fetchAllStats = async () => {
    try {
      setIsLoading(true);
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
      const transformedDatacenters = (providers.datacenters || []).map(dc => ({
        name: dc.datacenter,
        value: dc.dataset_count,
        provider_count: dc.provider_count
      }));
      setDatacenterStats(transformedDatacenters);
      
      // Fetch time-series data for system dataset count
      await fetchTimeSeries();
      
    } catch (err) {
      console.error('Error fetching admin statistics:', err);
      setError('Failed to load statistics: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

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
      setTimeSeriesData(formattedData);
      
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
    <div style={{ padding: '1.5rem', maxWidth: '1400px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem'
      }}>
        <div>
          <h2 style={{
            fontSize: '1.75rem',
            fontWeight: 700,
            color: 'var(--text)',
            marginBottom: '0.5rem'
          }}>
            Admin Dashboard
          </h2>
          <p style={{
            color: 'var(--text-light)',
            margin: 0
          }}>
            System-wide statistics and performance metrics
          </p>
        </div>
        
        <Button 
          onClick={triggerStatsCollection}
          disabled={isCollecting}
          isLoading={isCollecting}
        >
          <RefreshCw size={16} />
          Collect Stats
        </Button>
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
          
          {overviewStats.validation_success_rate !== null && (
            <StatCard
              title="Validation Success Rate"
              value={`${overviewStats.validation_success_rate.toFixed(1)}`}
              unit="%"
              icon={<CheckCircle size={20} />}
              color="var(--success)"
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

      {/* Last Updated Information */}
      {overviewStats?.last_updated && (
        <div style={{
          textAlign: 'center',
          color: 'var(--text-light)',
          fontSize: '0.875rem',
          marginTop: '2rem'
        }}>
          Last updated: {new Date(overviewStats.last_updated).toLocaleString()}
        </div>
      )}
    </div>
  );
}

export default AdminDashboard;