import React from 'react';

interface LoadingSkeletonProps {
  rows?: number;
  showIcons?: boolean;
  showCheckboxes?: boolean;
}

export const LoadingSkeleton: React.FC<LoadingSkeletonProps> = ({
  rows = 8,
  showIcons = true,
  showCheckboxes = true
}) => {
  return (
    <div className="animate-pulse">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="flex items-center py-2 px-2">
          {/* Expand arrow placeholder */}
          <div className="w-4 h-4 bg-gray-200 rounded mr-1" />
          
          {/* Icon placeholder */}
          {showIcons && <div className="w-5 h-5 bg-gray-200 rounded mr-2" />}
          
          {/* Name placeholder */}
          <div className="flex-1 min-w-0 mr-2">
            <div 
              className="h-4 bg-gray-200 rounded"
              style={{ width: `${Math.random() * 40 + 40}%` }}
            />
          </div>
          
          {/* Permission badge placeholder */}
          {Math.random() > 0.6 && (
            <div className="w-16 h-6 bg-gray-200 rounded mr-2" />
          )}
          
          {/* File size placeholder */}
          {Math.random() > 0.5 && (
            <div className="w-12 h-4 bg-gray-200 rounded mr-2" />
          )}
          
          {/* Checkbox placeholder */}
          {showCheckboxes && <div className="w-4 h-4 bg-gray-200 rounded" />}
        </div>
      ))}
    </div>
  );
};

interface SearchLoadingProps {
  query: string;
}

export const SearchLoading: React.FC<SearchLoadingProps> = ({ query }) => {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="text-center">
        <div className="relative">
          <div className="w-12 h-12 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin mx-auto mb-4" />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-4 h-4 bg-blue-600 rounded-full animate-pulse" />
          </div>
        </div>
        <p className="text-gray-600 font-medium">Searching for "{query}"...</p>
        <p className="text-gray-500 text-sm mt-1">This might take a moment for large directories</p>
      </div>
    </div>
  );
};

interface PermissionLoadingProps {
  action: string;
  count: number;
}

export const PermissionLoading: React.FC<PermissionLoadingProps> = ({ action, count }) => {
  return (
    <div className="flex items-center justify-center p-6">
      <div className="text-center">
        <div className="flex items-center justify-center mb-4">
          <div className="w-8 h-8 border-3 border-blue-200 border-t-blue-600 rounded-full animate-spin" />
        </div>
        <p className="text-gray-700 font-medium">
          {action} permissions for {count} item{count > 1 ? 's' : ''}...
        </p>
        <div className="mt-3 flex justify-center">
          <div className="flex space-x-1">
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="w-2 h-2 bg-blue-600 rounded-full animate-bounce"
                style={{ animationDelay: `${i * 0.1}s` }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};