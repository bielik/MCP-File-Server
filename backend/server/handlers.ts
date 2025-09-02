import { CallToolRequest, CallToolResult, ErrorCode, McpError } from '@modelcontextprotocol/sdk/types.js';
import { z } from 'zod';
import {
  FileOperationResult,
  SearchToolResult,
  FileMetadata,
} from '../types/index.js';
import {
  readFileContent,
  writeFileContent,
  createFile,
  listFiles,
  getFileMetadata,
  getFolderStructure,
  getFileType,
} from '../utils/file-utils.js';
import { filePermissionMatrix } from '../config/index.js';
import { logMCPRequest, logMCPResponse, createPerformanceTimer } from '../utils/logger.js';

// Validation schemas for tool parameters
const readFileSchema = z.object({
  file_path: z.string().min(1),
});

const writeFileSchema = z.object({
  file_path: z.string().min(1),
  content: z.string(),
});

const createFileSchema = z.object({
  file_path: z.string().min(1),
  content: z.string(),
  create_subdirectories: z.boolean().optional().default(true),
});

const listFilesSchema = z.object({
  directory_path: z.string().optional().default(''),
  recursive: z.boolean().optional().default(false),
  file_types: z.array(z.string()).optional(),
  permissions: z.array(z.enum(['read-only', 'read-write', 'agent-controlled'])).optional(),
  categories: z.array(z.enum(['context', 'working', 'output', 'methodology', 'literature', 'budget', 'timeline', 'introduction', 'conclusion', 'other'])).optional(),
});

const getFileMetadataSchema = z.object({
  file_path: z.string().min(1),
});

const getFolderStructureSchema = z.object({
  base_path: z.string().optional(),
  max_depth: z.number().optional().default(3),
});

const searchTextSchema = z.object({
  query: z.string().min(1),
  file_categories: z.array(z.enum(['context', 'working', 'output', 'methodology', 'literature', 'budget', 'timeline', 'introduction', 'conclusion', 'other'])).optional(),
  file_types: z.array(z.string()).optional(),
  max_results: z.number().optional().default(20),
});

const searchSemanticSchema = z.object({
  query: z.string().min(1),
  file_categories: z.array(z.enum(['context', 'working', 'output', 'methodology', 'literature', 'budget', 'timeline', 'introduction', 'conclusion', 'other'])).optional(),
  similarity_threshold: z.number().min(0).max(1).optional().default(0.7),
  max_results: z.number().optional().default(10),
});

const searchMultimodalSchema = z.object({
  query: z.string().min(1),
  modalities: z.array(z.enum(['text', 'image'])).optional().default(['text', 'image']),
  file_categories: z.array(z.enum(['context', 'working', 'output', 'methodology', 'literature', 'budget', 'timeline', 'introduction', 'conclusion', 'other'])).optional(),
  max_results: z.number().optional().default(15),
});

// Helper function to handle errors consistently
function handleToolError(error: unknown, toolName: string): CallToolResult {
  const errorMessage = error instanceof Error ? error.message : String(error);
  
  return {
    content: [
      {
        type: 'text',
        text: `Error in ${toolName}: ${errorMessage}`,
      },
    ],
    isError: true,
  };
}

// File Management Handlers
export async function handleReadFile(request: CallToolRequest): Promise<CallToolResult> {
  const timer = createPerformanceTimer('read_file');
  logMCPRequest('read_file', request.params);
  
  try {
    const params = readFileSchema.parse(request.params);
    const content = await readFileContent(params.file_path);
    const metadata = await getFileMetadata(params.file_path);
    
    const duration = timer.end(true);
    logMCPResponse('read_file', true, duration);
    
    const result: FileOperationResult = {
      success: true,
      data: {
        content,
        metadata,
      },
    };
    
    return {
      content: [
        {
          type: 'text',
          text: content,
        },
      ],
    };
  } catch (error) {
    const duration = timer.end(false);
    logMCPResponse('read_file', false, duration, (error as Error).message);
    return handleToolError(error, 'read_file');
  }
}

export async function handleWriteFile(request: CallToolRequest): Promise<CallToolResult> {
  const timer = createPerformanceTimer('write_file');
  logMCPRequest('write_file', request.params);
  
  try {
    const params = writeFileSchema.parse(request.params);
    await writeFileContent(params.file_path, params.content);
    const metadata = await getFileMetadata(params.file_path);
    
    const duration = timer.end(true);
    logMCPResponse('write_file', true, duration);
    
    const result: FileOperationResult = {
      success: true,
      data: {
        metadata,
        modified: true,
      },
    };
    
    return {
      content: [
        {
          type: 'text',
          text: `Successfully wrote ${params.content.length} characters to ${params.file_path}`,
        },
      ],
    };
  } catch (error) {
    const duration = timer.end(false);
    logMCPResponse('write_file', false, duration, (error as Error).message);
    return handleToolError(error, 'write_file');
  }
}

