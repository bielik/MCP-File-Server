import { create } from 'zustand';

// Re-using existing interfaces from App.tsx
interface ServerConfig {
  permissionMatrix: {
    contextFolders: string[];
    workingFolders: string[];
    outputFolder: string;
  };
  serverConfig: {
    mcpPort: number;
    webUIPort: number;
    enableCaching: boolean;
    logLevel: string;
  };
}

interface ServerStats {
  contextFiles: number;
  workingFiles: number;
  outputFiles: number;
  totalSize: number;
  lastAccess: string;
}

interface AppState {
  config: ServerConfig | null;
  stats: ServerStats | null;
  loading: boolean;
  error: string | null;
  fetchInitialData: () => Promise<void>;
  clearAllEmbeddings: () => Promise<string>;
}

export const useAppStore = create<AppState>((set, get) => ({
  config: null,
  stats: null,
  loading: true,
  error: null,
  fetchInitialData: async () => {
    set({ loading: true, error: null });
    try {
      const configRes = await fetch('/api/config');
      if (!configRes.ok) throw new Error('Failed to fetch server config');
      const configData = await configRes.json();

      const statsRes = await fetch('/api/stats');
      if (!statsRes.ok) throw new Error('Failed to fetch server stats');
      const statsData = await statsRes.json();
      
      set({ config: configData, stats: statsData, loading: false });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : 'Unknown error', loading: false });
    }
  },
  clearAllEmbeddings: async () => {
    const response = await fetch('/api/config/clear-embeddings', { method: 'POST' });
    if (!response.ok) {
        const result = await response.json();
        throw new Error(result.error || 'Failed to clear embeddings');
    }
    const result = await response.json();
    // Re-fetch stats after clearing to update the UI
    get().fetchInitialData();
    return result.message || 'Embeddings cleared successfully';
  }
}));