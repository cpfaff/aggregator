import React from 'react';
import Breadcrumbs from '../ui/Breadcrumbs';

const About = ({ currentUser }) => {
  const breadcrumbItems = [
    { label: 'Home', onClick: () => {} },
    { label: 'About', onClick: null }
  ];

  // Styles
  const styles = {
    container: {
      flexGrow: 1,
      padding: currentUser ? '2rem 1rem 4rem' : '3rem 1rem 4rem',
      maxWidth: '1200px',
      margin: '0 auto',
      width: '100%',
      minHeight: '60vh',
    },
    pageHeader: {
      marginBottom: '2rem',
      marginTop: '1rem',
    },
    pageHeaderTitle: {
      fontSize: '1.5rem',
      fontWeight: 600,
      color: 'var(--text)',
      marginBottom: '0.5rem',
    },
    pageHeaderSubtitle: {
      fontSize: '1rem',
      color: 'var(--text-light)',
      margin: 0,
      lineHeight: '1.5',
    },
    heroSection: {
      textAlign: 'center',
      marginBottom: '3rem',
      padding: '2rem 0',
    },
    heroTitle: {
      fontSize: 'clamp(2rem, 4vw, 2.75rem)',
      fontWeight: 700,
      marginBottom: '1rem',
      color: 'var(--text)',
      letterSpacing: '-0.025em',
    },
    heroSubtitle: {
      fontSize: 'clamp(1rem, 2.5vw, 1.25rem)',
      color: 'var(--text-light)',
      maxWidth: '600px',
      margin: '0 auto',
      lineHeight: '1.6',
    },
    contentCard: {
      backgroundColor: 'var(--card-bg)',
      borderRadius: '1rem',
      padding: '2.5rem',
      border: '1px solid var(--border)',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
      marginBottom: '1.5rem',
    },
    sectionTitle: {
      fontSize: '1.25rem',
      fontWeight: 600,
      marginBottom: '1.5rem',
      color: 'var(--text)',
    },
    text: {
      color: 'var(--text-light)',
      lineHeight: '1.7',
      marginBottom: '1rem',
    },
    calloutBox: {
      backgroundColor: 'rgba(59, 130, 246, 0.08)',
      borderLeft: '4px solid var(--primary)',
      padding: '1rem 1.25rem',
      borderRadius: '0 8px 8px 0',
      marginTop: '1.5rem',
      marginBottom: '0',
    },
    calloutContent: {
      display: 'flex',
      alignItems: 'flex-start',
      gap: '0.75rem',
    },
    calloutIcon: {
      flexShrink: 0,
      width: '20px',
      height: '20px',
      color: 'var(--primary)',
      marginTop: '2px',
    },
    calloutText: {
      color: 'var(--text)',
      lineHeight: '1.6',
      margin: 0,
      fontSize: '0.95rem',
    },
    link: {
      color: 'var(--primary)',
      textDecoration: 'none',
    },
  };

  return (
    <div style={styles.container}>
      {/* Breadcrumbs - only show when logged in */}
      {currentUser && <Breadcrumbs items={breadcrumbItems} />}
      
      {/* Header Section */}
      {currentUser ? (
        <div style={styles.pageHeader}>
          <h2 style={styles.pageHeaderTitle}>About</h2>
          <p style={styles.pageHeaderSubtitle}>
            Learn about the Data Provider Manager and the organization behind it.
          </p>
        </div>
      ) : (
        <header style={styles.heroSection}>
          <h1 style={styles.heroTitle}>GFBio Data Provider Manager</h1>
          <p style={styles.heroSubtitle}>
            Central registry for institutional biodiversity data providers in GFBio's research infrastructure
          </p>
        </header>
      )}

      {/* Main Content Card */}
      <section style={styles.contentCard}>
        <p style={styles.text}>
          The Data Provider Manager serves as the central registry for
          institutional providers to enter the GFBio Search and Harvesting
          Infrastructure (SAHIS). It is coordinating biodiversity data from
          certified data centers and partner institutions across Germany
          following FAIR data principles.
        </p>

        <p style={styles.text}>
          This service is operated by <strong>GFBio e.V.</strong> (Gesellschaft
          für Biologische Daten e.V.) as part of <strong>NFDI4Biodiversity</strong> and Germany's National Research
          Data Infrastructure, supporting the biological sciences community
          with professional data management infrastructure.
        </p>

        <p style={{...styles.text, marginBottom: 0}}>
          This platform is designed for data centers, scientific societies, and
          institutions managing biological collections data. When you are interested in
          publishing data with us get in touch with us.
        </p>

        {/* Callout box for individual researchers */}
        <div style={styles.calloutBox}>
          <div style={styles.calloutContent}>
            <svg style={styles.calloutIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p style={styles.calloutText}>
              <strong>Note for Individual Researchers:</strong> To search and access biodiversity data,
              please use the public <a href="https://search.gfbio.org" target="_blank" rel="noopener noreferrer" style={styles.link}>
              GFBio Search Portal</a> which provides access to all registered collections.
            </p>
          </div>
        </div>
      </section>

    </div>
  );
};

export default About;
