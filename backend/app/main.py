import os
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.database import create_db_and_tables, initialize_database
from app.api.endpoints import router as api_router
from app.api.indexer import router as indexer_router
from app.api.reindex import router as reindex_router
from app.api.websockets import ConnectionManager

# Import MCP services and schemas
from app.services import mcp_service, file_service, search_tools
from app.schemas import mcp as mcp_schemas

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - Initialize database with Phase 4A bootstrap
    initialize_database()

    # Reset any pre-created permission service singleton to ensure it uses the initialized database
    from app.services.database_permission_service import reset_database_permission_service
    reset_database_permission_service()

    yield
    # Shutdown
    pass

app = FastAPI(title="MCP KnowledgeExplorer Hub", lifespan=lifespan)

# Custom exception handler for structured error responses
from app.api.endpoints import StructuredHTTPException

@app.exception_handler(StructuredHTTPException)
async def structured_exception_handler(request: Request, exc: StructuredHTTPException):
    content = {"code": exc.error_code, "message": exc.message}
    if exc.details:
        content["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=content)

# Configure CORS
origins = [
    f"http://localhost",
    f"http://localhost:{os.getenv('FRONTEND_PORT', 5173)}",
    f"http://127.0.0.1:{os.getenv('FRONTEND_PORT', 5173)}",
    "http://localhost:5175",  # Additional port for development
    "http://127.0.0.1:5175",  # Additional port for development
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized connection managers
ui_manager = ConnectionManager()
mcp_manager = ConnectionManager()

# Map tool names to their implementation
tool_map = {
    "read_file": file_service.read_file,
    "list_files": file_service.list_files,
    "write_file": file_service.write_file,
    # Phase 4A Search Tools
    "list_all_files": search_tools.list_all_files,
    "search_files_by_metadata": search_tools.search_files_by_metadata,
    "get_file_info": search_tools.get_file_info,
    "get_search_statistics": search_tools.get_search_statistics,
    # Phase 4B Search Tools
    "search_fulltext": search_tools.search_fulltext,
}

app.include_router(api_router, prefix="/api")
app.include_router(indexer_router)
app.include_router(reindex_router)

@app.get("/")
def read_root():
    return {"message": "MCP KnowledgeExplorer Hub is running."}

@app.get("/live")
def liveness_probe():
    """Liveness probe for health checks."""
    return {"status": "ok", "service": "backend"}

@app.get("/ready")
def readiness_probe():
    """Readiness probe for health checks."""
    try:
        # Test database connectivity
        from app.database import get_db
        with next(get_db()) as session:
            session.execute("SELECT 1").fetchone()

        return {"status": "ready", "service": "backend", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service not ready: {e}")

async def process_mcp_request(request_data: dict) -> dict:
    """Process an MCP JSON-RPC request and return the response."""
    request_id = request_data.get("id")
    
    try:
        # Basic JSON-RPC validation
        if not all(k in request_data for k in ["jsonrpc", "method"]):
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32600, "message": "Invalid Request"}}
        if request_data["jsonrpc"] != "2.0":
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32600, "message": "Invalid Request"}}

        method = request_data["method"]
        params = request_data.get("params", {})

        # Log activity to UI
        await ui_manager.broadcast(f"MCP Request: {method} | Params: {json.dumps(params)}")

        # --- MCP Method Router ---
        if method == "initialize":
            # MCP initialization handshake
            init_result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {
                        "listChanged": True
                    },
                    "resources": {},
                    "prompts": {},
                    "logging": {}
                },
                "serverInfo": {
                    "name": "MCP KnowledgeExplorer Hub",
                    "version": "1.0.0"
                }
            }
            return {"jsonrpc": "2.0", "id": request_id, "result": init_result}

        elif method == "initialized":
            # Client confirms initialization complete - no response needed
            await ui_manager.broadcast("MCP Client initialized successfully.")
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}

        elif method == "tools/list":
            tools = mcp_service.get_tools()
            # Convert ToolDefinition objects to dictionaries with proper field names
            tools_dict = [tool.model_dump(by_alias=True) for tool in tools]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools_dict}}

        elif method == "tools/call":
            tool_call = mcp_schemas.ToolCallParams(**params)
            tool_name = tool_call.name
            
            if tool_name not in tool_map:
                return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Tool '{tool_name}' not found"}}
            
            # Execute the tool
            tool_function = tool_map[tool_name]
            result_content = tool_function(**tool_call.arguments)
            
            # Convert result to text part format
            text_part = mcp_schemas.TextPart(text=str(result_content))
            tool_result = mcp_schemas.ToolResult(content=[text_part])
            await ui_manager.broadcast(f"MCP Success: {tool_name} executed.")
            return {"jsonrpc": "2.0", "id": request_id, "result": tool_result.model_dump()}

        else:
            return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method '{method}' not found"}}

    except (ValidationError, ValueError) as e:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": "Invalid params", "data": str(e)}}
    except PermissionError as e:
        await ui_manager.broadcast(f"MCP Error: Permission Denied - {e}")
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32001, "message": "Permission Denied", "data": str(e)}}
    except FileNotFoundError as e:
        await ui_manager.broadcast(f"MCP Error: File Not Found - {e}")
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32002, "message": "File Not Found", "data": str(e)}}
    except Exception as e:
        # Catch-all for unexpected server errors
        await ui_manager.broadcast(f"MCP Error: Internal Server Error - {e}")
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32603, "message": "Internal error", "data": str(e)}}

