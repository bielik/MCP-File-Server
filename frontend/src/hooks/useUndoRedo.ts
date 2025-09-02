import { useState, useCallback, useRef } from 'react';

interface UndoRedoAction {
  type: 'permission-assign' | 'permission-remove' | 'selection-change';
  timestamp: number;
  data: {
    paths: string[];
    oldPermissions?: Record<string, string | null>;
    newPermissions?: Record<string, string | null>;
    oldSelection?: string[];
    newSelection?: string[];
  };
  description: string;
}

export const useUndoRedo = (maxHistorySize = 50) => {
  const [history, setHistory] = useState<UndoRedoAction[]>([]);
  const [currentIndex, setCurrentIndex] = useState(-1);
  const isUndoRedoInProgress = useRef(false);

  const addAction = useCallback((action: Omit<UndoRedoAction, 'timestamp'>) => {
    if (isUndoRedoInProgress.current) return;

    const newAction: UndoRedoAction = {
      ...action,
      timestamp: Date.now(),
    };

    setHistory(prev => {
      // Remove any actions after current index (when we were in the middle of history)
      const newHistory = prev.slice(0, currentIndex + 1);
      newHistory.push(newAction);
      
      // Keep only the last maxHistorySize actions
      return newHistory.slice(-maxHistorySize);
    });

    setCurrentIndex(prev => Math.min(prev + 1, maxHistorySize - 1));
  }, [currentIndex, maxHistorySize]);

  const undo = useCallback(async (
    onPermissionRestore: (paths: string[], permissions: Record<string, string | null>) => Promise<void>,
    onSelectionRestore: (selection: string[]) => void
  ) => {
    if (currentIndex < 0) return null;

    const action = history[currentIndex];
    if (!action) return null;

    isUndoRedoInProgress.current = true;

    try {
      switch (action.type) {
        case 'permission-assign':
        case 'permission-remove':
          if (action.data.oldPermissions) {
            await onPermissionRestore(action.data.paths, action.data.oldPermissions);
          }
          break;
        case 'selection-change':
          if (action.data.oldSelection) {
            onSelectionRestore(action.data.oldSelection);
          }
          break;
      }

      setCurrentIndex(prev => prev - 1);
      return action;
    } finally {
      isUndoRedoInProgress.current = false;
    }
  }, [currentIndex, history]);

  const redo = useCallback(async (
    onPermissionRestore: (paths: string[], permissions: Record<string, string | null>) => Promise<void>,
    onSelectionRestore: (selection: string[]) => void
  ) => {
    if (currentIndex >= history.length - 1) return null;

    const nextIndex = currentIndex + 1;
    const action = history[nextIndex];
    if (!action) return null;

    isUndoRedoInProgress.current = true;

    try {
      switch (action.type) {
        case 'permission-assign':
        case 'permission-remove':
          if (action.data.newPermissions) {
            await onPermissionRestore(action.data.paths, action.data.newPermissions);
          }
          break;
        case 'selection-change':
          if (action.data.newSelection) {
            onSelectionRestore(action.data.newSelection);
          }
          break;
      }

      setCurrentIndex(nextIndex);
      return action;
    } finally {
      isUndoRedoInProgress.current = false;
    }
  }, [currentIndex, history]);

  const canUndo = currentIndex >= 0;
  const canRedo = currentIndex < history.length - 1;

  const getUndoDescription = () => {
    if (currentIndex >= 0 && history[currentIndex]) {
      return `Undo: ${history[currentIndex].description}`;
    }
    return 'Undo';
  };

  const getRedoDescription = () => {
    const nextIndex = currentIndex + 1;
    if (nextIndex < history.length && history[nextIndex]) {
      return `Redo: ${history[nextIndex].description}`;
    }
    return 'Redo';
  };

  const clearHistory = useCallback(() => {
    setHistory([]);
    setCurrentIndex(-1);
  }, []);

  return {
    addAction,
    undo,
    redo,
    canUndo,
    canRedo,
    getUndoDescription,
    getRedoDescription,
    clearHistory,
    history: history.slice(0, currentIndex + 1), // Only show actions up to current index
  };
};