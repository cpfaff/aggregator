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
import { Plus } from 'lucide-react';

// Providers component with improved nested form integration
function Providers({ currentUser, onViewProviderDetails }) {
  const { handleTokenExpiration } = useAuth();
  const [providers, setProviders] = useState([]);
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
      setProviders(providers.filter(p => p.id !== id));
      setConfirmDelete(null);
      setError('');
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
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '1rem',
      }}>
        <h2 style={{ 
          fontSize: '1.5rem', 
          fontWeight: 600, 
          marginLeft: '0.1rem',
          color: 'var(--text)',
        }}>
          Providers
        </h2>
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
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', 
          gap: '1.5rem',
          marginBottom: '2rem',
        }}>
        {providers.map((provider) => (
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