@app.post("/mcp")
async def mcp_http_endpoint(request: Request):
    """HTTP MCP endpoint for Claude Code integration."""
    try:
        body = await request.body()
        request_data = json.loads(body)
        
        # Handle single request
        if isinstance(request_data, dict):
            response = await process_mcp_request(request_data)
            return JSONResponse(content=response)
        
        # Handle batch requests
        elif isinstance(request_data, list):
            responses = []
            for req in request_data:
                if isinstance(req, dict):
                    responses.append(await process_mcp_request(req))
                else:
                    responses.append({"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}})
            return JSONResponse(content=responses)
        
        else:
            return JSONResponse(
                content={"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "Invalid Request"}},
                status_code=400
            )
            
    except json.JSONDecodeError:
        return JSONResponse(
            content={"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}},
            status_code=400
        )
    except Exception as e:
        return JSONResponse(
            content={"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": "Internal error", "data": str(e)}},
            status_code=500
        )

@app.get("/ws/mcp")
def mcp_endpoint_info():
    return {
        "message": "MCP WebSocket endpoint available", 
        "protocol": "WebSocket", 
        "upgrade": "required",
        "mcp_version": "2024-11-05"
    }

@app.websocket("/ws/ui")
async def websocket_ui_endpoint(websocket: WebSocket):
    import sys
    print(f"[UI] WebSocket connection attempt from {websocket.client}", flush=True, file=sys.stderr)
    print(f"[UI] Headers: {dict(websocket.headers)}", flush=True, file=sys.stderr)

    try:
        await ui_manager.connect(websocket)
        print(f"[UI] WebSocket connected successfully", flush=True, file=sys.stderr)

        while True:
            # The UI websocket is primarily for receiving data
            data = await websocket.receive_text()
            print(f"[UI] Received message: {data}", flush=True, file=sys.stderr)
            # Don't echo back - just log the message
            # UI websocket is mainly for receiving broadcasts, not echoing
    except WebSocketDisconnect:
        ui_manager.disconnect(websocket)
        print("[UI] Client disconnected", flush=True, file=sys.stderr)
    except Exception as e:
        print(f"[UI] WebSocket error: {e}", flush=True, file=sys.stderr)
        ui_manager.disconnect(websocket)


async def send_mcp_error(websocket: WebSocket, error: mcp_schemas.JsonRpcError, request_id: int | str | None = None):
    response = mcp_schemas.JsonRpcResponse(id=request_id, error=error)
    await mcp_manager.send_personal_message(response.model_dump_json(exclude_none=True), websocket)

@app.websocket("/ws/test")
async def websocket_test_endpoint(websocket: WebSocket):
    print("TEST: WebSocket connection!")
    await websocket.accept()
    await websocket.send_text("Hello from test endpoint!")
    await websocket.close()

@app.websocket("/ws/mcp")
async def websocket_mcp_endpoint(websocket: WebSocket):
    import sys
    print(f"[MCP] Connection attempt from {websocket.client}", flush=True, file=sys.stderr)
    print(f"[MCP] Headers: {dict(websocket.headers)}", flush=True, file=sys.stderr)
    
    await websocket.accept()
    print(f"[MCP] WebSocket accepted", flush=True, file=sys.stderr)
    
    mcp_manager.active_connections.append(websocket)
    print(f"[MCP] Added to connection pool", flush=True, file=sys.stderr)
    try:
        while True:
            print(f"[MCP] Waiting for message...", flush=True, file=sys.stderr)
            data = await websocket.receive_text()
            print(f"[MCP] Received: {data}", flush=True, file=sys.stderr)
            request_id = None
            try:
                request_data = json.loads(data)
                request_id = request_data.get("id")

                # Basic JSON-RPC validation
                if not all(k in request_data for k in ["jsonrpc", "method"]):
                    raise ValueError("Missing required JSON-RPC fields.")
                if request_data["jsonrpc"] != "2.0":
                    raise ValueError("Invalid JSON-RPC version.")

                method = request_data["method"]
                params = request_data.get("params", {})

                # Log activity to UI
                await ui_manager.broadcast(f"MCP Request: {method} | Params: {json.dumps(params)}")

                # --- MCP Method Router ---
                if method == "initialize":
                    # MCP initialization handshake
                    init_result = {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {
                                "listChanged": True
                            },
                            "resources": {},
                            "prompts": {},
                            "logging": {}
                        },
                        "serverInfo": {
                            "name": "MCP KnowledgeExplorer Hub",
                            "version": "1.0.0"
                        }
                    }
                    response = mcp_schemas.JsonRpcResponse(id=request_id, result=init_result)
                    await mcp_manager.send_personal_message(response.model_dump_json(by_alias=True), websocket)

                elif method == "initialized":
                    # Client confirms initialization complete - no response needed
                    await ui_manager.broadcast("MCP Client initialized successfully.")

                elif method == "tools/list":
                    tools = mcp_service.get_tools()
                    # Convert ToolDefinition objects to dictionaries with proper field names
                    tools_dict = [tool.model_dump(by_alias=True) for tool in tools]
                    response = mcp_schemas.JsonRpcResponse(id=request_id, result={"tools": tools_dict})
                    await mcp_manager.send_personal_message(response.model_dump_json(by_alias=True), websocket)

                elif method == "tools/call":
                    tool_call = mcp_schemas.ToolCallParams(**params)
                    tool_name = tool_call.name
                    
                    if tool_name not in tool_map:
                        raise ValueError(f"Tool '{tool_name}' not found.")
                    
                    # Execute the tool
                    tool_function = tool_map[tool_name]
                    result_content = tool_function(**tool_call.arguments)
                    
                    # Convert result to text part format
                    text_part = mcp_schemas.TextPart(text=str(result_content))
                    tool_result = mcp_schemas.ToolResult(content=[text_part])
                    response = mcp_schemas.JsonRpcResponse(id=request_id, result=tool_result)
                    await mcp_manager.send_personal_message(response.model_dump_json(), websocket)
                    await ui_manager.broadcast(f"MCP Success: {tool_name} executed.")

                else:
                    raise ValueError(f"Method '{method}' not found.")

            except json.JSONDecodeError:
                await send_mcp_error(websocket, mcp_schemas.JsonRpcError.parse_error())
            except (ValidationError, ValueError) as e:
                await send_mcp_error(websocket, mcp_schemas.JsonRpcError.invalid_params(str(e)), request_id)
            except PermissionError as e:
                error = mcp_schemas.JsonRpcError(code=-32001, message="Permission Denied", data=str(e))
                await send_mcp_error(websocket, error, request_id)
                await ui_manager.broadcast(f"MCP Error: Permission Denied - {e}")
            except FileNotFoundError as e:
                error = mcp_schemas.JsonRpcError(code=-32002, message="File Not Found", data=str(e))
                await send_mcp_error(websocket, error, request_id)
                await ui_manager.broadcast(f"MCP Error: File Not Found - {e}")
            except Exception as e:
                # Catch-all for unexpected server errors
                await send_mcp_error(websocket, mcp_schemas.JsonRpcError.internal_error(str(e)), request_id)
                await ui_manager.broadcast(f"MCP Error: Internal Server Error - {e}")

    except WebSocketDisconnect:
        mcp_manager.disconnect(websocket)
        print(f"MCP Client disconnected: {websocket.client}")
        await ui_manager.broadcast("MCP Client disconnected.")
