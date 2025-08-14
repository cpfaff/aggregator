import React, { memo, useCallback } from 'react';
import Button from '../ui/Button';

const LandingPage = memo(({ onGetStarted, onLearnMore }) => {
  // Optimize callback functions to prevent unnecessary re-renders
  const handleGetStarted = useCallback(() => {
    onGetStarted?.();
  }, [onGetStarted]);

  const handleLearnMore = useCallback(() => {
    onLearnMore?.();
  }, [onLearnMore]);

  // Optimize hover handlers to prevent function recreation
  const handleCardHover = useCallback((e) => {
    e.currentTarget.style.transform = 'translateY(-4px)';
    e.currentTarget.style.boxShadow = '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)';
  }, []);

  const handleCardLeave = useCallback((e) => {
    e.currentTarget.style.transform = 'translateY(0)';
    e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)';
  }, []);

  const containerStyle = {
    flexGrow: 1,
    width: '100%',
    lineHeight: '1.7',
    fontSize: '1rem',
    // Performance optimization: use CSS transforms for smooth scrolling
    transform: 'translateZ(0)',
    WebkitBackfaceVisibility: 'hidden',
    backfaceVisibility: 'hidden',
  };

  const heroSectionStyle = {
    background: 'linear-gradient(135deg, var(--card-bg) 0%, var(--subtle-bg) 100%)',
    padding: '4rem 1rem',
    textAlign: 'center',
    borderBottom: '1px solid var(--border)',
  };

  const heroContentStyle = {
    maxWidth: '1200px',
    margin: '0 auto',
    width: '100%',
  };

  const titleStyle = {
    fontSize: 'clamp(2.25rem, 5vw, 3.5rem)',
    fontWeight: 800,
    marginBottom: '1.5rem',
    color: 'var(--text)',
    letterSpacing: '-0.035em',
    lineHeight: '1.1',
  };

  const subtitleStyle = {
    fontSize: 'clamp(1.125rem, 3vw, 1.375rem)',
    color: 'var(--text-light)',
    fontWeight: 400,
    maxWidth: '700px',
    margin: '0 auto 2.5rem auto',
    lineHeight: '1.5',
  };

  const ctaContainerStyle = {
    display: 'flex',
    gap: '1rem',
    justifyContent: 'center',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginBottom: '3rem',
  };

  const trustSignalsStyle = {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: '2rem',
    flexWrap: 'wrap',
    opacity: 0.8,
  };

  const trustBadgeStyle = {
    padding: '0.5rem 1rem',
    backgroundColor: 'var(--card-bg)',
    borderRadius: '0.5rem',
    border: '1px solid var(--border)',
    fontSize: '0.875rem',
    fontWeight: 600,
    color: 'var(--text)',
  };

  const contentSectionStyle = {
    padding: '4rem 1rem',
    maxWidth: '1200px',
    margin: '0 auto',
    width: '100%',
  };

  const sectionHeaderStyle = {
    fontSize: 'clamp(1.75rem, 4vw, 2.25rem)',
    fontWeight: 700,
    marginBottom: '3rem',
    color: 'var(--text)',
    textAlign: 'center',
    letterSpacing: '-0.025em',
  };

  const cardsGridStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '2rem',
    marginBottom: '4rem',
  };

  const cardStyle = {
    backgroundColor: 'var(--card-bg)',
    borderRadius: '1rem',
    padding: '2.5rem',
    border: '1px solid var(--border)',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    cursor: 'default',
    textAlign: 'center',
  };

  const cardIconStyle = {
    width: '60px',
    height: '60px',
    backgroundColor: 'var(--primary)',
    borderRadius: '1rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 1.5rem auto',
    fontSize: '1.5rem',
    color: 'white',
    fontWeight: 600,
  };

  const cardTitleStyle = {
    fontSize: '1.5rem',
    fontWeight: 600,
    marginBottom: '1rem',
    color: 'var(--text)',
  };

  const cardTextStyle = {
    color: 'var(--text-light)',
    lineHeight: '1.6',
    fontSize: '1rem',
  };

  const socialProofSectionStyle = {
    backgroundColor: 'var(--subtle-bg)',
    padding: '4rem 1rem',
    textAlign: 'center',
  };

  const statsContainerStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '2rem',
    maxWidth: '800px',
    margin: '2rem auto',
  };

  const statItemStyle = {
    padding: '1.5rem',
    backgroundColor: 'var(--card-bg)',
    borderRadius: '0.75rem',
    border: '1px solid var(--border)',
  };

  const statNumberStyle = {
    fontSize: '2.5rem',
    fontWeight: 800,
    color: 'var(--primary)',
    marginBottom: '0.5rem',
    lineHeight: '1',
  };

  const statLabelStyle = {
    fontSize: '0.875rem',
    color: 'var(--text-light)',
    fontWeight: 500,
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  };

  const processSectionStyle = {
    padding: '4rem 1rem',
    maxWidth: '1200px',
    margin: '0 auto',
    width: '100%',
  };

  const processStepsStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '2rem',
    marginBottom: '3rem',
  };

  const processStepStyle = {
    textAlign: 'center',
    position: 'relative',
  };

  const stepNumberStyle = {
    width: '50px',
    height: '50px',
    backgroundColor: 'var(--primary)',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 1.5rem auto',
    fontSize: '1.25rem',
    fontWeight: 700,
    color: 'white',
  };

  const stepTitleStyle = {
    fontSize: '1.25rem',
    fontWeight: 600,
    marginBottom: '0.75rem',
    color: 'var(--text)',
  };

  const stepDescStyle = {
    color: 'var(--text-light)',
    lineHeight: '1.6',
  };

  const finalCtaSectionStyle = {
    background: 'linear-gradient(135deg, var(--primary) 0%, #1d4ed8 100%)',
    padding: '4rem 1rem',
    textAlign: 'center',
    color: 'white',
  };

  const finalCtaContentStyle = {
    maxWidth: '800px',
    margin: '0 auto',
  };

  const finalCtaTitleStyle = {
    fontSize: 'clamp(1.75rem, 4vw, 2.25rem)',
    fontWeight: 700,
    marginBottom: '1rem',
    color: 'white',
  };

  const finalCtaTextStyle = {
    fontSize: '1.125rem',
    marginBottom: '2.5rem',
    color: 'rgba(255, 255, 255, 0.9)',
    lineHeight: '1.6',
  };

  const pathwaysStyle = {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '2rem',
    marginBottom: '2rem',
  };

  const pathwayStyle = {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: '1rem',
    padding: '2rem',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    backdropFilter: 'blur(10px)',
    WebkitBackdropFilter: 'blur(10px)',
  };

  const pathwayTitleStyle = {
    fontSize: '1.25rem',
    fontWeight: 600,
    marginBottom: '1rem',
    color: 'white',
  };

  const pathwayDescStyle = {
    fontSize: '0.9375rem',
    color: 'rgba(255, 255, 255, 0.8)',
    marginBottom: '1.5rem',
    lineHeight: '1.5',
  };

  const contactInfoStyle = {
    fontSize: '0.9375rem',
    color: 'rgba(255, 255, 255, 0.8)',
    marginTop: '2rem',
  };

  return (
    <div style={containerStyle}>
      {/* Hero Section */}
      <section style={heroSectionStyle}>
        <div style={heroContentStyle}>
          <h1 style={titleStyle}>
            Accelerate Research with Professional Data Management
          </h1>
          <p style={subtitleStyle}>
            Join Germany's leading biodiversity data infrastructure supporting 10+ research centers and thousands of datasets through GFBio's comprehensive platform.
          </p>
          
          <div style={ctaContainerStyle}>
            <Button 
              onClick={handleGetStarted}
              variant="primary"
              style={{
                minWidth: '160px',
                fontSize: '1.125rem',
                height: '3rem',
                padding: '0 2rem',
                // Optimize for mobile touch targets (minimum 48px)
                minHeight: '48px',
                touchAction: 'manipulation',
                WebkitTapHighlightColor: 'transparent',
              }}
            >
              Get Started
            </Button>
            <Button 
              onClick={handleLearnMore}
              variant="default"
              style={{
                minWidth: '140px',
                fontSize: '1rem',
                height: '3rem',
                padding: '0 2rem',
                // Optimize for mobile touch targets
                minHeight: '48px',
                touchAction: 'manipulation',
                WebkitTapHighlightColor: 'transparent',
              }}
            >
              Learn More
            </Button>
          </div>

          <div style={trustSignalsStyle}>
            <div style={trustBadgeStyle}>GFBio e.V.</div>
            <div style={trustBadgeStyle}>NFDI4Biodiversity</div>
            <div style={trustBadgeStyle}>DFG Funded</div>
          </div>
        </div>
      </section>

      {/* Value Propositions */}
      <section style={contentSectionStyle}>
        <h2 style={sectionHeaderStyle}>Why Leading Researchers Choose Our Platform</h2>
        
        <div style={cardsGridStyle}>
          <div 
            style={cardStyle}
            onMouseEnter={handleCardHover}
            onMouseLeave={handleCardLeave}
          >
            <div style={cardIconStyle}>✓</div>
            <h3 style={cardTitleStyle}>Ensure Data Quality</h3>
            <p style={cardTextStyle}>
              Automated ABCD XML validation ensures your datasets meet international standards, saving hours of manual review while maintaining research integrity.
            </p>
          </div>

          <div 
            style={cardStyle}
            onMouseEnter={handleCardHover}
            onMouseLeave={handleCardLeave}
          >
            <div style={cardIconStyle}>🔍</div>
            <h3 style={cardTitleStyle}>Accelerate Discovery</h3>
            <p style={cardTextStyle}>
              Seamless integration with GFBio's search infrastructure makes your research discoverable to thousands of scientists worldwide.
            </p>
          </div>

          <div 
            style={cardStyle}
            onMouseEnter={handleCardHover}
            onMouseLeave={handleCardLeave}
          >
            <div style={cardIconStyle}>📊</div>
            <h3 style={cardTitleStyle}>Maintain Compliance</h3>
            <p style={cardTextStyle}>
              Built-in FAIR principles compliance and professional infrastructure ensure your research meets funding requirements and institutional standards.
            </p>
          </div>
        </div>
      </section>

      {/* Social Proof */}
      <section style={socialProofSectionStyle}>
        <div style={heroContentStyle}>
          <h2 style={sectionHeaderStyle}>Trusted by the Research Community</h2>
          <div style={statsContainerStyle}>
            <div style={statItemStyle}>
              <div style={statNumberStyle}>10+</div>
              <div style={statLabelStyle}>Data Centers</div>
            </div>
            <div style={statItemStyle}>
              <div style={statNumberStyle}>1000s</div>
              <div style={statLabelStyle}>Datasets Managed</div>
            </div>
            <div style={statItemStyle}>
              <div style={statNumberStyle}>24/7</div>
              <div style={statLabelStyle}>Infrastructure</div>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section style={processSectionStyle}>
        <h2 style={sectionHeaderStyle}>Get Started in Three Simple Steps</h2>
        
        <div style={processStepsStyle}>
          <div style={processStepStyle}>
            <div style={stepNumberStyle}>1</div>
            <h3 style={stepTitleStyle}>Register Your Institution</h3>
            <p style={stepDescStyle}>
              Quick registration process with institutional verification and access credentials setup.
            </p>
          </div>

          <div style={processStepStyle}>
            <div style={stepNumberStyle}>2</div>
            <h3 style={stepTitleStyle}>Submit Your Datasets</h3>
            <p style={stepDescStyle}>
              Upload datasets with automatic validation and metadata enrichment for maximum discoverability.
            </p>
          </div>

          <div style={processStepStyle}>
            <div style={stepNumberStyle}>3</div>
            <h3 style={stepTitleStyle}>Enable Research Discovery</h3>
            <p style={stepDescStyle}>
              Your data becomes instantly searchable through GFBio's infrastructure, connecting with researchers globally.
            </p>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section style={finalCtaSectionStyle}>
        <div style={finalCtaContentStyle}>
          <h2 style={finalCtaTitleStyle}>Ready to Advance Your Research?</h2>
          <p style={finalCtaTextStyle}>
            Join the growing community of researchers leveraging professional data management to accelerate scientific discovery.
          </p>

          <div style={pathwaysStyle}>
            <div style={pathwayStyle}>
              <h3 style={pathwayTitleStyle}>For Researchers</h3>
              <p style={pathwayDescStyle}>
                Individual researchers looking to make their data discoverable and compliant with FAIR principles.
              </p>
              <Button 
                onClick={handleGetStarted}
                variant="primary"
                style={{
                  backgroundColor: 'white',
                  color: 'var(--primary)',
                  width: '100%',
                  minHeight: '48px',
                  touchAction: 'manipulation',
                  WebkitTapHighlightColor: 'transparent',
                }}
              >
                Start Research Account
              </Button>
            </div>

            <div style={pathwayStyle}>
              <h3 style={pathwayTitleStyle}>For Institutions</h3>
              <p style={pathwayDescStyle}>
                Data centers and institutions requiring professional infrastructure and institutional-level management.
              </p>
              <Button 
                onClick={handleLearnMore}
                variant="default"
                style={{
                  backgroundColor: 'rgba(255, 255, 255, 0.2)',
                  color: 'white',
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                  width: '100%',
                  minHeight: '48px',
                  touchAction: 'manipulation',
                  WebkitTapHighlightColor: 'transparent',
                }}
              >
                Contact Sales
              </Button>
            </div>
          </div>

          <div style={contactInfoStyle}>
            <strong>Need Help?</strong> Contact our support team at info@gfbio.org<br/>
            Available Monday-Friday, 9:00-17:00 CET
          </div>
        </div>
      </section>
    </div>
  );
});

// Add display name for debugging
LandingPage.displayName = 'LandingPage';

export default LandingPage;