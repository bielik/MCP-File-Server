import React, { useState } from 'react';
import { 
  CheckSquare, 
  Square, 
  Minus,
  Eye,
  Edit,
  Upload,
  Download,
  Copy,
  Trash2,
  MoreHorizontal
} from 'lucide-react';

interface BulkOperationsBarProps {
  totalItems: number;
  selectedPaths: string[];
  onSelectAll: () => void;
  onClearSelection: () => void;
  onSelectVisible: () => void;
  onInvertSelection: () => void;
  onBulkPermissionAssign: (paths: string[], permission: 'context' | 'working' | 'output') => void;
  onExportSelection: (paths: string[]) => void;
  onCopyPaths: (paths: string[]) => void;
  currentPermissions: Record<string, string | null>;
}

export const BulkOperationsBar: React.FC<BulkOperationsBarProps> = ({
  totalItems,
  selectedPaths,
  onSelectAll,
  onClearSelection,
  onSelectVisible,
  onInvertSelection,
  onBulkPermissionAssign,
  onExportSelection,
  onCopyPaths,
  currentPermissions
}) => {
  const [showMore, setShowMore] = useState(false);
  const selectedCount = selectedPaths.length;
  const isAllSelected = selectedCount === totalItems && totalItems > 0;
  const isPartiallySelected = selectedCount > 0 && selectedCount < totalItems;

  // Analyze permissions of selected items
  const permissionCounts = selectedPaths.reduce((counts, path) => {
    const permission = currentPermissions[path] || 'none';
    counts[permission] = (counts[permission] || 0) + 1;
    return counts;
  }, {} as Record<string, number>);

  const handleSelectToggle = () => {
    if (isAllSelected) {
      onClearSelection();
    } else {
      onSelectAll();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      action();
    }
  };

  return (
    <div className="bg-white border-b border-gray-200 px-4 py-3">
      <div className="flex items-center justify-between">
        {/* Selection Controls */}
        <div className="flex items-center space-x-4">
          {/* Select All/None Toggle */}
          <button
            onClick={handleSelectToggle}
            onKeyDown={(e) => handleKeyDown(e, handleSelectToggle)}
            className="flex items-center space-x-2 text-sm text-gray-600 hover:text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded p-1"
            aria-label={isAllSelected ? 'Deselect all items' : 'Select all items'}
          >
            {isAllSelected ? (
              <CheckSquare className="w-5 h-5 text-blue-600" />
            ) : isPartiallySelected ? (
              <Minus className="w-5 h-5 text-blue-600" />
            ) : (
              <Square className="w-5 h-5" />
            )}
            <span>
              {selectedCount > 0 
                ? `${selectedCount} of ${totalItems} selected`
                : `Select all ${totalItems} items`
              }
            </span>
          </button>

          {/* Quick Selection Options */}
          {selectedCount > 0 && (
            <div className="flex items-center space-x-2 text-xs">
              <button
                onClick={onSelectVisible}
                className="text-blue-600 hover:text-blue-800 underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-1"
                aria-label="Select all visible items"
              >
                Select visible
              </button>
              <span className="text-gray-300">|</span>
              <button
                onClick={onInvertSelection}
                className="text-blue-600 hover:text-blue-800 underline focus:outline-none focus:ring-2 focus:ring-blue-500 rounded px-1"
                aria-label="Invert selection"
              >
                Invert selection
              </button>
              <span className="text-gray-300">|</span>
              <button
                onClick={onClearSelection}
                className="text-red-600 hover:text-red-800 underline focus:outline-none focus:ring-2 focus:ring-red-500 rounded px-1"
                aria-label="Clear selection"
              >
                Clear
              </button>
            </div>
          )}
        </div>

        {/* Permission Assignment Actions */}
        {selectedCount > 0 && (
          <div className="flex items-center space-x-2">
            {/* Permission Statistics */}
            {Object.keys(permissionCounts).length > 1 && (
              <div className="text-xs text-gray-500 mr-4">
                Mixed permissions: {Object.entries(permissionCounts)
                  .map(([perm, count]) => `${count} ${perm}`)
                  .join(', ')}
              </div>
            )}

            {/* Quick Permission Assignment */}
            <div className="flex items-center space-x-1">
              <button
                onClick={() => onBulkPermissionAssign(selectedPaths, 'context')}
                className="flex items-center space-x-1 px-2 py-1 text-xs bg-blue-100 text-blue-700 rounded hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors"
                aria-label={`Assign context permission to ${selectedCount} selected items`}
                title="Assign context (read-only) permission"
              >
                <Eye className="w-3 h-3" />
                <span className="hidden sm:inline">Context</span>
              </button>

              <button
                onClick={() => onBulkPermissionAssign(selectedPaths, 'working')}
                className="flex items-center space-x-1 px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 focus:outline-none focus:ring-2 focus:ring-green-500 transition-colors"
                aria-label={`Assign working permission to ${selectedCount} selected items`}
                title="Assign working (read-write) permission"
              >
                <Edit className="w-3 h-3" />
                <span className="hidden sm:inline">Working</span>
              </button>

              <button
                onClick={() => onBulkPermissionAssign(selectedPaths, 'output')}
                className="flex items-center space-x-1 px-2 py-1 text-xs bg-purple-100 text-purple-700 rounded hover:bg-purple-200 focus:outline-none focus:ring-2 focus:ring-purple-500 transition-colors"
                aria-label={`Assign output permission to ${selectedCount} selected items`}
                title="Assign output (agent-controlled) permission"
              >
                <Upload className="w-3 h-3" />
                <span className="hidden sm:inline">Output</span>
              </button>
            </div>

            {/* More Actions */}
            <div className="relative">
              <button
                onClick={() => setShowMore(!showMore)}
                className="flex items-center space-x-1 px-2 py-1 text-xs text-gray-600 border border-gray-300 rounded hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500 transition-colors"
                aria-label="More bulk actions"
                aria-expanded={showMore}
              >
                <MoreHorizontal className="w-3 h-3" />
                <span className="hidden sm:inline">More</span>
              </button>

              {showMore && (
                <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 w-48">
                  <div className="py-1">
                    <button
                      onClick={() => {
                        onExportSelection(selectedPaths);
                        setShowMore(false);
                      }}
                      className="flex items-center space-x-2 w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 focus:outline-none focus:bg-gray-100"
                    >
                      <Download className="w-4 h-4" />
                      <span>Export selection</span>
                    </button>

                    <button
                      onClick={() => {
                        onCopyPaths(selectedPaths);
                        setShowMore(false);
                      }}
                      className="flex items-center space-x-2 w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 focus:outline-none focus:bg-gray-100"
                    >
                      <Copy className="w-4 h-4" />
                      <span>Copy paths</span>
                    </button>

                    <div className="border-t border-gray-200 my-1" />

                    <button
                      onClick={() => {
                        onClearSelection();
                        setShowMore(false);
                      }}
                      className="flex items-center space-x-2 w-full px-3 py-2 text-sm text-red-700 hover:bg-red-50 focus:outline-none focus:bg-red-50"
                    >
                      <Trash2 className="w-4 h-4" />
                      <span>Clear selection</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Selection Summary for Screen Readers */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {selectedCount > 0 
          ? `${selectedCount} items selected out of ${totalItems} total items`
          : `No items selected. ${totalItems} items available for selection`
        }
      </div>
    </div>
  );
};