import React, { useState, useRef, useEffect } from 'react';
import type { LucideIcon } from 'lucide-react';
import { PermissionSelector } from '../Permissions/PermissionBadge';
import { 
  X, 
  FileText, 
  Folder, 
  Code, 
  FileSpreadsheet,
  Database
} from 'lucide-react';
import clsx from 'clsx';

interface CreateFileModalProps {
  onClose: () => void;
  onCreate: (name: string, type: 'file' | 'folder', content?: string) => void;
  defaultPath?: string;
}

type FileTemplate = {
  id: string;
  name: string;
  icon: LucideIcon;
  extension: string;
  content: string;
  description: string;
  category: 'document' | 'code' | 'data' | 'other';
};

const fileTemplates: FileTemplate[] = [
  {
    id: 'markdown',
    name: 'Markdown Document',
    icon: FileText,
    extension: '.md',
    content: '# New Document\n\nStart writing your content here...\n',
    description: 'Formatted text document with markdown syntax',
    category: 'document',
  },
  {
    id: 'text',
    name: 'Plain Text',
    icon: FileText,
    extension: '.txt',
    content: '',
    description: 'Simple text file',
    category: 'document',
  },
  {
    id: 'javascript',
    name: 'JavaScript File',
    icon: Code,
    extension: '.js',
    content: '// New JavaScript file\nconsole.log("Hello, world!");\n',
    description: 'JavaScript source code',
    category: 'code',
  },
  {
    id: 'typescript',
    name: 'TypeScript File',
    icon: Code,
    extension: '.ts',
    content: '// New TypeScript file\nfunction hello(name: string): string {\n  return `Hello, ${name}!`;\n}\n\nconsole.log(hello("World"));\n',
    description: 'TypeScript source code',
    category: 'code',
  },
  {
    id: 'json',
    name: 'JSON Data',
    icon: Database,
    extension: '.json',
    content: '{\n  "name": "New JSON file",\n  "version": "1.0.0"\n}\n',
    description: 'Structured data file',
    category: 'data',
  },
  {
    id: 'csv',
    name: 'CSV Spreadsheet',
    icon: FileSpreadsheet,
    extension: '.csv',
    content: 'Column1,Column2,Column3\nValue1,Value2,Value3\n',
    description: 'Comma-separated values',
    category: 'data',
  },
];

