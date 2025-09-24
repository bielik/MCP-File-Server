from typing import List
from app.schemas import mcp as mcp_schemas

def get_tools() -> List[mcp_schemas.ToolDefinition]:
    """Returns the list of available tools for the MCP client."""
    
    tools = [
        mcp_schemas.ToolDefinition(
            name="read_file",
            description="Reads the entire content of a specified file.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the file from the shared directory root."
                    }
                },
                "required": ["path"]
            }
        ),
        mcp_schemas.ToolDefinition(
            name="list_files",
            description="Lists all files and subdirectories in a specified directory.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the directory from the shared directory root."
                    }
                },
                "required": ["path"]
            }
        ),
        mcp_schemas.ToolDefinition(
            name="write_file",
            description="Writes content to a specified file, overwriting it if it exists or creating it if it does not.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the file to be written."
                    },
                    "content": {
                        "type": "string",
                        "description": "The content to write into the file."
                    }
                },
                "required": ["path", "content"]
            }
        ),

        # Phase 4A Search Tools
        mcp_schemas.ToolDefinition(
            name="list_all_files",
            description="Lists all discoverable files and directories within the workspace scope, with optional depth control and pagination.",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of files to return (default: 1000, max: 5000)",
                        "default": 1000,
                        "minimum": 1,
                        "maximum": 5000
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of files to skip for pagination (default: 0, used when cursor is not provided)",
                        "default": 0,
                        "minimum": 0
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Base64-encoded cursor for efficient pagination (preferred over offset)"
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Maximum directory depth to traverse (optional)",
                        "minimum": 1
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Field to sort by: 'path', 'size', 'mtime', or 'discovered'",
                        "enum": ["path", "size", "mtime", "discovered"],
                        "default": "path"
                    }
                },
                "required": []
            }
        ),

        mcp_schemas.ToolDefinition(
            name="search_files_by_metadata",
            description="Searches for files based on metadata properties like filename patterns, file types, size, and modification date.",
            input_schema={
                "type": "object",
                "properties": {
                    "filename_pattern": {
                        "type": "string",
                        "description": "Pattern to match against filenames (supports * and ? wildcards)"
                    },
                    "file_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of file extensions to include (e.g., ['.txt', '.pdf', '.md'])"
                    },
                    "size_min": {
                        "type": "integer",
                        "description": "Minimum file size in bytes",
                        "minimum": 0
                    },
                    "size_max": {
                        "type": "integer",
                        "description": "Maximum file size in bytes",
                        "minimum": 0
                    },
                    "mtime_after": {
                        "type": "integer",
                        "description": "Files modified after this Unix timestamp"
                    },
                    "mtime_before": {
                        "type": "integer",
                        "description": "Files modified before this Unix timestamp"
                    },
                    "indexed_only": {
                        "type": "boolean",
                        "description": "If true, only return files that have been indexed",
                        "default": False
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 100, max: 1000)",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 1000
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Number of results to skip for pagination (default: 0)",
                        "default": 0,
                        "minimum": 0
                    }
                },
                "required": []
            }
        ),

        mcp_schemas.ToolDefinition(
            name="get_file_info",
            description="Get detailed information about a specific file by its document ID.",
            input_schema={
                "type": "object",
                "properties": {
                    "doc_id": {
                        "type": "string",
                        "description": "Document ID of the file to get information about"
                    }
                },
                "required": ["doc_id"]
            }
        ),

        mcp_schemas.ToolDefinition(
            name="get_search_statistics",
            description="Get comprehensive statistics about the indexed files and search capabilities.",
            input_schema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),

        mcp_schemas.ToolDefinition(
            name="search_fulltext",
            description="Perform full-text search across indexed document content using FTS5.",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string. Supports phrase search with quotes, boolean operators (AND, OR, NOT), and wildcards (*)."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10, max: 100)",
                        "minimum": 1,
                        "maximum": 100,
                        "default": 10
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Cursor for pagination to get next set of results"
                    },
                    "highlight": {
                        "type": "boolean",
                        "description": "Whether to include highlighted text snippets (default: true)",
                        "default": True
                    },
                    "highlight_start": {
                        "type": "string",
                        "description": "Start marker for highlighted text (default: '<mark>')",
                        "default": "<mark>"
                    },
                    "highlight_end": {
                        "type": "string",
                        "description": "End marker for highlighted text (default: '</mark>')",
                        "default": "</mark>"
                    },
                    "file_types": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of file extensions to filter by (e.g., ['.txt', '.md', '.py'])"
                    },
                    "date_from": {
                        "type": "integer",
                        "description": "Optional start timestamp for date filtering (Unix epoch)"
                    },
                    "date_to": {
                        "type": "integer",
                        "description": "Optional end timestamp for date filtering (Unix epoch)"
                    }
                },
                "required": ["query"]
            }
        )
    ]
    return tools
