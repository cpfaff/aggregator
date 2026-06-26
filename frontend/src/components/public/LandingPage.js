import React, { memo, useCallback, useState, useEffect } from 'react';
import Button from '../ui/Button';
import StatCard from '../ui/StatCard';
import { useResponsiveGrid } from '../../hooks/useMediaQuery';
import { publicStatsApi } from '../../utils/statisticsApi';

const LandingPage = memo(({ onGetStarted, onLearnMore, onViewStatistics }) => {
  const { getGridColumns } = useResponsiveGrid();

  // Optimize callback functions to prevent unnecessary re-renders
  const handleGetStarted = useCallback(() => {
    onGetStarted?.();
  }, [onGetStarted]);

  const handleLearnMore = useCallback(() => {
    onLearnMore?.();
  }, [onLearnMore]);

  // Optimize hover handlers to prevent function recreation
  const handleCardHover = useCallback((e) => {
    e.currentTarget.style.transform = 'translateY(-2px)';
    e.currentTarget.style.boxShadow = '0 8px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)';
  }, []);

  const handleCardLeave = useCallback((e) => {
    e.currentTarget.style.transform = 'translateY(0)';
    e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -1px rgba(0, 0, 0, 0.04)';
  }, []);

  // Trust badge hover effects
  const handleBadgeHover = useCallback((e) => {
    e.currentTarget.style.transform = 'translateY(-2px)';
    e.currentTarget.style.boxShadow = '0 6px 12px -2px rgba(0, 0, 0, 0.1)';
  }, []);

  const handleBadgeLeave = useCallback((e) => {
    e.currentTarget.style.transform = 'translateY(0)';
    e.currentTarget.style.boxShadow = '0 2px 4px -1px rgba(0, 0, 0, 0.05)';
  }, []);

  // State for live statistics
  const [stats, setStats] = useState(null);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [statsError, setStatsError] = useState(false);

  // Fetch live statistics on mount through the shared public client
  // (REQ-SH-FE-1): publicStatsApi.getOverview encapsulates the API_BASE
  // composition and the timeout-bounded, ok-guarded, typed-error fetch
  // (FR-13, REQ-FE-CLIENT-5). REQ-SH-FE-2: an effect-scoped AbortController
  // cancels the in-flight request if the page unmounts mid-flight.
  useEffect(() => {
    const controller = new AbortController();
    publicStatsApi
      .getOverview({ signal: controller.signal })
      .then((data) => {
        setStats(data);
        setStatsError(false);
        setIsLoadingStats(false);
      })
      .catch((err) => {
        // Ignore the abort our own unmount cleanup fires (REQ-SH-FE-2).
        if (controller.signal.aborted) return;
        // Keep any last-known stats (stale-while-error, a credited strength);
        // surface the failure rather than swallowing it.
        console.error('Failed to load overview statistics:', err);
        setStatsError(true);
        setIsLoadingStats(false);
      });
    return () => controller.abort();
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
    padding: '5rem 1rem 4rem 1rem',
    textAlign: 'center',
    borderBottom: '1px solid var(--border)',
    position: 'relative',
    overflow: 'hidden',
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
    textShadow: '0 2px 4px rgba(0, 0, 0, 0.02)',
  };

  const subtitleStyle = {
    fontSize: 'clamp(1.125rem, 3vw, 1.375rem)',
    color: 'var(--text-light)',
    fontWeight: 400,
    maxWidth: '650px',
    margin: '0 auto 3rem auto',
    lineHeight: '1.6',
    opacity: 0.9,
  };

  const ctaContainerStyle = {
    display: 'flex',
    gap: '1.25rem',
    justifyContent: 'center',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginBottom: '3.5rem',
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
    padding: '0.625rem 1.25rem',
    backgroundColor: 'var(--card-bg)',
    borderRadius: '0.75rem',
    border: '1px solid var(--border)',
    fontSize: '0.875rem',
    fontWeight: 600,
    color: 'var(--text)',
    boxShadow: '0 2px 4px -1px rgba(0, 0, 0, 0.05)',
    transition: 'all 0.2s ease-out',
  };

  const contentSectionStyle = {
    padding: '5rem 1rem',
    maxWidth: '1200px',
    margin: '0 auto',
    width: '100%',
  };

  const sectionHeaderStyle = {
    fontSize: 'clamp(1.75rem, 4vw, 2.25rem)',
    fontWeight: 700,
    marginBottom: '3.5rem',
    color: 'var(--text)',
    textAlign: 'center',
    letterSpacing: '-0.025em',
    position: 'relative',
  };

  const cardsGridStyle = {
    display: 'grid',
    gridTemplateColumns: getGridColumns(320),
    gap: '2.5rem',
    marginBottom: '4rem',
  };

  const cardStyle = {
    backgroundColor: 'var(--card-bg)',
    borderRadius: '1.25rem',
    padding: '2.75rem 2.25rem',
    border: '1px solid var(--border)',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -1px rgba(0, 0, 0, 0.04)',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    cursor: 'default',
    textAlign: 'center',
    position: 'relative',
    overflow: 'hidden',
  };

  const cardIconStyle = {
    width: '64px',
    height: '64px',
    backgroundColor: 'var(--primary)',
    borderRadius: '1.25rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 1.75rem auto',
    fontSize: '1.5rem',
    color: 'white',
    fontWeight: 600,
    boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)',
    position: 'relative',
    zIndex: 1,
  };

  const cardTitleStyle = {
    fontSize: '1.5rem',
    fontWeight: 600,
    marginBottom: '1.125rem',
    color: 'var(--text)',
    lineHeight: '1.3',
  };

  const cardTextStyle = {
    color: 'var(--text-light)',
    lineHeight: '1.65',
    fontSize: '1rem',
    opacity: 0.9,
  };

  const socialProofSectionStyle = {
    backgroundColor: 'var(--subtle-bg)',
    padding: '5rem 1rem',
    textAlign: 'center',
    borderTop: '1px solid var(--border)',
    borderBottom: '1px solid var(--border)',
  };

  return (
    <div style={containerStyle}>
      {/* Hero Section */}
      <section style={heroSectionStyle}>
        <div style={heroContentStyle}>
          <h1 style={titleStyle}>
            Data Provider Manager
          </h1>
          <p style={subtitleStyle}>
            A platform for managing biodiversity datasets and connecting research data with the GFBio infrastructure.
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
              Sign In
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
            <div
              style={trustBadgeStyle}
              onMouseEnter={handleBadgeHover}
              onMouseLeave={handleBadgeLeave}
            >
              GFBio e.V.
            </div>
            <div
              style={trustBadgeStyle}
              onMouseEnter={handleBadgeHover}
              onMouseLeave={handleBadgeLeave}
            >
              NFDI4Biodiversity
            </div>
          </div>
        </div>
      </section>

      {/* Value Propositions */}
      <section style={contentSectionStyle}>
        <h2 style={sectionHeaderStyle}>Core Features</h2>

        <div style={cardsGridStyle}>
          <div
            style={cardStyle}
            onMouseEnter={handleCardHover}
            onMouseLeave={handleCardLeave}
          >
            <div style={cardIconStyle}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 2V8H15M9 2H4V22H20V8M9 2H15L20 8" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M7 13H17M7 17H17" stroke="white" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <h3 style={cardTitleStyle}>Self-Service Registry</h3>
            <p style={cardTextStyle}>
              Institutional dataset management platform supporting BioCASe providers with ABCD (Access to Biological Collection Data) format for biological collections.
            </p>
          </div>

          <div
            style={cardStyle}
            onMouseEnter={handleCardHover}
            onMouseLeave={handleCardLeave}
          >
            <div style={cardIconStyle}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 12L11 14L15 10" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3C16.9706 3 21 7.02944 21 12Z" stroke="white" strokeWidth="2"/>
                <path d="M3 12H8M16 12H21M12 3V8M12 16V21" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
              </svg>
            </div>
            <h3 style={cardTitleStyle}>Validation & Analytics</h3>
            <p style={cardTextStyle}>
              Automated ABCD standard validation ensuring data quality, plus comprehensive dataset statistics including biological unit counts and metrics.
            </p>
          </div>

          <div
            style={cardStyle}
            onMouseEnter={handleCardHover}
            onMouseLeave={handleCardLeave}
          >
            <div style={cardIconStyle}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="11" cy="11" r="8" stroke="white" strokeWidth="2"/>
                <path d="M21 21L16.65 16.65" stroke="white" strokeWidth="2" strokeLinecap="round"/>
                <circle cx="8" cy="8" r="2" stroke="white" strokeWidth="1.5"/>
                <circle cx="14" cy="8" r="2" stroke="white" strokeWidth="1.5"/>
                <circle cx="11" cy="14" r="2" stroke="white" strokeWidth="1.5"/>
                <path d="M8 8L14 8M8 8L11 14M14 8L11 14" stroke="white" strokeWidth="1" strokeLinecap="round"/>
              </svg>
            </div>
            <h3 style={cardTitleStyle}>Network Discovery</h3>
            <p style={cardTextStyle}>
              Publish your datasets to the GFBio network infrastructure, enhancing visibility and accessibility for the research community.
            </p>
          </div>
        </div>
      </section>

      {/* Platform Overview with Live Statistics */}
      <section style={socialProofSectionStyle}>
        <div style={heroContentStyle}>
          <h2 style={sectionHeaderStyle}>Platform Overview</h2>
          {statsError && (
            <p style={{ textAlign: 'center', color: 'var(--text-light)', marginBottom: '1rem' }}>
              Live statistics are currently unavailable.
            </p>
          )}
          <div style={{
            display: 'grid',
            gridTemplateColumns: getGridColumns(300),
            gap: '2rem',
            marginBottom: '2rem'
          }}>
            <StatCard
              title="Data Providers"
              value={stats?.total_providers || 0}
              isLoading={isLoadingStats}
              color="var(--success)"
            />

            <StatCard
              title="Data Centers"
              value={stats?.total_datacenters || 0}
              isLoading={isLoadingStats}
              color="var(--warning)"
            />

            <StatCard
              title="Total Datasets"
              value={stats?.total_datasets || 0}
              isLoading={isLoadingStats}
              color="var(--primary)"
            />
          </div>

          {/* Link to full statistics dashboard - centered */}
          <div style={{
            display: 'flex',
            justifyContent: 'center',
            marginTop: '2rem',
          }}>
            <Button
              onClick={() => onViewStatistics && onViewStatistics()}
              variant="default"
              style={{
                padding: '0.75rem 1.5rem',
                fontSize: '0.95rem',
                backgroundColor: 'transparent',
                color: 'var(--primary)',
                border: '2px solid var(--primary)',
                borderRadius: '0.5rem',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                fontWeight: 600,
              }}
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = 'var(--primary)';
                e.target.style.color = 'white';
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = 'transparent';
                e.target.style.color = 'var(--primary)';
              }}
            >
              View Detailed Statistics →
            </Button>
          </div>
        </div>
      </section>

    </div>
  );
});

// Add display name for debugging
LandingPage.displayName = 'LandingPage';

export default LandingPage;
