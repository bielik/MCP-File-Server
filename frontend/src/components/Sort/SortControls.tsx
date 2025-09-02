import React, { useState, useRef, useEffect } from 'react';
import { SortOptions } from '../../types/index';
import { ArrowUpDown, ChevronDown, ArrowUp, ArrowDown } from 'lucide-react';
import clsx from 'clsx';

interface SortOption {
  field: keyof SortOptions['field'];
  label: string;
}

interface SortControlsProps {
  sorting: SortOptions;
  onSortingChange: (sorting: SortOptions) => void;
  options: SortOption[];
  className?: string;
}

export function SortControls({
  sorting,
  onSortingChange,
  options,
  className,
}: SortControlsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const currentOption = options.find(option => option.field === sorting.field);

  const handleSort = (field: SortOptions['field']) => {
    const newDirection = 
      sorting.field === field && sorting.direction === 'asc' ? 'desc' : 'asc';
    
    onSortingChange({ field, direction: newDirection });
    setIsOpen(false);
  };

  const toggleDirection = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSortingChange({
      field: sorting.field,
      direction: sorting.direction === 'asc' ? 'desc' : 'asc',
    });
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div ref={dropdownRef} className={clsx('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-white border border-gray-300 rounded-md hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors"
      >
        <ArrowUpDown size={14} className="text-gray-500" />
        <span className="text-gray-700">
          Sort by {currentOption?.label || 'Name'}
        </span>
        <div className="flex items-center space-x-1">
          <button
            onClick={toggleDirection}
            className="p-0.5 hover:bg-gray-100 rounded transition-colors"
            title={`Sort ${sorting.direction === 'asc' ? 'descending' : 'ascending'}`}
          >
            {sorting.direction === 'asc' ? (
              <ArrowUp size={14} className="text-gray-500" />
            ) : (
              <ArrowDown size={14} className="text-gray-500" />
            )}
          </button>
          <ChevronDown 
            size={14} 
            className={clsx(
              'text-gray-500 transition-transform',
              isOpen && 'rotate-180'
            )} 
          />
        </div>
      </button>

      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-48 bg-white border border-gray-200 rounded-md shadow-lg z-10">
          <div className="py-1">
            {options.map((option) => (
              <button
                key={option.field}
                onClick={() => handleSort(option.field)}
                className={clsx(
                  'w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-gray-50 transition-colors',
                  sorting.field === option.field && 'bg-primary-50 text-primary-700'
                )}
              >
                <span>{option.label}</span>
                {sorting.field === option.field && (
                  <div className="flex items-center">
                    {sorting.direction === 'asc' ? (
                      <ArrowUp size={14} />
                    ) : (
                      <ArrowDown size={14} />
                    )}
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}