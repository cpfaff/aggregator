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
    html, body { 
      margin: 0; 
      padding: 0;
      scrollbar-width: thin;
      scrollbar-color: var(--border) var(--card-bg);
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
