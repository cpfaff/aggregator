import React from 'react';
import Breadcrumbs from '../ui/Breadcrumbs';
import MermaidDiagram from '../ui/MermaidDiagram';

const About = ({ currentUser, isDarkTheme }) => {
  const breadcrumbItems = [
    { label: 'Home', onClick: () => {} },
    { label: 'About', onClick: null }
  ];

  // System architecture diagram — the route a dataset travels from a data
  // center, through registration and harvesting, into the search index and the
  // public portal. Kept deliberately high-level for a non-technical audience.
  const architectureDiagram = `
flowchart LR
    subgraph Sources ["Data Centers and Providers"]
        direction TB
        collections("Natural-history collections<br/><i>ABCD / BioCASe</i>")
        repos("PANGAEA, ENA, DataCite<br/><i>OAI-PMH</i>")
        gbif("GBIF<br/><i>Darwin Core</i>")
    end

    dpm("Data Provider Manager<br/><i>register, validate, monitor</i>")
    harvester("panFMP Harvester<br/><i>collect, crosswalk, load</i>")
    esIndex[("Search Index<br/>Elasticsearch")]
    portal("GFBio Search Portal<br/><i>search.gfbio.org</i>")

    collections -->|register| dpm
    dpm -->|harvest feed| harvester
    repos --> harvester
    gbif --> harvester
    harvester -->|harmonised records| esIndex
    esIndex --> portal
    dpm -. reads status .-> esIndex
`;

  // The end-to-end journey of a dataset, expressed as four plain-language steps.
  const journeySteps = [
    {
      step: 'Step 1',
      title: 'Register',
      description:
        'A data center describes its data providers and datasets in the Data Provider Manager and marks the records that are ready to be published.',
    },
    {
      step: 'Step 2',
      title: 'Validate',
      description:
        'Each dataset’s ABCD metadata is checked against the international TDWG standards and scored for quality, so problems are caught before publication.',
    },
    {
      step: 'Step 3',
      title: 'Harvest & harmonise',
      description:
        'The harvester collects metadata from every source — in whatever standard each provider speaks — and translates it all into one common format.',
    },
    {
      step: 'Step 4',
      title: 'Index & discover',
      description:
        'The harmonised records are loaded into the shared search index and become discoverable to researchers worldwide through the GFBio Search Portal.',
    },
  ];

  // What the Data Provider Manager itself does, at a glance.
  const capabilities = [
    {
      icon: 'registry',
      title: 'Provider & dataset registry',
      text:
        'A single, authoritative record of which institutions contribute data and which datasets they publish into GFBio.',
    },
    {
      icon: 'shield',
      title: 'Quality validation',
      text:
        'Automated checks of ABCD metadata against the TDWG standards, with a quality score that guides curation.',
    },
    {
      icon: 'flag',
      title: 'Harvest readiness',
      text:
        'Curators decide exactly which datasets are ready for publication; only those are offered to the harvester.',
    },
    {
      icon: 'pulse',
      title: 'Status & statistics',
      text:
        'A live view of whether registered data has reached the search index, plus growth and data-quality statistics over time.',
    },
  ];

  // The components of the wider infrastructure, and the services it connects to.
  const components = [
    {
      name: 'Data Provider Manager',
      tag: 'This service',
      text:
        'The registration front door (this application). Manages providers, datasets and quality, and publishes a feed of harvest-ready data.',
    },
    {
      name: 'Harvester (panFMP)',
      tag: 'Collection',
      text:
        'Gathers metadata from every source and crosswalks the many input standards into one shared schema for the index.',
    },
    {
      name: 'Search Index',
      tag: 'Storage',
      text:
        'An Elasticsearch catalogue holding one harmonised record per dataset — the searchable heart of the platform.',
    },
    {
      name: 'GFBio Search Portal',
      tag: 'Discovery',
      text:
        'The public website at search.gfbio.org where researchers find, filter, map and collect datasets for reuse.',
    },
    {
      name: 'Terminology Service',
      tag: 'Connected',
      text:
        'Expands searches with scientific synonyms and common names so users find data even when wording differs.',
    },
    {
      name: 'Collections & VAT',
      tag: 'Connected',
      text:
        'Downstream GFBio tools that let researchers package selected datasets and move them into analysis workflows.',
    },
  ];

  // Standards and principles the platform is built on.
  const standards = [
    'FAIR data principles',
    'ABCD / BioCASe',
    'Darwin Core',
    'OAI-PMH',
    'DataCite',
    'EML',
    'NFDI4Biodiversity',
  ];

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
    diagramCaption: {
      fontSize: '0.8125rem',
      color: 'var(--text-light)',
      textAlign: 'center',
      margin: '0.75rem 0 0',
      fontStyle: 'italic',
    },
    // Capability + component grids (responsive without media queries)
    featureGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
      gap: '1rem',
      marginTop: '0.5rem',
    },
    featureItem: {
      display: 'flex',
      gap: '0.875rem',
      padding: '1.25rem',
      backgroundColor: 'var(--subtle-bg)',
      borderRadius: '0.75rem',
      border: '1px solid var(--border)',
    },
    featureIcon: {
      flexShrink: 0,
      width: '22px',
      height: '22px',
      color: 'var(--primary)',
      marginTop: '2px',
    },
    featureTitle: {
      fontSize: '0.9375rem',
      fontWeight: 600,
      color: 'var(--text)',
      marginBottom: '0.25rem',
    },
    featureText: {
      fontSize: '0.875rem',
      color: 'var(--text-light)',
      lineHeight: '1.55',
      margin: 0,
    },
    componentCard: {
      padding: '1.25rem',
      backgroundColor: 'var(--subtle-bg)',
      borderRadius: '0.75rem',
      border: '1px solid var(--border)',
    },
    componentTag: {
      display: 'inline-block',
      fontSize: '0.6875rem',
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
      color: 'var(--primary)',
      marginBottom: '0.5rem',
    },
    componentName: {
      fontSize: '0.9375rem',
      fontWeight: 600,
      color: 'var(--text)',
      marginBottom: '0.35rem',
    },
    pillRow: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '0.5rem',
      marginTop: '1.25rem',
    },
    pill: {
      display: 'inline-block',
      padding: '0.35rem 0.8rem',
      borderRadius: '999px',
      backgroundColor: 'var(--subtle-bg)',
      border: '1px solid var(--border)',
      fontSize: '0.8125rem',
      fontWeight: 500,
      color: 'var(--text)',
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

  // Icons as inline SVGs (consistent with this page's hand-drawn icon set)
  const icons = {
    info: (
      <svg style={styles.calloutIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    manage: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <ellipse cx="12" cy="5" rx="9" ry="3" />
        <path d="M3 5v14a9 3 0 0 0 18 0V5" />
        <path d="M3 12a9 3 0 0 0 18 0" />
      </svg>
    ),
    network: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
        <line x1="3" y1="9" x2="21" y2="9" />
        <line x1="9" y1="21" x2="9" y2="9" />
      </svg>
    ),
    journey: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="6" cy="19" r="3" />
        <path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15" />
        <circle cx="18" cy="5" r="3" />
      </svg>
    ),
    grid: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
      </svg>
    ),
    standards: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
    // small feature icons
    registry: (
      <svg style={styles.featureIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 7h18M3 12h18M3 17h18" />
      </svg>
    ),
    shield: (
      <svg style={styles.featureIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </svg>
    ),
    flag: (
      <svg style={styles.featureIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
        <line x1="4" y1="22" x2="4" y2="15" />
      </svg>
    ),
    pulse: (
      <svg style={styles.featureIcon} fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
      </svg>
    ),
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
            What the Data Provider Manager does, and how it fits into the GFBio
            Search &amp; Harvesting Infrastructure.
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

      {/* About / intro Section */}
      <section style={styles.contentCard}>
        <p style={styles.text}>
          The Data Provider Manager is the central registry through which
          institutional providers enter the GFBio Search and Harvesting
          Infrastructure (SAHIS). It coordinates biodiversity data from certified
          data centers and partner institutions across Germany, following the
          FAIR data principles.
        </p>

        <p style={styles.text}>
          This service is operated by <strong>GFBio e.V.</strong> (Gesellschaft
          für Biologische Daten e.V.) as part of <strong>NFDI4Biodiversity</strong>,
          Germany's National Research Data Infrastructure, supporting the
          biological sciences community with professional data management.
        </p>

        <p style={{ ...styles.text, marginBottom: 0 }}>
          It is designed for data centers, scientific societies and institutions
          managing biological collections. If you are interested in publishing
          data with us, please get in touch.
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

      {/* What the Data Provider Manager does */}
      <section style={styles.contentCard}>
        <div style={styles.cardHeader}>
          <div style={{ ...styles.cardIcon, backgroundColor: 'var(--subtle-bg)', color: 'var(--text-light)' }}>
            {icons.manage}
          </div>
          <div>
            <h2 style={styles.sectionTitle}>What this service does</h2>
            <p style={styles.sectionSubtitle}>The registration front door to GFBio search</p>
          </div>
        </div>

        <p style={styles.text}>
          The Data Provider Manager is where data centers describe the data they
          contribute and prepare it for publication. It does not store the
          research records themselves — it manages who provides data, what they
          publish, and whether that data is fit and ready to reach researchers.
        </p>

        <div style={styles.featureGrid}>
          {capabilities.map((cap, i) => (
            <div key={i} style={styles.featureItem}>
              {icons[cap.icon]}
              <div>
                <div style={styles.featureTitle}>{cap.title}</div>
                <p style={styles.featureText}>{cap.text}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* How the system fits together — architecture */}
      <section style={styles.contentCard}>
        <div style={styles.cardHeader}>
          <div style={{ ...styles.cardIcon, backgroundColor: 'var(--subtle-bg)', color: 'var(--text-light)' }}>
            {icons.network}
          </div>
          <div>
            <h2 style={styles.sectionTitle}>How the system fits together</h2>
            <p style={styles.sectionSubtitle}>From data center to search portal</p>
          </div>
        </div>

        <p style={styles.text}>
          GFBio search is built from a handful of cooperating parts. Data centers
          register with the Data Provider Manager; the harvester then collects
          metadata from every source and translates the many different input
          standards into one shared format; the harmonised records are stored in
          a single search index; and the public Search Portal lets researchers
          discover them. The Data Provider Manager also reads back from the index
          to confirm that registered data has actually been published.
        </p>

        <div style={styles.diagramContainer}>
          <MermaidDiagram chart={architectureDiagram} isDarkTheme={isDarkTheme} />
        </div>
        <p style={styles.diagramCaption}>
          The path biodiversity metadata follows, from a contributing data center
          through to a researcher's search.
        </p>
      </section>

      {/* How your data reaches researchers — the journey */}
      <section style={styles.contentCard}>
        <div style={styles.cardHeader}>
          <div style={{ ...styles.cardIcon, backgroundColor: 'var(--subtle-bg)', color: 'var(--text-light)' }}>
            {icons.journey}
          </div>
          <div>
            <h2 style={styles.sectionTitle}>How your data reaches researchers</h2>
            <p style={styles.sectionSubtitle}>The journey of a dataset, in four steps</p>
          </div>
        </div>

        <p style={styles.text}>
          Every dataset published through GFBio follows the same path — from the
          moment a data center registers it, to the moment a researcher finds it
          in the portal.
        </p>

        <div style={styles.timeline}>
          {journeySteps.map((item, index) => (
            <div key={index} style={styles.timelineItem}>
              <div style={styles.timelineMarker} />
              <div style={styles.timelineContent}>
                <h3 style={styles.timelineTitle}>
                  <span style={{ color: 'var(--primary)', marginRight: '0.5rem' }}>{item.step}:</span>
                  {item.title}
                </h3>
                <p style={styles.timelineText}>{item.description}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* The components at a glance */}
      <section style={styles.contentCard}>
        <div style={styles.cardHeader}>
          <div style={{ ...styles.cardIcon, backgroundColor: 'var(--subtle-bg)', color: 'var(--text-light)' }}>
            {icons.grid}
          </div>
          <div>
            <h2 style={styles.sectionTitle}>The components at a glance</h2>
            <p style={styles.sectionSubtitle}>The wider landscape this service is part of</p>
          </div>
        </div>

        <div style={styles.featureGrid}>
          {components.map((comp, i) => (
            <div key={i} style={styles.componentCard}>
              <span style={styles.componentTag}>{comp.tag}</span>
              <div style={styles.componentName}>{comp.name}</div>
              <p style={styles.featureText}>{comp.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Standards & principles */}
      <section style={styles.contentCard}>
        <div style={styles.cardHeader}>
          <div style={{ ...styles.cardIcon, backgroundColor: 'var(--subtle-bg)', color: 'var(--text-light)' }}>
            {icons.standards}
          </div>
          <div>
            <h2 style={styles.sectionTitle}>Built on open standards</h2>
            <p style={styles.sectionSubtitle}>Interoperable by design</p>
          </div>
        </div>

        <p style={{ ...styles.text, marginBottom: 0 }}>
          Biodiversity data arrives in many community standards. GFBio harmonises
          them into one searchable catalogue so a single query can reach across
          natural-history collections, environmental archives and molecular
          repositories alike — and so the data stays Findable, Accessible,
          Interoperable and Reusable.
        </p>

        <div style={styles.pillRow}>
          {standards.map((s, i) => (
            <span key={i} style={styles.pill}>{s}</span>
          ))}
        </div>
      </section>
    </div>
  );
};

export default About;
