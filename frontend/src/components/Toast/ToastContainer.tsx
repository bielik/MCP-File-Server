import React from 'react';
import { ToastNotification } from '../../types/index';
import { 
  CheckCircle, 
  AlertCircle, 
  XCircle, 
  Info, 
  X,
  AlertTriangle
} from 'lucide-react';
import clsx from 'clsx';

interface ToastProps {
  toast: ToastNotification;
  onRemove: (id: string) => void;
}

function Toast({ toast, onRemove }: ToastProps) {
  const getToastIcon = () => {
    switch (toast.type) {
      case 'success': return CheckCircle;
      case 'error': return XCircle;
      case 'warning': return AlertTriangle;
      case 'info': return Info;
      default: return Info;
    }
  };

  const getToastStyles = () => {
    switch (toast.type) {
      case 'success':
        return {
          container: 'bg-success-50 border-success-200',
          icon: 'text-success-600',
          title: 'text-success-800',
          message: 'text-success-700',
          button: 'text-success-600 hover:text-success-800',
        };
      case 'error':
        return {
          container: 'bg-danger-50 border-danger-200',
          icon: 'text-danger-600',
          title: 'text-danger-800',
          message: 'text-danger-700',
          button: 'text-danger-600 hover:text-danger-800',
        };
      case 'warning':
        return {
          container: 'bg-warning-50 border-warning-200',
          icon: 'text-warning-600',
          title: 'text-warning-800',
          message: 'text-warning-700',
          button: 'text-warning-600 hover:text-warning-800',
        };
      case 'info':
      default:
        return {
          container: 'bg-primary-50 border-primary-200',
          icon: 'text-primary-600',
          title: 'text-primary-800',
          message: 'text-primary-700',
          button: 'text-primary-600 hover:text-primary-800',
        };
    }
  };

  const IconComponent = getToastIcon();
  const styles = getToastStyles();

  return (
    <div
      className={clsx(
        'max-w-sm w-full bg-white shadow-lg rounded-lg pointer-events-auto ring-1 ring-black ring-opacity-5 overflow-hidden transform transition-all duration-300 ease-in-out',
        styles.container
      )}
    >
      <div className="p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <IconComponent size={20} className={styles.icon} />
          </div>
          <div className="ml-3 w-0 flex-1 pt-0.5">
            <p className={clsx('text-sm font-medium', styles.title)}>
              {toast.title}
            </p>
            {toast.message && (
              <p className={clsx('mt-1 text-sm', styles.message)}>
                {toast.message}
              </p>
            )}
            {toast.action && (
              <div className="mt-3">
                <button
                  onClick={() => {
                    toast.action?.onClick();
                    onRemove(toast.id);
                  }}
                  className={clsx(
                    'text-sm font-medium underline',
                    styles.button
                  )}
                >
                  {toast.action.label}
                </button>
              </div>
            )}
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              className={clsx(
                'inline-flex rounded-md p-1.5 focus:outline-none focus:ring-2 focus:ring-offset-2',
                styles.button
              )}
              onClick={() => onRemove(toast.id)}
            >
              <span className="sr-only">Close</span>
              <X size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

interface ToastContainerProps {
  toasts: ToastNotification[];
  onRemove: (id: string) => void;
  position?: 'top-right' | 'top-left' | 'bottom-right' | 'bottom-left';
  className?: string;
}

export function ToastContainer({
  toasts,
  onRemove,
  position = 'top-right',
  className,
}: ToastContainerProps) {
  const getPositionStyles = () => {
    switch (position) {
      case 'top-left':
        return 'top-0 left-0';
      case 'top-right':
        return 'top-0 right-0';
      case 'bottom-left':
        return 'bottom-0 left-0';
      case 'bottom-right':
        return 'bottom-0 right-0';
      default:
        return 'top-0 right-0';
    }
  };

  if (toasts.length === 0) {
    return null;
  }

  return (
    <div
      aria-live="assertive"
      className={clsx(
        'fixed inset-0 flex items-end px-4 py-6 pointer-events-none z-50',
        position.includes('top') ? 'items-start' : 'items-end',
        className
      )}
    >
      <div className={clsx('w-full flex flex-col items-center space-y-4', getPositionStyles())}>
        <div
          className={clsx(
            'max-w-sm w-full space-y-2',
            position.includes('right') ? 'items-end' : 'items-start'
          )}
        >
          {toasts.map((toast, index) => (
            <div
              key={toast.id}
              className={clsx(
                'transform transition-all duration-500 ease-in-out',
                // Animate in from the side
                position.includes('right') 
                  ? 'translate-x-0 opacity-100' 
                  : 'translate-x-0 opacity-100',
                // Stacking effect
                index > 0 && 'mt-2'
              )}
              style={{
                zIndex: 1000 - index,
              }}
            >
              <Toast toast={toast} onRemove={onRemove} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Hook for managing toasts
export function useToast() {
  const [toasts, setToasts] = React.useState<ToastNotification[]>([]);

  const addToast = React.useCallback((toast: Omit<ToastNotification, 'id'>) => {
    const id = Math.random().toString(36).substr(2, 9);
    const newToast: ToastNotification = { ...toast, id };
    
    setToasts(prev => [...prev, newToast]);

    // Auto-remove toast if duration is specified
    if (toast.duration && toast.duration > 0) {
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id));
      }, toast.duration);
    }

    return id;
  }, []);

  const removeToast = React.useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const clearToasts = React.useCallback(() => {
    setToasts([]);
  }, []);

  return {
    toasts,
    addToast,
    removeToast,
    clearToasts,
  };
}