import { Tool } from '@modelcontextprotocol/sdk/types.js';

// File Management Tools
export const fileManagementTools: Tool[] = [
  {
    name: 'read_file',
    description: 'Read the content of a file from context or working directories. Supports text files including markdown, plain text, and other text-based formats.',
    inputSchema: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: 'Path to the file to read (relative or absolute)',
        },
      },
      required: ['file_path'],
    },
  },
  {
    name: 'write_file',
    description: 'Write content to a file in working directories. Creates the file if it doesn\'t exist, overwrites if it does. Cannot write to read-only context directories.',
    inputSchema: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: 'Path to the file to write (relative or absolute)',
        },
        content: {
          type: 'string',
          description: 'Content to write to the file',
        },
      },
      required: ['file_path', 'content'],
    },
  },
  {
    name: 'create_file',
    description: 'Create a new file in the output directory or its subfolders. Perfect for generating new research documents, notes, or organized content. Can create subdirectories as needed.',
    inputSchema: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: 'Path for the new file (relative to output directory or absolute)',
        },
        content: {
          type: 'string',
          description: 'Initial content for the new file',
        },
        create_subdirectories: {
          type: 'boolean',
          description: 'Whether to create subdirectories if they don\'t exist (default: true)',
          default: true,
        },
      },
      required: ['file_path', 'content'],
    },
  },
  {
    name: 'list_files',
    description: 'List files in a directory with filtering options. Useful for browsing available files and understanding the file structure.',
    inputSchema: {
      type: 'object',
      properties: {
        directory_path: {
          type: 'string',
          description: 'Directory path to list (defaults to all accessible directories)',
          default: '',
        },
        recursive: {
          type: 'boolean',
          description: 'Whether to list files recursively in subdirectories',
          default: false,
        },
        file_types: {
          type: 'array',
          items: { type: 'string' },
          description: 'Filter by file extensions (e.g., [".md", ".txt", ".pdf"])',
        },
        permissions: {
          type: 'array',
          items: { 
            type: 'string',
            enum: ['read-only', 'read-write', 'agent-controlled']
          },
          description: 'Filter by permission types',
        },
        categories: {
          type: 'array',
          items: {
            type: 'string',
            enum: ['context', 'working', 'output', 'methodology', 'literature', 'budget', 'timeline', 'introduction', 'conclusion', 'other']
          },
          description: 'Filter by document categories',
        },
      },
      required: [],
    },
  },
  {
    name: 'get_file_metadata',
    description: 'Get detailed metadata about a file including size, dates, permissions, and categorization. Useful for understanding file properties before reading or processing.',
    inputSchema: {
      type: 'object',
      properties: {
        file_path: {
          type: 'string',
          description: 'Path to the file to analyze',
        },
      },
      required: ['file_path'],
    },
  },
  {
    name: 'get_folder_structure',
    description: 'Get the hierarchical structure of a directory, showing folders and files in a tree format. Essential for understanding how to organize new files and navigate the file system.',
    inputSchema: {
      type: 'object',
      properties: {
        base_path: {
          type: 'string',
          description: 'Base directory path to analyze (defaults to output directory for file organization)',
        },
        max_depth: {
          type: 'number',
          description: 'Maximum depth to traverse (default: 3)',
          default: 3,
        },
      },
      required: [],
    },
  },
];

// Search Tools (to be implemented in later phases)
export const searchTools: Tool[] = [
  {
    name: 'search_text',
    description: 'Fast keyword and phrase search across all accessible documents. Best for finding specific terms, file names, exact quotes, or known terminology. Supports multilingual queries.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query - can be keywords, phrases, or exact terms',
        },
        file_categories: {
          type: 'array',
          items: {
            type: 'string',
            enum: ['context', 'working', 'output', 'methodology', 'literature', 'budget', 'timeline', 'introduction', 'conclusion', 'other']
          },
          description: 'Limit search to specific file categories',
        },
        file_types: {
          type: 'array',
          items: { type: 'string' },
          description: 'Limit search to specific file types (e.g., [".md", ".txt"])',
        },
        max_results: {
          type: 'number',
          description: 'Maximum number of results to return (default: 20)',
          default: 20,
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'search_semantic',
    description: 'Semantic search using AI embeddings to find conceptually related content. Perfect for "how-to" questions, finding similar approaches, or discovering related ideas even when exact terms don\'t match.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Conceptual query or question - describe what you\'re looking for',
        },
        file_categories: {
          type: 'array',
          items: {
            type: 'string',
            enum: ['context', 'working', 'output', 'methodology', 'literature', 'budget', 'timeline', 'introduction', 'conclusion', 'other']
          },
          description: 'Limit search to specific file categories',
        },
        similarity_threshold: {
          type: 'number',
          description: 'Minimum similarity score (0.0-1.0, default: 0.7)',
          default: 0.7,
          minimum: 0.0,
          maximum: 1.0,
        },
        max_results: {
          type: 'number',
          description: 'Maximum number of results to return (default: 10)',
          default: 10,
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'search_multimodal',
    description: 'Search across both text and images using multimodal AI. Find relevant images with text queries, or find text sections related to visual content. Excellent for discovering diagrams, charts, and figures without captions.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Query that can match both text and image content',
        },
        modalities: {
          type: 'array',
          items: {
            type: 'string',
            enum: ['text', 'image']
          },
          description: 'Which content types to search (default: both)',
          default: ['text', 'image'],
        },
        file_categories: {
          type: 'array',
          items: {
            type: 'string',
            enum: ['context', 'working', 'output', 'methodology', 'literature', 'budget', 'timeline', 'introduction', 'conclusion', 'other']
          },
          description: 'Limit search to specific file categories',
        },
        max_results: {
          type: 'number',
          description: 'Maximum number of results to return (default: 15)',
          default: 15,
        },
      },
      required: ['query'],
    },
  },
];

// Combined tool definitions
export const allTools: Tool[] = [
  ...fileManagementTools,
  ...searchTools,
];

export default allTools;