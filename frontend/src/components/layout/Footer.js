import React from 'react';

const Footer = () => {
  return (
    <footer style={{
      backgroundColor: 'var(--card-bg)',
      borderTop: '1px solid var(--border)',
      padding: '16px',
      textAlign: 'center',
      color: 'var(--text-light)',
      transition: 'background-color 0.3s, border-color 0.3s',
    }}>
      <p style={{ margin: 0, fontSize: '0.875rem' }}>
        2025 Data Provider Manager. All rights reserved.
      </p>
    </footer>
  );
};

export default Footer;
