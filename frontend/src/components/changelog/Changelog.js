import React from 'react';
import Breadcrumbs from '../ui/Breadcrumbs';

const Changelog = () => {
  // Changelog entries based on actual project development
  const changelogEntries = [
    {
      version: '1.9.0',
      date: 'July 31, 2025',
      changes: [
        'Added data center classification system to distinguish between official GFBio data centers and regular data providers',
        'Portal administrators can now designate providers as official data centers through the admin interface',
        'Enhanced data provider management with improved categorization for better organization',
        'Strengthened deployment infrastructure with automated database backup system',
        'Improved database migration reliability with enhanced error handling and rollback capabilities',
        'Optimized CI/CD pipeline for more robust and consistent deployments'
      ]
    },
    {
      version: '1.8.0',
      date: 'April 15, 2025',
      changes: [
        'Fixed issue with validation jobs getting stuck in pending state',
        'Improved handling of Celery task IDs to prevent mismatches',
        'Added support for force-revalidation of datasets',
        'Enhanced validation status tracking with obsolete state detection',
        'Improved validation error messages with better formatting and examples',
        'Fixed inconsistencies in displayed validation timestamps'
      ]
    },
    {
      version: '1.7.0',
      date: 'April 10, 2025',
      changes: [
        'Added maintenance mode feature for smoother service updates and deployments',
        'Improved CI/CD pipeline for production deployments with GitLab',
        'Enhanced docker-compose configuration with maintenance container',
        'Added Makefile commands for enabling/disabling maintenance mode',
        'Updated environment variable handling for better deployment flexibility'
      ]
    },
    {
      version: '1.6.0',
      date: 'March 25, 2025',
      changes: [
        'Added XML validation system with support for ABCD schemas (2.06, 2.1, 3.0)',
        'Implemented validation job model for tracking validation progress and results',
        'Created API versioning structure for better maintainability',
        'Added validation results modal to display validation details in frontend',
        'Implemented asynchronous validation task processing with Celery',
        'Enhanced database performance with additional indexes on relationship columns',
        'Updated Docker configuration to support validator microservice'
      ]
    },
    {
      version: '1.5.1',
      date: 'March 18, 2025',
      changes: [
        'Added timestamp tracking for providers and datasets with created_at and updated_at fields',
        'Implemented "Last updated" information display on provider and dataset cards',
        'Added database migration to support timestamp fields',
        'Improved UI with subtle timestamp display that maintains visual hierarchy'
      ]
    },
    {
      version: '1.5.0',
      date: 'March 17, 2025',
      changes: [
        'Improved cache invalidation strategy for better data consistency across the application',
        'Fixed issues with provider overview not immediately reflecting new datasets',
        'Enhanced data synchronization between related entities (providers, datasets, XML archives, and useful links)',
        'Optimized backend performance with more efficient cache management',
        'Fixed UI inconsistencies when creating or updating related entities',
        'Refactored frontend codebase with improved component organization and structure'
      ]
    },
    {
      version: '1.4.0',
      date: 'March 14, 2025',
      changes: [
        'Enhanced ActionMenu component with content-relative positioning for improved usability',
        'Fixed dataset deletion functionality to correctly respect provider-admin permissions',
        'Improved UI design consistency across provider and dataset detail views',
        'Added proper role-based access control for editing and deleting datasets',
        'Optimized layout and positioning for action buttons across all views'
      ]
    },
    {
      version: '1.3.0',
      date: 'March 13, 2025',
      changes: [
        'Added Changelog page to track application updates',
        'Implemented "single latest" selection logic for XML archives and useful links',
        'Enhanced breadcrumb navigation with dark mode support',
        'Improved UI spacing and minor visual refinements across dashboard components'
      ]
    },
    {
      version: '1.2.0',
      date: 'March 5, 2025',
      changes: [
        'Implemented global AuthContext for centralized authentication management',
        'Added automatic token refresh to prevent session timeouts',
        'Improved event-based token synchronization across components',
        'Created floating ActionMenu component for quick access to common actions',
        'Enhanced user experience with better session expiration handling'
      ]
    },
    {
      version: '1.1.0',
      date: 'February 28, 2025',
      changes: [
        'Standardized API endpoints to use consistent kebab-case convention',
        'Improved error handling and feedback in form submissions',
        'Added comprehensive test suite for backend API',
        'Enhanced data organization with separate provider data sources',
        'Fixed bugs in provider associations and resource handling'
      ]
    },
    {
      version: '1.0.0',
      date: 'February 24, 2025',
      changes: [
        'Initial release of Data Provider Manager',
        'Implemented JWT-based user authentication and authorization',
        'Created provider and dataset management system',
        'Added XML archive and useful links management functionality',
        'Set up database migrations with Alembic',
        'Implemented Docker-based deployment configuration'
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
        marginBottom: '3rem',
        marginTop: '1rem',
        textAlign: 'center'
      }}>
        <h2 style={{ 
          fontSize: '2rem', 
          fontWeight: 700, 
          color: 'var(--text)',
          marginBottom: '0.5rem'
        }}>
          History
        </h2>
        <p style={{
          fontSize: '1rem',
          color: 'var(--text-light)',
          margin: 0,
          maxWidth: '600px',
          marginLeft: 'auto',
          marginRight: 'auto',
          lineHeight: '1.5'
        }}>
          Track the evolution of the Data Provider Manager platform through our release history
        </p>
      </div>
      
      {/* Timeline Container */}
      <div style={{
        position: 'relative',
        maxWidth: '900px',
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
                maxWidth: isMobile ? 'none' : '420px',
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
                    marginBottom: '1rem',
                    margin: 0,
                    marginBottom: '1rem'
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
              {!isMobile && <div style={{ flex: 1, maxWidth: '420px' }} />}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Changelog;
