// Theme variables using CSS variables approach
export const themeVariables = {
  light: {
    '--primary': '#2563eb',
    '--primary-rgb': '37, 99, 235',
    '--success': '#16a34a',
    '--error': '#dc2626',
    '--error-rgb': '220, 38, 38',
    '--warning': '#ea580c',
    '--info': '#0891b2',
    '--background': '#f8fafc',      // page background
    '--card-bg': '#ffffff',         // main card/container background
    '--card-footer-bg': '#f8fafc',
    '--subtle-bg': '#f1f5f9',       // smaller sub-panels or highlight sections
    '--subtle-btn-bg': '#ffffff',
    '--text': '#1e293b',
    '--text-light': '#64748b',
    '--border': '#e2e8f0',
    // Professional dashboard colors
    '--neutral-primary': '#475569',     // Most important metrics
    '--neutral-secondary': '#64748b',   // Secondary metrics  
    '--neutral-tertiary': '#94a3b8',    // Supporting metrics
    '--neutral-subtle': '#cbd5e1',      // Least critical metrics
    '--success-professional': '#059669', // Muted success indicator
    '--performance-indicator': '#d97706', // Muted performance indicator
    '--neutral-icon-bg': '#f1f5f9',     // Subtle icon backgrounds
  },
  dark: {
    '--primary': '#3b82f6',
    '--primary-rgb': '59, 130, 246',
    '--success': '#22c55e',
    '--error': '#ef4444',
    '--error-rgb': '239, 68, 68',
    '--warning': '#f97316',
    '--info': '#0891b2',
    '--background': '#1e293b',
    '--card-bg': '#273444',
    '--card-footer-bg': '#233042',
    '--subtle-bg': '#2f3e4e',
    '--subtle-btn-bg': '#273444',
    '--text': '#f8fafc',
    '--text-light': '#cbd5e1',
    '--border': '#3b4a63',
    // Professional dashboard colors (dark theme)
    '--neutral-primary': '#64748b',       // Lighter in dark theme
    '--neutral-secondary': '#475569',     // Medium in dark theme
    '--neutral-tertiary': '#334155',      // Darker in dark theme  
    '--neutral-subtle': '#1e293b',        // Darkest in dark theme
    '--success-professional': '#10b981',  // Brighter success for dark
    '--performance-indicator': '#f59e0b', // Brighter amber for dark
    '--neutral-icon-bg': '#2d3748',       // Subtle dark icon backgrounds
  }
};

// Apply theme function for components to use
export const applyTheme = (isDarkTheme) => {
  const theme = isDarkTheme ? themeVariables.dark : themeVariables.light;
  Object.entries(theme).forEach(([property, value]) => {
    document.documentElement.style.setProperty(property, value);
  });
};
