from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal, Generic, TypeVar

# --- Generic JSON-RPC 2.0 Models ---

T = TypeVar('T')
U = TypeVar('U')

class JsonRpcError(BaseModel):
    code: int
    message: str
    data: Any | None = None

    @classmethod
    def parse_error(cls, data: Any | None = None) -> 'JsonRpcError':
        return cls(code=-32700, message="Parse error", data=data)

    @classmethod
    def invalid_request(cls, data: Any | None = None) -> 'JsonRpcError':
        return cls(code=-32600, message="Invalid Request", data=data)

    @classmethod
    def method_not_found(cls, data: Any | None = None) -> 'JsonRpcError':
        return cls(code=-32601, message="Method not found", data=data)

    @classmethod
    def invalid_params(cls, data: Any | None = None) -> 'JsonRpcError':
        return cls(code=-32602, message="Invalid params", data=data)

    @classmethod
    def internal_error(cls, data: Any | None = None) -> 'JsonRpcError':
        return cls(code=-32603, message="Internal error", data=data)

class JsonRpcRequest(BaseModel, Generic[T]):
    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: T | None = None
    id: int | str | None = None

class JsonRpcResponse(BaseModel, Generic[U]):
    jsonrpc: Literal["2.0"] = "2.0"
    result: U | None = None
    error: JsonRpcError | None = None
    id: int | str | None

# --- MCP Specific Models ---

class McpHelloParams(BaseModel):
    version: str
    capabilities: Dict[str, Any] = {}

class ToolParameter(BaseModel):
    name: str
    type: Literal["string", "number", "boolean", "object", "array"]
    description: str
    required: bool = True

class ToolDefinition(BaseModel):
    tool_name: str = Field(..., alias="toolName")
    description: str
    parameters: List[ToolParameter] = []

class ToolCallParams(BaseModel):
    tool_name: str = Field(..., alias="toolName")
    arguments: Dict[str, Any] = {}

class ToolResult(BaseModel):
    content: str | List[Dict[str, Any]] | Dict[str, Any]
