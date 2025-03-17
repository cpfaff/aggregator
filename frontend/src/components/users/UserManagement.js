import React, { useState, useEffect } from 'react';
import { Edit, Trash2, Plus } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { apiRequest } from '../../utils/apiUtils';
import Alert from '../ui/Alert';
import Button from '../ui/Button';
import Modal from '../ui/Modal';
import ConfirmModal from '../ui/ConfirmModal';
import Breadcrumbs from '../ui/Breadcrumbs';
import ActionMenu from '../ui/ActionMenu';

// UserManagement component
function UserManagement() {
  const { handleTokenExpiration, user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [editingUser, setEditingUser] = useState(null);
  const [addingUser, setAddingUser] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedRole, setSelectedRole] = useState('admin'); // Set default role to 'admin'
  const [formData, setFormData] = useState({ username: '', password: '', is_global_admin: false, provider_roles: {} });
  const [oldPassword, setOldPassword] = useState('');
  const [confirmDeleteUser, setConfirmDeleteUser] = useState(null);

  // Breadcrumb items for User Management
  const breadcrumbItems = [
    { label: 'Home', onClick: () => window.location.href = '/' },
    { label: 'User Management', onClick: null }
  ];

  const fetchProviders = async () => {
    try {
      const res = await apiRequest('/data-providers', {}, handleTokenExpiration);
      
      if (!res.ok) {
        console.error('Failed to fetch providers:', res.status);
        return;
      }
      
      const data = await res.json();
      setProviders(data);
    } catch (err) {
      console.error('Error fetching providers:', err.message);
    }
  };

  useEffect(() => {
    fetchUsers();
    fetchProviders();
  }, []);

  const handleAddProviderRole = () => {
    if (selectedProvider && selectedRole) {
      setFormData(prev => ({
        ...prev,
        provider_roles: {
          ...prev.provider_roles,
          [selectedProvider]: selectedRole
        }
      }));
      setSelectedProvider('');
      setSelectedRole('admin'); // Reset role to default after adding
    }
  };

  const handleRemoveProviderRole = (providerId) => {
    setFormData(prev => {
      const newRoles = { ...prev.provider_roles };
      delete newRoles[providerId];
      return {
        ...prev,
        provider_roles: newRoles
      };
    });
  };

  const fetchUsers = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const res = await apiRequest('/users', {}, handleTokenExpiration);
      
      if (!res.ok) {
        setError('Failed to fetch users');
        setIsLoading(false);
        return;
      }
      
      const data = await res.json();
      setUsers(data);
      setIsLoading(false);
    } catch (err) {
      setError('Error fetching users: ' + err.message);
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleSaveUser = async (formData) => {
    setIsLoading(true);
    setError('');
    
    try {
      let res;
      if (editingUser) {
        // Create a copy of the user data for the update
        const userData = { 
          is_global_admin: formData.is_global_admin,
          provider_roles: formData.provider_roles
        };
        
        // Only include password if it's not empty
        if (formData.password && formData.password.trim() !== '') {
          userData.password = formData.password;
        }
        
        let requestOptions = {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            user: userData
          })
        };
        
        // If updating password and it's the current user, include old_password
        if (userData.password && currentUser && currentUser.username === editingUser.username) {
          requestOptions = {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              user: userData,
              old_password: oldPassword
            })
          };
        }
        
        res = await apiRequest(`/users/${editingUser.username}`, requestOptions, handleTokenExpiration);
      } else {
        res = await apiRequest('/users', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        }, handleTokenExpiration);
      }
      
      if (!res.ok) {
        let errorMessage = 'Failed to save user';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          // If we can't parse the error response, use the default message
        }
        setError(errorMessage);
        setIsLoading(false);
        return;
      }
      
      setEditingUser(null);
      setAddingUser(false);
      fetchUsers();
      setIsLoading(false);
    } catch (err) {
      // Only set error if it's not a token expiration error
      // Token expiration is handled by the onTokenExpired callback
      if (!err.message || !err.message.includes('Session expired')) {
        setError('Error saving user: ' + err.message);
      }
      setIsLoading(false);
    }
  };

  const handleDeleteUser = async (username) => {
    setIsLoading(true);
    setError('');
    
    try {
      const res = await apiRequest(`/users/${username}`, {
        method: 'DELETE'
      }, handleTokenExpiration);
      
      if (!res.ok) {
        let errorMessage = 'Failed to delete user';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          // If we can't parse the error response, use the default message
        }
        setError(errorMessage);
        setIsLoading(false);
        return;
      }
      
      fetchUsers();
      setIsLoading(false);
    } catch (err) {
      setError('Error deleting user: ' + err.message);
      setIsLoading(false);
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    setFormData({ 
      username: user.username, 
      password: '', 
      is_global_admin: user.is_global_admin, 
      provider_roles: user.provider_roles || {} 
    });
    setAddingUser(true);
  };

  const handleDelete = (username) => {
    setConfirmDeleteUser({ username });
  };

  return (
    <div 
      style={{ 
        flexGrow: 1,
        padding: '2rem 1rem',
        maxWidth: '1200px',
        margin: '0 auto',
        width: '100%',
      }}
      className="content-container"
    >
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
         Users 
        </h2>
      </div>
    
      
      {/* Floating action menu */}
      <ActionMenu
        actions={[
          {
            icon: <Plus size={24} />,
            label: 'Add User',
            onClick: () => { 
              setAddingUser(true); 
              setEditingUser(null); 
              setFormData({ username: '', password: '', is_global_admin: false, provider_roles: {} }); 
            },
            color: 'var(--primary)'
          }
        ]}
        mode="content-relative"
        offset={16}
      />
      
      {error && <Alert type="error">{error}</Alert>}
      
      {isLoading && !addingUser ? (
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
      ) : users.length === 0 && !addingUser ? (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          backgroundColor: 'var(--card-bg)',
          borderRadius: '0.75rem',
          color: 'var(--text-light)',
          boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
        }}>
          <h3 style={{ marginTop: 0, color: 'var(--text)' }}>No users found</h3>
          <p style={{ marginBottom: '1.5rem' }}>Get started by adding your first user</p>
          <Button onClick={() => { 
            setAddingUser(true); 
            setEditingUser(null); 
            setFormData({ username: '', password: '', is_global_admin: false, provider_roles: {} }); 
          }}>
            Add User
          </Button>
        </div>
      ) : (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', 
          gap: '1.5rem',
          marginBottom: '2rem',
        }}>
          {users.map((user) => (
            <div 
              key={user.username} 
              style={{
                backgroundColor: 'var(--card-bg)',
                borderRadius: '0.75rem',
                border: '1px solid var(--border)',
                overflow: 'hidden',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
                transition: 'all 0.3s',
                display: 'flex',
                flexDirection: 'column',
                height: '100%', // Make card fill its container height
              }}
            >
              <div style={{ 
                padding: '1.25rem', 
                flexGrow: 1, // Make body expand to fill available space
                display: 'flex',
                flexDirection: 'column',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '2rem' }}>
                  <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--primary)',
                    color: 'white',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    marginRight: '0.75rem',
                    fontWeight: 600,
                    fontSize: '1rem',
                  }}>
                    {user.username.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <h3 style={{ 
                      margin: '0', 
                      fontSize: '1.125rem', 
                      fontWeight: 600,
                      color: 'var(--text)',
                    }}>
                      {user.username}
                    </h3>
                  </div>
                </div>
                
                {/* Flexible spacer to push roles to the center */}
                <div style={{ flexGrow: 1 }}></div>
                
                {/* Roles section with subtle heading */}
                <div style={{ marginBottom: '2rem' }}>
                  <div style={{ 
                    fontSize: '0.75rem', 
                    textTransform: 'uppercase', 
                    fontWeight: 500, 
                    color: 'var(--text-light)',
                    marginBottom: '0.5rem',
                    letterSpacing: '0.025em',
                  }}>
                    Roles
                  </div>
                  
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                    {/* Show Global Admin tag first if applicable */}
                    {user.is_global_admin && (
                      <div 
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '0.5rem',
                          backgroundColor: 'var(--subtle-bg)',
                          borderRadius: '0.375rem',
                          fontSize: '0.875rem',
                        }}
                      >
                        <div style={{ flex: 1 }}>
                          <strong>Global Admin</strong>
                        </div>
                      </div>
                    )}
                    
                    {Object.keys(user.provider_roles || {}).length === 0 && !user.is_global_admin ? (
                      <div style={{ 
                        color: 'var(--text-light)', 
                        fontSize: '0.875rem',
                        fontStyle: 'italic'
                      }}>
                        No roles assigned
                      </div>
                    ) : (
                      <>
                        {Object.entries(user.provider_roles).map(([providerId, role]) => {
                          const provider = providers.find(p => p.id.toString() === providerId);
                          return (
                            <div 
                              key={providerId}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                padding: '0.5rem',
                                backgroundColor: 'var(--subtle-bg)',
                                borderRadius: '0.375rem',
                                fontSize: '0.875rem',
                              }}
                            >
                              <div style={{ flex: 1 }}>
                                <strong>{provider ? provider.shortName : providerId}</strong>
                                <span style={{ marginLeft: '0.5rem', color: 'var(--text-light)' }}>
                                  {role}
                                </span>
                              </div>
                            </div>
                          );
                        })}
                      </>
                    )}
                  </div>
                </div>
                
                {/* Flexible spacer to push roles to the center */}
                <div style={{ flexGrow: 1 }}></div>
              </div>
              
              {/* Footer with action buttons - fixed height, not affected by content */}
              <div style={{ 
                borderTop: '1px solid var(--border)',
                display: 'flex',
                justifyContent: 'flex-end',
                alignItems: 'center',
                padding: '0.75rem',
                gap: '0.5rem',
                height: '60px',
                flexShrink: 0, // Prevent footer from shrinking
                boxSizing: 'border-box'
              }}>
                <button 
                  onClick={() => handleEdit(user)}
                  style={{
                    width: '36px',
                    height: '36px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: 'var(--subtle-bg)',
                    color: 'var(--text-light)',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    padding: 0
                  }}
                >
                  <Edit size={16} />
                </button>
                <button 
                  onClick={() => handleDelete(user.username)}
                  style={{
                    width: '36px',
                    height: '36px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    backgroundColor: 'var(--subtle-bg)',
                    color: 'var(--error)',
                    border: 'none',
                    borderRadius: '0.375rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    padding: 0
                  }}
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      
      {confirmDeleteUser && (
        <ConfirmModal
          isOpen={true}
          title="Delete User"
          message={`Are you sure you want to delete "${confirmDeleteUser.username}"? This action cannot be undone.`}
          onConfirm={() => { handleDeleteUser(confirmDeleteUser.username); setConfirmDeleteUser(null); }}
          onCancel={() => setConfirmDeleteUser(null)}
        />
      )}
      
      <Modal
        isOpen={addingUser}
        onClose={() => { setAddingUser(false); setEditingUser(null); }}
        title={editingUser ? `Edit User: ${editingUser.username}` : 'Add User'}
      >
        <div>
          {error && <Alert type="error">{error}</Alert>}
          
          <form onSubmit={(e) => { e.preventDefault(); handleSaveUser(formData); }}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ 
                display: 'block', 
                fontSize: '0.875rem', 
                fontWeight: 500, 
                marginBottom: '0.5rem', 
                color: 'var(--text)',
              }}>
                Username
              </label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                required
                disabled={!!editingUser}
                placeholder="Enter username"
                autoComplete="username"
                style={{
                  display: 'block',
                  width: '100%',
                  padding: '0.625rem 0.75rem',
                  fontSize: '0.875rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--card-bg)',
                  color: 'var(--text)',
                  transition: 'border-color 0.2s',
                }}
              />
              {editingUser && (
                <div style={{
                  fontSize: '0.75rem',
                  color: 'var(--text-light)',
                  marginTop: '0.25rem',
                }}>
                  Username cannot be changed
                </div>
              )}
            </div>
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ 
                display: 'block', 
                fontSize: '0.875rem', 
                fontWeight: 500, 
                marginBottom: '0.5rem', 
                color: 'var(--text)',
              }}>
                Password
              </label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required={!editingUser}
                placeholder={editingUser ? "Leave blank to keep current password" : "Enter password"}
                autoComplete="current-password"
                style={{
                  display: 'block',
                  width: '100%',
                  padding: '0.625rem 0.75rem',
                  fontSize: '0.875rem',
                  borderRadius: '0.5rem',
                  border: '1px solid var(--border)',
                  backgroundColor: 'var(--card-bg)',
                  color: 'var(--text)',
                  transition: 'border-color 0.2s',
                }}
              />
            </div>
            
            {/* Add Old Password field if editing the current user */}
            {editingUser && currentUser && currentUser.username === editingUser.username && formData.password && (
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ 
                  display: 'block', 
                  fontSize: '0.875rem', 
                  fontWeight: 500, 
                  marginBottom: '0.5rem', 
                  color: 'var(--text)',
                }}>
                  Current Password (required to update your password)
                </label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required={!!formData.password}
                  placeholder="Enter your current password"
                  autoComplete="current-password"
                  style={{
                    display: 'block',
                    width: '100%',
                    padding: '0.625rem 0.75rem',
                    fontSize: '0.875rem',
                    borderRadius: '0.5rem',
                    border: '1px solid var(--border)',
                    backgroundColor: 'var(--card-bg)',
                    color: 'var(--text)',
                    transition: 'border-color 0.2s',
                  }}
                />
              </div>
            )}
            
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ 
                display: 'flex', 
                alignItems: 'center',
                fontSize: '0.875rem', 
                fontWeight: 500, 
                color: 'var(--text)',
              }}>
                <input
                  type="checkbox"
                  checked={formData.is_global_admin}
                  onChange={(e) => setFormData({ ...formData, is_global_admin: e.target.checked })}
                  style={{
                    width: '1rem',
                    height: '1rem',
                    borderRadius: '0.25rem',
                    marginRight: '0.5rem',
                    accentColor: 'var(--primary)',
                  }}
                />
                Global Admin
              </label>
              <div style={{
                fontSize: '0.75rem',
                color: 'var(--text-light)',
                marginTop: '0.25rem',
                marginLeft: '1.5rem',
              }}>
                Global admins have full access to all providers and user management
              </div>
            </div>
            
            {!formData.is_global_admin && (
              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ 
                  display: 'block', 
                  fontSize: '0.875rem', 
                  fontWeight: 500, 
                  marginBottom: '0.5rem', 
                  color: 'var(--text)',
                }}>
                  Provider Roles
                </label>
                
                <div style={{ marginBottom: '1rem' }}>
                  {Object.entries(formData.provider_roles).map(([providerId, role]) => {
                    const provider = providers.find(p => p.id.toString() === providerId);
                    return (
                      <div 
                        key={providerId}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          padding: '0.5rem',
                          backgroundColor: 'var(--subtle-bg)',
                          borderRadius: '0.375rem',
                          marginBottom: '0.5rem',
                        }}
                      >
                        <div style={{ flex: 1 }}>
                          <strong>{provider ? provider.shortName : providerId}</strong>
                          <span style={{ marginLeft: '0.5rem', color: 'var(--text-light)' }}>
                            {role}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRemoveProviderRole(providerId)}
                          style={{
                            padding: '0.25rem 0.5rem',
                            backgroundColor: 'transparent',
                            border: 'none',
                            color: 'var(--error)',
                            cursor: 'pointer',
                          }}
                        >
                          ×
                        </button>
                      </div>
                    );
                  })}
                </div>

                <div style={{ 
                  display: 'flex', 
                  gap: '0.5rem',
                  marginBottom: '0.5rem'
                }}>
                  <select
                    value={selectedProvider}
                    onChange={(e) => setSelectedProvider(e.target.value)}
                    style={{
                      flex: '2',
                      padding: '0.625rem 0.75rem',
                      fontSize: '0.875rem',
                      borderRadius: '0.5rem',
                      border: '1px solid var(--border)',
                      backgroundColor: 'var(--card-bg)',
                      color: 'var(--text)',
                    }}
                  >
                    <option value="">Select Provider</option>
                    {providers.map(provider => (
                      <option key={provider.id} value={provider.id}>
                        {provider.shortName}
                      </option>
                    ))}
                  </select>
                  
                  <select
                    value={selectedRole}
                    onChange={(e) => setSelectedRole(e.target.value)}
                    style={{
                      flex: '1',
                      padding: '0.625rem 0.75rem',
                      fontSize: '0.875rem',
                      borderRadius: '0.5rem',
                      border: '1px solid var(--border)',
                      backgroundColor: 'var(--card-bg)',
                      color: 'var(--text)',
                    }}
                  >
                    <option value="admin">Admin</option>
                    <option value="curator">Curator</option>
                  </select>
                  
                  <button
                    type="button"
                    onClick={handleAddProviderRole}
                    disabled={!selectedProvider}
                    style={{
                      padding: '0.625rem 1rem',
                      backgroundColor: selectedProvider ? 'var(--primary)' : 'var(--border)',
                      color: 'white',
                      border: 'none',
                      borderRadius: '0.5rem',
                      fontSize: '0.875rem',
                    }}
                  >
                    Add
                  </button>
                </div>
              </div>
            )}
            
            <div style={{ 
              display: 'flex', 
              justifyContent: 'flex-end', 
              gap: '0.75rem'
            }}>
              <Button
                variant="secondary"
                type="button"
                onClick={() => { setEditingUser(null); setAddingUser(false); }}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                isLoading={isLoading}
                disabled={isLoading}
              >
                {editingUser ? (isLoading ? 'Updating...' : 'Update User') : (isLoading ? 'Creating...' : 'Create User')}
              </Button>
            </div>
          </form>
        </div>
      </Modal>
    </div>
  );
}

export default UserManagement;
