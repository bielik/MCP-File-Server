import React from 'react';
import { LucideIcon } from 'lucide-react';
import clsx from 'clsx';

interface EmptyStateAction {
  label: string;
  onClick: () => void;
  primary?: boolean;
  disabled?: boolean;
}

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actions?: EmptyStateAction[];
  illustration?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actions = [],
  illustration,
  className,
}: EmptyStateProps) {
  return (
    <div className={clsx('flex flex-col items-center justify-center p-8 text-center', className)}>
      {/* Icon or Illustration */}
      <div className="mb-4">
        {illustration ? (
          illustration
        ) : Icon ? (
          <div className="w-16 h-16 mx-auto mb-4 text-gray-400">
            <Icon size={64} className="w-full h-full" />
          </div>
        ) : (
          <div className="w-16 h-16 mx-auto mb-4 bg-gray-100 rounded-full flex items-center justify-center">
            <div className="w-8 h-8 bg-gray-300 rounded-full" />
          </div>
        )}
      </div>

      {/* Title */}
      <h3 className="text-xl font-semibold text-gray-900 mb-2">
        {title}
      </h3>

      {/* Description */}
      <p className="text-gray-500 mb-6 max-w-sm">
        {description}
      </p>

      {/* Actions */}
      {actions.length > 0 && (
        <div className="flex flex-col sm:flex-row gap-3">
          {actions.map((action, index) => (
            <button
              key={index}
              onClick={action.onClick}
              disabled={action.disabled}
              className={clsx(
                'px-4 py-2 rounded-md text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2',
                action.primary
                  ? 'bg-primary-600 text-white hover:bg-primary-700 focus:ring-primary-500 disabled:bg-primary-300'
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-50 focus:ring-primary-500 disabled:bg-gray-100 disabled:text-gray-400',
                action.disabled && 'cursor-not-allowed'
              )}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// Preset empty states for common scenarios
export const FileEmptyState = ({ onCreate }: { onCreate?: () => void }) => (
  <EmptyState
    title="No files found"
    description="Get started by creating your first file or adjusting your search filters"
    actions={onCreate ? [
      {
        label: 'Create File',
        onClick: onCreate,
        primary: true,
      },
    ] : []}
  />
);

export const SearchEmptyState = ({ query, onClear }: { query: string; onClear?: () => void }) => (
  <EmptyState
    title="No results found"
    description={`We couldn't find any files matching "${query}". Try adjusting your search terms or filters.`}
    actions={onClear ? [
      {
        label: 'Clear Search',
        onClick: onClear,
      },
    ] : []}
  />
);

export const ErrorEmptyState = ({ onRetry }: { onRetry?: () => void }) => (
  <EmptyState
    title="Something went wrong"
    description="We encountered an error while loading your files. Please try again."
    actions={onRetry ? [
      {
        label: 'Try Again',
        onClick: onRetry,
        primary: true,
      },
    ] : []}
  />
);

export const LoadingEmptyState = () => (
  <EmptyState
    title="Loading files..."
    description="Please wait while we fetch your files"
    illustration={
      <div className="w-16 h-16 mx-auto mb-4">
        <div className="animate-spin rounded-full h-16 w-16 border-4 border-primary-200 border-t-primary-600" />
      </div>
    }
  />
);