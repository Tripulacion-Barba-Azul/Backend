"""Service websocket"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

websocket_router = APIRouter()

class WebsocketManage:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    async def close_connection(self, websocket: WebSocket):
        if websocket in self.active_connections:
            await websocket.close()
            self.active_connections.remove(websocket)


    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections[:]:
            await connection.send_text(message)

    async def broadcast_except(self, message: str, skip_ws: WebSocket):
        for connection in self.active_connections:
            if connection != skip_ws:
                try:
                    await connection.send_text(message)
                except Exception:
                    self.active_connections.remove(connection)

    def count(self) -> int:
        return len(self.active_connections)

games_ws : dict[int, WebsocketManage] = {}

def create_manager(game_id: int):
    games_ws[game_id] = WebsocketManage()

def get_manager(game_id : int):
    return games_ws.get(game_id)

def remove_manager(game_id: int):
    games_ws.pop(game_id, None)

@websocket_router.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: int):
    if not get_manager(game_id):
        create_manager(game_id)

    manager = get_manager(game_id)
    await manager.connect(websocket)
    
    try:
        await manager.send_message(f"Connected to ws from game {game_id}", websocket)
        while True:
            data = await websocket.receive_text()
            print(f"Received message from ws [Game {game_id}] : {data}")
    except WebSocketDisconnect:
        print(f"Client disconnected from ws [Game {game_id}]")
    finally:
        await manager.close_connection(websocket)
        if manager.count() == 0:
            remove_manager(game_id)