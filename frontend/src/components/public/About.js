import React from 'react';

const About = () => {
  const containerStyle = {
    flexGrow: 1,
    padding: '2rem 1rem',
    maxWidth: '1200px',
    margin: '0 auto',
    width: '100%',
    lineHeight: '1.7',
    fontSize: '1rem',
  };

  const heroSectionStyle = {
    textAlign: 'center',
    marginBottom: '3rem',
    padding: '2rem 0',
  };

  const titleStyle = {
    fontSize: 'clamp(2rem, 4vw, 2.75rem)',
    fontWeight: 700,
    marginBottom: '1rem',
    color: 'var(--text)',
    letterSpacing: '-0.025em',
  };

  const subtitleStyle = {
    fontSize: 'clamp(1rem, 2.5vw, 1.25rem)',
    color: 'var(--text-light)',
    fontWeight: 400,
    maxWidth: '600px',
    margin: '0 auto',
    lineHeight: '1.6',
  };

  const sectionStyle = {
    backgroundColor: 'var(--card-bg)',
    borderRadius: '1rem',
    padding: '2.5rem',
    marginBottom: '2rem',
    border: '1px solid var(--border)',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
    transition: 'all 0.2s ease',
  };

  const sectionHoverStyle = {
    ...sectionStyle,
    ':hover': {
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.08)',
      transform: 'translateY(-1px)',
    }
  };

  const sectionHeaderStyle = {
    fontSize: '1.75rem',
    fontWeight: 600,
    marginBottom: '1.5rem',
    color: 'var(--text)',
    borderBottom: '2px solid var(--primary)',
    paddingBottom: '0.5rem',
    display: 'inline-block',
  };

  const subsectionHeaderStyle = {
    fontSize: '1.5rem',
    fontWeight: 600,
    marginTop: '2.5rem',
    marginBottom: '1rem',
    color: 'var(--text)',
  };

  const h3Style = {
    fontSize: '1.3rem',
    fontWeight: 600,
    marginTop: '2rem',
    marginBottom: '1rem',
    color: 'var(--primary)',
  };

  const paragraphStyle = {
    color: 'var(--text-light)',
    marginBottom: '1.25rem',
    lineHeight: '1.7',
  };

  const highlightParagraphStyle = {
    ...paragraphStyle,
    backgroundColor: 'var(--subtle-bg)',
    padding: '1.25rem',
    borderRadius: '0.5rem',
    borderLeft: '4px solid var(--primary)',
    fontWeight: 500,
    color: 'var(--text)',
  };

  const featureListStyle = {
    listStyle: 'none',
    padding: 0,
    margin: '1.5rem 0',
  };

  const featureItemStyle = {
    color: 'var(--text-light)',
    marginBottom: '1rem',
    padding: '1rem 1.25rem',
    backgroundColor: 'var(--subtle-bg)',
    borderRadius: '0.5rem',
    borderLeft: '3px solid var(--primary)',
    position: 'relative',
    transition: 'all 0.2s ease',
  };

  const contactSectionStyle = {
    ...sectionStyle,
    background: 'linear-gradient(135deg, var(--card-bg) 0%, var(--subtle-bg) 100%)',
  };

  const contactItemStyle = {
    display: 'flex',
    alignItems: 'center',
    marginBottom: '1rem',
    padding: '0.75rem',
    backgroundColor: 'var(--card-bg)',
    borderRadius: '0.5rem',
    border: '1px solid var(--border)',
  };

  const contactLabelStyle = {
    fontWeight: 600,
    color: 'var(--text)',
    minWidth: '100px',
    marginRight: '1rem',
  };

  const contactValueStyle = {
    color: 'var(--text-light)',
  };

  const legalSectionStyle = {
    backgroundColor: 'var(--subtle-bg)',
    borderRadius: '0.75rem',
    padding: '2rem',
    border: '1px solid var(--border)',
    marginBottom: '2rem',
  };

  const addressStyle = {
    backgroundColor: 'var(--card-bg)',
    padding: '1.25rem',
    borderRadius: '0.5rem',
    border: '1px solid var(--border)',
    marginBottom: '1rem',
    lineHeight: '1.6',
  };

  const supportSectionStyle = {
    background: 'linear-gradient(135deg, var(--primary) 0%, #1d4ed8 100%)',
    borderRadius: '0.75rem',
    padding: '2.5rem',
    textAlign: 'center',
    border: 'none',
    color: 'white',
  };

  const supportHeaderStyle = {
    fontSize: '1.5rem',
    fontWeight: 600,
    marginBottom: '1rem',
    color: 'white',
  };

  const supportTextStyle = {
    margin: 0,
    fontSize: '1rem',
    lineHeight: '1.6',
    color: 'rgba(255, 255, 255, 0.9)',
  };

  return (
    <div style={containerStyle} className="content-container">
      {/* Hero Section */}
      <header style={heroSectionStyle}>
        <h1 style={titleStyle}>
          GFBio Data Provider Manager
        </h1>
        <p style={subtitleStyle}>
          Comprehensive data provider and dataset management for the GFBio Search and Harvesting Infrastructure
        </p>
      </header>

      {/* Main Content Section */}
      <section style={sectionStyle}>
        <h2 style={sectionHeaderStyle}>What We Do</h2>
        
        <p style={paragraphStyle}>
          The GFBio Aggregator provides comprehensive data provider and dataset management for the GFBio Search and Harvesting Infrastructure (SAHIS), enabling the discovery and integration of biodiversity data from certified data centers following FAIR principles.

          We serve as the central registry that coordinates the entire research data ecosystem from harvesting through publication, ensuring seamless integration and discoverability of biological data across Germany's research infrastructure.
        
        </p>
        
        <h3 style={subsectionHeaderStyle}>Who We Are</h3>
        
        <p style={paragraphStyle}>
          The GFBio Aggregator is a core service of the GFBio Search and Harvesting Infrastructure, operated by <strong>GFBio e.V. (Gesellschaft für Biologische Daten e.V.)</strong>, a registered non-profit association dedicated to advancing science and research in the field of scientific data management.
        </p>
        
        <p style={paragraphStyle}>
          As a gemeinnütziger Verein and coordinating partner in <strong>NFDI4Biodiversity</strong>, we operate this service to support the biological sciences community with professional research data infrastructure as part of Germany's National Research Data Infrastructure.
        </p>
        
        <h3 style={subsectionHeaderStyle}>Our Mission</h3>
        
        <p style={paragraphStyle}>
          We make diverse biodiversity data available and usable in the long term by managing the registry of data providers and datasets that feeds into the GFBio search infrastructure, serving as the foundation for professional management of biological data in Germany and beyond.
        </p>
        
        <h3 style={h3Style}>Key Features</h3>
        
        <ul style={featureListStyle}>
          <li style={featureItemStyle}>
            <strong>Data Provider Registry Management</strong> — Comprehensive management for the GFBio harvesting infrastructure
          </li>
          <li style={featureItemStyle}>
            <strong>Dataset Cataloging & Metadata Coordination</strong> — Working with 10+ specialized data centers
          </li>
          <li style={featureItemStyle}>
            <strong>ABCD XML Validation</strong> — Access to Biological Collection Data validation and quality assurance
          </li>
          <li style={featureItemStyle}>
            <strong>GFBio Search Integration</strong> — Seamless integration with search interface and harvesting components
          </li>
          <li style={featureItemStyle}>
            <strong>Ecosystem Monitoring</strong> — Statistical monitoring and reporting for the research data ecosystem
          </li>
          <li style={featureItemStyle}>
            <strong>FAIR Data API</strong> — RESTful API supporting FAIR data management principles
          </li>
        </ul>
        
        <h3 style={subsectionHeaderStyle}>For Researchers</h3>
        
        <p style={paragraphStyle}>
          This service is available free of charge to researchers in biology, ecology, and environmental sciences. The aggregator ensures your data becomes discoverable through the GFBio search infrastructure, supporting data from field observations, collections, genomics, and environmental monitoring.
        </p>
      </section>
      
      {/* Contact Section */}
      <section style={contactSectionStyle}>
        <h2 style={sectionHeaderStyle}>Contact Information</h2>
        
        <p style={paragraphStyle}>
          For service-related inquiries and technical support:
        </p>
        
        <div style={contactItemStyle}>
          <span style={contactLabelStyle}>Email:</span>
          <span style={contactValueStyle}>info@gfbio.org</span>
        </div>
        
        <div style={contactItemStyle}>
          <span style={contactLabelStyle}>Helpdesk:</span>
          <span style={contactValueStyle}>Available Monday-Friday, 9:00-17:00 CET</span>
        </div>
        
      </section>
      
      {/* Legal Information */}
      <section style={contactSectionStyle}>
        <h2 style={sectionHeaderStyle}>Legal Information</h2>
        
        <div style={contactItemStyle}>
          <div style={{color: 'var(--text-light)'}}>
            <strong style={{color: 'var(--text)', display: 'block', marginBottom: '0.75rem'}}>
              GFBio e.V. (Gesellschaft für Biologische Daten e.V.)
            </strong>
            <div style={{marginBottom: '1rem'}}>
              Unicom 2, Haus 2-4<br/>
              Mary-Somerville-Str. 2<br/>
              28359 Bremen<br/>
              Registered at Amtsgericht Bremen
            </div>
            <div style={{fontSize: '0.9rem'}}>
              For complete legal information including Impressum, data protection, and organizational details, visit our main website at <strong style={{color: 'var(--text)'}}>gfbio.org</strong>
            </div>
          </div>
        </div>
      </section>
      
      {/* Support Section */}
      <section style={supportSectionStyle}>
        <h3 style={supportHeaderStyle}>Supporting Open Science</h3>
        
        <p style={supportTextStyle}>
          As a non-profit association funded by the German Research Foundation (DFG) and member contributions, we rely on institutional support to maintain free services for the research community as part of NFDI4Biodiversity and the German National Research Data Infrastructure (NFDI).
        </p>
      </section>
    </div>
  );
};

export default About;
