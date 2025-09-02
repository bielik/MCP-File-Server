import winston from 'winston';
import path from 'path';
import { serverConfig, getAbsolutePath } from '../config/index.js';

// Custom log format
const logFormat = winston.format.combine(
  winston.format.timestamp({
    format: 'YYYY-MM-DD HH:mm:ss.SSS',
  }),
  winston.format.errors({ stack: true }),
  winston.format.printf(({ level, message, timestamp, stack, ...meta }) => {
    let logMessage = `${timestamp} [${level.toUpperCase()}]: ${message}`;
    
    // Add metadata if present
    if (Object.keys(meta).length > 0) {
      logMessage += ` ${JSON.stringify(meta)}`;
    }
    
    // Add stack trace for errors
    if (stack) {
      logMessage += `\n${stack}`;
    }
    
    return logMessage;
  })
);

// Console format for development
const consoleFormat = winston.format.combine(
  winston.format.colorize(),
  winston.format.timestamp({
    format: 'HH:mm:ss',
  }),
  winston.format.printf(({ level, message, timestamp, ...meta }) => {
    let logMessage = `${timestamp} ${level}: ${message}`;
    
    // Add metadata if present (except for common fields)
    const filteredMeta = { ...meta };
    delete filteredMeta.timestamp;
    delete filteredMeta.level;
    delete filteredMeta.message;
    
    if (Object.keys(filteredMeta).length > 0) {
      logMessage += ` ${JSON.stringify(filteredMeta)}`;
    }
    
    return logMessage;
  })
);

// Create logger instance
const logger = winston.createLogger({
  level: serverConfig.logLevel,
  format: logFormat,
  defaultMeta: {
    service: 'mcp-research-server',
  },
  transports: [
    // File transport
    new winston.transports.File({
      filename: getAbsolutePath(serverConfig.logFile),
      maxsize: 10 * 1024 * 1024, // 10MB
      maxFiles: 5,
      tailable: true,
    }),
    // Error-only file
    new winston.transports.File({
      filename: getAbsolutePath(path.dirname(serverConfig.logFile) + '/error.log'),
      level: 'error',
      maxsize: 10 * 1024 * 1024,
      maxFiles: 3,
    }),
  ],
});

// Add console transport for development
if (process.env.NODE_ENV !== 'production') {
  logger.add(
    new winston.transports.Console({
      format: consoleFormat,
    })
  );
}

// Utility functions for structured logging
export const logWithContext = {
  info: (message: string, context?: Record<string, unknown>) => {
    logger.info(message, context);
  },
  
  warn: (message: string, context?: Record<string, unknown>) => {
    logger.warn(message, context);
  },
  
  error: (message: string, error?: Error, context?: Record<string, unknown>) => {
    logger.error(message, { 
      ...context,
      error: error ? {
        name: error.name,
        message: error.message,
        stack: error.stack,
      } : undefined,
    });
  },
  
  debug: (message: string, context?: Record<string, unknown>) => {
    logger.debug(message, context);
  },
};

// Request/response logging helpers
export const logMCPRequest = (tool: string, params: unknown): void => {
  logWithContext.info('MCP tool request', {
    tool,
    params: typeof params === 'object' ? params : { value: params },
  });
};

export const logMCPResponse = (tool: string, success: boolean, duration: number, error?: string): void => {
  if (success) {
    logWithContext.info('MCP tool response', { tool, duration_ms: duration });
  } else {
    logWithContext.error('MCP tool error', undefined, { tool, duration_ms: duration, error });
  }
};

export const logFileOperation = (
  operation: string, 
  filePath: string, 
  success: boolean, 
  userId?: string,
  error?: string
): void => {
  const context = {
    operation,
    filePath,
    userId,
    success,
    error,
  };
  
  if (success) {
    logWithContext.info('File operation completed', context);
  } else {
    logWithContext.warn('File operation failed', context);
  }
};

export const logSearchQuery = (
  query: string,
  strategy: 'keyword' | 'semantic' | 'multimodal',
  resultCount: number,
  duration: number
): void => {
  logWithContext.info('Search query executed', {
    query: query.length > 100 ? query.substring(0, 100) + '...' : query,
    strategy,
    resultCount,
    duration_ms: duration,
  });
};

// Performance monitoring
export const createPerformanceTimer = (operation: string) => {
  const start = Date.now();
  
  return {
    end: (success: boolean = true, context?: Record<string, unknown>) => {
      const duration = Date.now() - start;
      logWithContext.info(`Operation completed: ${operation}`, {
        ...context,
        duration_ms: duration,
        success,
      });
      return duration;
    },
  };
};

// Health check logging
export const logHealthCheck = (component: string, healthy: boolean, details?: Record<string, unknown>): void => {
  const level = healthy ? 'info' : 'error';
  logger[level](`Health check: ${component}`, {
    healthy,
    ...details,
  });
};

// Export the main logger for direct use
export { logger };
export default logger;