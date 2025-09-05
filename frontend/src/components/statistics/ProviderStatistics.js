import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { authStatsApi, statsUtils } from '../../utils/statisticsApi';
import { apiRequest } from '../../utils/apiUtils';
import axios from 'axios';
import StatCard from '../ui/StatCard';
import TimeSeriesChart from '../ui/TimeSeriesChart';
import Alert from '../ui/Alert';
import { Database, CheckCircle, XCircle, Activity, Package, Clock } from 'lucide-react';

/**
 * ProviderStatistics component for displaying provider-specific statistics
 */
function ProviderStatistics({ providerId, providerName }) {
  const { handleTokenExpiration } = useAuth();
  const [stats, setStats] = useState(null);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [biologicalUnitsTimeSeriesData, setBiologicalUnitsTimeSeriesData] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [datasetStats, setDatasetStats] = useState({});
  const [validationStatuses, setValidationStatuses] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [isTimeSeriesLoading, setIsTimeSeriesLoading] = useState(false);
  const [isBiologicalUnitsTimeSeriesLoading, setIsBiologicalUnitsTimeSeriesLoading] = useState(false);
  const [isDatasetsLoading, setIsDatasetsLoading] = useState(false);
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
      
      // Fetch datasets with statistics
      await fetchDatasetStats();
      
    } catch (err) {
      console.error('Error fetching provider statistics:', err);
      setError('Failed to load provider statistics: ' + err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchDatasetStats = async () => {
    try {
      setIsDatasetsLoading(true);
      
      // Fetch datasets for this provider
      const datasetsRes = await apiRequest(`/data-providers/${providerId}/data-sets`, {}, handleTokenExpiration);
      
      if (!datasetsRes.ok) {
        console.error('Failed to fetch datasets');
        return;
      }
      
      const datasetsData = await datasetsRes.json();
      setDatasets(datasetsData);
      
      // Fetch statistics and validation statuses for each dataset in parallel
      const promises = datasetsData.map(async (dataset) => {
        const results = await Promise.all([
          // Fetch dataset statistics
          authStatsApi.getDatasetStats(dataset.id, handleTokenExpiration).catch(error => {
            console.error(`Error fetching stats for dataset ${dataset.id}:`, error);
            return null;
          }),
          // Fetch validation status from the validators API (the correct source)
          fetchValidationStatus(dataset.id).catch(error => {
            console.error(`Error fetching validation status for dataset ${dataset.id}:`, error);
            return null;
          })
        ]);
        
        return {
          stats: { [dataset.id]: results[0] },
          validation: { [dataset.id]: results[1] }
        };
      });
      
      const allResults = await Promise.all(promises);
      
      // Combine all stats
      const combinedStats = allResults.reduce((acc, result) => ({ ...acc, ...result.stats }), {});
      setDatasetStats(combinedStats);
      
      // Combine all validation statuses
      const combinedValidation = allResults.reduce((acc, result) => ({ ...acc, ...result.validation }), {});
      setValidationStatuses(combinedValidation);
      
    } catch (err) {
      console.error('Error fetching dataset statistics:', err);
      // Don't set error for dataset stats failure, just log it
    } finally {
      setIsDatasetsLoading(false);
    }
  };

  // Fetch validation status from the validators API (same as DatasetCard does)
  const fetchValidationStatus = async (datasetId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${process.env.REACT_APP_API_BASE_URL || ''}/api/v1/validators/datasets/${datasetId}/validation-status`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error fetching validation status:', error);
      return null;
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
        metricType: 'provider_biological_units',
        entityType: 'provider',
        entityId: providerId,
        period: 'daily',
        limit: 30
      };
      
      const data = await authStatsApi.getTimeSeries(params, handleTokenExpiration);
      const formattedData = statsUtils.formatTimeSeriesForChart(data.data_points);
      
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
          {providerName || 'Provider Statistics'}
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
              Last activity: {new Date(stats.last_activity).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
              })}
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
          Real-time overview of biological data contributions and temporal trends
        </p>
      </div>

      {/* Key Metrics Cards - Only 2 cards now */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
        gap: '2rem',
        marginBottom: '3rem',
        maxWidth: '800px',
        margin: '0 auto 3rem auto'
      }}>
        <StatCard
          title="Total Datasets"
          value={stats.dataset_count}
          icon={<Database size={20} />}
          color="var(--primary)"
        />
        
        <StatCard
          title="Validation Success Rate"
          value={stats.validation_success_rate ? `${stats.validation_success_rate.toFixed(1)}` : 'N/A'}
          unit={stats.validation_success_rate ? '%' : ''}
          icon={<CheckCircle size={20} />}
          color="var(--success)"
        />
      </div>


      {/* Dataset Cards Section */}
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
        {/* Background decoration */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '60%',
          height: '100%',
          background: 'radial-gradient(ellipse at 0% 50%, var(--primary)08 0%, transparent 70%)',
          pointerEvents: 'none'
        }} />
        
        <div style={{
          position: 'relative',
          zIndex: 1
        }}>
          <h3 style={{
            fontSize: '1.5rem',
            fontWeight: 700,
            color: 'var(--text)',
            marginBottom: '1rem',
            letterSpacing: '-0.5px',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem'
          }}>
            <Package size={24} style={{ color: 'var(--primary)' }} />
            Dataset Biological Units
          </h3>
          
          <p style={{
            color: 'var(--text-light)',
            margin: '0 0 2rem 0',
            fontSize: '1rem',
            lineHeight: '1.6'
          }}>
            Unit counts for each dataset in this provider's collection
          </p>
          
          {isDatasetsLoading ? (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '3rem 0'
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
          ) : datasets.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '3rem 0',
              color: 'var(--text-light)'
            }}>
              No datasets found for this provider
            </div>
          ) : (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: '1.5rem'
            }}>
              {datasets.map((dataset) => {
                const stats = datasetStats[dataset.id];
                const unitCount = stats?.unit_count;
                const validationStatus = validationStatuses[dataset.id];
                
                return (
                  <div
                    key={dataset.id}
                    style={{
                      backgroundColor: 'rgba(255, 255, 255, 0.05)',
                      borderRadius: '0.75rem',
                      border: '1px solid var(--border)',
                      padding: '1.5rem',
                      transition: 'all 0.2s ease',
                      backdropFilter: 'blur(10px)',
                      cursor: 'default'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.transform = 'translateY(-2px)';
                      e.currentTarget.style.boxShadow = '0 8px 16px rgba(0, 0, 0, 0.1)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.transform = 'translateY(0)';
                      e.currentTarget.style.boxShadow = 'none';
                    }}
                  >
                    {/* Dataset header */}
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      marginBottom: '1rem'
                    }}>
                      <span style={{
                        backgroundColor: 'var(--primary)',
                        color: 'white',
                        padding: '0.25rem 0.625rem',
                        borderRadius: '0.375rem',
                        fontSize: '0.75rem',
                        fontWeight: 600,
                        display: 'inline-block',
                      }}>
                        #{dataset.id}
                      </span>
                    </div>
                    
                    {/* Dataset title */}
                    <h4 style={{
                      fontSize: '1rem',
                      fontWeight: 600,
                      color: 'var(--text)',
                      margin: '0 0 1.25rem 0',
                      lineHeight: '1.4',
                      display: '-webkit-box',
                      WebkitLineClamp: '2',
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      minHeight: '2.8rem'
                    }}>
                      {dataset.title || 'Untitled Dataset'}
                    </h4>
                    
                    {/* Biological units count */}
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.75rem',
                      padding: '1rem 0',
                      borderTop: '1px solid var(--border-light)',
                      borderBottom: '1px solid var(--border-light)'
                    }}>
                      <Database 
                        size={20} 
                        style={{ 
                          color: unitCount > 0 ? 'var(--primary)' : 'var(--text-light)',
                          flexShrink: 0 
                        }} 
                      />
                      <div>
                        <div style={{
                          fontSize: '1.75rem',
                          fontWeight: 800,
                          color: unitCount > 0 ? 'var(--primary)' : 'var(--text-light)',
                          lineHeight: 1
                        }}>
                          {unitCount !== null && unitCount !== undefined ? unitCount.toLocaleString() : '–'}
                        </div>
                        <div style={{
                          fontSize: '0.8rem',
                          color: 'var(--text-light)',
                          fontWeight: 500,
                          textTransform: 'uppercase',
                          letterSpacing: '0.5px',
                          marginTop: '0.25rem'
                        }}>
                          biological units
                        </div>
                      </div>
                    </div>
                    
                    {/* Additional info */}
                    {(stats || validationStatus) && (
                      <div style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.5rem',
                        marginTop: '1rem',
                        fontSize: '0.8rem',
                        color: 'var(--text-light)'
                      }}>
                        {stats?.last_modified && (
                          <div>
                            Last updated: {new Date(stats.last_modified).toLocaleDateString()}
                          </div>
                        )}
                        {validationStatus && validationStatus.has_latest_archive && (
                          <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.5rem'
                          }}>
                            {validationStatus.validation_status === 'completed' ? (
                              validationStatus.is_valid ? (
                                <CheckCircle size={14} style={{ color: 'var(--success)' }} />
                              ) : (
                                <XCircle size={14} style={{ color: 'var(--error)' }} />
                              )
                            ) : validationStatus.validation_status === 'pending' || validationStatus.validation_status === 'running' ? (
                              <Activity size={14} style={{ color: 'var(--warning)' }} />
                            ) : (
                              <Activity size={14} style={{ color: 'var(--text-light)' }} />
                            )}
                            Validation: {
                              validationStatus.validation_status === 'completed' 
                                ? (validationStatus.is_valid ? 'Valid' : 'Invalid')
                                : validationStatus.validation_status === 'pending' 
                                  ? 'Pending'
                                  : validationStatus.validation_status === 'running'
                                    ? 'Running'
                                    : validationStatus.validation_status || 'Not validated'
                            }
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
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