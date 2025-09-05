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
    },
    sectionTitle: {
      fontSize: '1.5rem',
      fontWeight: 600,
      marginBottom: '1.5rem',
      color: 'var(--text)',
    },
    text: {
      color: 'var(--text-light)',
      lineHeight: '1.7',
      marginBottom: '1rem',
    },
    subsectionTitle: {
      fontSize: '1.2rem',
      fontWeight: 600,
      color: 'var(--text)',
      marginBottom: '0.75rem',
      marginTop: '2rem',
    },
    link: {
      color: 'var(--primary)',
      textDecoration: 'none',
    },
    contactSection: {
      marginTop: '2.5rem',
      paddingTop: '2rem',
      borderTop: '1px solid var(--border)',
    },
    contactGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
      gap: '2rem',
      marginTop: '1rem',
    },
    contactItem: {
      marginBottom: '1rem',
    },
    contactLabel: {
      display: 'block',
      color: 'var(--text)',
      marginBottom: '0.5rem',
      fontWeight: 600,
    },
    contactText: {
      margin: '0.25rem 0',
      color: 'var(--text-light)',
      lineHeight: '1.5',
    },
    textMuted: {
      fontSize: '0.9rem',
      color: 'var(--text-light)',
      display: 'block',
      marginTop: '0.25rem',
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
        </div>
      ) : (
        <header style={styles.heroSection}>
          <h1 style={styles.heroTitle}>GFBio Data Provider Manager</h1>
          <p style={styles.heroSubtitle}>
            Central registry for institutional biodiversity data providers in GFBio's research infrastructure
          </p>
        </header>
      )}

      {/* Single Content Card */}
      <section style={styles.contentCard}>
        <h2 style={styles.sectionTitle}>About This Service</h2>
        
        <p style={styles.text}>
          The Data Provider Manager serves as the central registry for
          institutional providers to enter the GFBio Search and Harvesting
          Infrastructure (SAHIS). It is coordinating biodiversity data from
          certified data centers and partner institutions across Germany
          following FAIR data principles.
        </p>
        
        <p style={styles.text}>
          This service is operated by <strong>GFBio e.V.</strong> (Gesellschaft
          für Biologische Daten e.V.) as part of
          <strong>NFDI4Biodiversity</strong> and Germany's National Research
          Data Infrastructure, supporting the biological sciences community
          with professional data management infrastructure.
        </p>

        <p style={styles.text}>
          This platform is designed for data centers, scientific societies, and
          institutions managing biological collections data. When you are interested in 
          publishing data with us get in touch with us.
        </p>
        
        <p style={styles.text}>
          <strong>Note for Individual Researchers:</strong> To search and access biodiversity data, 
          please use the public <a href="https://search.gfbio.org" target="_blank" rel="noopener noreferrer" style={styles.link}>
          GFBio Search Portal</a> which provides access to all registered collections.
        </p>

        {/* Contact & Legal Section within the same card */}
        <div style={styles.contactSection}>
          <h3 style={styles.subsectionTitle}>Contact & Legal Information</h3>
          
          <div style={styles.contactGrid}>
            <div style={styles.contactItem}>
              <strong style={styles.contactLabel}>GFBio e.V.</strong>
              <p style={styles.contactText}>
                Unicom 2, Haus 2-4<br/>
                Mary-Somerville-Str. 2<br/>
                28359 Bremen<br/>
                Germany
              </p>
              <span style={styles.textMuted}>
                Website: <a href="https://www.gfbio.org" target="_blank" rel="noopener noreferrer" style={styles.link}>www.gfbio.org</a><br/>
                Email: <a href="mailto:info@gfbio.org" style={styles.link}>info@gfbio.org</a>
              </span>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default About;
