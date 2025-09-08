#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { config, validateConfiguration } from '../config/index.js';
import { allTools } from './tools.js';
import { toolHandlers, initializeSearchServices } from './handlers.js';
import { logger, logWithContext } from '../utils/logger.js';
import { initializeFileSystem, cleanupFileSystem } from '../files/index.js';
import { WebServer } from './web-server.js';

class MCPResearchFileServer {
  private server: Server;
  private webServer: WebServer;

  constructor() {
    this.server = new Server(
      {
        name: 'mcp-research-file-server',
        version: '1.0.0',
        description: 'Multimodal MCP File Server for Research Proposal Development',
      },
      {
        capabilities: {
          tools: {},
          logging: {},
        },
      }
    );

    this.webServer = new WebServer();
    this.setupHandlers();
  }

  private setupHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      logWithContext.debug('Listing available tools', { toolCount: allTools.length });
      
      return {
        tools: allTools,
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name } = request.params;
      
      logWithContext.info('Tool called', { toolName: name });

      // Check if handler exists
      if (!(name in toolHandlers)) {
        const errorMessage = `Unknown tool: ${name}`;
        logWithContext.error(errorMessage, undefined, { availableTools: Object.keys(toolHandlers) });
        
        throw new Error(errorMessage);
      }

      // Call the appropriate handler
      try {
        const handler = toolHandlers[name as keyof typeof toolHandlers];
        const result = await handler(request);
        
        logWithContext.debug('Tool executed successfully', { toolName: name });
        return result;
      } catch (error) {
        logWithContext.error('Tool execution failed', error as Error, { 
          toolName: name,
          params: request.params,
        });
        
        // Re-throw to let MCP SDK handle the error response
        throw error;
      }
    });

    // Handle server notifications and errors
    this.server.onerror = (error) => {
      logWithContext.error('MCP Server error', error);
    };
  }

  async start(): Promise<void> {
    try {
      // Validate configuration before starting
      validateConfiguration();
      logWithContext.info('Configuration validated successfully');

      // Initialize file management system
      await initializeFileSystem();
      logWithContext.info('File management system initialized');

      // Initialize search services for Phase 3 Step 1
      try {
        await initializeSearchServices();
        logWithContext.info('Search services initialized successfully');
      } catch (error) {
        logWithContext.warn('Failed to initialize search services - search functionality will be limited', error as Error);
        // Continue startup - search services are optional for basic file operations
      }

      // Start web server for frontend management
      await this.webServer.start();
      logWithContext.info('Web server started for frontend management');

      // Create transport
      const transport = new StdioServerTransport();
      
      // Connect server to transport
      await this.server.connect(transport);
      
      logWithContext.info('MCP Research File Server started', {
        serverName: 'mcp-research-file-server',
        version: '1.0.0',
        toolCount: allTools.length,
        nodeVersion: process.version,
        platform: process.platform,
      });

      // Log configuration summary (without sensitive data)
      logWithContext.info('Server configuration', {
        contextFolders: config.filePermissions.contextFolders.length,
        workingFolders: config.filePermissions.workingFolders.length,
        outputFolder: !!config.filePermissions.outputFolder,
        enableCaching: config.server.enableCaching,
        logLevel: config.server.logLevel,
        supportedLanguages: config.processing.supportedLanguages,
      });

      // Log available tools
      const toolsByCategory = {
        fileManagement: allTools.filter(t => t.name.startsWith('read_') || t.name.startsWith('write_') || t.name.startsWith('create_') || t.name.startsWith('list_') || t.name.startsWith('get_')),
        search: allTools.filter(t => t.name.startsWith('search_')),
      };

      logWithContext.info('Available tools registered', {
        fileManagementTools: toolsByCategory.fileManagement.length,
        searchTools: toolsByCategory.search.length,
        totalTools: allTools.length,
      });

    } catch (error) {
      logWithContext.error('Failed to start MCP server', error as Error);
      process.exit(1);
    }
  }

  async stop(): Promise<void> {
    try {
      // Stop web server first
      await this.webServer.stop();
      
      // Cleanup file management system
      await cleanupFileSystem();
      
      // Close MCP server
      await this.server.close();
      logWithContext.info('MCP Research File Server stopped');
    } catch (error) {
      logWithContext.error('Error stopping MCP server', error as Error);
    }
  }
}

// Handle process termination gracefully
async function main(): Promise<void> {
  const server = new MCPResearchFileServer();

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
if (import.meta.url === `file://${process.argv[1]}`) {
  main().catch((error) => {
    console.error('Failed to start server:', error);
    process.exit(1);
  });
}

export { MCPResearchFileServer };
export default MCPResearchFileServer;