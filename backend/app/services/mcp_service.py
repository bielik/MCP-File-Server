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
        )
    ]
    return tools
