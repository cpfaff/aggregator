/**
 * Date and time utility functions for formatting and displaying dates.
 */

/**
 * Format a date as a relative time string (e.g., "2 days ago", "3 hours ago")
 * or as an absolute date if too old.
 *
 * @param {string|Date} dateString - ISO date string or Date object
 * @returns {string} Formatted date string
 */
export function formatRelativeTime(dateString) {
  if (!dateString) {
    return 'Never';
  }

  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  // Just now (< 1 minute)
  if (diffSec < 60) {
    return 'Just now';
  }

  // Minutes ago (< 1 hour)
  if (diffMin < 60) {
    return `${diffMin} ${diffMin === 1 ? 'minute' : 'minutes'} ago`;
  }

  // Hours ago (< 24 hours)
  if (diffHour < 24) {
    return `${diffHour} ${diffHour === 1 ? 'hour' : 'hours'} ago`;
  }

  // Days ago (< 7 days)
  if (diffDay < 7) {
    return `${diffDay} ${diffDay === 1 ? 'day' : 'days'} ago`;
  }

  // Weeks ago (< 30 days)
  if (diffDay < 30) {
    const weeks = Math.floor(diffDay / 7);
    return `${weeks} ${weeks === 1 ? 'week' : 'weeks'} ago`;
  }

  // Months ago (< 365 days)
  if (diffDay < 365) {
    const months = Math.floor(diffDay / 30);
    return `${months} ${months === 1 ? 'month' : 'months'} ago`;
  }

  // For dates older than a year, show the absolute date
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

/**
 * Format a date for a chart axis tick (REQ-SH-FE-4/5).
 *
 * The single shared helper for compact chart-axis dates. Pins an explicit locale
 * (default 'en-US') rather than relying on the runtime default, so axis labels do
 * not vary by browser/server locale (discovery F-I; the de_DE default separators
 * gotcha). Replaces the inline, locale-default `new Date(d).toLocaleDateString()`
 * copies in the statistics chart formatters.
 *
 * @param {string|Date} value - ISO date string or Date object
 * @param {string} [locale='en-US'] - explicit locale
 * @returns {string} Short date string in the given locale
 */
export function formatChartDate(value, locale = 'en-US') {
  return new Date(value).toLocaleDateString(locale);
}

/**
 * Format a date as an absolute date and time.
 *
 * @param {string|Date} dateString - ISO date string or Date object
 * @returns {string} Formatted date and time string
 */
export function formatAbsoluteDateTime(dateString) {
  if (!dateString) {
    return 'Never';
  }

  const date = new Date(dateString);
  return date.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}
