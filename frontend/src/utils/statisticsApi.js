/**
 * Statistics API service utilities
 * Provides functions to interact with the statistics endpoints
 */
import { apiRequest, API_BASE, API_VERSION } from './apiUtils';

/**
 * Public statistics API calls (no authentication required)
 */
export const publicStatsApi = {
  /**
   * Get public registry overview
   * @returns {Promise<Object>} Overview statistics
   */
  getOverview: async () => {
    const response = await fetch(`${API_BASE}${API_VERSION}/public-statistics/overview`);
    if (!response.ok) {
      throw new Error(`Failed to fetch public overview: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Get quality metrics
   * @returns {Promise<Object>} Quality metrics
   */
  getQuality: async () => {
    const response = await fetch(`${API_BASE}${API_VERSION}/public-statistics/quality`);
    if (!response.ok) {
      throw new Error(`Failed to fetch quality metrics: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Get timeline data
   * @param {Object} params - Timeline parameters
   * @returns {Promise<Object>} Timeline data
   */
  getTimeline: async (params = {}) => {
    const queryParams = new URLSearchParams({
      period: params.period || 'daily',
      months: params.months || 1
    });
    const response = await fetch(`${API_BASE}${API_VERSION}/public-statistics/timeline?${queryParams}`);
    if (!response.ok) {
      throw new Error(`Failed to fetch timeline: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Get provider statistics
   * @returns {Promise<Array>} Provider statistics
   */
  getProviders: async () => {
    const response = await fetch(`${API_BASE}${API_VERSION}/public-statistics/providers`);
    if (!response.ok) {
      throw new Error(`Failed to fetch provider stats: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Get recent dataset activity
   * @returns {Promise<Array>} Recent activity
   */
  getRecentActivity: async () => {
    const response = await fetch(`${API_BASE}${API_VERSION}/public-statistics/datasets/recent`);
    if (!response.ok) {
      throw new Error(`Failed to fetch recent activity: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Get registry health status
   * @returns {Promise<Object>} Health metrics
   */
  getHealth: async () => {
    const response = await fetch(`${API_BASE}${API_VERSION}/public-statistics/health`);
    if (!response.ok) {
      throw new Error(`Failed to fetch health status: ${response.status}`);
    }
    return response.json();
  }
};

/**
 * Authenticated statistics API calls
 */
export const authStatsApi = {
  /**
   * Get admin system overview
   * @param {Function} onTokenExpired - Token expiration handler
   * @returns {Promise<Object>} System overview
   */
  getOverview: async (onTokenExpired) => {
    const response = await apiRequest('/statistics/overview', {}, onTokenExpired);
    if (!response.ok) {
      throw new Error(`Failed to fetch admin overview: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Get provider-specific statistics
   * @param {number} providerId - Provider ID
   * @param {Function} onTokenExpired - Token expiration handler
   * @returns {Promise<Object>} Provider statistics
   */
  getProviderStats: async (providerId, onTokenExpired) => {
    const response = await apiRequest(`/statistics/providers/${providerId}`, {}, onTokenExpired);
    if (!response.ok) {
      throw new Error(`Failed to fetch provider ${providerId} stats: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Get dataset-specific statistics
   * @param {number} datasetId - Dataset ID
   * @param {Function} onTokenExpired - Token expiration handler
   * @returns {Promise<Object>} Dataset statistics
   */
  getDatasetStats: async (datasetId, onTokenExpired) => {
    const response = await apiRequest(`/statistics/datasets/${datasetId}`, {}, onTokenExpired);
    if (!response.ok) {
      throw new Error(`Failed to fetch dataset ${datasetId} stats: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Get time-series data
   * @param {Object} params - Query parameters
   * @param {Function} onTokenExpired - Token expiration handler
   * @returns {Promise<Object>} Time-series data
   */
  getTimeSeries: async (params, onTokenExpired) => {
    const queryParams = new URLSearchParams({
      metric_type: params.metricType,
      entity_type: params.entityType,
      period: params.period || 'daily',
      limit: params.limit || 30,
      ...(params.entityId && { entity_id: params.entityId }),
      ...(params.startDate && { start_date: params.startDate }),
      ...(params.endDate && { end_date: params.endDate })
    });

    const response = await apiRequest(
      `/statistics/time-series?${queryParams}`, 
      {}, 
      onTokenExpired
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch time-series data: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Get quality metrics (admin)
   * @param {Function} onTokenExpired - Token expiration handler
   * @returns {Promise<Object>} Quality metrics
   */
  getQualityMetrics: async (onTokenExpired) => {
    const response = await apiRequest('/statistics/quality', {}, onTokenExpired);
    if (!response.ok) {
      throw new Error(`Failed to fetch quality metrics: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Search statistics
   * @param {Object} params - Search parameters
   * @param {Function} onTokenExpired - Token expiration handler
   * @returns {Promise<Array>} Statistics search results
   */
  searchStats: async (params, onTokenExpired) => {
    const queryParams = new URLSearchParams({
      limit: params.limit || 10,
      offset: params.offset || 0,
      ...(params.metricTypes && { metric_types: params.metricTypes.join(',') }),
      ...(params.entityTypes && { entity_types: params.entityTypes.join(',') }),
      ...(params.entityIds && { entity_ids: params.entityIds.join(',') }),
      ...(params.periods && { periods: params.periods.join(',') }),
      ...(params.startDate && { start_date: params.startDate }),
      ...(params.endDate && { end_date: params.endDate })
    });

    const response = await apiRequest(
      `/statistics/search?${queryParams}`, 
      {}, 
      onTokenExpired
    );
    if (!response.ok) {
      throw new Error(`Failed to search statistics: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Trigger statistics collection
   * @param {string} targetDate - Optional target date (YYYY-MM-DD)
   * @param {Function} onTokenExpired - Token expiration handler
   * @returns {Promise<Object>} Collection status
   */
  triggerCollection: async (targetDate, onTokenExpired) => {
    const queryParams = targetDate ? `?target_date=${targetDate}` : '';
    const response = await apiRequest(
      `/statistics/collect${queryParams}`, 
      { method: 'POST' }, 
      onTokenExpired
    );
    if (!response.ok) {
      throw new Error(`Failed to trigger collection: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Trigger XML analysis
   * @param {Object} params - Analysis parameters
   * @param {Function} onTokenExpired - Token expiration handler
   * @returns {Promise<Object>} Analysis status
   */
  triggerXmlAnalysis: async (params, onTokenExpired) => {
    const queryParams = new URLSearchParams({
      batch_size: params.batchSize || 50,
      offset: params.offset || 0
    });

    const response = await apiRequest(
      `/statistics/analyze-xml?${queryParams}`, 
      { method: 'POST' }, 
      onTokenExpired
    );
    if (!response.ok) {
      throw new Error(`Failed to trigger XML analysis: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Get biological units timeline (system-wide aggregation)
   * @param {Object} params - Query parameters
   * @param {Function} onTokenExpired - Token expiration handler
   * @returns {Promise<Object>} Biological units timeline data
   */
  getBiologicalUnitsTimeline: async (params, onTokenExpired) => {
    const queryParams = new URLSearchParams({
      period: params.period || 'daily',
      limit: params.limit || 30,
      ...(params.startDate && { start_date: params.startDate }),
      ...(params.endDate && { end_date: params.endDate })
    });

    const response = await apiRequest(
      `/statistics/biological-units-timeline?${queryParams}`, 
      {}, 
      onTokenExpired
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch biological units timeline: ${response.status}`);
    }
    return response.json();
  }
};

/**
 * Utility functions for statistics data processing
 */
export const statsUtils = {
  /**
   * Format time-series data for charts
   * @param {Array} dataPoints - Raw time-series data points
   * @returns {Array} Formatted data for charts
   */
  formatTimeSeriesForChart: (dataPoints) => {
    return dataPoints.map(point => ({
      date: new Date(point.date).toLocaleDateString(),
      value: point.value,
      fullDate: point.date,
      ...point.extra_data
    }));
  },

  /**
   * Calculate percentage change
   * @param {number} current - Current value
   * @param {number} previous - Previous value
   * @returns {number} Percentage change
   */
  calculatePercentageChange: (current, previous) => {
    if (previous === 0) return current > 0 ? 100 : 0;
    return ((current - previous) / previous) * 100;
  },

  /**
   * Format large numbers with appropriate units
   * @param {number} value - Number to format
   * @returns {string} Formatted number
   */
  formatLargeNumber: (value) => {
    if (value >= 1000000) {
      return `${(value / 1000000).toFixed(1)}M`;
    } else if (value >= 1000) {
      return `${(value / 1000).toFixed(1)}K`;
    }
    return value.toString();
  },

  /**
   * Get color for metric type
   * @param {string} metricType - Metric type
   * @returns {string} Color value
   */
  getMetricColor: (metricType) => {
    const colorMap = {
      dataset_count: 'var(--primary)',
      provider_count: 'var(--success)',
      validation_success_rate: 'var(--primary)',
      xml_archive_count: 'var(--warning)',
      provider_dataset_count: 'var(--success)',
      provider_biological_units: 'var(--success)',
      biological_units_timeline: 'var(--success)'
    };
    return colorMap[metricType] || 'var(--text-light)';
  }
};

export default {
  publicStatsApi,
  authStatsApi,
  statsUtils
};