import React, { useState, useRef, useEffect } from 'react';
import { 
  Home, 
  ChevronRight, 
  Edit3, 
  Check, 
  X, 
  Folder,
  HardDrive,
  User
} from 'lucide-react';

interface BreadcrumbItem {
  name: string;
  path: string;
}

interface AddressBarProps {
  currentPath: string;
  onNavigate: (path: string) => void;
  isNavigating?: boolean;
}

export const AddressBar: React.FC<AddressBarProps> = ({
  currentPath,
  onNavigate,
  isNavigating = false
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editPath, setEditPath] = useState('');
  const [suggestions, setSuggestions] = useState<{ name: string; path: string; icon: string }[]>([]);
  const [commonPaths, setCommonPaths] = useState<{ name: string; path: string; icon: string }[]>([]);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const suggestionRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Load common paths from backend
  useEffect(() => {
    const fetchCommonPaths = async () => {
      try {
        const response = await fetch('/api/filesystem/common-paths');
        if (response.ok) {
          const paths = await response.json();
          setCommonPaths(paths);
        }
      } catch (error) {
        console.warn('Failed to fetch common paths:', error);
        // Fallback to static paths
        const userProfile = 'C:\\Users\\MartinBielik';
        setCommonPaths([
          { name: 'This PC', path: '', icon: 'hard-drive' },
          { name: 'Documents', path: `${userProfile}\\Documents`, icon: 'folder' },
          { name: 'Downloads', path: `${userProfile}\\Downloads`, icon: 'folder' },
          { name: 'OneDrive - Decoding Spaces', path: `${userProfile}\\OneDrive - Decoding Spaces GbR`, icon: 'folder' },
          { name: 'Desktop', path: `${userProfile}\\Desktop`, icon: 'folder' },
        ]);
      }
    };

    fetchCommonPaths();
  }, []);

  const getIconComponent = (iconName: string) => {
    switch (iconName) {
      case 'hard-drive': return <HardDrive className="w-4 h-4" />;
      case 'folder': return <Folder className="w-4 h-4" />;
      case 'user': return <User className="w-4 h-4" />;
      default: return <Folder className="w-4 h-4" />;
    }
  };

  const getBreadcrumbPath = (): BreadcrumbItem[] => {
    if (!currentPath) return [{ name: 'This PC', path: '' }];
    
    const parts = currentPath.split(/[/\\]/).filter(Boolean);
    const breadcrumbs: BreadcrumbItem[] = [{ name: 'This PC', path: '' }];
    
    let accumulatedPath = '';
    parts.forEach((part, index) => {
      if (index === 0 && part.endsWith(':')) {
        // Windows drive letter
        accumulatedPath = part + '\\';
        breadcrumbs.push({ name: part, path: accumulatedPath });
      } else {
        accumulatedPath += (accumulatedPath.endsWith('\\') ? '' : '\\') + part;
        breadcrumbs.push({ name: part, path: accumulatedPath });
      }
    });
    
    return breadcrumbs;
  };

  const handleEditStart = () => {
    setIsEditing(true);
    setEditPath(currentPath || '');
    setTimeout(() => inputRef.current?.focus(), 0);
  };

  const handleEditCancel = () => {
    setIsEditing(false);
    setEditPath('');
    setSuggestions([]);
  };

  const handleEditSubmit = async () => {
    if (editPath.trim()) {
      // Validate path with backend before navigating
      try {
        const response = await fetch('/api/filesystem/validate-path', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ path: editPath.trim() }),
        });

        const result = await response.json();
        
        if (result.valid && result.accessible) {
          onNavigate(result.normalizedPath);
          setValidationMessage(null);
        } else {
          if (result.suggestion) {
            setValidationMessage(`Path not found. Did you mean: ${result.suggestion}?`);
            setEditPath(result.suggestion);
          } else {
            setValidationMessage(result.error || 'Path is not accessible');
          }
          return; // Don't close editing mode if path is invalid
        }
      } catch (error) {
        setValidationMessage('Failed to validate path');
        return;
      }
    }
    setIsEditing(false);
    setSuggestions([]);
    setValidationMessage(null);
  };

  const handleInputChange = (value: string) => {
    setEditPath(value);
    setValidationMessage(null);
    
    // Generate suggestions based on input
    const filtered = commonPaths
      .filter(item => 
        item.path.toLowerCase().includes(value.toLowerCase()) ||
        item.name.toLowerCase().includes(value.toLowerCase())
      )
      .slice(0, 5);
    
    setSuggestions(filtered);
  };

  const handleSuggestionClick = (path: string) => {
    setEditPath(path);
    setSuggestions([]);
    inputRef.current?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleEditSubmit();
    } else if (e.key === 'Escape') {
      handleEditCancel();
    }
  };

  // Auto-focus input when editing starts
  useEffect(() => {
    if (isEditing && inputRef.current) {
      inputRef.current.select();
    }
  }, [isEditing]);

  if (isEditing) {
    return (
      <div className="relative">
        <div className="flex items-center space-x-2 p-2 border border-blue-500 rounded bg-white">
          <div className="flex items-center flex-1 min-w-0">
            <input
              ref={inputRef}
              type="text"
              value={editPath}
              onChange={(e) => handleInputChange(e.target.value)}
              onKeyDown={handleKeyDown}
              className="flex-1 min-w-0 px-2 py-1 text-sm bg-transparent outline-none"
              placeholder="Enter path (e.g., C:\Users\MartinBielik\Documents)"
            />
          </div>
          <div className="flex items-center space-x-1">
            <button
              onClick={handleEditSubmit}
              disabled={isNavigating}
              className="p-1 text-green-600 hover:text-green-800 hover:bg-green-50 rounded"
              title="Navigate to path"
            >
              <Check className="w-4 h-4" />
            </button>
            <button
              onClick={handleEditCancel}
              className="p-1 text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded"
              title="Cancel"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
        
        {/* Validation message */}
        {validationMessage && (
          <div className="absolute top-full left-0 right-0 z-10 mt-1 bg-yellow-50 border border-yellow-200 rounded-md p-2 text-sm text-yellow-800">
            {validationMessage}
          </div>
        )}

        {/* Suggestions dropdown */}
        {suggestions.length > 0 && (
          <div className="absolute top-full left-0 right-0 z-10 mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-48 overflow-y-auto">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                ref={(el) => suggestionRefs.current[index] = el}
                onClick={() => handleSuggestionClick(suggestion.path)}
                className="w-full px-3 py-2 text-left text-sm hover:bg-gray-50 focus:bg-gray-50 focus:outline-none flex items-center space-x-2"
              >
                {getIconComponent(suggestion.icon)}
                <div>
                  <div className="font-medium">{suggestion.name}</div>
                  {suggestion.path && (
                    <div className="text-xs text-gray-500">{suggestion.path}</div>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Common shortcuts */}
        <div className="mt-2 flex flex-wrap gap-1">
          {commonPaths.slice(1, 6).map((item) => (
            <button
              key={item.path}
              onClick={() => handleSuggestionClick(item.path)}
              className="inline-flex items-center space-x-1 px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded text-gray-700"
            >
              {getIconComponent(item.icon)}
              <span>{item.name}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-2">
      {/* Breadcrumb navigation */}
      <nav className="flex items-center space-x-1 flex-1 min-w-0">
        {getBreadcrumbPath().map((breadcrumb, index) => (
          <React.Fragment key={breadcrumb.path}>
            {index > 0 && <ChevronRight className="w-3 h-3 text-gray-400 flex-shrink-0" />}
            <button
              onClick={() => onNavigate(breadcrumb.path)}
              disabled={isNavigating}
              className="flex items-center space-x-1 px-2 py-1 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded truncate disabled:opacity-50"
              title={breadcrumb.path || 'This PC'}
            >
              {breadcrumb.name === 'This PC' ? (
                <Home className="w-4 h-4 flex-shrink-0" />
              ) : (
                <span className="truncate">{breadcrumb.name}</span>
              )}
            </button>
          </React.Fragment>
        ))}
      </nav>

      {/* Edit button */}
      <button
        onClick={handleEditStart}
        disabled={isNavigating}
        className="p-1 text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded flex-shrink-0 disabled:opacity-50"
        title="Edit address"
      >
        <Edit3 className="w-4 h-4" />
      </button>
    </div>
  );
};

export default AddressBar;