export async function handleCreateFile(request: CallToolRequest): Promise<CallToolResult> {
  const timer = createPerformanceTimer('create_file');
  logMCPRequest('create_file', request.params);
  
  try {
    const params = createFileSchema.parse(request.params);
    await createFile(params.file_path, params.content, params.create_subdirectories);
    const metadata = await getFileMetadata(params.file_path);
    
    const duration = timer.end(true);
    logMCPResponse('create_file', true, duration);
    
    const result: FileOperationResult = {
      success: true,
      data: {
        metadata,
        created: true,
      },
    };
    
    return {
      content: [
        {
          type: 'text',
          text: `Successfully created file ${params.file_path} with ${params.content.length} characters`,
        },
      ],
    };
  } catch (error) {
    const duration = timer.end(false);
    logMCPResponse('create_file', false, duration, (error as Error).message);
    return handleToolError(error, 'create_file');
  }
}

export async function handleListFiles(request: CallToolRequest): Promise<CallToolResult> {
  const timer = createPerformanceTimer('list_files');
  logMCPRequest('list_files', request.params);
  
  try {
    const params = listFilesSchema.parse(request.params);
    
    // Determine directories to scan
    const directoriesToScan = params.directory_path 
      ? [params.directory_path]
      : [
          ...filePermissionMatrix.contextFolders,
          ...filePermissionMatrix.workingFolders,
          filePermissionMatrix.outputFolder,
        ].filter(Boolean);
    
    let allFiles: FileMetadata[] = [];
    
    // Scan each directory
    for (const directory of directoriesToScan) {
      try {
        const files = await listFiles(directory, params.recursive, (file) => {
          // Apply filters
          if (params.file_types && params.file_types.length > 0) {
            const fileExt = file.filename.substring(file.filename.lastIndexOf('.'));
            if (!params.file_types.includes(fileExt)) {
              return false;
            }
          }
          
          if (params.permissions && params.permissions.length > 0) {
            if (!params.permissions.includes(file.permissions)) {
              return false;
            }
          }
          
          if (params.categories && params.categories.length > 0) {
            if (!file.category || !params.categories.includes(file.category)) {
              return false;
            }
          }
          
          return true;
        });
        
        allFiles = allFiles.concat(files);
      } catch (error) {
        // Continue with other directories if one fails
        console.warn(`Failed to scan directory ${directory}:`, error);
      }
    }
    
    // Sort by modification date (newest first)
    allFiles.sort((a, b) => b.modified.getTime() - a.modified.getTime());
    
    const duration = timer.end(true);
    logMCPResponse('list_files', true, duration);
    
    // Format results for display
    const fileList = allFiles
      .map(file => {
        const sizeKB = (file.size / 1024).toFixed(1);
        const modifiedDate = file.modified.toLocaleDateString();
        const permissionSymbol = 
          file.permissions === 'read-only' ? '🔒' :
          file.permissions === 'read-write' ? '✏️' : 
          '🤖';
        
        return `${permissionSymbol} ${file.filename} (${sizeKB}KB, ${modifiedDate}) - ${file.category}`;
      })
      .join('\n');
    
    return {
      content: [
        {
          type: 'text',
          text: `Found ${allFiles.length} files:\n\n${fileList}`,
        },
      ],
    };
  } catch (error) {
    const duration = timer.end(false);
    logMCPResponse('list_files', false, duration, (error as Error).message);
    return handleToolError(error, 'list_files');
  }
}

export async function handleGetFileMetadata(request: CallToolRequest): Promise<CallToolResult> {
  const timer = createPerformanceTimer('get_file_metadata');
  logMCPRequest('get_file_metadata', request.params);
  
  try {
    const params = getFileMetadataSchema.parse(request.params);
    const metadata = await getFileMetadata(params.file_path);
    
    const duration = timer.end(true);
    logMCPResponse('get_file_metadata', true, duration);
    
    const sizeKB = (metadata.size / 1024).toFixed(1);
    const metadataText = [
      `File: ${metadata.filename}`,
      `Path: ${metadata.path}`,
      `Size: ${sizeKB} KB`,
      `Type: ${metadata.type}`,
      `Category: ${metadata.category}`,
      `Permissions: ${metadata.permissions}`,
      `Created: ${metadata.created.toLocaleString()}`,
      `Modified: ${metadata.modified.toLocaleString()}`,
    ].join('\n');
    
    return {
      content: [
        {
          type: 'text',
          text: metadataText,
        },
      ],
    };
  } catch (error) {
    const duration = timer.end(false);
    logMCPResponse('get_file_metadata', false, duration, (error as Error).message);
    return handleToolError(error, 'get_file_metadata');
  }
}

