import React from 'react';
import Breadcrumbs from '../ui/Breadcrumbs';

/**
 * CHANGELOG CONTENT GUIDELINES
 * ============================
 *
 * Rule 1: Maximum 5 bullet points per release
 *         - Forces prioritization of the most important user-facing changes
 *         - Group minor fixes into "Various bug fixes and performance improvements"
 *
 * Rule 2: User-focused language
 *         - Describe WHAT users can do, not HOW it was built
 *         - Good: "New statistics dashboard with real-time charts"
 *         - Bad: "Implemented React component with Redux state management"
 *
 * Rule 3: No internal implementation details
 *         - No technology names (Celery, Docker, React, Alembic, JWT, etc.)
 *         - No infrastructure details (CI/CD, GitLab, database queries, caching)
 *         - No security implementation specifics (token refresh, auth context)
 *         - No internal tooling (Makefile, task management, test suites)
 *
 * Rule 4: No DevOps or deployment information
 *         - Users don't need to know about deployments, migrations, or pipelines
 *
 * Rule 5: Combine related items
 *         - Instead of 5 separate bug fixes, use "Various bug fixes and improvements"
 */

const Changelog = () => {
  const changelogEntries = [
    {
      version: '2.0.2',
      date: 'January 9, 2026',
      changes: [
        'Added unsaved changes confirmation when closing forms',
        'Redesigned validation statistics with new Trends modal',
        'Improved visual consistency across page headers',
        'Enhanced login error display with clearer messages',
        'Various bug fixes and stability improvements'
      ]
    },
    {
      version: '2.0.1',
      date: 'January 7, 2026',
      changes: [
        'Simplified statistics system with improved reliability',
        'Performance improvements and codebase optimization',
        'Improved handling of data collection errors'
      ]
    },
    {
      version: '2.0.0',
      date: 'September 5, 2025',
      changes: [
        'New statistics dashboard with real-time data visualization',
        'Added biological units tracking with timeline charts',
        'Advanced search filters for providers and users',
        'Redesigned landing page and footer',
        'Various bug fixes and performance improvements'
      ]
    },
    {
      version: '1.9.0',
      date: 'July 31, 2025',
      changes: [
        'Added data center classification to distinguish official GFBio data centers from regular providers',
        'Portal administrators can now designate providers as official data centers',
        'Improved system reliability and stability'
      ]
    },
    {
      version: '1.8.0',
      date: 'April 15, 2025',
      changes: [
        'Fixed validation jobs getting stuck in pending state',
        'Added support for force-revalidation of datasets',
        'Improved validation error messages and status tracking'
      ]
    },
    {
      version: '1.7.0',
      date: 'April 10, 2025',
      changes: [
        'Added maintenance mode for smoother service updates',
        'Improved deployment reliability'
      ]
    },
    {
      version: '1.6.0',
      date: 'March 25, 2025',
      changes: [
        'Added XML validation system with support for ABCD schemas (2.06, 2.1, 3.0)',
        'Validation progress and results now tracked per dataset',
        'New validation results modal in the interface',
        'Improved database performance'
      ]
    },
    {
      version: '1.5.1',
      date: 'March 18, 2025',
      changes: [
        'Added "Last updated" timestamps on provider and dataset cards',
        'Improved visual hierarchy of timestamp display'
      ]
    },
    {
      version: '1.5.0',
      date: 'March 17, 2025',
      changes: [
        'Improved data consistency — changes now reflect immediately across the application',
        'Fixed provider overview not showing newly added datasets',
        'Various UI improvements and bug fixes'
      ]
    },
    {
      version: '1.4.0',
      date: 'March 14, 2025',
      changes: [
        'Improved action menu positioning for better usability',
        'Fixed dataset deletion permissions for provider admins',
        'UI consistency improvements across detail views'
      ]
    },
    {
      version: '1.3.0',
      date: 'March 13, 2025',
      changes: [
        'Added Changelog page to track application updates',
        'Improved selection logic for XML archives and useful links',
        'Enhanced breadcrumb navigation with dark mode support',
        'Minor visual refinements across dashboard'
      ]
    },
    {
      version: '1.2.0',
      date: 'March 5, 2025',
      changes: [
        'Improved session handling — no more unexpected logouts',
        'Added floating action menu for quick access to common actions',
        'Better session expiration handling'
      ]
    },
    {
      version: '1.1.0',
      date: 'February 28, 2025',
      changes: [
        'Standardized API endpoints for consistency',
        'Improved error handling and form feedback',
        'Fixed bugs in provider associations'
      ]
    },
    {
      version: '1.0.0',
      date: 'February 24, 2025',
      changes: [
        'Initial release of Data Provider Manager',
        'User authentication and authorization',
        'Provider, dataset, and XML archive management',
        'Useful links management functionality'
      ]
    }
  ];

  return (
    <div 
      className="content-container"
      style={{ 
        padding: '2rem 1rem', 
        width: '100%',
        flexGrow: 1,
      }}
    >
      {/* Breadcrumb navigation */}
      <Breadcrumbs 
        items={[
          { label: 'Home', onClick: () => {} },
          { label: 'Changelog', onClick: () => {} }
        ]} 
      />
      
      <div style={{
        maxWidth: '1200px',
        margin: '1rem auto 2rem auto'
      }}>
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: 600,
          color: 'var(--text)',
          marginBottom: '0.5rem'
        }}>
          History
        </h2>
        <p style={{
          fontSize: '1rem',
          color: 'var(--text-light)',
          margin: 0,
          lineHeight: '1.5'
        }}>
          Track the evolution of the platform through our release history.
        </p>
      </div>
      
      {/* Timeline Container */}
      <div style={{
        position: 'relative',
        maxWidth: '1200px',
        margin: '0 auto',
        paddingBottom: '2rem'
      }}>
        {/* Timeline Line */}
        <div style={{
          position: 'absolute',
          left: window.innerWidth <= 768 ? '24px' : '50%',
          transform: window.innerWidth <= 768 ? 'translateX(-50%)' : 'translateX(-50%)',
          width: '2px',
          height: '100%',
          background: 'linear-gradient(to bottom, var(--primary) 0%, var(--border) 100%)',
          zIndex: 1
        }} />
        
        {changelogEntries.map((entry, entryIndex) => {
          const isMobile = window.innerWidth <= 768;
          return (
            <div 
              key={entry.version}
              style={{
                position: 'relative',
                marginBottom: '3rem',
                display: 'flex',
                alignItems: 'flex-start',
                flexDirection: isMobile ? 'row' : (entryIndex % 2 === 0 ? 'row' : 'row-reverse'),
                gap: isMobile ? '1rem' : '2rem'
              }}
            >
              {/* Timeline Indicator */}
              <div style={{
                position: 'absolute',
                left: isMobile ? '24px' : '50%',
                transform: isMobile ? 'translateX(-50%)' : 'translateX(-50%)',
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                backgroundColor: 'var(--primary)',
                border: '4px solid var(--card-bg)',
                boxShadow: '0 0 0 2px var(--primary)',
                zIndex: 2,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: 'white'
                }} />
              </div>
              
              {/* Content Card */}
              <div style={{
                flex: 1,
                maxWidth: isMobile ? 'none' : '520px',
                marginLeft: isMobile ? '60px' : '0',
                backgroundColor: 'var(--card-bg)',
                borderRadius: '12px',
                boxShadow: '0 4px 20px rgba(0, 0, 0, 0.08)',
                border: '1px solid var(--border)',
                padding: isMobile ? '1.5rem' : '2rem',
                position: 'relative',
                transition: 'all 0.3s ease',
                cursor: 'default'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)';
                e.currentTarget.style.boxShadow = '0 6px 24px rgba(0, 0, 0, 0.1)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = 'translateY(0)';
                e.currentTarget.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.08)';
              }}
              >
                {/* Card Arrow - hidden on mobile */}
                {!isMobile && (
                  <div style={{
                    position: 'absolute',
                    top: '24px',
                    [entryIndex % 2 === 0 ? 'right' : 'left']: '-8px',
                    width: '16px',
                    height: '16px',
                    backgroundColor: 'var(--card-bg)',
                    border: '1px solid var(--border)',
                    borderRight: entryIndex % 2 === 0 ? '1px solid var(--border)' : 'none',
                    borderTop: entryIndex % 2 === 0 ? '1px solid var(--border)' : 'none',
                    borderLeft: entryIndex % 2 === 0 ? 'none' : '1px solid var(--border)',
                    borderBottom: entryIndex % 2 === 0 ? 'none' : '1px solid var(--border)',
                    transform: `rotate(${entryIndex % 2 === 0 ? '-45deg' : '135deg'})`,
                    zIndex: 1
                  }} />
                )}
                
                {/* Mobile-specific arrow */}
                {isMobile && (
                  <div style={{
                    position: 'absolute',
                    top: '24px',
                    left: '-8px',
                    width: '16px',
                    height: '16px',
                    backgroundColor: 'var(--card-bg)',
                    border: '1px solid var(--border)',
                    borderRight: 'none',
                    borderTop: 'none',
                    transform: 'rotate(135deg)',
                    zIndex: 1
                  }} />
                )}
                
                {/* Version Header */}
                <div style={{ 
                  marginBottom: '1.5rem',
                  textAlign: isMobile ? 'left' : (entryIndex % 2 === 0 ? 'right' : 'left')
                }}>
                  <h3 style={{ 
                    fontSize: isMobile ? '1.25rem' : '1.5rem', 
                    fontWeight: 700, 
                    margin: 0,
                    color: 'var(--primary)',
                    marginBottom: '0.5rem'
                  }}>
                    v{entry.version}
                  </h3>
                  <div style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    backgroundColor: 'var(--primary-light, var(--bg-light))',
                    color: 'var(--primary)',
                    padding: '0.375rem 0.75rem',
                    borderRadius: '20px',
                    fontSize: '0.875rem',
                    fontWeight: 600,
                    border: '1px solid var(--primary)',
                  }}>
                    {entry.date}
                  </div>
                </div>
                
                {/* Changes List */}
                <div style={{
                  textAlign: 'left'
                }}>
                  <h4 style={{
                    fontSize: '1rem',
                    fontWeight: 600,
                    color: 'var(--text)',
                    margin: 0,
                    marginBottom: '16px'
                  }}>
                    What's New
                  </h4>
                  <ul style={{ 
                    margin: 0, 
                    paddingLeft: '0', 
                    color: 'var(--text)',
                    listStyle: 'none'
                  }}>
                    {entry.changes.map((change, index) => (
                      <li key={index} style={{ 
                        marginBottom: '0.75rem',
                        position: 'relative',
                        paddingLeft: '1.5rem',
                        lineHeight: '1.5',
                        fontSize: isMobile ? '0.9rem' : '1rem'
                      }}>
                        <div style={{
                          position: 'absolute',
                          left: '0',
                          top: isMobile ? '0.4rem' : '0.5rem',
                          width: '6px',
                          height: '6px',
                          borderRadius: '50%',
                          backgroundColor: 'var(--primary)',
                          opacity: 0.7
                        }} />
                        {change}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
              
              {/* Empty space for alternating layout - hidden on mobile */}
              {!isMobile && <div style={{ flex: 1, maxWidth: '520px' }} />}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Changelog;
