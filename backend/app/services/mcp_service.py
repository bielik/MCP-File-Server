from typing import List
from app.schemas import mcp as mcp_schemas

def get_tools() -> List[mcp_schemas.ToolDefinition]:
    """Returns the list of available tools for the MCP client."""
    
    tools = [
        mcp_schemas.ToolDefinition(
            toolName="read_file",
            description="Reads the entire content of a specified file.",
            parameters=[
                mcp_schemas.ToolParameter(name="path", type="string", description="The relative path to the file from the shared directory root.")
            ]
        ),
        mcp_schemas.ToolDefinition(
            toolName="list_files",
            description="Lists all files and subdirectories in a specified directory.",
            parameters=[
                mcp_schemas.ToolParameter(name="path", type="string", description="The relative path to the directory from the shared directory root.")
            ]
        ),
        mcp_schemas.ToolDefinition(
            toolName="write_file",
            description="Writes content to a specified file, overwriting it if it exists or creating it if it does not.",
            parameters=[
                mcp_schemas.ToolParameter(name="path", type="string", description="The relative path to the file to be written."),
                mcp_schemas.ToolParameter(name="content", type="string", description="The content to write into the file.")
            ]
        )
    ]
    return tools
