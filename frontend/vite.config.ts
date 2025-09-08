import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  base: '/',
  
  // Move cache to temp directory to avoid Windows permission issues
  cacheDir: path.join(process.env.TEMP || 'C:/temp', 'vite-cache'),
  
  // Path aliases
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@/components': path.resolve(__dirname, './src/components'),
      '@/types': path.resolve(__dirname, './src/types'),
      '@/services': path.resolve(__dirname, './src/services'),
      '@/hooks': path.resolve(__dirname, './src/hooks'),
      '@/utils': path.resolve(__dirname, './src/utils'),
    },
  },

  // Development server configuration
  server: {
    port: 3004,
    host: true,
    strictPort: true,
    
    // Proxy API calls to the backend server
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true,
        secure: false,
      },
      '/socket.io': {
        target: 'http://localhost:3001',
        changeOrigin: true,
        ws: true,
      },
    },
  },

  // Build configuration
  build: {
    outDir: './dist',
    sourcemap: true,
    
    // Optimize dependencies
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['lucide-react', 'react-dnd', 'react-dnd-html5-backend'],
          utils: ['react-window'],
        },
      },
    },
  },

  // Environment variables
  define: {
    __API_BASE_URL__: JSON.stringify(process.env.NODE_ENV === 'production' ? '' : 'http://localhost:3001'),
  },
});