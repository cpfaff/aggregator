import React, { useState, useEffect } from 'react';
import { Edit, Trash2, Plus, Search } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { apiRequest } from '../../utils/apiUtils';
import useFormValidation from '../../utils/useFormValidation';
import validationRules from '../../utils/validationRules';
import { formatRelativeTime } from '../../utils/dateUtils';
import FormField from '../ui/FormField';
import Alert from '../ui/Alert';
import Button from '../ui/Button';
import Modal from '../ui/Modal';
import ConfirmModal from '../ui/ConfirmModal';
import Breadcrumbs from '../ui/Breadcrumbs';
import ActionMenu from '../ui/ActionMenu';
import { showToast } from '../ui/Toast';
import { useResponsiveGrid } from '../../hooks/useMediaQuery';

// UserManagement component
function UserManagement() {
  const { handleTokenExpiration, user: currentUser } = useAuth();
  const { getGridColumns } = useResponsiveGrid();
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [editingUser, setEditingUser] = useState(null);
  const [addingUser, setAddingUser] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [selectedRole, setSelectedRole] = useState('admin'); // Set default role to 'admin'
  const [isFormLoading, setIsFormLoading] = useState(false);
  const [formError, setFormError] = useState('');
  const [confirmDeleteUser, setConfirmDeleteUser] = useState(null);
  const [confirmDiscardChanges, setConfirmDiscardChanges] = useState(false);

  // Breadcrumb items for User Management
  const breadcrumbItems = [
    { label: 'Home', onClick: () => window.location.href = '/' },
    { label: 'Users', onClick: null }
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

  // Filter users based on search query
  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredUsers(users);
    } else {
      const query = searchQuery.toLowerCase();
      const filtered = users.filter(user => {
        // Filter on username
        if (user.username && user.username.toLowerCase().includes(query)) {
          return true;
        }
        // Filter on provider roles
        if (user.provider_roles) {
          for (const [providerId, role] of Object.entries(user.provider_roles)) {
            const provider = providers.find(p => p.id.toString() === providerId);
            if (provider && provider.shortName && provider.shortName.toLowerCase().includes(query)) {
              return true;
            }
            if (role && role.toLowerCase().includes(query)) {
              return true;
            }
          }
        }
        // Filter on global admin status
        if (user.is_global_admin && 'global admin'.includes(query)) {
          return true;
        }
        return false;
      });
      setFilteredUsers(filtered);
    }
  }, [searchQuery, users, providers]);

  // Define validation schema
  const getValidationSchema = (isEditing, isCurrentUser) => {
    const schema = {
      username: isEditing ? [] : [
        validationRules.required('Username is required'),
        validationRules.minLength(3, 'Username must be at least 3 characters'),
        validationRules.maxLength(50, 'Username must be less than 50 characters'),
        validationRules.pattern(/^[a-zA-Z0-9_-]+$/, 'Username can only contain letters, numbers, hyphens, and underscores')
      ],
      password: isEditing ? [
        validationRules.conditional(
          (values) => values.password && values.password.trim() !== '',
          validationRules.minLength(8, 'Password must be at least 8 characters')
        )
      ] : [
        validationRules.required('Password is required'),
        validationRules.minLength(8, 'Password must be at least 8 characters')
      ]
    };

    // Add oldPassword validation if editing current user's password
    if (isEditing && isCurrentUser) {
      schema.oldPassword = [
        validationRules.conditional(
          (values) => values.password && values.password.trim() !== '',
          validationRules.required('Current password is required to update your password')
        )
      ];
    }

    return schema;
  };

  const handleAddProviderRole = () => {
    if (selectedProvider && selectedRole) {
      form.setFieldValue('provider_roles', {
        ...form.values.provider_roles,
        [selectedProvider]: selectedRole
      });
      setSelectedProvider('');
      setSelectedRole('admin'); // Reset role to default after adding
    }
  };

  const handleRemoveProviderRole = (providerId) => {
    const newRoles = { ...form.values.provider_roles };
    delete newRoles[providerId];
    form.setFieldValue('provider_roles', newRoles);
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

  // Form submission handler
  const handleFormSubmit = async (values) => {
    setIsFormLoading(true);
    setFormError('');

    try {
      let res;
      if (editingUser) {
        // Create a copy of the user data for the update
        const userData = {
          is_global_admin: values.is_global_admin,
          provider_roles: values.provider_roles
        };

        // Only include password if it's not empty
        if (values.password && values.password.trim() !== '') {
          userData.password = values.password;
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
              old_password: values.oldPassword
            })
          };
        }

        res = await apiRequest(`/users/${editingUser.username}`, requestOptions, handleTokenExpiration);
      } else {
        res = await apiRequest('/users', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(values)
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
        setFormError(errorMessage);
        setIsFormLoading(false);
        return;
      }

      setEditingUser(null);
      setAddingUser(false);
      fetchUsers();
      setIsFormLoading(false);
      showToast(
        editingUser
          ? `User "${values.username}" updated successfully!`
          : `User "${values.username}" created successfully!`,
        'success'
      );
    } catch (err) {
      // Only set error if it's not a token expiration error
      // Token expiration is handled by the onTokenExpired callback
      if (!err.message || !err.message.includes('Session expired')) {
        setFormError('Error saving user: ' + err.message);
      }
      setIsFormLoading(false);
    }
  };

  // Initialize form validation hook - need to reinitialize when switching between add/edit
  const initialFormValues = editingUser ? {
    username: editingUser.username,
    password: '',
    oldPassword: '',
    is_global_admin: editingUser.is_global_admin,
    provider_roles: editingUser.provider_roles || {}
  } : {
    username: '',
    password: '',
    oldPassword: '',
    is_global_admin: false,
    provider_roles: {}
  };

  const form = useFormValidation(
    initialFormValues,
    getValidationSchema(!!editingUser, editingUser && currentUser && currentUser.username === editingUser.username),
    handleFormSubmit
  );

  // Update form values when editingUser changes
  useEffect(() => {
    if (editingUser) {
      form.setFieldValue('username', editingUser.username);
      form.setFieldValue('password', '');
      form.setFieldValue('oldPassword', '');
      form.setFieldValue('is_global_admin', editingUser.is_global_admin);
      form.setFieldValue('provider_roles', editingUser.provider_roles || {});
    } else if (addingUser && !editingUser) {
      // Reset form for new user
      form.resetForm();
    }
  }, [editingUser, addingUser]);

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
      showToast(`User "${username}" deleted successfully!`, 'success');
    } catch (err) {
      setError('Error deleting user: ' + err.message);
      setIsLoading(false);
    }
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    setAddingUser(true);
    // Form values will be set automatically by useFormValidation hook
  };

  const handleDelete = (username) => {
    setConfirmDeleteUser({ username });
  };

  // Handle modal close with unsaved changes check
  const handleModalClose = () => {
    if (form.isDirty) {
      setConfirmDiscardChanges(true);
    } else {
      setAddingUser(false);
      setEditingUser(null);
      form.resetForm();
    }
  };

  // Confirm discard changes
  const handleConfirmDiscard = () => {
    setConfirmDiscardChanges(false);
    setAddingUser(false);
    setEditingUser(null);
    form.resetForm();
  };

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
          Users
        </h2>
        <p style={{
          fontSize: '1rem',
          color: 'var(--text-light)',
          margin: 0,
          lineHeight: '1.5',
        }}>
          Manage user accounts and role assignments.
        </p>
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
            },
            color: 'var(--primary)'
          }
        ]}
        mode="content-relative"
        offset={16}
      />

      {error && <Alert type="error">{error}</Alert>}

      {/* Search filter - only show when there are more than 6 users */}
      {users.length > 6 && (
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
            placeholder="Search users..."
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
          }}>
            Add User
          </Button>
        </div>
      ) : (
        <>
          {filteredUsers.length > 0 ? (
            <div style={{
              display: 'grid',
              gridTemplateColumns: getGridColumns(300),
              gap: '1.5rem',
              marginBottom: '2rem',
            }}>
              {filteredUsers.map((user) => (
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
                    <div style={{
                      fontSize: '0.75rem',
                      color: 'var(--text-light)',
                      marginTop: '0.25rem'
                    }}>
                      {user.last_login
                        ? `Last login: ${formatRelativeTime(user.last_login)}`
                        : 'Never logged in'}
                    </div>
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
                    width: '44px',
                    height: '44px',
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
                  aria-label={`Edit user: ${user.username}`}
                  title="Edit user"
                >
                  <Edit size={20} />
                </button>
                <button
                  onClick={() => handleDelete(user.username)}
                  style={{
                    width: '44px',
                    height: '44px',
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
                  aria-label={`Delete user: ${user.username}`}
                  title="Delete user"
                >
                  <Trash2 size={20} />
                </button>
              </div>
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
                No users match your search criteria. Try a different search term.
              </p>
            </div>
          )}
        </>
      )}

      {confirmDeleteUser && (
        <ConfirmModal
          isOpen={true}
          title="Delete User"
          message={`Are you sure you want to delete "${confirmDeleteUser.username}"? This action cannot be undone.`}
          confirmText="Delete"
          onConfirm={() => { handleDeleteUser(confirmDeleteUser.username); setConfirmDeleteUser(null); }}
          onCancel={() => setConfirmDeleteUser(null)}
        />
      )}

      {confirmDiscardChanges && (
        <ConfirmModal
          isOpen={true}
          title="Discard changes?"
          message="You have unsaved changes. Are you sure you want to close this form?"
          confirmText="Discard"
          cancelText="Keep Editing"
          onConfirm={handleConfirmDiscard}
          onCancel={() => setConfirmDiscardChanges(false)}
        />
      )}

      <Modal
        isOpen={addingUser}
        onClose={handleModalClose}
        title={editingUser ? `Edit User: ${editingUser.username}` : 'Add User'}
      >
        <div>
          {formError && <Alert type="error">{formError}</Alert>}

          <form onSubmit={form.handleSubmit} noValidate>
            <FormField
              type="text"
              name="username"
              label="Username"
              value={form.values.username}
              onChange={form.handleChange}
              onBlur={form.handleBlur}
              error={form.errors.username}
              touched={form.touched.username}
              placeholder="Enter username"
              autoComplete="username"
              disabled={!!editingUser}
              required={!editingUser}
              helpText={editingUser ? "Username cannot be changed" : "Choose a unique username (3-50 characters)"}
            />

            <FormField
              type="password"
              name="password"
              label="Password"
              value={form.values.password}
              onChange={form.handleChange}
              onBlur={form.handleBlur}
              error={form.errors.password}
              touched={form.touched.password}
              placeholder={editingUser ? "Leave blank to keep current password" : "Enter password"}
              autoComplete="new-password"
              required={!editingUser}
              helpText={editingUser ? "Only fill if you want to change the password" : "Minimum 8 characters"}
              showPasswordToggle={true}
            />

            {/* Add Old Password field if editing the current user */}
            {editingUser && currentUser && currentUser.username === editingUser.username && form.values.password && (
              <FormField
                type="password"
                name="oldPassword"
                label="Current Password"
                value={form.values.oldPassword}
                onChange={form.handleChange}
                onBlur={form.handleBlur}
                error={form.errors.oldPassword}
                touched={form.touched.oldPassword}
                placeholder="Enter your current password"
                autoComplete="current-password"
                required={true}
                helpText="Required to update your password"
                showPasswordToggle={true}
              />
            )}

            <FormField
              type="checkbox"
              name="is_global_admin"
              label="Global Admin"
              checked={form.values.is_global_admin}
              onChange={form.handleChange}
              onBlur={form.handleBlur}
              error={form.errors.is_global_admin}
              touched={form.touched.is_global_admin}
              helpText="Global admins have full access to all providers and user management"
            />

            {!form.values.is_global_admin && (
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
                  {Object.entries(form.values.provider_roles).map(([providerId, role]) => {
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
                onClick={handleModalClose}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                isLoading={isFormLoading}
                disabled={isFormLoading}
              >
                {editingUser ? (isFormLoading ? 'Updating...' : 'Update User') : (isFormLoading ? 'Creating...' : 'Create User')}
              </Button>
            </div>
          </form>
        </div>
      </Modal>
    </div>
  );
}

export default UserManagement;
