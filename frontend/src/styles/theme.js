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
    '--background': '#f8fafc',
    '--card-bg': '#ffffff',
    '--card-footer-bg': '#f8fafc',
    '--subtle-bg': '#f1f5f9',
    '--subtle-btn-bg': '#ffffff',
    '--text': '#1e293b',
    '--text-light': '#64748b',
    '--border': '#e2e8f0',
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
  }
};

// Apply theme function for components to use
export const applyTheme = (isDarkTheme) => {
  const theme = isDarkTheme ? themeVariables.dark : themeVariables.light;
  Object.entries(theme).forEach(([property, value]) => {
    document.documentElement.style.setProperty(property, value);
  });
};
