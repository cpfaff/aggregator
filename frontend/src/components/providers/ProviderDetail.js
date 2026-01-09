import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { apiRequest } from '../../utils/apiUtils';
import { Globe, Server, Plus, Search, ArrowLeft, Database, ExternalLink, Edit, Trash2, CheckCircle, TrendingUp } from 'lucide-react';
import Alert from '../ui/Alert';
import Modal from '../ui/Modal';
import Breadcrumbs from '../ui/Breadcrumbs';
import ActionMenu from '../ui/ActionMenu';
import DatasetCard from '../datasets/DatasetCard';
import DatasetForm from '../datasets/DatasetForm';
import ProviderForm from './ProviderForm';
import ConfirmModal from '../ui/ConfirmModal';
import { ProviderStatistics } from '../statistics';
import { showToast } from '../ui/Toast';
import { authStatsApi } from '../../utils/statisticsApi';

const ProviderDetail = ({ currentUser }) => {
  const { id } = useParams();
  const navigate = useNavigate();
  const { handleTokenExpiration } = useAuth();
  const [provider, setProvider] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [filteredDatasets, setFilteredDatasets] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingProvider, setIsLoadingProvider] = useState(true);
  const [error, setError] = useState('');
  const [editingDataset, setEditingDataset] = useState(null);
  const [addingDataset, setAddingDataset] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [editingProvider, setEditingProvider] = useState(null);
  const [addingProvider, setAddingProvider] = useState(false);
  const [showStatistics, setShowStatistics] = useState(false);
  const [providerStats, setProviderStats] = useState(null);

  // Fetch provider stats
  const fetchProviderStats = async () => {
    try {
      const stats = await authStatsApi.getProviderStats(id, handleTokenExpiration);
      setProviderStats(stats);
    } catch (err) {
      console.error('Error fetching provider stats:', err);
    }
  };

  // Fetch provider data when component mounts or ID changes
  useEffect(() => {
    fetchProvider();
  }, [id]);

  // Fetch datasets and stats when provider is loaded
  useEffect(() => {
    if (provider) {
      fetchDatasets();
      fetchProviderStats();
    }
  }, [provider]);

  useEffect(() => {
    if (searchQuery.trim() === '') {
      // Ensure datasets are properly normalized before setting filteredDatasets
      const normalizedDatasets = datasets.map(dataset => ({
        ...dataset,
        xmlArchives: Array.isArray(dataset.xmlArchives) ? dataset.xmlArchives : [],
        usefulLinks: Array.isArray(dataset.usefulLinks) ? dataset.usefulLinks : []
      }));
      setFilteredDatasets(normalizedDatasets);
    } else {
      const query = searchQuery.toLowerCase();
      // Apply the same normalization during filtering
      const filtered = datasets.filter(dataset => {
        // Ensure properties are properly normalized for filtering
        const normalizedDataset = {
          ...dataset,
          xmlArchives: Array.isArray(dataset.xmlArchives) ? dataset.xmlArchives : [],
          usefulLinks: Array.isArray(dataset.usefulLinks) ? dataset.usefulLinks : []
        };
        
        // Filter on title
        if (normalizedDataset.title && normalizedDataset.title.toLowerCase().includes(query)) {
          return true;
        }
        // Filter on source
        if (normalizedDataset.source && normalizedDataset.source.toLowerCase().includes(query)) {
          return true;
        }
        // Filter on id
        if (normalizedDataset.id && normalizedDataset.id.toString().includes(query)) {
          return true;
        }
        // Filter on landing page URL
        if (normalizedDataset.landingPageUrl && normalizedDataset.landingPageUrl.toLowerCase().includes(query)) {
          return true;
        }
        // Filter on number of archives or links - use normalized data
        if (normalizedDataset.xmlArchives.length.toString().includes(query)) {
          return true;
        }
        if (normalizedDataset.usefulLinks.length.toString().includes(query)) {
          return true;
        }
        
        return false;
      });
      
      // Make sure the filtered results are also normalized
      const normalizedFiltered = filtered.map(dataset => ({
        ...dataset,
        xmlArchives: Array.isArray(dataset.xmlArchives) ? dataset.xmlArchives : [], 
        usefulLinks: Array.isArray(dataset.usefulLinks) ? dataset.usefulLinks : []
      }));
      
      setFilteredDatasets(normalizedFiltered);
    }
  }, [searchQuery, datasets]);

  const fetchProvider = async () => {
    setIsLoadingProvider(true);
    setError('');
    
    try {
      const res = await apiRequest(`/data-providers/${id}`, {}, handleTokenExpiration);
      
      if (!res.ok) {
        if (res.status === 404) {
          setError('Provider not found');
        } else if (res.status === 403) {
          setError('You do not have permission to view this provider');
        } else {
          setError('Failed to fetch provider details');
        }
        setIsLoadingProvider(false);
        return;
      }
      
      const data = await res.json();
      setProvider(data);
      setIsLoadingProvider(false);
    } catch (err) {
      setError('Error fetching provider: ' + err.message);
      setIsLoadingProvider(false);
    }
  };

  const fetchDatasets = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const res = await apiRequest(`/data-providers/${id}/data-sets`, {}, handleTokenExpiration);
      
      if (!res.ok) {
        setError('Failed to fetch datasets');
        setIsLoading(false);
        return;
      }
      
      const data = await res.json();
      
      // Ensure each dataset has properly normalized data and provider_id
      const normalizedData = data.map(dataset => ({
        ...dataset,
        provider_id: id, // Ensure provider_id is set correctly
        xmlArchives: Array.isArray(dataset.xmlArchives) ? dataset.xmlArchives : [],
        usefulLinks: Array.isArray(dataset.usefulLinks) ? dataset.usefulLinks : []
      }));
      
      setDatasets(normalizedData);
      setIsLoading(false);
    } catch (err) {
      setError('Error fetching datasets: ' + err.message);
      setIsLoading(false);
    }
  };

  const deleteDataset = async (datasetId) => {
    try {
      const res = await apiRequest(`/data-providers/${id}/data-sets/${datasetId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        }
      }, handleTokenExpiration);
      
      if (!res.ok) {
        let errorMessage = 'Failed to delete dataset';
        try {
          const errorData = await res.json();
          if (res.status === 403) {
            errorMessage = 'You do not have permission to delete this dataset';
          } else if (res.status === 404) {
            errorMessage = 'Dataset not found';
          } else {
            errorMessage = errorData.detail || errorMessage;
          }
        } catch (e) {
          console.error('Error parsing error response:', e);
        }
        setError(errorMessage);
        return;
      }
      
      // After successful deletion, update the UI
      const deletedDataset = datasets.find(d => d.id === datasetId);
      setDatasets(datasets.filter(d => d.id !== datasetId));
      setConfirmDelete(null);
      setError('');
      showToast(`Dataset "${deletedDataset?.title}" deleted successfully!`, 'success');
    } catch (err) {
      console.error('Error deleting dataset:', err);
      if (!err.message?.includes('Session expired')) {
        setError('Error deleting dataset: ' + err.message);
      }
    }
  };

  const handleDatasetUpdate = async (updatedDataset) => {
    if (!updatedDataset) {
      setEditingDataset(null);
      setAddingDataset(false);
      return;
    }
    
    // Handle adding a new dataset
    if (!editingDataset) {
      // For new datasets, use the data directly from the API response and ensure provider_id
      const normalizedDataset = {
        ...updatedDataset,
        provider_id: id, // Ensure provider_id is set
        xmlArchives: Array.isArray(updatedDataset.xmlArchives) ? updatedDataset.xmlArchives : [],
        usefulLinks: Array.isArray(updatedDataset.usefulLinks) ? updatedDataset.usefulLinks : []
      };
      
      // Add to datasets using functional update
      setDatasets(prevDatasets => [...prevDatasets, normalizedDataset]);
      
      setEditingDataset(null);
      setAddingDataset(false);
      return;
    }
    
    // For the most reliable update, re-fetch all datasets after an edit
    // This ensures we always have the most current data from the API
    setIsLoading(true);
    setEditingDataset(null);
    setAddingDataset(false);
    
    try {
      await fetchDatasets();
    } catch (err) {
      console.error('Error refreshing datasets:', err);
      setIsLoading(false);
    }
  };

  const deleteProvider = async (providerId) => {
    try {
      const res = await apiRequest(`/data-providers/${providerId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json'
        }
      }, handleTokenExpiration);
      
      if (!res.ok) {
        let errorMessage = 'Failed to delete provider';
        try {
          const errorData = await res.json();
          if (res.status === 403) {
            errorMessage = 'You do not have permission to delete this provider';
          } else if (res.status === 404) {
            errorMessage = 'Provider not found';
          } else {
            errorMessage = errorData.detail || errorMessage;
          }
        } catch (e) {
          console.error('Error parsing error response:', e);
        }
        setError(errorMessage);
        return;
      }
      
      // After successful deletion, navigate back to providers list
      showToast(`Provider "${provider?.name}" deleted successfully!`, 'success');
      navigate('/providers');
      setError('');
    } catch (err) {
      console.error('Error deleting provider:', err);
      if (!err.message?.includes('Session expired')) {
        setError('Error deleting provider: ' + err.message);
      }
    }
  };

  // Breadcrumb items
  const breadcrumbItems = [
    { label: 'Home', onClick: () => navigate('/') },
    { label: 'Providers', onClick: () => navigate('/providers') },
    { label: provider?.name || 'Provider Detail', onClick: null }
  ];

  // Show loading state while fetching provider
  if (isLoadingProvider) {
    return (
      <div style={{ 
        flexGrow: 1,
        padding: '2rem 1rem',
        width: '100%',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center'
      }}>
        <div style={{
          width: '32px',
          height: '32px',
          border: '3px solid var(--border)',
          borderRadius: '50%',
          borderTopColor: 'var(--primary)',
          animation: 'spin 1s linear infinite',
        }}></div>
      </div>
    );
  }

  // Show error if provider not found
  if (!provider && !isLoadingProvider) {
    return (
      <div style={{ 
        flexGrow: 1,
        padding: '2rem 1rem',
        width: '100%'
      }}>
        <Alert type="error">
          {error || 'Provider not found'}
          <button 
            onClick={() => navigate('/providers')}
            style={{
              marginLeft: '1rem',
              padding: '0.25rem 0.5rem',
              backgroundColor: 'var(--primary)',
              color: 'white',
              border: 'none',
              borderRadius: '0.25rem',
              cursor: 'pointer'
            }}
          >
            Back to Providers
          </button>
        </Alert>
      </div>
    );
  }

  if (!provider) return null;

  return (
    <div 
      style={{ 
        flexGrow: 1,
        padding: '2rem 1rem',
        width: '100%',
      }}
      className="content-container"
    >
      {/* Breadcrumbs navigation */}
      <Breadcrumbs items={breadcrumbItems} />
      
      {/* Floating action menu - visible to both global admins and provider curators */}
      <ActionMenu
        actions={[
          {
            icon: <Plus size={24} />,
            label: 'Add Dataset',
            onClick: () => { setAddingDataset(true); setEditingDataset(null); },
            color: 'var(--primary)'
          }
        ]}
        mode="content-relative"
        offset={16}
      />
      
      {/* Provider details card with integrated title */}
      <div style={{
        backgroundColor: 'var(--card-bg)',
        borderRadius: '0.75rem',
        border: '1px solid var(--border)',
        padding: '1.5rem',
        marginBottom: '2rem'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
          <div>
            <h2 style={{ 
              fontSize: '1.5rem', 
              fontWeight: 600, 
              margin: 0,
              color: 'var(--text)',
            }}>
              {provider.name}
            </h2>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-light)', margin: '0.25rem 0 0' }}>
              {provider.datacenter}
            </p>
          </div>
          <span style={{
            backgroundColor: 'var(--subtle-bg)',
            padding: '0.375rem 0.75rem',
            borderRadius: '0.375rem',
            fontSize: '0.875rem',
            fontWeight: 500
          }}>
            {provider.shortName}
          </span>
        </div>

        {/* Stats section */}
        <div style={{
          marginTop: '1.5rem',
          marginBottom: '1.5rem',
          paddingLeft: '0.25rem'
        }}>
          {/* Stats content with accent bar */}
          <div style={{ position: 'relative' }}>
            {/* Vertical border */}
            <div style={{
              position: 'absolute',
              top: 0,
              bottom: 0,
              left: '0.25rem',
              width: '1.5px',
              backgroundColor: 'var(--text-light)',
              opacity: 0.4,
              zIndex: 0
            }}></div>

            <div style={{
              fontSize: '0.8125rem',
              textTransform: 'uppercase',
              fontWeight: 600,
              color: 'var(--text-light)',
              marginBottom: '0.75rem',
              letterSpacing: '0.025em',
              display: 'flex',
              alignItems: 'center',
              paddingLeft: '0.75rem',
              position: 'relative',
              zIndex: 1
            }}>
              Stats
            </div>

            <div style={{
              paddingLeft: '1.5rem',
              position: 'relative',
              zIndex: 1,
              display: 'flex',
              flexDirection: 'column',
              gap: '0.5rem'
            }}>
              {/* Datasets count */}
              <div style={{
                display: 'flex',
                alignItems: 'center'
              }}>
                <Database
                  size={15}
                  style={{
                    color: 'var(--primary)',
                    marginRight: '0.75rem',
                    flexShrink: 0
                  }}
                />
                <span style={{
                  fontSize: '0.8125rem',
                  color: 'var(--text)',
                  display: 'flex',
                  alignItems: 'center',
                }}>
                  <span style={{
                    fontWeight: 600,
                    color: datasets.length > 0 ? 'var(--text)' : 'var(--text-light)',
                    marginRight: '0.375rem'
                  }}>
                    {datasets.length}
                  </span>
                  {datasets.length === 1 ? 'dataset' : 'datasets'}
                </span>
              </div>

              {/* Validation success rate */}
              {providerStats?.validation_success_rate !== undefined && providerStats?.validation_success_rate !== null && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center'
                }}>
                  <CheckCircle
                    size={15}
                    style={{
                      color: 'var(--success)',
                      marginRight: '0.75rem',
                      flexShrink: 0
                    }}
                  />
                  <span style={{
                    fontSize: '0.8125rem',
                    color: 'var(--text)',
                    display: 'flex',
                    alignItems: 'center',
                  }}>
                    <span style={{
                      fontWeight: 600,
                      color: providerStats.validation_success_rate > 0 ? 'var(--text)' : 'var(--text-light)',
                      marginRight: '0.375rem'
                    }}>
                      {providerStats.validation_success_rate.toFixed(1)}%
                    </span>
                    validation success rate
                  </span>
                </div>
              )}

              {/* Action button inside accent bar */}
              <div style={{ marginTop: '0.5rem' }}>
                <button
                  onClick={() => setShowStatistics(true)}
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '0.375rem',
                    padding: '0.375rem 0.75rem',
                    border: '1.5px solid var(--primary)',
                    borderRadius: '0.5rem',
                    backgroundColor: 'var(--card-bg)',
                    fontSize: '0.75rem',
                    fontWeight: 500,
                    color: 'var(--primary)',
                    cursor: 'pointer',
                    transition: 'all 150ms ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--subtle-bg)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.backgroundColor = 'var(--card-bg)';
                  }}
                >
                  <TrendingUp size={14} />
                  View Trends
                </button>
              </div>
            </div>
          </div>
        </div>
        
        {/* Links section with flatter design */}
        <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: '1rem', position: 'relative' }}>
          {/* Vertical border for the section */}
          <div style={{
            position: 'absolute',
            top: '1rem',
            bottom: 0,
            left: '0.25rem',
            width: '1.5px',
            backgroundColor: 'var(--text-light)',
            opacity: 0.4,
            zIndex: 0
          }}></div>
          
          {/* Links header */}
          <div style={{ 
            fontSize: '0.8125rem', 
            textTransform: 'uppercase', 
            fontWeight: 600, 
            color: 'var(--text-light)',
            marginBottom: '0.75rem',
            letterSpacing: '0.025em',
            display: 'flex',
            alignItems: 'center',
            paddingLeft: '0.75rem',
            position: 'relative',
            zIndex: 1
          }}>
            Links
          </div>
          
          {/* Links content */}
          <div style={{ 
            paddingLeft: '1.5rem',
            position: 'relative',
            zIndex: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: '0.75rem'
          }}>
            {/* Website link */}
            {provider.url && (
              <a 
                href={provider.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{ 
                  display: 'flex', 
                  alignItems: 'center',
                  fontSize: '0.8125rem',
                  color: 'var(--text)',
                  textDecoration: 'none',
                  transition: 'color 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = 'var(--primary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = 'var(--text)';
                }}
              >
                <Globe size={15} style={{ marginRight: '0.75rem', color: 'var(--primary)', flexShrink: 0 }} />
                Website
                <ExternalLink size={12} style={{ marginLeft: '0.375rem', opacity: 0.5 }} />
              </a>
            )}
            
            {/* BioCASe link */}
            {provider.biocaseUrl && (
              <a 
                href={provider.biocaseUrl}
                target="_blank"
                rel="noopener noreferrer"
                style={{ 
                  display: 'flex', 
                  alignItems: 'center',
                  fontSize: '0.8125rem',
                  color: 'var(--text)',
                  textDecoration: 'none',
                  transition: 'color 0.2s',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = 'var(--primary)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = 'var(--text)';
                }}
              >
                <Server size={15} style={{ marginRight: '0.75rem', color: 'var(--primary)', flexShrink: 0 }} />
                BioCASe Provider
                <ExternalLink size={12} style={{ marginLeft: '0.375rem', opacity: 0.5 }} />
              </a>
            )}
          </div>
        </div>
        
        {/* ACTIONS FOOTER */}
        <div style={{ 
          display: 'flex',
          padding: '0.75rem 1.25rem',
          gap: '0.625rem',
          borderTop: '1px solid var(--border)',
          justifyContent: 'flex-end',
          backgroundColor: 'var(--card-bg)',
          minHeight: '52px',
          height: 'auto',
          flexShrink: 0,
          boxSizing: 'border-box',
          marginTop: '1.5rem',
          marginLeft: '-1.5rem',
          marginRight: '-1.5rem',
          marginBottom: '-1.5rem',
          borderBottomLeftRadius: '0.75rem',
          borderBottomRightRadius: '0.75rem'
        }}>
          {/* Edit Button - visible to all */}
          <button 
            onClick={() => { setEditingProvider(provider); setAddingProvider(true); }}
            style={{
              width: '36px',
              height: '36px',
              backgroundColor: 'var(--subtle-bg)',
              color: 'var(--text-light)',
              border: 'none',
              borderRadius: '0.375rem',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
              padding: 0
            }}
            aria-label={`Edit provider: ${provider.name}`}
            title="Edit provider"
          >
            <Edit size={18} />
          </button>
          
          {/* Delete Button - only visible to global admins */}
          {currentUser?.is_global_admin && (
            <button 
              onClick={() => setConfirmDelete(provider)}
              style={{
                width: '36px',
                height: '36px',
                backgroundColor: 'var(--subtle-bg)',
                color: 'var(--error)',
                border: 'none',
                borderRadius: '0.375rem',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                transition: 'all 0.2s',
                padding: 0
              }}
              aria-label={`Delete provider: ${provider.name}`}
              title="Delete provider"
            >
              <Trash2 size={18} />
            </button>
          )}
        </div>
      </div>
      
      {error && <Alert type="error">{error}</Alert>}
      
      {datasets.length > 0 && (
        <div style={{ marginTop: '2rem' }}>
          <div style={{
            marginBottom: '1rem'
          }}>
            {/* Search Input - Full width */}
            <div style={{
              position: 'relative',
              width: '100%',
              marginBottom: '1.25rem',
            }}>
              <Search 
                size={18} 
                style={{
                  position: 'absolute',
                  left: '0.75rem',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  color: 'var(--text-light)'
                }}
              />
              <input
                type="text"
                placeholder="Search datasets..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  height: '2.75rem',
                  padding: '0.5rem 0.75rem 0.5rem 2.5rem',
                  fontSize: '0.875rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--card-bg)',
                  color: 'var(--text)',
                  outline: 'none',
                  transition: 'border-color 0.2s, box-shadow 0.2s',
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'var(--primary)';
                  e.target.style.boxShadow = '0 0 0 2px rgba(var(--primary-rgb), 0.2)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = 'var(--border)';
                  e.target.style.boxShadow = 'none';
                }}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  style={{
                    position: 'absolute',
                    right: '0.75rem',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'none',
                    border: 'none',
                    fontSize: '1.25rem',
                    lineHeight: 1,
                    color: 'var(--text-light)',
                    cursor: 'pointer',
                    padding: '0',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '1.5rem',
                    height: '1.5rem',
                    borderRadius: '50%',
                  }}
                  aria-label="Clear search"
                >
                  &times;
                </button>
              )}
            </div>
          </div>

          {filteredDatasets.length > 0 ? (
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', 
              gap: '1.5rem',
              marginBottom: '1.5rem'
            }}>
              {filteredDatasets.map(dataset => (
                <div key={dataset.id}>
                  <DatasetCard 
                    dataset={dataset} 
                    onEdit={(dataset) => {
                      setEditingDataset(dataset);
                      setAddingDataset(true);
                    }} 
                    onDelete={(dataset) => {
                      setConfirmDelete(dataset);
                    }}
                  />
                </div>
              ))}
            </div>
          ) : (
            <div style={{
              padding: '2rem',
              textAlign: 'center',
              backgroundColor: 'var(--subtle-bg)',
              borderRadius: '0.75rem',
              color: 'var(--text-light)',
            }}>
              <p style={{ margin: 0, fontSize: '1rem' }}>
                No datasets match your search criteria. Try a different search term.
              </p>
            </div>
          )}
         </div>
      )}
      
      {/* Confirmation modal for deletion */}
      {confirmDelete && (
        <ConfirmModal
          isOpen={true}
          title={confirmDelete.title ? "Delete Dataset" : "Delete Provider"}
          message={confirmDelete.title 
            ? `Are you sure you want to delete dataset "${confirmDelete.title}"?`
            : `Are you sure you want to delete "${confirmDelete.name}"? This will remove all associated datasets.`}
          confirmText="Delete"
          cancelText="Cancel"
          confirmVariant="danger"
          onConfirm={() => {
            if (confirmDelete.title) {
              // This is a dataset deletion
              deleteDataset(confirmDelete.id);
            } else {
              // This is a provider deletion
              deleteProvider(confirmDelete.id);
            }
          }}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
      
      {/* Dataset form modal */}
      <Modal
        isOpen={addingDataset}
        onClose={() => { setAddingDataset(false); setEditingDataset(null); }}
        title={editingDataset ? `Edit Dataset: ${editingDataset.title}` : 'Add Dataset'}
      >
        <DatasetForm
          providerId={id}
          dataset={editingDataset}
          onClose={handleDatasetUpdate}
          onTokenExpired={handleTokenExpiration}
        />
      </Modal>
      
      {/* Modal for editing provider */}
      <Modal
        isOpen={addingProvider}
        onClose={() => { setAddingProvider(false); setEditingProvider(null); }}
        title={`Edit Provider: ${editingProvider?.name || ""}`}
      >
        <ProviderForm
          provider={editingProvider}
          onClose={(updatedProvider) => {
            // If we got an updated provider, refresh the current provider data
            if (updatedProvider) {
              // Update the local state with the updated provider data
              const updatedProviderData = {
                ...provider,
                ...updatedProvider
              };
              
              // Update the local provider state with new data
              setProvider(updatedProviderData);
            }
            setAddingProvider(false);
            setEditingProvider(null);
          }}
          onTokenExpired={handleTokenExpiration}
          currentUser={currentUser}
        />
      </Modal>

      {/* Provider Trends Modal */}
      <Modal
        isOpen={showStatistics}
        onClose={() => setShowStatistics(false)}
        title="Trends"
        size="large"
      >
        <ProviderStatistics 
          providerId={id}
          providerName={provider?.name}
        />
      </Modal>
    </div>
  );
};

export default ProviderDetail;