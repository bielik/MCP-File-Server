#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { config, validateConfiguration } from '../config/index.js';
import { allTools } from '../server/tools.js';
import { toolHandlers, initializeSearchServices } from '../server/handlers.js';
import { logger, logWithContext } from '../utils/logger.js';
import { initializeFileSystem, cleanupFileSystem } from '../files/index.js';
import { WebServer } from '../server/web-server.js';

/**
 * Unified MCP Research File Server
 * 
 * This is the single entry point for the entire application, managing both:
 * - MCP Server: Handles Model Context Protocol communication with AI agents
 * - Web Server: Provides REST API and serves frontend UI
 * 
 * Architecture: Integrated Monolithic Approach
 * - Single process manages all functionality
 * - Shared configuration and state
 * - Unified error handling and logging
 */
class MCPResearchFileServer {
  private server: Server;
  private webServer: WebServer;

  constructor() {
    logWithContext.info('Initializing MCP Research File Server');
    
    // Initialize MCP Server
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

    // Initialize Web Server
    this.webServer = new WebServer();
    
    this.setupMCPHandlers();
  }

  /**
   * Setup MCP Server request handlers
   */
  private setupMCPHandlers(): void {
    // List available tools
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      logWithContext.debug('MCP: Listing available tools', { toolCount: allTools.length });
      
      return {
        tools: allTools,
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name } = request.params;
      const startTime = Date.now();
      
      logWithContext.info('MCP: Tool called', { toolName: name });

      // Check if handler exists
      if (!(name in toolHandlers)) {
        const errorMessage = `Unknown tool: ${name}`;
        logWithContext.error('MCP: Unknown tool requested', new Error(errorMessage), { 
          toolName: name,
          availableTools: Object.keys(toolHandlers) 
        });
        
        throw new Error(errorMessage);
      }

      // Call the appropriate handler
      try {
        const handler = toolHandlers[name as keyof typeof toolHandlers];
        const result = await handler(request);
        
        const duration = Date.now() - startTime;
        logWithContext.debug('MCP: Tool executed successfully', { 
          toolName: name,
          duration: `${duration}ms`
        });
        
        return result;
      } catch (error) {
        const duration = Date.now() - startTime;
        logWithContext.error('MCP: Tool execution failed', error as Error, { 
          toolName: name,
          duration: `${duration}ms`,
          params: request.params,
        });
        
        // Re-throw to let MCP SDK handle the error response
        throw error;
      }
    });

    // Handle server notifications and errors
    this.server.onerror = (error) => {
      logWithContext.error('MCP: Server error', error);
    };
  }

  /**
   * Start the unified server (both MCP and Web)
   */
  async start(): Promise<void> {
    try {
      logWithContext.info('Starting MCP Research File Server...');
      
      // Step 1: Validate configuration
      validateConfiguration();
      logWithContext.info('✓ Configuration validated');

      // Step 2: Initialize file management system
      await initializeFileSystem();
      logWithContext.info('✓ File management system initialized');

      // Step 3: Initialize search services (optional for Phase 1)
      try {
        await initializeSearchServices();
        logWithContext.info('✓ Search services initialized');
      } catch (error) {
        logWithContext.warn('⚠ Search services initialization failed - continuing with basic file operations', error as Error);
        // Continue startup - search services are optional for Phase 1
      }

      // Step 4: Start Web Server for UI and API
      await this.webServer.start();
      logWithContext.info('✓ Web server started', { port: config.server.webUIPort });

      // Step 5: Start MCP Server for agent communication
      const transport = new StdioServerTransport();
      await this.server.connect(transport);
      
      logWithContext.info('✅ MCP Research File Server fully started', {
        serverName: 'mcp-research-file-server',
        version: '1.0.0',
        mcpPort: config.server.mcpPort,
        webPort: config.server.webUIPort,
        toolCount: allTools.length,
        nodeVersion: process.version,
        platform: process.platform,
      });

      // Log configuration summary (without sensitive data)
      logWithContext.info('Server configuration summary', {
        contextFolders: config.filePermissions.contextFolders.length,
        workingFolders: config.filePermissions.workingFolders.length,
        outputFolder: !!config.filePermissions.outputFolder,
        enableCaching: config.server.enableCaching,
        logLevel: config.server.logLevel,
        supportedLanguages: config.processing.supportedLanguages,
      });

      // Log available tools by category
      const toolsByCategory = {
        fileManagement: allTools.filter(t => 
          t.name.startsWith('read_') || 
          t.name.startsWith('write_') || 
          t.name.startsWith('create_') || 
          t.name.startsWith('list_') || 
          t.name.startsWith('get_')
        ),
        search: allTools.filter(t => t.name.startsWith('search_')),
      };

      logWithContext.info('Available MCP tools', {
        fileManagementTools: toolsByCategory.fileManagement.map(t => t.name),
        searchTools: toolsByCategory.search.map(t => t.name),
        totalTools: allTools.length,
      });

    } catch (error) {
      logWithContext.error('❌ Failed to start MCP server', error as Error);
      process.exit(1);
    }
  }

  /**
   * Gracefully stop the unified server
   */
  async stop(): Promise<void> {
    try {
      logWithContext.info('Stopping MCP Research File Server...');
      
      // Stop web server first
      await this.webServer.stop();
      logWithContext.info('✓ Web server stopped');
      
      // Cleanup file management system
      await cleanupFileSystem();
      logWithContext.info('✓ File system cleanup completed');
      
      // Close MCP server
      await this.server.close();
      logWithContext.info('✅ MCP Research File Server stopped gracefully');
      
    } catch (error) {
      logWithContext.error('❌ Error stopping MCP server', error as Error);
    }
  }
}

/**
 * Main application entry point with proper error handling
 */
async function main(): Promise<void> {
  const server = new MCPResearchFileServer();

  // Handle shutdown signals gracefully
  const shutdown = async (signal: string) => {
    logWithContext.info(`Received ${signal}, shutting down gracefully...`);
    await server.stop();
    process.exit(0);
  };

  process.on('SIGINT', () => shutdown('SIGINT'));
  process.on('SIGTERM', () => shutdown('SIGTERM'));

  // Handle uncaught exceptions
  process.on('uncaughtException', (error) => {
    logWithContext.error('❌ Uncaught exception', error);
    process.exit(1);
  });

  process.on('unhandledRejection', (reason, promise) => {
    logWithContext.error('❌ Unhandled rejection', new Error(String(reason)), {
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
    console.error('💥 Fatal error starting server:', error);
    process.exit(1);
  });
}

export { MCPResearchFileServer };
export default MCPResearchFileServer;