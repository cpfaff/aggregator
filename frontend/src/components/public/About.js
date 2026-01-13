import React from 'react';
import Breadcrumbs from '../ui/Breadcrumbs';
import MermaidDiagram from '../ui/MermaidDiagram';

const About = ({ currentUser, isDarkTheme }) => {
  const breadcrumbItems = [
    { label: 'Home', onClick: () => {} },
    { label: 'About', onClick: null }
  ];

  // Current architecture diagram
  const currentArchitectureDiagram = `
flowchart LR
    subgraph Providers ["Data Providers"]
        direction TB
        bioCase1("BioCASe Provider")
        bioCase2("BioCASe Provider")
        bioCase3("...")
        oaiPMH1("OAI-PMH Provider")
        oaiPMH2("OAI-PMH Provider")
        oaiPMH3("...")
        gbifProvider("DwC Provider")
    end

    Aggregator("Aggregator<br/><i>registration, validation, statistics</i>")
    panFMPHarvester("panFMP Harvester<br/><i>registration, validation, etl</i>")
    bmsHarvester("BMS Harvester<br/><i>etl</i>")
    gbifHarvester("GBIF Harvester<br/><i>registration, etl</i>")

    subgraph Search ["GFBio Search"]
        gfbioSearch("Search Portal<br/><i>interface, api</i>")
    end

    subgraph Storage ["Storage"]
        elasticsearchIndex[("Elasticsearch Index")]
    end

    bioCase1 & bioCase2 & bioCase3 --- Aggregator
    oaiPMH1 & oaiPMH2 & oaiPMH3 --- panFMPHarvester
    gbifProvider --- gbifHarvester
    Aggregator --- bmsHarvester
    bmsHarvester --- panFMPHarvester
    gbifHarvester --- elasticsearchIndex
    panFMPHarvester --- elasticsearchIndex
    gfbioSearch --- elasticsearchIndex
`;

  // Future architecture diagram - DCAT v3 migration
  const futureArchitectureDiagram = `
flowchart LR
    subgraph Providers ["Data Providers"]
        bioCase("BioCASe")
        oaiPMH("OAI-PMH")
        dwcProvider("Darwin Core")
        genericProvider("...")
    end

    subgraph Registry ["Registration Layer"]
        aggregator("Universal Catalog<br/><i>protocol-agnostic, semantic metadata</i>")
    end

    subgraph Harvesting ["Harvesting Pipeline"]
        harvest("Unified Harvesting<br/><i>transformation, enrichment, validation</i>")
    end

    subgraph Storage ["Storage Layer"]
        openSearch[("OpenSearch<br/>(Search Index)")]
    end

    subgraph Federation ["Federation Network"]
        nfdi("NFDI Partners")
        euPortals("European Portals")
        otherPartners("...")
    end

    subgraph Access ["Access Layer"]
        api("API")
        search("Search Portal")
        tools("Research Tools")
    end

    %% Connections
    bioCase & oaiPMH & dwcProvider & genericProvider --> aggregator
    aggregator --> harvest
    harvest --> openSearch

    openSearch --> api
    api --> search
    api --> tools

    aggregator -.-> nfdi
    aggregator -.-> euPortals
    aggregator -.-> otherPartners
`;

  // Styles
  const styles = {
    container: {
      flexGrow: 1,
      padding: '2rem 1rem 4rem',
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
      maxWidth: '700px',
      margin: '0 auto',
      lineHeight: '1.6',
    },
    contentCard: {
      backgroundColor: 'var(--card-bg)',
      borderRadius: '1rem',
      padding: '2rem',
      border: '1px solid var(--border)',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
      marginBottom: '1.5rem',
    },
    cardHeader: {
      display: 'flex',
      alignItems: 'center',
      gap: '0.75rem',
      marginBottom: '1.5rem',
      paddingBottom: '1rem',
      borderBottom: '1px solid var(--border)',
    },
    cardIcon: {
      width: '36px',
      height: '36px',
      borderRadius: '0.5rem',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      flexShrink: 0,
    },
    sectionTitle: {
      fontSize: '1.25rem',
      fontWeight: 600,
      margin: 0,
      color: 'var(--text)',
    },
    sectionSubtitle: {
      fontSize: '0.875rem',
      color: 'var(--text-light)',
      margin: 0,
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
    diagramContainer: {
      backgroundColor: 'var(--subtle-bg)',
      borderRadius: '0.75rem',
      padding: '1.5rem',
      marginTop: '1rem',
      border: '1px solid var(--border)',
      overflow: 'auto',
    },
    timeline: {
      display: 'flex',
      flexDirection: 'column',
      gap: '1rem',
      marginTop: '1.5rem',
    },
    timelineItem: {
      display: 'flex',
      gap: '1rem',
      padding: '1rem',
      backgroundColor: 'var(--subtle-bg)',
      borderRadius: '0.75rem',
      border: '1px solid var(--border)',
    },
    timelineMarker: {
      width: '8px',
      height: '8px',
      borderRadius: '50%',
      backgroundColor: 'var(--primary)',
      marginTop: '0.5rem',
      flexShrink: 0,
    },
    timelineContent: {
      flex: 1,
    },
    timelineTitle: {
      fontSize: '0.9375rem',
      fontWeight: 600,
      color: 'var(--text)',
      marginBottom: '0.25rem',
    },
    timelineText: {
      fontSize: '0.875rem',
      color: 'var(--text-light)',
      lineHeight: '1.5',
      margin: 0,
    },
  };

  // Icons as inline SVGs
  const icons = {
    info: (
      <svg style={styles.calloutIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    current: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="9" y1="21" x2="9" y2="9" />
      </svg>
    ),
    future: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polygon points="12 2 2 7 12 12 22 7 12 2" />
        <polyline points="2 17 12 22 22 17" />
        <polyline points="2 12 12 17 22 12" />
      </svg>
    ),
    roadmap: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="12" y1="20" x2="12" y2="10" />
        <line x1="18" y1="20" x2="18" y2="4" />
        <line x1="6" y1="20" x2="6" y2="16" />
      </svg>
    ),
  };

  const roadmapItems = [
    { phase: 'Phase 1', title: 'DCAT v3 Schema Design', description: 'Define semantic metadata model with mappings for existing providers' },
    { phase: 'Phase 2', title: 'Protocol Abstraction Layer', description: 'Implement unified interface for multiple harvesting protocols' },
    { phase: 'Phase 3', title: 'Federation Endpoints', description: 'Expose DCAT-compliant catalog for NFDI and European partners' },
  ];

  return (
    <div style={styles.container}>
      {/* Breadcrumbs - only show when logged in */}
      {currentUser && <Breadcrumbs items={breadcrumbItems} />}

      {/* Header Section */}
      {currentUser ? (
        <div style={styles.pageHeader}>
          <h2 style={styles.pageHeaderTitle}>About</h2>
          <p style={styles.pageHeaderSubtitle}>
            Learn about the Data Provider Manager, its architecture, and future development.
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

      {/* About Section */}
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
            {icons.info}
            <p style={styles.calloutText}>
              <strong>Note for Individual Researchers:</strong> To search and access biodiversity data,
              please use the public <a href="https://search.gfbio.org" target="_blank" rel="noopener noreferrer" style={styles.link}>
              GFBio Search Portal</a> which provides access to all registered collections.
            </p>
          </div>
        </div>
      </section>

      {/* Current Architecture Section */}
      <section style={styles.contentCard}>
        <div style={styles.cardHeader}>
          <div style={{ ...styles.cardIcon, backgroundColor: 'var(--subtle-bg)', color: 'var(--text-light)' }}>
            {icons.current}
          </div>
          <div>
            <h2 style={styles.sectionTitle}>Current Architecture</h2>
            <p style={styles.sectionSubtitle}>Production system serving GFBio Search</p>
          </div>
        </div>

        <p style={styles.text}>
          The current system consists of multiple specialized harvesters coordinating data flow from
          various provider types. BioCASe providers are registered through the Aggregator, while OAI-PMH
          providers connect via panFMP Harvester and Darwin Core providers through the GBIF Harvester.
          All data flows into a shared Elasticsearch index powering the GFBio Search Portal.
        </p>

        <div style={styles.diagramContainer}>
          <MermaidDiagram chart={currentArchitectureDiagram} isDarkTheme={isDarkTheme} />
        </div>
      </section>

      {/* Future Architecture Section */}
      <section style={styles.contentCard}>
        <div style={styles.cardHeader}>
          <div style={{ ...styles.cardIcon, backgroundColor: 'var(--subtle-bg)', color: 'var(--text-light)' }}>
            {icons.future}
          </div>
          <div>
            <h2 style={styles.sectionTitle}>Future Architecture with DCAT v3</h2>
            <p style={styles.sectionSubtitle}>Next-generation federated infrastructure</p>
          </div>
        </div>

        <p style={styles.text}>
          The future architecture introduces DCAT v3 as the semantic backbone, enabling
          protocol-agnostic provider registration, richer metadata semantics, and direct
          federation with NFDI partners and European research infrastructures.
        </p>

        <div style={styles.diagramContainer}>
          <MermaidDiagram chart={futureArchitectureDiagram} isDarkTheme={isDarkTheme} />
        </div>
      </section>

      {/* Roadmap Section */}
      <section style={styles.contentCard}>
        <div style={styles.cardHeader}>
          <div style={{ ...styles.cardIcon, backgroundColor: 'var(--subtle-bg)', color: 'var(--text-light)' }}>
            {icons.roadmap}
          </div>
          <div>
            <h2 style={styles.sectionTitle}>Migration Roadmap</h2>
            <p style={styles.sectionSubtitle}>Key milestones for DCAT v3 transition</p>
          </div>
        </div>

        <div style={styles.timeline}>
          {roadmapItems.map((item, index) => (
            <div key={index} style={styles.timelineItem}>
              <div style={styles.timelineMarker} />
              <div style={styles.timelineContent}>
                <h3 style={styles.timelineTitle}>
                  <span style={{ color: 'var(--primary)', marginRight: '0.5rem' }}>{item.phase}:</span>
                  {item.title}
                </h3>
                <p style={styles.timelineText}>{item.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default About;
