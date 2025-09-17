from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

# Global instance that can be imported by other modules
_ui_manager = None

def get_ui_manager() -> ConnectionManager:
    """Get the global UI manager instance."""
    global _ui_manager
    if _ui_manager is None:
        # This will be set by main.py after creating the manager
        from app.main import ui_manager
        _ui_manager = ui_manager
    return _ui_manager

def set_ui_manager(manager: ConnectionManager):
    """Set the global UI manager instance (called from main.py)."""
    global _ui_manager
    _ui_manager = manager
