/**
 * Statistics API service utilities
 * Provides functions to interact with the statistics endpoints
 */
import { apiRequest, API_BASE, API_VERSION, fetchWithTimeout, parseErrorResponse } from './apiUtils';

/**
 * Public statistics API calls (no authentication required)
 */
export const publicStatsApi = {
  /**
   * Get public registry overview
   * @returns {Promise<Object>} Overview statistics
   */
  getOverview: async (options = {}) => {
    const response = await fetchWithTimeout(`${API_BASE}${API_VERSION}/statistics/overview`, options);
    if (!response.ok) {
      throw await parseErrorResponse(response);
    }
    return response.json();
  },

  /**
   * Get timeline data
   * @param {Object} params - Timeline parameters
   * @returns {Promise<Object>} Timeline data
   */
  getTimeline: async (params = {}, options = {}) => {
    const queryParams = new URLSearchParams({
      period: params.period || 'daily',
      months: params.months || 1
    });
    const response = await fetchWithTimeout(`${API_BASE}${API_VERSION}/statistics/timeline?${queryParams}`, options);
    if (!response.ok) {
      throw await parseErrorResponse(response);
    }
    return response.json();
  },

  /**
   * Get provider statistics
   * @returns {Promise<Array>} Provider statistics
   */
  getProviders: async (options = {}) => {
    const response = await fetchWithTimeout(`${API_BASE}${API_VERSION}/statistics/providers`, options);
    if (!response.ok) {
      throw await parseErrorResponse(response);
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
   * Get provider datasets timeline
   * @param {number} providerId - Provider ID
   * @param {Object} params - Query parameters
   * @param {Function} onTokenExpired - Token expiration handler
   * @returns {Promise<Object>} Provider datasets timeline data
   */
  getProviderDatasetsTimeline: async (providerId, params, onTokenExpired) => {
    const queryParams = new URLSearchParams({
      period: params.period || 'monthly',
      months: params.months || 12
    });

    const response = await apiRequest(
      `/statistics/providers/${providerId}/datasets-timeline?${queryParams}`,
      {},
      onTokenExpired
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch provider ${providerId} datasets timeline: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Get provider biological units timeline
   * @param {number} providerId - Provider ID
   * @param {Object} params - Query parameters
   * @param {Function} onTokenExpired - Token expiration handler
   * @returns {Promise<Object>} Provider biological units timeline data
   */
  getProviderBiologicalUnitsTimeline: async (providerId, params, onTokenExpired) => {
    const queryParams = new URLSearchParams({
      period: params.period || 'daily',
      limit: params.limit || 30,
      ...(params.startDate && { start_date: params.startDate }),
      ...(params.endDate && { end_date: params.endDate })
    });

    const response = await apiRequest(
      `/statistics/providers/${providerId}/biological-units-timeline?${queryParams}`,
      {},
      onTokenExpired
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch provider ${providerId} biological units timeline: ${response.status}`);
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
  },

  /**
   * Get multi-provider biological units timeline (all providers as separate lines)
   * @param {Object} params - Query parameters
   * @param {Function} onTokenExpired - Token expiration handler
   * @returns {Promise<Object>} Multi-provider biological units timeline data
   */
  getMultiProviderBiologicalUnits: async (params, onTokenExpired) => {
    const queryParams = new URLSearchParams({
      period: params.period || 'daily',
      limit: params.limit || 30,
      ...(params.startDate && { start_date: params.startDate }),
      ...(params.endDate && { end_date: params.endDate })
    });

    const response = await apiRequest(
      `/statistics/multi-provider-biological-units?${queryParams}`,
      {},
      onTokenExpired
    );
    if (!response.ok) {
      throw new Error(`Failed to fetch multi-provider biological units: ${response.status}`);
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
   * Format multi-provider time-series data for charts
   * @param {Array} dataPoints - Raw multi-provider data points
   * @returns {Array} Formatted data for multi-line charts
   */
  formatMultiProviderTimeSeriesForChart: (dataPoints) => {
    return dataPoints.map(point => ({
      ...point,
      date: new Date(point.date).toLocaleDateString(),
      fullDate: point.date
    }));
  },

  /**
   * Read any statistics timeline response into one canonical chart series (REQ-SH-TL-3).
   *
   * Resolves the per-endpoint container key in ONE place so call sites never branch
   * on it: a narrow time series ({ date, value }) lives under `data_points`
   * (TimeSeriesResponse) or is passed as a bare array (a GrowthMetrics sub-timeline);
   * the multi-provider wide-row payload lives under `series` (REQ-SH-TL-2). Returns a
   * chart-ready array; [] when no recognised series is present.
   *
   * @param {Object|Array} response - A statistics timeline response or a points array
   * @returns {Array} Chart-ready series points
   */
  toChartSeries: (response) => {
    if (!response) return [];
    if (Array.isArray(response)) {
      return statsUtils.formatTimeSeriesForChart(response);
    }
    if (Array.isArray(response.series)) {
      return statsUtils.formatMultiProviderTimeSeriesForChart(response.series);
    }
    if (Array.isArray(response.data_points)) {
      return statsUtils.formatTimeSeriesForChart(response.data_points);
    }
    return [];
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

const statisticsApi = {
  publicStatsApi,
  authStatsApi,
  statsUtils
};

export default statisticsApi;
