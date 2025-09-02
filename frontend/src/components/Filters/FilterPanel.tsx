import React, { useState, useCallback } from 'react';
import { UIState } from '../../types/index';
import { PermissionSelector } from '../Permissions/PermissionBadge';
import { 
  X, 
  Filter, 
  FileText, 
  Image, 
  FileVideo, 
  FileAudio, 
  Archive, 
  Code,
  FileSpreadsheet,
  Presentation,
  Database,
  File,
  Calendar,
  HardDrive
} from 'lucide-react';
import clsx from 'clsx';

interface FilterPanelProps {
  filters: UIState['filters'];
  onFiltersChange: (filters: UIState['filters']) => void;
  onClose: () => void;
  className?: string;
}

const fileTypeOptions = [
  { value: 'document', label: 'Documents', icon: FileText, count: 0 },
  { value: 'image', label: 'Images', icon: Image, count: 0 },
  { value: 'video', label: 'Videos', icon: FileVideo, count: 0 },
  { value: 'audio', label: 'Audio', icon: FileAudio, count: 0 },
  { value: 'archive', label: 'Archives', icon: Archive, count: 0 },
  { value: 'code', label: 'Code', icon: Code, count: 0 },
  { value: 'spreadsheet', label: 'Spreadsheets', icon: FileSpreadsheet, count: 0 },
  { value: 'presentation', label: 'Presentations', icon: Presentation, count: 0 },
  { value: 'database', label: 'Databases', icon: Database, count: 0 },
  { value: 'other', label: 'Other', icon: File, count: 0 },
];

const categoryOptions = [
  { value: 'research', label: 'Research', description: 'Academic papers, studies, references' },
  { value: 'draft', label: 'Drafts', description: 'Work in progress documents' },
  { value: 'final', label: 'Final', description: 'Completed documents' },
  { value: 'template', label: 'Templates', description: 'Reusable document templates' },
  { value: 'notes', label: 'Notes', description: 'Meeting notes, ideas, sketches' },
  { value: 'data', label: 'Data', description: 'Datasets, analysis files' },
  { value: 'media', label: 'Media', description: 'Images, videos, audio files' },
  { value: 'reference', label: 'Reference', description: 'Guidelines, manuals, documentation' },
];

const sizeRanges = [
  { value: 'tiny', label: 'Tiny (< 1KB)', min: 0, max: 1024 },
  { value: 'small', label: 'Small (1KB - 100KB)', min: 1024, max: 102400 },
  { value: 'medium', label: 'Medium (100KB - 10MB)', min: 102400, max: 10485760 },
  { value: 'large', label: 'Large (10MB - 100MB)', min: 10485760, max: 104857600 },
  { value: 'huge', label: 'Huge (> 100MB)', min: 104857600, max: Infinity },
];

const dateRanges = [
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'Past Week' },
  { value: 'month', label: 'Past Month' },
  { value: 'quarter', label: 'Past 3 Months' },
  { value: 'year', label: 'Past Year' },
  { value: 'older', label: 'Older than 1 Year' },
];

