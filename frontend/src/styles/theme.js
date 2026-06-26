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
    // Quality badge colors - green (good)
    '--badge-green-bg': 'rgba(22, 163, 74, 0.1)',
    '--badge-green-border': 'rgb(22, 163, 74)',
    '--badge-green-text': 'rgb(22, 163, 74)',
    // Quality badge colors - amber (warning)
    '--badge-amber-bg': 'rgba(217, 119, 6, 0.1)',
    '--badge-amber-border': 'rgb(217, 119, 6)',
    '--badge-amber-text': 'rgb(161, 98, 7)',
    // Quality badge colors - red (poor)
    '--badge-red-bg': 'rgba(220, 38, 38, 0.1)',
    '--badge-red-border': 'rgb(220, 38, 38)',
    '--badge-red-text': 'rgb(220, 38, 38)',
    // Ghost button colors (blue emphasis for primary actions)
    '--ghost-btn-text': 'rgb(37, 99, 235)',
    '--ghost-btn-border': 'rgb(191, 219, 254)',
    '--ghost-btn-hover-text': 'rgb(29, 78, 216)',
    '--ghost-btn-hover-border': 'rgb(37, 99, 235)',
    '--ghost-btn-hover-bg': 'rgba(37, 99, 235, 0.05)',
    // Section footer border
    '--section-footer-border': 'rgb(226, 232, 240)',
    // Stats icon color (muted gray for informational items)
    '--stats-icon': 'rgb(100, 116, 139)',
    // Skeleton loading placeholder (base = resting fill, highlight = shimmer sweep)
    '--skeleton-base': '#e2e8f0',
    '--skeleton-highlight': '#f4f6f9',
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
    // Quality badge colors - green (good)
    '--badge-green-bg': 'rgba(34, 197, 94, 0.15)',
    '--badge-green-border': 'rgb(34, 197, 94)',
    '--badge-green-text': 'rgb(34, 197, 94)',
    // Quality badge colors - amber (warning)
    '--badge-amber-bg': 'rgba(250, 204, 21, 0.15)',
    '--badge-amber-border': 'rgb(250, 204, 21)',
    '--badge-amber-text': 'rgb(253, 224, 71)',
    // Quality badge colors - red (poor)
    '--badge-red-bg': 'rgba(239, 68, 68, 0.15)',
    '--badge-red-border': 'rgb(239, 68, 68)',
    '--badge-red-text': 'rgb(252, 165, 165)',
    // Ghost button colors (blue emphasis for primary actions)
    '--ghost-btn-text': 'rgb(96, 165, 250)',
    '--ghost-btn-border': 'rgb(51, 65, 85)',
    '--ghost-btn-hover-text': 'rgb(147, 197, 253)',
    '--ghost-btn-hover-border': 'rgb(96, 165, 250)',
    '--ghost-btn-hover-bg': 'rgba(96, 165, 250, 0.1)',
    // Section footer border
    '--section-footer-border': 'rgb(51, 65, 85)',
    // Stats icon color (muted gray for informational items)
    '--stats-icon': 'rgb(148, 163, 184)',
    // Skeleton loading placeholder (base = resting fill, highlight = shimmer sweep)
    '--skeleton-base': '#334155',
    '--skeleton-highlight': '#475569',
  }
};

// Apply theme function for components to use
export const applyTheme = (isDarkTheme) => {
  const theme = isDarkTheme ? themeVariables.dark : themeVariables.light;
  Object.entries(theme).forEach(([property, value]) => {
    document.documentElement.style.setProperty(property, value);
  });
};
