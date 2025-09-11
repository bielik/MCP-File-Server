import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"

// [https://vitejs.dev/config/](https://vitejs.dev/config/)
export default defineConfig({
  plugins: [react()],
  server: {
    host: true, // Listen on all network interfaces
    port: 5173,
    watch: {
      usePolling: true, // Use polling for file changes
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
})
