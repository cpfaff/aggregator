import React from 'react';
import Modal from './Modal';

/**
 * ConfirmModal - A standardized confirmation dialog component
 * 
 * @param {Object} props - Component props
 * @param {boolean} props.isOpen - Whether the modal is open
 * @param {string} props.title - The title of the modal (defaults to 'Confirm Action')
 * @param {string} props.message - The message to display in the confirmation dialog
 * @param {string} props.confirmText - The text for the confirm button (defaults to 'Confirm')
 * @param {string} props.cancelText - The text for the cancel button (defaults to 'Cancel')
 * @param {string} props.confirmVariant - The variant for the confirm button (primary, danger, secondary, defaults to 'danger')
 * @param {Function} props.onConfirm - Function to call when the confirm button is clicked
 * @param {Function} props.onCancel - Function to call when the cancel button is clicked
 */
function ConfirmModal({ 
  isOpen = false,
  title = 'Confirm Action', 
  message, 
  confirmText = 'Confirm', 
  cancelText = 'Cancel',
  confirmVariant = 'danger',
  onConfirm, 
  onCancel
}) {
  if (!isOpen) return null;
  
  return (
    <Modal 
      isOpen={true} 
      onClose={onCancel}
      title={title}
      footer={
        <>
          <button 
            onClick={onCancel}
            style={{
              padding: '0.75rem 1rem',
              backgroundColor: 'transparent',
              color: 'var(--text-light)',
              border: '1px solid var(--border)',
              borderRadius: '0.5rem',
              fontSize: '1rem',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'background-color 0.3s',
            }}
          >
            {cancelText}
          </button>
          <button 
            onClick={onConfirm}
            style={{
              padding: '0.75rem 1rem',
              backgroundColor: confirmVariant === 'danger' ? 'var(--error)' : 
                               confirmVariant === 'primary' ? 'var(--primary)' : 'transparent',
              color: confirmVariant === 'secondary' ? 'var(--text-light)' : 'white',
              border: confirmVariant === 'secondary' ? '1px solid var(--border)' : 'none',
              borderRadius: '0.5rem',
              fontSize: '1rem',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'background-color 0.3s',
            }}
          >
            {confirmText}
          </button>
        </>
      }
    >
      <p style={{ color: 'var(--text)', marginBottom: '1rem', fontSize: '1rem', lineHeight: '1.5' }}>{message}</p>
    </Modal>
  );
}

export default ConfirmModal;
