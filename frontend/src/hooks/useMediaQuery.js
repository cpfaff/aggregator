import { useState, useEffect } from 'react';

/**
 * Custom hook for responsive design using CSS media queries
 * @param {string} query - Media query string (e.g., '(max-width: 575px)')
 * @returns {boolean} - Whether the media query currently matches
 */
export const useMediaQuery = (query) => {
  const [matches, setMatches] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.matchMedia(query).matches;
    }
    return false;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia(query);
    const handler = (event) => setMatches(event.matches);

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handler);
      return () => mediaQuery.removeEventListener('change', handler);
    }
    // Legacy browsers
    mediaQuery.addListener(handler);
    return () => mediaQuery.removeListener(handler);
  }, [query]);

  return matches;
};

// Convenience hooks with standard breakpoints
export const useIsMobile = () => useMediaQuery('(max-width: 575px)');
export const useIsSmallTablet = () => useMediaQuery('(min-width: 576px) and (max-width: 767px)');
export const useIsTablet = () => useMediaQuery('(min-width: 576px) and (max-width: 991px)');
export const useIsDesktop = () => useMediaQuery('(min-width: 992px)');
export const useIsLargeDesktop = () => useMediaQuery('(min-width: 1200px)');

// Check if we're below the tablet breakpoint (for hamburger menu)
export const useIsMobileOrSmallTablet = () => useMediaQuery('(max-width: 767px)');

/**
 * Combined hook for responsive grid layouts
 * Returns viewport state and a helper function for grid columns
 */
export const useResponsiveGrid = () => {
  const isMobile = useIsMobile();
  const isTablet = useIsTablet();
  const isDesktop = useIsDesktop();

  /**
   * Get responsive grid-template-columns value
   * @param {number} defaultMin - Minimum column width for desktop (default 300)
   * @returns {string} - CSS grid-template-columns value
   */
  const getGridColumns = (defaultMin = 300) => {
    if (isMobile) return '1fr';
    if (isTablet) return 'repeat(2, 1fr)';
    return `repeat(auto-fill, minmax(min(100%, ${defaultMin}px), 1fr))`;
  };

  return { isMobile, isTablet, isDesktop, getGridColumns };
};

export default useMediaQuery;
