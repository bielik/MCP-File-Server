import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.database import create_db_and_tables
from app.api.endpoints import router as api_router
from app.api.websockets import ConnectionManager

app = FastAPI(title="MCP KnowledgeExplorer Hub")

# Configure CORS
origins = [
    f"http://localhost",
    f"http://localhost:{os.getenv('FRONTEND_PORT', 5173)}",
    f"[http://127.0.0.1](http://127.0.0.1):{os.getenv('FRONTEND_PORT', 5173)}",
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

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

app.include_router(api_router, prefix="/api")

@app.get("/")
def read_root():
    return {"message": "MCP KnowledgeExplorer Hub is running."}

@app.websocket("/ws/ui")
async def websocket_ui_endpoint(websocket: WebSocket):
    await ui_manager.connect(websocket)
    try:
        while True:
            # The UI websocket is primarily for receiving data
            data = await websocket.receive_text()
            # For now, we can just echo back or log
            await ui_manager.send_personal_message(f"Echo from UI: {data}", websocket)
    except WebSocketDisconnect:
        ui_manager.disconnect(websocket)
        print("UI Client disconnected")


@app.websocket("/ws/mcp")
async def websocket_mcp_endpoint(websocket: WebSocket):
    await mcp_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # This is where MCP protocol logic would go
            # For now, we log the tool call and echo back
            print(f"Received MCP call: {data}")
            
            # Simulate logging to the UI
            await ui_manager.broadcast(f"MCP Activity: {data}")

            # Send result back to AI client
            await mcp_manager.send_personal_message(f"Result for '{data}'", websocket)

    except WebSocketDisconnect:
        mcp_manager.disconnect(websocket)
        print("MCP Client disconnected")
