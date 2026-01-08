import React, { useState, useEffect } from 'react';
import { useAuth } from '../auth/AuthContext';
import { apiRequest } from '../../utils/apiUtils';
import Alert from '../ui/Alert';
import Button from '../ui/Button';
import Modal from '../ui/Modal';
import ConfirmModal from '../ui/ConfirmModal';
import Breadcrumbs from '../ui/Breadcrumbs';
import ActionMenu from '../ui/ActionMenu';
import ProviderCard from '../providers/ProviderCard';
import ProviderForm from '../providers/ProviderForm';
import { Plus, Search } from 'lucide-react';
import { showToast } from '../ui/Toast';

// Providers component with improved nested form integration
function Providers({ currentUser, onViewProviderDetails }) {
  const { handleTokenExpiration } = useAuth();
  const [providers, setProviders] = useState([]);
  const [filteredProviders, setFilteredProviders] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingProvider, setEditingProvider] = useState(null);
  const [addingProvider, setAddingProvider] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const fetchProviders = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const res = await apiRequest('/data-providers', {}, handleTokenExpiration);
      
      if (!res.ok) {
        if (res.status === 403) {
          setError('You do not have permission to view providers');
        } else {
          setError('Failed to fetch providers');
        }
        setIsLoading(false);
        return;
      }
      
      const data = await res.json();
      setProviders(data);
      setIsLoading(false);
    } catch (err) {
      setError('Error fetching providers: ' + err.message);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProviders();
  }, []);

  // Filter providers based on search query
  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredProviders(providers);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = providers.filter(provider => {
        // Filter on name
        if (provider.name && provider.name.toLowerCase().includes(query)) {
          return true;
        }
        // Filter on shortName
        if (provider.shortName && provider.shortName.toLowerCase().includes(query)) {
          return true;
        }
        // Filter on datacenter
        if (provider.datacenter && provider.datacenter.toLowerCase().includes(query)) {
          return true;
        }
        // Filter on id
        if (provider.id && provider.id.toString().includes(query)) {
          return true;
        }
        return false;
      });
      setFilteredProviders(filtered);
    }
  }, [searchQuery, providers]);

  const deleteProvider = async (id) => {
    try {
      const res = await apiRequest(`/data-providers/${id}`, {
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
      
      // Remove from local state and close modal
      const deletedProvider = providers.find(p => p.id === id);
      setProviders(providers.filter(p => p.id !== id));
      setConfirmDelete(null);
      setError('');
      showToast(`Provider "${deletedProvider?.name}" deleted successfully!`, 'success');
    } catch (err) {
      console.error('Error deleting provider:', err);
      if (!err.message?.includes('Session expired')) {
        setError('Error deleting provider: ' + err.message);
      }
    }
  };

  const closeModals = () => {
    setEditingProvider(null);
    setAddingProvider(false);
  };

  const handleProviderUpdate = (updatedProvider) => {
    if (!updatedProvider) {
      closeModals();
      return;
    }
    
    // Update the local state immediately with the new data
    if (editingProvider) {
      setProviders(providers.map(p => 
        p.id === updatedProvider.id ? updatedProvider : p
      ));
    } else {
      setProviders([...providers, updatedProvider]);
    }
    
    closeModals();
  };

  // Breadcrumb items for Providers
  const breadcrumbItems = [
    { label: 'Home', onClick: () => window.location.href = '/' },
    { label: 'Providers', onClick: null }
  ];

  return (
    <div style={{ 
      flexGrow: 1,
      padding: '2rem 1rem',
      width: '100%',
    }}
    className="content-container">
      {/* Breadcrumbs navigation */}
      <Breadcrumbs items={breadcrumbItems} />
    
      {/* Page title and actions */}
      <div style={{
        marginBottom: '2rem',
        marginTop: '1rem',
      }}>
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: 600,
          color: 'var(--text)',
          marginBottom: '0.5rem',
        }}>
          Providers
        </h2>
        <p style={{
          fontSize: '1rem',
          color: 'var(--text-light)',
          margin: 0,
          lineHeight: '1.5',
        }}>
          Manage data providers and their institutional information.
        </p>
      </div>
      
      {/* Floating action menu */}
      {currentUser?.is_global_admin && (
        <ActionMenu
          actions={[
            {
              icon: <Plus size={24} />,
              label: 'Add Provider',
              onClick: () => { setAddingProvider(true); setEditingProvider(null); },
              color: 'var(--primary)'
            }
          ]}
          mode="content-relative"
          offset={16}
        />
      )}
      
      {error && <Alert type="error">{error}</Alert>}
      
      {/* Search filter - only show when there are more than 6 providers */}
      {providers.length > 6 && (
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
            placeholder="Search providers..."
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
      )}
      
      {isLoading && !addingProvider && !editingProvider ? (
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          alignItems: 'center', 
          padding: '4rem 0' 
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
      ) : providers.length === 0 && !addingProvider ? (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          backgroundColor: 'var(--card-bg)',
          borderRadius: '0.75rem',
          color: 'var(--text-light)',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        }}>
          <h3 style={{ marginTop: 0, color: 'var(--text)' }}>No providers found</h3>
          <p style={{ marginBottom: '1.5rem' }}>Get started by adding your first data provider</p>
          {currentUser?.is_global_admin && (
            <Button onClick={() => { setAddingProvider(true); setEditingProvider(null); }}>
              Add Provider
            </Button>
          )}
        </div>
      ) : (
        <>
          {filteredProviders.length > 0 ? (
            <div style={{ 
              display: 'grid', 
              gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', 
              gap: '1.5rem',
              marginBottom: '2rem',
            }}>
              {filteredProviders.map((provider) => (
                <ProviderCard 
                  key={provider.id}
                  provider={provider}
                  currentUser={currentUser}
                  onEdit={(provider) => { setEditingProvider(provider); setAddingProvider(true); }}
                  onDelete={(provider) => setConfirmDelete(provider)}
                  onViewDetails={onViewProviderDetails}
                />
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
                No providers match your search criteria. Try a different search term.
              </p>
            </div>
          )}
        </>
      )}
      
      {confirmDelete && (
        <ConfirmModal
          isOpen={true}
          title="Delete Provider"
          message={`Are you sure you want to delete "${confirmDelete.name}"? This will remove all associated datasets.`}
          confirmText="Delete"
          cancelText="Cancel"
          confirmVariant="danger"
          onConfirm={() => deleteProvider(confirmDelete.id)}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
      
      <Modal
        isOpen={addingProvider}
        onClose={closeModals}
        title={editingProvider ? `Edit Provider: ${editingProvider.name}` : 'Add Provider'}
      >
        <ProviderForm
          provider={editingProvider}
          onClose={handleProviderUpdate}
          onTokenExpired={handleTokenExpiration}
          currentUser={currentUser}
        />
      </Modal>
    </div>
  );
}

export default Providers;