export function FilterPanel({
  filters,
  onFiltersChange,
  onClose,
  className,
}: FilterPanelProps) {
  const [activeTab, setActiveTab] = useState<'permissions' | 'types' | 'categories' | 'advanced'>('permissions');

  const handlePermissionToggle = useCallback((permission: string) => {
    const newPermissions = filters.permissions.includes(permission)
      ? filters.permissions.filter(p => p !== permission)
      : [...filters.permissions, permission];
    
    onFiltersChange({
      ...filters,
      permissions: newPermissions,
    });
  }, [filters, onFiltersChange]);

  const handleFileTypeToggle = useCallback((fileType: string) => {
    const newFileTypes = filters.fileTypes.includes(fileType)
      ? filters.fileTypes.filter(t => t !== fileType)
      : [...filters.fileTypes, fileType];
    
    onFiltersChange({
      ...filters,
      fileTypes: newFileTypes,
    });
  }, [filters, onFiltersChange]);

  const handleCategoryToggle = useCallback((category: string) => {
    const newCategories = filters.categories.includes(category)
      ? filters.categories.filter(c => c !== category)
      : [...filters.categories, category];
    
    onFiltersChange({
      ...filters,
      categories: newCategories,
    });
  }, [filters, onFiltersChange]);

  const clearAllFilters = useCallback(() => {
    onFiltersChange({
      permissions: [],
      fileTypes: [],
      categories: [],
    });
  }, [onFiltersChange]);

  const hasActiveFilters = 
    filters.permissions.length > 0 || 
    filters.fileTypes.length > 0 || 
    filters.categories.length > 0;

  const tabs = [
    { id: 'permissions', label: 'Permissions', count: filters.permissions.length },
    { id: 'types', label: 'File Types', count: filters.fileTypes.length },
    { id: 'categories', label: 'Categories', count: filters.categories.length },
    { id: 'advanced', label: 'Advanced', count: 0 },
  ] as const;

  return (
    <div className={clsx('bg-white border-l border-gray-200', className)}>
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Filter size={18} className="text-gray-600" />
              <h3 className="text-lg font-medium text-gray-900">Filters</h3>
              {hasActiveFilters && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-100 text-primary-800">
                  {filters.permissions.length + filters.fileTypes.length + filters.categories.length}
                </span>
              )}
            </div>
            <div className="flex items-center space-x-2">
              {hasActiveFilters && (
                <button
                  onClick={clearAllFilters}
                  className="text-sm text-gray-500 hover:text-gray-700"
                >
                  Clear All
                </button>
              )}
              <button
                onClick={onClose}
                className="p-1 text-gray-400 hover:text-gray-600 rounded"
              >
                <X size={18} />
              </button>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="px-4 pt-3">
          <nav className="flex space-x-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={clsx(
                  'px-3 py-2 text-sm font-medium rounded-lg transition-colors',
                  activeTab === tab.id
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                )}
              >
                {tab.label}
                {tab.count > 0 && (
                  <span className="ml-1 inline-flex items-center px-1.5 py-0.5 rounded-full text-xs bg-gray-200 text-gray-700">
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto px-4 py-4">
          {activeTab === 'permissions' && (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3">Permission Levels</h4>
                <div className="space-y-2">
                  {(['read-only', 'read-write', 'agent-controlled'] as const).map((permission) => (
                    <label
                      key={permission}
                      className={clsx(
                        'flex items-center p-3 rounded-lg border cursor-pointer transition-all',
                        filters.permissions.includes(permission)
                          ? 'border-primary-200 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300'
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={filters.permissions.includes(permission)}
                        onChange={() => handlePermissionToggle(permission)}
                        className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      <div className="ml-3 flex-1">
                        <div className="text-sm font-medium text-gray-900">
                          {permission === 'read-only' && 'Read Only'}
                          {permission === 'read-write' && 'Read Write'}
                          {permission === 'agent-controlled' && 'Agent Controlled'}
                        </div>
                        <div className="text-xs text-gray-500">
                          {permission === 'read-only' && 'Reference materials - cannot be modified'}
                          {permission === 'read-write' && 'Editable documents for collaboration'}
                          {permission === 'agent-controlled' && 'AI agents can create and manage files'}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'types' && (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3">File Types</h4>
                <div className="grid grid-cols-2 gap-2">
                  {fileTypeOptions.map((option) => {
                    const IconComponent = option.icon;
                    return (
                      <label
                        key={option.value}
                        className={clsx(
                          'flex items-center p-3 rounded-lg border cursor-pointer transition-all',
                          filters.fileTypes.includes(option.value)
                            ? 'border-primary-200 bg-primary-50'
                            : 'border-gray-200 hover:border-gray-300'
                        )}
                      >
                        <input
                          type="checkbox"
                          checked={filters.fileTypes.includes(option.value)}
                          onChange={() => handleFileTypeToggle(option.value)}
                          className="sr-only"
                        />
                        <IconComponent size={16} className="mr-2 text-gray-600" />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-gray-900 truncate">
                            {option.label}
                          </div>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'categories' && (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3">Content Categories</h4>
                <div className="space-y-2">
                  {categoryOptions.map((option) => (
                    <label
                      key={option.value}
                      className={clsx(
                        'flex items-start p-3 rounded-lg border cursor-pointer transition-all',
                        filters.categories.includes(option.value)
                          ? 'border-primary-200 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300'
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={filters.categories.includes(option.value)}
                        onChange={() => handleCategoryToggle(option.value)}
                        className="mt-0.5 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      <div className="ml-3 flex-1">
                        <div className="text-sm font-medium text-gray-900">
                          {option.label}
                        </div>
                        <div className="text-xs text-gray-500">
                          {option.description}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'advanced' && (
            <div className="space-y-6">
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3">File Size</h4>
                <div className="space-y-2">
                  {sizeRanges.map((range) => (
                    <label
                      key={range.value}
                      className="flex items-center p-2 rounded hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      <HardDrive size={14} className="ml-3 mr-2 text-gray-400" />
                      <span className="text-sm text-gray-700">{range.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3">Date Modified</h4>
                <div className="space-y-2">
                  {dateRanges.map((range) => (
                    <label
                      key={range.value}
                      className="flex items-center p-2 rounded hover:bg-gray-50 cursor-pointer"
                    >
                      <input
                        type="checkbox"
                        className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                      />
                      <Calendar size={14} className="ml-3 mr-2 text-gray-400" />
                      <span className="text-sm text-gray-700">{range.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-3">Custom Date Range</h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      From
                    </label>
                    <input
                      type="date"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-700 mb-1">
                      To
                    </label>
                    <input
                      type="date"
                      className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
          <div className="flex items-center justify-between text-sm text-gray-600">
            <span>
              {hasActiveFilters 
                ? `${filters.permissions.length + filters.fileTypes.length + filters.categories.length} filter${filters.permissions.length + filters.fileTypes.length + filters.categories.length === 1 ? '' : 's'} active`
                : 'No filters applied'
              }
            </span>
            {hasActiveFilters && (
              <button
                onClick={clearAllFilters}
                className="text-primary-600 hover:text-primary-700 font-medium"
              >
                Clear All
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}