// Add global styles with CSS variables support
export const addGlobalStyles = () => {
  const style = document.createElement('style');
  style.innerHTML = `
    @keyframes spin {
      from { transform: rotate(0deg); }
      to { transform: rotate(360deg); }
    }
    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }
    @keyframes slideInUp {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.5; }
    }

    /* Animation classes for statistics components */
    .fade-in {
      animation: fadeIn 0.3s ease-out;
    }
    .slide-in-up {
      animation: slideInUp 0.4s ease-out;
    }

    /* Prevent layout shifts */
    .content-container {
      min-height: calc(100vh - 200px);
      opacity: 1;
      transition: opacity 0.15s ease-out;
      max-width: 100vw;
      overflow-x: hidden;
    }

    /* Stabilize navigation transitions */
    nav a {
      will-change: color, transform;
    }

    /* ===== Base Styles ===== */
    html {
      margin: 0;
      padding: 0;
      scrollbar-width: thin;
      scrollbar-color: var(--border) var(--card-bg);
      overflow-y: scroll;
      overflow-x: hidden;
      max-width: 100vw;
    }
    body {
      margin: 0;
      padding: 0;
      overflow-x: hidden;
      max-width: 100vw;
    }
    * { box-sizing: border-box; }

    /* Focus and disabled states */
    button:focus, input:focus, textarea:focus, select:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }
    input:disabled, textarea:disabled, select:disabled, button:disabled {
      background-color: var(--subtle-bg);
      cursor: not-allowed;
    }

    /* Scrollbar styling */
    html::-webkit-scrollbar,
    body::-webkit-scrollbar,
    .modal-content-scrollable::-webkit-scrollbar {
      width: 6px;
    }
    html::-webkit-scrollbar-track,
    body::-webkit-scrollbar-track,
    .modal-content-scrollable::-webkit-scrollbar-track {
      background: var(--card-bg);
    }
    html::-webkit-scrollbar-thumb,
    body::-webkit-scrollbar-thumb,
    .modal-content-scrollable::-webkit-scrollbar-thumb {
      background-color: var(--border);
      border-radius: 3px;
    }
    html::-webkit-scrollbar-thumb:hover,
    body::-webkit-scrollbar-thumb:hover,
    .modal-content-scrollable::-webkit-scrollbar-thumb:hover {
      background-color: var(--text-light);
    }

    /* ===== Mobile Navigation ===== */
    .mobile-nav-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background-color: rgba(0, 0, 0, 0.5);
      z-index: 999;
      opacity: 0;
      visibility: hidden;
      transition: opacity 0.3s ease, visibility 0.3s ease;
    }
    .mobile-nav-overlay.open {
      opacity: 1;
      visibility: visible;
    }
    .mobile-nav-panel {
      position: fixed;
      top: 0;
      right: 0;
      width: min(300px, 80vw);
      height: 100vh;
      background-color: var(--card-bg);
      transform: translateX(100%);
      transition: transform 0.3s ease;
      overflow-y: auto;
      z-index: 1000;
      box-shadow: -4px 0 20px rgba(0, 0, 0, 0.15);
    }
    .mobile-nav-overlay.open .mobile-nav-panel {
      transform: translateX(0);
    }

    /* Cards should not overflow their containers */
    [class*='card'] {
      max-width: 100%;
      word-wrap: break-word;
      overflow-wrap: break-word;
    }

    /* Container padding utility */
    .responsive-container {
      padding: clamp(1rem, 3vw, 2rem);
    }

    /* Smooth transitions for layout changes */
    .responsive-grid {
      transition: grid-template-columns 0.3s ease;
    }

    /* ===== Touch Target Links ===== */
    /* Invisible 44x44px hit area for WCAG 2.5.5 compliance without visual bloat */
    .touch-target-link {
      position: relative;
      display: inline-flex;
      align-items: center;
      padding: 4px 0;
      text-decoration: none;
      transition: color 0.2s ease;
    }
    .touch-target-link::before {
      content: '';
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      min-width: 44px;
      min-height: 44px;
      width: 100%;
    }

    /* ===== Responsive Breakpoints ===== */

    /* Mobile: < 576px */
    @media (max-width: 575px) {
      h1 {
        font-size: clamp(1.5rem, 5vw, 2.25rem);
      }
      h2 {
        font-size: clamp(1.25rem, 4vw, 1.75rem);
      }
      h3 {
        font-size: clamp(1rem, 3vw, 1.25rem);
      }
    }

    /* Tablet and below: < 768px */
    @media (max-width: 767px) {
      /* Navigation touch targets */
      nav a {
        min-height: 44px;
        padding: 0.75rem 1rem;
        display: flex;
        align-items: center;
      }

      /* Visibility utilities */
      .hide-mobile {
        display: none !important;
      }
    }

    /* Desktop: >= 768px */
    @media (min-width: 768px) {
      .hide-desktop {
        display: none !important;
      }
    }

    /* Legacy responsive utilities (kept for backwards compatibility) */
    @media (max-width: 768px) {
      .stats-grid {
        grid-template-columns: 1fr !important;
      }
      .chart-grid {
        grid-template-columns: 1fr !important;
      }
      .stats-card {
        min-width: unset !important;
      }
    }
  `;
  document.head.appendChild(style);
};
