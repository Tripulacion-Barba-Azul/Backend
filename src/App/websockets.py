"""Service websocket"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


websocket_router = APIRouter()

class GameConnectionPool:
    
    active_connections: dict[int, WebSocket]

    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket: WebSocket, player_id: int):
        await websocket.accept()
        self.active_connections[player_id] = websocket

    def disconnect(self, player_id: int):
        if player_id in self.active_connections:
            self.active_connections.pop(player_id)

    def get_connection(self, player_id: int) -> WebSocket | None:
        return self.active_connections.get(player_id)

    async def send_message(self, message: dict, player_id: int):
        websocket = self.get_connection(player_id)
        if websocket:
            await websocket.send_json(message)

    async def broadcast(self, message: dict):
        for websocket in self.active_connections.values():
            await websocket.send_json(message)

class ConnectionManager:
    def __init__(self):
        self.games: dict[int, GameConnectionPool] = {}

    def get_game_pool(self, game_id: int) -> GameConnectionPool:
        if game_id not in self.games:
            self.games[game_id] = GameConnectionPool()
        return self.games[game_id]

    async def connect(self, game_id: int, player_id: int, websocket: WebSocket):
        game_pool = self.get_game_pool(game_id)
        await game_pool.connect(websocket, player_id)

    def disconnect(self, game_id: int, player_id: int):
        game_pool = self.games.get(game_id)
        if not game_pool:
            return
        game_pool.disconnect(player_id)

        if not game_pool.active_connections:
            self.games.pop(game_id)

    async def send_to_player(self, game_id: int, player_id: int, message: dict):
        game_pool = self.games.get(game_id)
        if game_pool:
            await game_pool.send_message(message, player_id)

    async def broadcast(self, game_id: int, message: dict):
        game_pool = self.games.get(game_id)
        if game_pool:
            await game_pool.broadcast(message)


manager = ConnectionManager()

@websocket_router.websocket("/ws/{game_id}/{player_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: int, player_id: int):
    await manager.connect(game_id, player_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(game_id, player_id)
