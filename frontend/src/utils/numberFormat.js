/**
 * Shared number formatting helpers.
 */

/**
 * Format a number with a compact K/M suffix (REQ-SH-FE-3).
 *
 * The single source for the `>= 1e6 -> M` / `>= 1e3 -> K` ladder that every chart
 * tick formatter reuses (discovery F-H: the identical ladder had been inlined and
 * had already drifted on decimal count). Values below 1000 are returned unchanged
 * (a raw number) so axis formatters keep their existing sub-1000 presentation.
 *
 * @param {number} value - the value to format
 * @param {Object} [options]
 * @param {number} [options.decimals=1] - fraction digits for the K/M suffix
 *   (integer-only axes pass 0)
 * @returns {string|number} a compact string for values >= 1000, else the raw value
 */
export function formatCompactNumber(value, { decimals = 1 } = {}) {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(decimals)}M`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(decimals)}K`;
  }
  return value;
}