export async function handleGetFolderStructure(request: CallToolRequest): Promise<CallToolResult> {
  const timer = createPerformanceTimer('get_folder_structure');
  logMCPRequest('get_folder_structure', request.params);
  
  try {
    const params = getFolderStructureSchema.parse(request.params);
    const basePath = params.base_path || filePermissionMatrix.outputFolder;
    
    const structure = await getFolderStructure(basePath);
    
    // Format structure as text tree
    function formatTree(node: any, indent = ''): string {
      const icon = node.type === 'directory' ? '📁' : '📄';
      let result = `${indent}${icon} ${node.name}\n`;
      
      if (node.children) {
        for (const child of node.children) {
          result += formatTree(child, indent + '  ');
        }
      }
      
      return result;
    }
    
    const duration = timer.end(true);
    logMCPResponse('get_folder_structure', true, duration);
    
    return {
      content: [
        {
          type: 'text',
          text: `Folder structure for ${basePath}:\n\n${formatTree(structure)}`,
        },
      ],
    };
  } catch (error) {
    const duration = timer.end(false);
    logMCPResponse('get_folder_structure', false, duration, (error as Error).message);
    return handleToolError(error, 'get_folder_structure');
  }
}

// Search Handlers (placeholder implementations)
export async function handleSearchText(request: CallToolRequest): Promise<CallToolResult> {
  const timer = createPerformanceTimer('search_text');
  logMCPRequest('search_text', request.params);
  
  try {
    const params = searchTextSchema.parse(request.params);
    
    // TODO: Implement FlexSearch integration
    const duration = timer.end(true);
    logMCPResponse('search_text', true, duration);
    
    return {
      content: [
        {
          type: 'text',
          text: `Text search for "${params.query}" is not yet implemented. This will use FlexSearch for fast keyword matching.`,
        },
      ],
    };
  } catch (error) {
    const duration = timer.end(false);
    logMCPResponse('search_text', false, duration, (error as Error).message);
    return handleToolError(error, 'search_text');
  }
}

export async function handleSearchSemantic(request: CallToolRequest): Promise<CallToolResult> {
  const timer = createPerformanceTimer('search_semantic');
  logMCPRequest('search_semantic', request.params);
  
  try {
    const params = searchSemanticSchema.parse(request.params);
    
    // TODO: Implement M-CLIP semantic search
    const duration = timer.end(true);
    logMCPResponse('search_semantic', true, duration);
    
    return {
      content: [
        {
          type: 'text',
          text: `Semantic search for "${params.query}" is not yet implemented. This will use M-CLIP embeddings for conceptual matching.`,
        },
      ],
    };
  } catch (error) {
    const duration = timer.end(false);
    logMCPResponse('search_semantic', false, duration, (error as Error).message);
    return handleToolError(error, 'search_semantic');
  }
}

export async function handleSearchMultimodal(request: CallToolRequest): Promise<CallToolResult> {
  const timer = createPerformanceTimer('search_multimodal');
  logMCPRequest('search_multimodal', request.params);
  
  try {
    const params = searchMultimodalSchema.parse(request.params);
    
    // TODO: Implement M-CLIP multimodal search
    const duration = timer.end(true);
    logMCPResponse('search_multimodal', true, duration);
    
    return {
      content: [
        {
          type: 'text',
          text: `Multimodal search for "${params.query}" is not yet implemented. This will search across both text and images using M-CLIP.`,
        },
      ],
    };
  } catch (error) {
    const duration = timer.end(false);
    logMCPResponse('search_multimodal', false, duration, (error as Error).message);
    return handleToolError(error, 'search_multimodal');
  }
}

// Tool handler registry
export const toolHandlers = {
  read_file: handleReadFile,
  write_file: handleWriteFile,
  create_file: handleCreateFile,
  list_files: handleListFiles,
  get_file_metadata: handleGetFileMetadata,
  get_folder_structure: handleGetFolderStructure,
  search_text: handleSearchText,
  search_semantic: handleSearchSemantic,
  search_multimodal: handleSearchMultimodal,
};

export default toolHandlers;