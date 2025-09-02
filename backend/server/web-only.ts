#!/usr/bin/env node

import { config, validateConfiguration } from '../config/index.js';
import { WebServer } from './web-server.js';
import { logger, logWithContext } from '../utils/logger.js';
import { initializeFileSystem, cleanupFileSystem } from '../files/index.js';

class WebOnlyServer {
  private webServer: WebServer;

  constructor() {
    this.webServer = new WebServer();
  }

  async start(): Promise<void> {
    try {
      // Validate configuration before starting
      validateConfiguration();
      logWithContext.info('Configuration validated successfully');

      // Initialize file management system
      await initializeFileSystem();
      logWithContext.info('File management system initialized');

      // Start web server for frontend management
      await this.webServer.start();
      logWithContext.info('Web-only server started successfully', {
        webUIPort: config.server.webUIPort,
        url: `http://${config.server.host}:${config.server.webUIPort}`,
      });

      // Log configuration summary
      logWithContext.info('Server configuration', {
        contextFolders: config.filePermissions.contextFolders.length,
        workingFolders: config.filePermissions.workingFolders.length,
        outputFolder: !!config.filePermissions.outputFolder,
        enableCaching: config.server.enableCaching,
        logLevel: config.server.logLevel,
      });

      console.log(`✅ MCP Research File Server is running!`);
      console.log(`📊 Backend API: http://${config.server.host}:${config.server.webUIPort}`);
      console.log(`🎨 Frontend UI: http://${config.server.host}:3002`);
      console.log(`📝 Use the frontend to configure file permissions and monitor the MCP server`);

    } catch (error) {
      logWithContext.error('Failed to start web-only server', error as Error);
      process.exit(1);
    }
  }

  async stop(): Promise<void> {
    try {
      // Stop web server
      await this.webServer.stop();
      
      // Cleanup file management system
      await cleanupFileSystem();
      
      logWithContext.info('Web-only server stopped');
    } catch (error) {
      logWithContext.error('Error stopping web-only server', error as Error);
    }
  }
}

// Handle process termination gracefully
async function main(): Promise<void> {
  const server = new WebOnlyServer();

  // Handle shutdown signals
  const shutdown = async (signal: string) => {
    logWithContext.info(`Received ${signal}, shutting down gracefully`);
    await server.stop();
    process.exit(0);
  };

  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));

  // Handle uncaught exceptions
  process.on('uncaughtException', (error) => {
    logWithContext.error('Uncaught exception', error);
    process.exit(1);
  });

  process.on('unhandledRejection', (reason, promise) => {
    logWithContext.error('Unhandled rejection', new Error(String(reason)), {
      promise: promise.toString(),
    });
    process.exit(1);
  });

  // Start the server
  await server.start();
}

// Run the server if this file is executed directly
if (import.meta.url === `file://${process.argv[1]}` || import.meta.url.endsWith('web-only.ts')) {
  main().catch((error) => {
    console.error('Failed to start web-only server:', error);
    process.exit(1);
  });
}

export { WebOnlyServer };
export default WebOnlyServer;