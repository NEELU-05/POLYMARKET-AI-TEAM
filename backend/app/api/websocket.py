import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List

from app.core.event_bus import event_bus, Event
from app.core.logging import get_logger

log = get_logger("websocket")

router = APIRouter(prefix="/api/ws", tags=["websocket"])

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info("ws_client_connected", clients=len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            log.info("ws_client_disconnected", clients=len(self.active_connections))

    async def broadcast(self, message: dict):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)
        
        for connection in dead_connections:
            self.disconnect(connection)

manager = ConnectionManager()

async def ws_event_subscriber(event: Event):
    """Forward internal events to all connected WebSocket clients."""
    await manager.broadcast({
        "type": "event_bus",
        "topic": event.topic,
        "source": event.source,
        "data": event.data,
        "timestamp": event.timestamp,
        "event_id": event.event_id
    })

# Register our subscriber to all topics
event_bus.subscribe("*", ws_event_subscriber)

@router.websocket("/events")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Send initial status
        from app.services.scheduler import get_status
        await websocket.send_json({
            "type": "system_status",
            "data": get_status()
        })
        
        # Keep connection open and handle incoming messages (e.g. ping)
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        log.error("websocket_error", error=str(e))
        manager.disconnect(websocket)
