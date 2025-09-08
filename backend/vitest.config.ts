/**
 * Vitest Configuration for MCP Research File Server Backend
 * 
 * Configuration for testing Phase 3 Step 1: Connect Existing Search to MCP Tools
 */

import { defineConfig } from 'vitest/config';
import path from 'path';

export default defineConfig({
  test: {
    // Test environment
    environment: 'node',
    
    // Global test setup
    globals: true,
    
    // Test file patterns
    include: [
      'tests/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}',
      '**/__tests__/**/*.{js,mjs,cjs,ts,mts,cts,jsx,tsx}',
      '**/test/**/*.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'
    ],
    
    // Exclude patterns
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      '**/.{idea,git,cache,output,temp}/**'
    ],
    
    // Test timeout (increased for integration tests)
    testTimeout: 10000,
    
    // Hook timeout
    hookTimeout: 10000,
    
    // Coverage configuration
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      reportsDirectory: './coverage',
      include: [
        'server/**/*.ts',
        'src/**/*.ts'
      ],
      exclude: [
        'tests/**',
        'dist/**',
        '**/*.d.ts',
        '**/node_modules/**',
        '**/*.config.ts',
        '**/test-*.ts'
      ],
      // Minimum coverage thresholds for Phase 3 Step 1
      thresholds: {
        global: {
          branches: 70,
          functions: 70,
          lines: 70,
          statements: 70
        },
        // Specific thresholds for search handlers
        'server/handlers.ts': {
          branches: 80,
          functions: 80,
          lines: 80,
          statements: 80
        }
      }
    },
    
    // Reporter configuration
    reporters: ['verbose'],
    
    // Mock configuration
    clearMocks: true,
    mockReset: true,
    restoreMocks: true,
    
    // Parallel test execution
    pool: 'threads',
    poolOptions: {
      threads: {
        singleThread: false,
        maxThreads: 4,
        minThreads: 1
      }
    },
    
    // Test setup files
    setupFiles: [
      './tests/setup.ts'
    ]
  },
  
  // Resolve configuration
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
      '@server': path.resolve(__dirname, './server'),
      '@src': path.resolve(__dirname, './src'),
      '@tests': path.resolve(__dirname, './tests'),
      '@types': path.resolve(__dirname, './types'),
      '@utils': path.resolve(__dirname, './utils'),
      '@config': path.resolve(__dirname, './config')
    }
  },
  
  // Define configuration for different environments
  define: {
    __TEST_ENV__: true
  },
  
  // ESM configuration
  esbuild: {
    target: 'node18',
    format: 'esm'
  }
});