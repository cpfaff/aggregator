import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../auth/AuthContext';
import { authStatsApi, publicStatsApi, statsUtils } from '../../utils/statisticsApi';
import StatCard from '../ui/StatCard';
import TimeSeriesChart from '../ui/TimeSeriesChart';
import MultiLineTimeSeriesChart from '../ui/MultiLineTimeSeriesChart';
import PieChart from '../ui/PieChart';
import Alert from '../ui/Alert';
import Breadcrumbs from '../ui/Breadcrumbs';

/**
 * AdminDashboard component for comprehensive system statistics
 * Displays real-time metrics and historical trends
 */
function AdminDashboard() {
  const { handleTokenExpiration } = useAuth();
  const [overviewStats, setOverviewStats] = useState(null);
  const [qualityMetrics, setQualityMetrics] = useState(null);
  const [datacenterStats, setDatacenterStats] = useState([]);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [biologicalUnitsData, setBiologicalUnitsData] = useState([]);
  const [multiProviderBiologicalUnits, setMultiProviderBiologicalUnits] = useState({ data: [], providers: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);
  const [biologicalUnitsScaleType, setBiologicalUnitsScaleType] = useState('log'); // Default to log for better visibility

  // Breadcrumb navigation items
  const breadcrumbItems = [
    { label: 'Home', onClick: () => window.location.href = '/' },
    { label: 'Statistics', onClick: null }
  ];

  const fetchAllStats = useCallback(async () => {
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
      // Sort by dataset count (descending) to ensure largest gets primary color
      // Group smaller data centers into "Other" category if too many
      const transformedDatacenters = (() => {
        const sorted = (providers.datacenters || [])
          .map(dc => ({
            name: dc.datacenter,
            value: dc.dataset_count,
            provider_count: dc.provider_count
          }))
          .sort((a, b) => b.value - a.value); // Sort descending by dataset count
        
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
      })();
      
      setDatacenterStats(prev => {
        const prevDataStr = JSON.stringify(prev);
        const newDataStr = JSON.stringify(transformedDatacenters);
        if (prevDataStr !== newDataStr) {
          return transformedDatacenters;
        }
        return prev;
      });
      
      
      // Fetch time-series data for system dataset count and biological units
      await Promise.all([
        fetchTimeSeries(),
        fetchBiologicalUnitsTimeline(),
        fetchMultiProviderBiologicalUnits()
      ]);
      
      // Update last refreshed timestamp
      setLastUpdated(new Date());
      
    } catch (err) {
      console.error('Error fetching admin statistics:', err);
      setError('Failed to load statistics: ' + err.message);
    } finally {
      setIsLoading(false);
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

  const fetchMultiProviderBiologicalUnits = async () => {
    try {
      const params = {
        period: 'daily',
        limit: 30
      };
      
      const data = await authStatsApi.getMultiProviderBiologicalUnits(params, handleTokenExpiration);
      const formattedData = statsUtils.formatMultiProviderTimeSeriesForChart(data.data_points);
      
      // Only update if data has actually changed to prevent chart re-renders
      setMultiProviderBiologicalUnits(prev => {
        const prevDataStr = JSON.stringify(prev);
        const newDataStr = JSON.stringify({ data: formattedData, providers: data.providers });
        if (prevDataStr !== newDataStr) {
          return { data: formattedData, providers: data.providers };
        }
        return prev;
      });
      
    } catch (err) {
      console.error('Error fetching multi-provider biological units:', err);
      // Don't set error for multi-provider biological units failure
    }
  };


  useEffect(() => {
    fetchAllStats();
  }, [fetchAllStats]);

  if (isLoading) {
    return (
      <div 
        style={{ 
          flexGrow: 1,
          padding: '2rem 1rem',
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
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: 600,
          marginLeft: '0.1rem',
          color: 'var(--text)',
          margin: 0
        }}>
          Statistics
        </h2>
      </div>
      
      <p style={{
        color: 'var(--text-light)',
        margin: '0 0 2rem 0'
      }}>
        System statistics and performance metrics with real-time data updates.
      </p>

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
          />
          
          <StatCard
            title="Data Centers"
            value={overviewStats.total_datacenters}
            color="var(--warning)"
          />
          
          <StatCard
            title="Total Datasets"
            value={overviewStats.total_datasets}
            color="var(--primary)"
          />
          
          <StatCard
            title="XML Archives"
            value={overviewStats.total_xml_archives}
            color="var(--info)"
          />
          
          {qualityMetrics && (
            <StatCard
              title="Total Validations"
              value={qualityMetrics.total_validations}
              color="var(--warning)"
              />
          )}
          
          {overviewStats.validation_success_rate !== null && (
            <StatCard
              title="Validation Success Rate"
              value={`${overviewStats.validation_success_rate.toFixed(1)}`}
              unit="%"
              color="var(--success)"
              />
          )}
          
          {qualityMetrics && qualityMetrics.average_processing_time && (
            <StatCard
              title="Average Validation Time"
              value={`${qualityMetrics.average_processing_time.toFixed(1)}`}
              unit="s"
              color="var(--warning)"
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
          integerOnly={true}
        />

        {/* Data Center Distribution */}
        <PieChart
          data={datacenterStats}
          title="Data Center Distribution"
          subtitle="Datasets by data center"
          height={350}
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

      {/* Multi-Provider Biological Units Comparison - Full Width */}
      <div style={{
        marginBottom: '2rem'
      }}>
        <MultiLineTimeSeriesChart
          data={multiProviderBiologicalUnits.data}
          providers={multiProviderBiologicalUnits.providers}
          title="Provider Biological Units Comparison"
          subtitle="Compare biological units across different data providers over time"
          height={600}
          colors={[
            'var(--primary)',
            'var(--success)', 
            'var(--warning)',
            'var(--error)',
            '#8B5CF6',
            '#F59E0B',
            '#EF4444',
            '#10B981',
            '#3B82F6',
            '#6366F1'
          ]}
          scaleType={biologicalUnitsScaleType}
          onScaleTypeChange={setBiologicalUnitsScaleType}
        />
      </div>



    </div>
  );
}

export default AdminDashboard;