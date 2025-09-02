import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Search, X, Clock, FileText, Image, Folder } from 'lucide-react';
import clsx from 'clsx';

interface SearchSuggestion {
  id: string;
  text: string;
  type: 'file' | 'folder' | 'content' | 'recent';
  path?: string;
  preview?: string;
}

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  suggestions?: SearchSuggestion[];
  isLoading?: boolean;
  onSuggestionSelect?: (suggestion: SearchSuggestion) => void;
  onSearch?: (query: string) => void;
  className?: string;
}

const mockSuggestions: SearchSuggestion[] = [
  {
    id: '1',
    text: 'research-proposal.md',
    type: 'file',
    path: '/working/research-proposal.md',
    preview: 'Draft research proposal for multimodal AI...',
  },
  {
    id: '2',
    text: 'methodology',
    type: 'content',
    preview: 'Found in 3 documents...',
  },
  {
    id: '3',
    text: 'figures',
    type: 'folder',
    path: '/context/figures',
  },
  {
    id: '4',
    text: 'neural networks',
    type: 'recent',
  },
];

export function SearchBar({
  value,
  onChange,
  placeholder = 'Search files and content...',
  suggestions = mockSuggestions,
  isLoading = false,
  onSuggestionSelect,
  onSearch,
  className,
}: SearchBarProps) {
  const [isFocused, setIsFocused] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Filter suggestions based on input
  const filteredSuggestions = suggestions.filter(suggestion =>
    suggestion.text.toLowerCase().includes(value.toLowerCase())
  );

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
    setSelectedIndex(-1);
    setShowSuggestions(newValue.length > 0);
  }, [onChange]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!showSuggestions) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < filteredSuggestions.length - 1 ? prev + 1 : 0
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev > 0 ? prev - 1 : filteredSuggestions.length - 1
        );
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          const suggestion = filteredSuggestions[selectedIndex];
          handleSuggestionSelect(suggestion);
        } else if (onSearch) {
          onSearch(value);
          setShowSuggestions(false);
        }
        break;
      case 'Escape':
        setShowSuggestions(false);
        setSelectedIndex(-1);
        inputRef.current?.blur();
        break;
    }
  }, [showSuggestions, selectedIndex, filteredSuggestions, value, onSearch]);

  const handleSuggestionSelect = useCallback((suggestion: SearchSuggestion) => {
    onChange(suggestion.text);
    setShowSuggestions(false);
    setSelectedIndex(-1);
    onSuggestionSelect?.(suggestion);
    inputRef.current?.blur();
  }, [onChange, onSuggestionSelect]);

  const handleClear = useCallback(() => {
    onChange('');
    setShowSuggestions(false);
    setSelectedIndex(-1);
    inputRef.current?.focus();
  }, [onChange]);

  const handleFocus = useCallback(() => {
    setIsFocused(true);
    if (value.length > 0) {
      setShowSuggestions(true);
    }
  }, [value]);

  const handleBlur = useCallback(() => {
    setIsFocused(false);
    // Delay hiding suggestions to allow clicks
    setTimeout(() => setShowSuggestions(false), 150);
  }, []);

  // Close suggestions when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(event.target as Node) &&
        !inputRef.current?.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getSuggestionIcon = (type: SearchSuggestion['type']) => {
    switch (type) {
      case 'file': return FileText;
      case 'folder': return Folder;
      case 'content': return Search;
      case 'recent': return Clock;
      default: return Search;
    }
  };

  return (
    <div className={clsx('relative', className)}>
      <div
        className={clsx(
          'relative flex items-center rounded-lg border transition-all duration-200',
          isFocused
            ? 'border-primary-300 ring-2 ring-primary-100 bg-white'
            : 'border-gray-300 bg-gray-50 hover:bg-white hover:border-gray-400'
        )}
      >
        <div className="absolute left-3 flex items-center">
          {isLoading ? (
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary-500 border-t-transparent" />
          ) : (
            <Search size={16} className="text-gray-400" />
          )}
        </div>
        
        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={placeholder}
          className="w-full pl-10 pr-10 py-2.5 bg-transparent focus:outline-none text-sm placeholder-gray-500"
        />
        
        {value && (
          <button
            onClick={handleClear}
            className="absolute right-3 p-0.5 text-gray-400 hover:text-gray-600 rounded transition-colors"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Suggestions Dropdown */}
      {showSuggestions && filteredSuggestions.length > 0 && (
        <div
          ref={suggestionsRef}
          className="absolute top-full left-0 right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-50 max-h-64 overflow-y-auto"
        >
          <div className="py-1">
            {filteredSuggestions.map((suggestion, index) => {
              const IconComponent = getSuggestionIcon(suggestion.type);
              return (
                <button
                  key={suggestion.id}
                  onClick={() => handleSuggestionSelect(suggestion)}
                  className={clsx(
                    'w-full flex items-start px-3 py-2 text-left hover:bg-gray-50 transition-colors',
                    index === selectedIndex && 'bg-primary-50'
                  )}
                >
                  <div className="flex-shrink-0 mt-0.5">
                    <IconComponent 
                      size={16} 
                      className={clsx(
                        'mr-3',
                        suggestion.type === 'file' && 'text-blue-500',
                        suggestion.type === 'folder' && 'text-orange-500',
                        suggestion.type === 'content' && 'text-green-500',
                        suggestion.type === 'recent' && 'text-gray-400'
                      )} 
                    />
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm text-gray-900 truncate">
                      {suggestion.text}
                    </div>
                    
                    {suggestion.path && (
                      <div className="text-xs text-gray-500 truncate mt-0.5">
                        {suggestion.path}
                      </div>
                    )}
                    
                    {suggestion.preview && (
                      <div className="text-xs text-gray-600 truncate mt-0.5">
                        {suggestion.preview}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex-shrink-0 ml-2">
                    <span className={clsx(
                      'inline-block px-1.5 py-0.5 rounded text-xs font-medium',
                      suggestion.type === 'file' && 'bg-blue-100 text-blue-700',
                      suggestion.type === 'folder' && 'bg-orange-100 text-orange-700',
                      suggestion.type === 'content' && 'bg-green-100 text-green-700',
                      suggestion.type === 'recent' && 'bg-gray-100 text-gray-700'
                    )}>
                      {suggestion.type}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
          
          {/* Search Footer */}
          <div className="border-t border-gray-100 px-3 py-2 bg-gray-50">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Press Enter to search all files</span>
              <div className="flex items-center space-x-2">
                <kbd className="px-1.5 py-0.5 bg-gray-200 rounded text-xs">↑↓</kbd>
                <span>navigate</span>
                <kbd className="px-1.5 py-0.5 bg-gray-200 rounded text-xs">Enter</kbd>
                <span>select</span>
                <kbd className="px-1.5 py-0.5 bg-gray-200 rounded text-xs">Esc</kbd>
                <span>close</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}