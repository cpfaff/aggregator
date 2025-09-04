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
    
    /* Responsive utilities */
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
    }
    
    /* Stabilize navigation transitions */
    nav a {
      will-change: color, transform;
    }
    
    html { 
      margin: 0; 
      padding: 0;
      scrollbar-width: thin;
      scrollbar-color: var(--border) var(--card-bg);
      overflow-y: scroll; /* Always show scrollbar to prevent layout shift */
    }
    body {
      margin: 0;
      padding: 0;
    }
    * { box-sizing: border-box; }
    button:focus, input:focus, textarea:focus, select:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
    }
    input:disabled, textarea:disabled, select:disabled, button:disabled {
      background-color: var(--subtle-bg);
      cursor: not-allowed;
    }
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
  `;
  document.head.appendChild(style);
};
