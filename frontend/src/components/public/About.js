import React from 'react';

const About = () => {
  return (
    <div style={{
      padding: '2rem',
      maxWidth: '800px',
      margin: '0 auto',
      lineHeight: '1.6',
    }}>
      <h1 style={{
        fontSize: '2rem',
        fontWeight: 700,
        marginBottom: '2rem',
        color: 'var(--text)',
      }}>
        About GFBio Data Portal
      </h1>
      
      <div style={{
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.75rem',
        padding: '2rem',
        marginBottom: '2rem',
        border: '1px solid var(--border)',
      }}>
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: 600,
          marginBottom: '1rem',
          color: 'var(--text)',
        }}>
          Scientific Dataset Management Platform
        </h2>
        
        <p style={{
          color: 'var(--text-light)',
          marginBottom: '1rem',
        }}>
          The GFBio (German Federation for Biological Data) Aggregator is a comprehensive 
          platform designed to catalog and manage scientific datasets from various data providers. 
          Our mission is to facilitate the discovery, access, and integration of biological data 
          for research and scientific collaboration.
        </p>
        
        <h3 style={{
          fontSize: '1.25rem',
          fontWeight: 600,
          marginTop: '1.5rem',
          marginBottom: '1rem',
          color: 'var(--text)',
        }}>
          Key Features
        </h3>
        
        <ul style={{
          color: 'var(--text-light)',
          paddingLeft: '1.5rem',
          marginBottom: '1rem',
        }}>
          <li style={{ marginBottom: '0.5rem' }}>
            Comprehensive dataset cataloging and metadata management
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            Data provider registration and management
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            ABCD (Access to Biological Collection Data) XML validation
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            Statistical analysis and reporting tools
          </li>
          <li style={{ marginBottom: '0.5rem' }}>
            RESTful API for system integration
          </li>
        </ul>
        
        <h3 style={{
          fontSize: '1.25rem',
          fontWeight: 600,
          marginTop: '1.5rem',
          marginBottom: '1rem',
          color: 'var(--text)',
        }}>
          Technology Stack
        </h3>
        
        <p style={{
          color: 'var(--text-light)',
          marginBottom: '1rem',
        }}>
          Built with modern web technologies including FastAPI backend with PostgreSQL database,
          React frontend with responsive design, and Docker containerization for scalable deployment.
        </p>
      </div>
      
      <div style={{
        backgroundColor: 'var(--subtle-bg)',
        borderRadius: '0.5rem',
        padding: '1.5rem',
        textAlign: 'center',
        border: '1px solid var(--border)',
      }}>
        <p style={{
          color: 'var(--text-light)',
          margin: 0,
          fontSize: '0.875rem',
        }}>
          For more information about GFBio and our data services, please visit our main website
          or contact our support team.
        </p>
      </div>
    </div>
  );
};

export default About;