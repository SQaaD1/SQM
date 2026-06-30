"""
Cloud-compatible chat server using WebSockets
Can be deployed to Heroku, Railway, Render, or any VPS
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import json
import asyncio

app = FastAPI()

# Enable CORS for all origins (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[websocket] = username
        print(f"[SERVER] {username} connected")
    
    def disconnect(self, websocket: WebSocket):
        username = self.active_connections.get(websocket, "Unknown")
        if websocket in self.active_connections:
            del self.active_connections[websocket]
        print(f"[SERVER] {username} disconnected")
        return username
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str, exclude: WebSocket = None):
        for connection in self.active_connections:
            if connection != exclude:
                try:
                    await connection.send_text(message)
                except:
                    pass

manager = ConnectionManager()

def get_timestamp():
    return datetime.now().strftime("%H:%M:%S")

@app.get("/")
async def root():
    return {"status": "online", "message": "Chat server is running"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "connections": len(manager.active_connections),
        "users": list(manager.active_connections.values())
    }

@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    await manager.connect(websocket, username)
    
    # Send welcome message to the user
    await manager.send_personal_message(
        json.dumps({
            'type': 'system',
            'message': f'Welcome to the chat, {username}!',
            'timestamp': get_timestamp()
        }),
        websocket
    )
    
    # Broadcast to all users that someone joined
    await manager.broadcast(
        json.dumps({
            'type': 'system',
            'message': f'{username} joined the chat',
            'timestamp': get_timestamp()
        }),
        exclude=websocket
    )
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get('type') == 'chat':
                print(f"[CHAT] {username}: {message.get('message')}")
                
                # Broadcast to all clients
                await manager.broadcast(
                    json.dumps({
                        'type': 'chat',
                        'username': username,
                        'message': message.get('message'),
                        'timestamp': get_timestamp()
                    })
                )
    except WebSocketDisconnect:
        username = manager.disconnect(websocket)
        
        # Broadcast to all users that someone left
        await manager.broadcast(
            json.dumps({
                'type': 'system',
                'message': f'{username} left the chat',
                'timestamp': get_timestamp()
            })
        )

if __name__ == "__main__":
    import uvicorn
    print("[SERVER] Starting cloud chat server...")
    print("[SERVER] WebSocket endpoint: ws://localhost:8000/ws/{username}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
