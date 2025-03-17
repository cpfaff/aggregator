import React from 'react';
import Breadcrumbs from '../ui/Breadcrumbs';

const Changelog = () => {
  // Changelog entries based on actual project development
  const changelogEntries = [
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
        padding: '2rem', 
        maxWidth: '1200px', 
        margin: '0 auto', 
        width: '100%' 
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
        marginBottom: '2rem',
        marginTop: '1rem' 
      }}>
        <h2 style={{ 
          fontSize: '1.5rem', 
          fontWeight: 600, 
          color: 'var(--text)',
        }}>
          Changelog
        </h2>
      </div>
      
      <div style={{
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.75rem',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
        border: '1px solid var(--border)',
        overflow: 'hidden',
      }}>
        {changelogEntries.map((entry, entryIndex) => (
          <div 
            key={entry.version}
            style={{
              padding: '1.5rem',
              borderBottom: entryIndex !== changelogEntries.length - 1 ? '1px solid var(--border)' : 'none',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <h3 style={{ 
                fontSize: '1.125rem', 
                fontWeight: 600, 
                margin: 0,
                color: 'var(--text)',
              }}>
                Version {entry.version}
              </h3>
              <span style={{ 
                fontSize: '0.875rem',
                color: 'var(--text-light)',
                fontWeight: 500
              }}>
                {entry.date}
              </span>
            </div>
            
            <ul style={{ 
              margin: 0, 
              paddingLeft: '1.5rem', 
              color: 'var(--text)'
            }}>
              {entry.changes.map((change, index) => (
                <li key={index} style={{ marginBottom: '0.5rem' }}>
                  {change}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Changelog;
