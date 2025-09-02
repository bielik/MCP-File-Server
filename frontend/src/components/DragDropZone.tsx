import React, { useState, useCallback, useRef } from 'react';
import { 
  Upload, 
  Eye, 
  Edit, 
  FolderPlus, 
  AlertTriangle,
  Check,
  X
} from 'lucide-react';

interface DragDropZoneProps {
  onPermissionAssign: (paths: string[], permission: 'context' | 'working' | 'output') => void;
  selectedPaths: string[];
  onClearSelection: () => void;
}

interface DropZone {
  id: 'context' | 'working' | 'output';
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
  description: string;
}

export const DragDropZone: React.FC<DragDropZoneProps> = ({
  onPermissionAssign,
  selectedPaths,
  onClearSelection
}) => {
  const [draggedOver, setDraggedOver] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [pendingAssignment, setPendingAssignment] = useState<{ permission: 'context' | 'working' | 'output'; paths: string[] } | null>(null);
  const dragCounter = useRef(0);

  const dropZones: DropZone[] = [
    {
      id: 'context',
      label: 'Context (Read-Only)',
      icon: Eye,
      color: 'text-blue-600',
      bgColor: 'bg-blue-50 border-blue-300',
      description: 'Files agents can read for context'
    },
    {
      id: 'working',
      label: 'Working (Read-Write)',
      icon: Edit,
      color: 'text-green-600',
      bgColor: 'bg-green-50 border-green-300',
      description: 'Files agents can read and modify'
    },
    {
      id: 'output',
      label: 'Output (Agent-Controlled)',
      icon: Upload,
      color: 'text-purple-600',
      bgColor: 'bg-purple-50 border-purple-300',
      description: 'Folder where agents can create files'
    }
  ];

  const handleDragStart = useCallback((e: React.DragEvent) => {
    if (selectedPaths.length === 0) {
      e.preventDefault();
      return;
    }
    setIsDragging(true);
    e.dataTransfer.setData('text/plain', JSON.stringify(selectedPaths));
    e.dataTransfer.effectAllowed = 'copy';
  }, [selectedPaths]);

  const handleDragEnd = useCallback(() => {
    setIsDragging(false);
    setDraggedOver(null);
    dragCounter.current = 0;
  }, []);

  const handleDragEnter = useCallback((e: React.DragEvent, zoneId: string) => {
    e.preventDefault();
    dragCounter.current++;
    setDraggedOver(zoneId);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    dragCounter.current--;
    if (dragCounter.current === 0) {
      setDraggedOver(null);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
  }, []);

  const handleDrop = useCallback((e: React.DragEvent, permission: 'context' | 'working' | 'output') => {
    e.preventDefault();
    setDraggedOver(null);
    dragCounter.current = 0;

    try {
      const droppedPaths = JSON.parse(e.dataTransfer.getData('text/plain'));
      if (Array.isArray(droppedPaths) && droppedPaths.length > 0) {
        setPendingAssignment({ permission, paths: droppedPaths });
        setShowConfirmation(true);
      }
    } catch (error) {
      console.error('Failed to parse dropped data:', error);
    }
  }, []);

  const confirmAssignment = useCallback(() => {
    if (pendingAssignment) {
      onPermissionAssign(pendingAssignment.paths, pendingAssignment.permission);
      setShowConfirmation(false);
      setPendingAssignment(null);
      onClearSelection();
    }
  }, [pendingAssignment, onPermissionAssign, onClearSelection]);

  const cancelAssignment = useCallback(() => {
    setShowConfirmation(false);
    setPendingAssignment(null);
  }, []);

  if (selectedPaths.length === 0) {
    return null;
  }

  return (
    <>
      {/* Drag and Drop Zones */}
      <div className="border-t border-gray-200 bg-gray-50 p-4">
        <div className="mb-3">
          <h3 className="text-sm font-medium text-gray-700 mb-1">
            Drag & Drop Assignment
          </h3>
          <p className="text-xs text-gray-500">
            Drag your {selectedPaths.length} selected item{selectedPaths.length > 1 ? 's' : ''} to assign permissions
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {dropZones.map((zone) => {
            const Icon = zone.icon;
            const isHovered = draggedOver === zone.id;
            
            return (
              <div
                key={zone.id}
                className={`
                  relative border-2 border-dashed rounded-lg p-4 transition-all duration-200
                  ${isHovered 
                    ? `${zone.bgColor} border-solid scale-105 shadow-md` 
                    : 'bg-gray-50 border-gray-300 hover:border-gray-400'
                  }
                  ${isDragging ? 'cursor-copy' : 'cursor-default'}
                `}
                onDragEnter={(e) => handleDragEnter(e, zone.id)}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={(e) => handleDrop(e, zone.id)}
              >
                <div className="text-center">
                  <Icon className={`w-8 h-8 mx-auto mb-2 ${isHovered ? zone.color : 'text-gray-400'}`} />
                  <h4 className={`font-medium text-sm ${isHovered ? zone.color : 'text-gray-600'}`}>
                    {zone.label}
                  </h4>
                  <p className="text-xs text-gray-500 mt-1">
                    {zone.description}
                  </p>
                </div>

                {isHovered && (
                  <div className="absolute inset-0 flex items-center justify-center bg-white bg-opacity-90 rounded-lg">
                    <div className="text-center">
                      <FolderPlus className={`w-6 h-6 mx-auto mb-1 ${zone.color}`} />
                      <span className={`text-sm font-medium ${zone.color}`}>
                        Drop to assign
                      </span>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Invisible draggable area for selected items */}
        <div 
          className="absolute inset-0 pointer-events-none"
          draggable={selectedPaths.length > 0}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        />
      </div>

      {/* Confirmation Modal */}
      {showConfirmation && pendingAssignment && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <div className="flex items-center mb-4">
              <AlertTriangle className="w-6 h-6 text-amber-500 mr-2" />
              <h3 className="text-lg font-medium text-gray-900">Confirm Permission Assignment</h3>
            </div>

            <div className="mb-6">
              <p className="text-gray-600 mb-4">
                Are you sure you want to assign <strong>{pendingAssignment.permission}</strong> permission 
                to {pendingAssignment.paths.length} selected item{pendingAssignment.paths.length > 1 ? 's' : ''}?
              </p>

              <div className="bg-gray-50 rounded-lg p-3">
                <h4 className="text-sm font-medium text-gray-700 mb-2">Selected items:</h4>
                <div className="max-h-32 overflow-y-auto">
                  {pendingAssignment.paths.slice(0, 5).map((path, index) => (
                    <div key={index} className="text-xs text-gray-600 truncate">
                      {path.split(/[/\\]/).pop() || path}
                    </div>
                  ))}
                  {pendingAssignment.paths.length > 5 && (
                    <div className="text-xs text-gray-500 mt-1">
                      ...and {pendingAssignment.paths.length - 5} more items
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="flex space-x-3">
              <button
                onClick={confirmAssignment}
                className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors flex items-center justify-center"
              >
                <Check className="w-4 h-4 mr-2" />
                Confirm
              </button>
              <button
                onClick={cancelAssignment}
                className="flex-1 bg-gray-200 text-gray-800 py-2 px-4 rounded-lg hover:bg-gray-300 transition-colors flex items-center justify-center"
              >
                <X className="w-4 h-4 mr-2" />
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};