export function CreateFileModal({
  onClose,
  onCreate,
  defaultPath = '',
}: CreateFileModalProps) {
  const [step, setStep] = useState<'type' | 'details'>('type');
  const [fileType, setFileType] = useState<'file' | 'folder'>('file');
  const [selectedTemplate, setSelectedTemplate] = useState<FileTemplate>(fileTemplates[0]);
  const [fileName, setFileName] = useState('');
  const [fileContent, setFileContent] = useState('');
  const [permission, setPermission] = useState<'read-only' | 'read-write' | 'agent-controlled'>('read-write');
  const [isCreating, setIsCreating] = useState(false);

  const modalRef = useRef<HTMLDivElement>(null);
  const fileNameInputRef = useRef<HTMLInputElement>(null);

  // Focus file name input when step changes to details
  useEffect(() => {
    if (step === 'details' && fileNameInputRef.current) {
      fileNameInputRef.current.focus();
    }
  }, [step]);

  // Handle escape key and click outside
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    const handleClickOutside = (event: MouseEvent) => {
      if (modalRef.current && !modalRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleClickOutside);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);

  const handleNext = () => {
    if (fileType === 'file') {
      setFileContent(selectedTemplate.content);
      setFileName(selectedTemplate.name.toLowerCase().replace(/\s+/g, '-'));
    } else {
      setFileName('new-folder');
      setFileContent('');
    }
    setStep('details');
  };

  const handleCreate = async () => {
    if (!fileName.trim()) return;

    setIsCreating(true);
    try {
      const finalName = fileType === 'file' && !fileName.includes('.') 
        ? fileName + selectedTemplate.extension 
        : fileName;
      
      await onCreate(finalName.trim(), fileType, fileContent);
    } catch (error) {
      console.error('Failed to create file:', error);
    } finally {
      setIsCreating(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (step === 'type') {
      handleNext();
    } else {
      handleCreate();
    }
  };

  const groupedTemplates = fileTemplates.reduce((groups, template) => {
    if (!groups[template.category]) {
      groups[template.category] = [];
    }
    groups[template.category].push(template);
    return groups;
  }, {} as Record<string, FileTemplate[]>);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div
        ref={modalRef}
        className="bg-white rounded-lg shadow-xl w-full max-w-2xl mx-4 max-h-[90vh] overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {step === 'type' ? 'Create New' : `Create ${fileType === 'file' ? 'File' : 'Folder'}`}
            </h2>
            {step === 'details' && (
              <p className="text-sm text-gray-500 mt-1">
                Step 2 of 2: Configure details
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col h-full">
          <div className="flex-1 overflow-y-auto">
            {step === 'type' ? (
              <div className="p-6">
                {/* Type Selection */}
                <div className="mb-6">
                  <div className="flex space-x-4">
                    <button
                      type="button"
                      onClick={() => setFileType('file')}
                      className={clsx(
                        'flex-1 p-4 border-2 rounded-lg transition-all',
                        fileType === 'file'
                          ? 'border-primary-300 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300'
                      )}
                    >
                      <FileText size={32} className="mx-auto mb-2 text-primary-600" />
                      <div className="text-sm font-medium text-gray-900">File</div>
                      <div className="text-xs text-gray-500">Create a new document or code file</div>
                    </button>
                    
                    <button
                      type="button"
                      onClick={() => setFileType('folder')}
                      className={clsx(
                        'flex-1 p-4 border-2 rounded-lg transition-all',
                        fileType === 'folder'
                          ? 'border-primary-300 bg-primary-50'
                          : 'border-gray-200 hover:border-gray-300'
                      )}
                    >
                      <Folder size={32} className="mx-auto mb-2 text-primary-600" />
                      <div className="text-sm font-medium text-gray-900">Folder</div>
                      <div className="text-xs text-gray-500">Organize files in a new folder</div>
                    </button>
                  </div>
                </div>

                {/* Template Selection (only for files) */}
                {fileType === 'file' && (
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 mb-3">Choose a template</h3>
                    <div className="space-y-4">
                      {Object.entries(groupedTemplates).map(([category, templates]) => (
                        <div key={category}>
                          <h4 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                            {category}
                          </h4>
                          <div className="grid grid-cols-2 gap-2">
                            {templates.map((template) => {
                              const IconComponent = template.icon;
                              return (
                                <button
                                  key={template.id}
                                  type="button"
                                  onClick={() => setSelectedTemplate(template)}
                                  className={clsx(
                                    'flex items-start p-3 text-left border rounded-lg transition-all',
                                    selectedTemplate.id === template.id
                                      ? 'border-primary-300 bg-primary-50'
                                      : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                                  )}
                                >
                                  <IconComponent size={20} className="mr-3 mt-0.5 flex-shrink-0 text-gray-600" />
                                  <div className="flex-1 min-w-0">
                                    <div className="text-sm font-medium text-gray-900">
                                      {template.name}
                                    </div>
                                    <div className="text-xs text-gray-500 mt-1">
                                      {template.description}
                                    </div>
                                  </div>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="p-6 space-y-6">
                {/* File Name */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    {fileType === 'file' ? 'File Name' : 'Folder Name'}
                  </label>
                  <div className="flex">
                    <input
                      ref={fileNameInputRef}
                      type="text"
                      value={fileName}
                      onChange={(e) => setFileName(e.target.value)}
                      className="flex-1 px-3 py-2 border border-gray-300 rounded-l-md focus:ring-primary-500 focus:border-primary-500"
                      placeholder={fileType === 'file' ? 'my-document' : 'my-folder'}
                      required
                    />
                    {fileType === 'file' && (
                      <div className="flex items-center px-3 py-2 bg-gray-50 border border-l-0 border-gray-300 rounded-r-md text-sm text-gray-500">
                        {selectedTemplate.extension}
                      </div>
                    )}
                  </div>
                </div>

                {/* File Content (only for files) */}
                {fileType === 'file' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Initial Content
                    </label>
                    <textarea
                      value={fileContent}
                      onChange={(e) => setFileContent(e.target.value)}
                      rows={8}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-primary-500 focus:border-primary-500 font-mono text-sm"
                      placeholder="Start typing your content..."
                    />
                  </div>
                )}

                {/* Permission Selection */}
                <div>
                  <PermissionSelector
                    value={permission}
                    onChange={(p) => setPermission(p as any)}
                    disabled={false}
                  />
                </div>

                {/* Path Preview */}
                {defaultPath && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Will be created at:
                    </label>
                    <div className="px-3 py-2 bg-gray-50 border border-gray-300 rounded-md text-sm font-mono text-gray-600">
                      {defaultPath}{defaultPath.endsWith('/') ? '' : '/'}{fileName}{fileType === 'file' ? selectedTemplate.extension : ''}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 bg-gray-50">
            <div className="flex items-center space-x-2">
              {step === 'details' && (
                <button
                  type="button"
                  onClick={() => setStep('type')}
                  className="px-3 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
                >
                  ← Back
                </button>
              )}
            </div>

            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
              
              <button
                type="submit"
                disabled={isCreating || (step === 'details' && !fileName.trim())}
                className={clsx(
                  'px-4 py-2 text-sm font-medium rounded-md transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500',
                  isCreating || (step === 'details' && !fileName.trim())
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-primary-600 text-white hover:bg-primary-700'
                )}
              >
                {isCreating ? (
                  <div className="flex items-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                    Creating...
                  </div>
                ) : step === 'type' ? (
                  'Next →'
                ) : (
                  `Create ${fileType === 'file' ? 'File' : 'Folder'}`
                )}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}