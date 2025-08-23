"""
ShellPilot Web Interface - FastAPI Backend
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import List, Dict, Any, Optional
import json
import asyncio
import uvicorn
from datetime import datetime

# Import your existing ShellPilot core
from shellpilot.config import get_config
from shellpilot.core.session import get_session_store
from shellpilot import __version__

# Import API routers
from .api.commands import router as commands_router
from .api.workflows import router as workflows_router
from .api.session import router as session_router

# Create FastAPI app
app = FastAPI(
    title="ShellPilot Web Interface",
    description="AI-Powered Linux System Administration Web Interface",
    version=__version__,
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(commands_router, prefix="/api", tags=["commands"])
app.include_router(workflows_router, prefix="/api", tags=["workflows"])
app.include_router(session_router, prefix="/api", tags=["session"])

# WebSocket connection manager
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

    async def send_json_message(self, data: dict, websocket: WebSocket):
        await websocket.send_text(json.dumps(data))

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "ShellPilot Web Interface",
        "version": __version__,
        "docs": "/api/docs",
        "websocket": "/ws",
        "status": "running"
    }

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        config = get_config()
        session_store = get_session_store()
        session_info = session_store.get_session_info()

        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": __version__,
            "config": {
                "provider": config.get_default_provider(),
                "model": config.get_default_model(),
                "safe_mode": config.safe_mode
            },
            "session": {
                "session_id": session_info["session_id"],
                "total_commands": session_info["total_commands"]
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

# Configuration endpoint
@app.get("/api/config")
async def get_config_info():
    """Get current ShellPilot configuration"""
    try:
        config = get_config()

        return {
            "provider": config.get_default_provider(),
            "model": config.get_default_model(),
            "safe_mode": config.safe_mode,
            "log_level": config.log_level,
            "available_providers": ["deepseek", "openai", "anthropic", "ollama", "gemini"],
            "api_keys_configured": list(config.api_keys.keys())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# WebSocket endpoint for real-time communication
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time command execution"""
    await manager.connect(websocket)
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)

            # Echo back for now (we'll implement command execution later)
            response = {
                "type": "response",
                "timestamp": datetime.now().isoformat(),
                "data": f"Received: {message}"
            }

            await manager.send_json_message(response, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Simple web interface for testing
@app.get("/test", response_class=HTMLResponse)
async def test_interface():
    """Simple test interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ShellPilot Web Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; }
            .status { padding: 10px; background: #f0f0f0; margin: 20px 0; }
            button { padding: 10px 20px; margin: 5px; }
            #output { background: #f8f8f8; padding: 20px; min-height: 200px; margin: 20px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚁 ShellPilot Web Interface Test</h1>
            <div class="status">
                <strong>Status:</strong> <span id="status">Connecting...</span>
            </div>

            <button onclick="testHealth()">Test Health</button>
            <button onclick="testConfig()">Test Config</button>
            <button onclick="testWebSocket()">Test WebSocket</button>

            <div id="output"></div>
        </div>

        <script>
            const output = document.getElementById('output');
            const status = document.getElementById('status');

            // Test API endpoints
            async function testHealth() {
                try {
                    const response = await fetch('/api/health');
                    const data = await response.json();
                    output.innerHTML = '<h3>Health Check:</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                    status.textContent = 'API Connected ✅';
                } catch (error) {
                    output.innerHTML = '<h3>Error:</h3><pre>' + error.message + '</pre>';
                    status.textContent = 'API Error ❌';
                }
            }

            async function testConfig() {
                try {
                    const response = await fetch('/api/config');
                    const data = await response.json();
                    output.innerHTML = '<h3>Configuration:</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                } catch (error) {
                    output.innerHTML = '<h3>Error:</h3><pre>' + error.message + '</pre>';
                }
            }

            function testWebSocket() {
                const ws = new WebSocket('ws://localhost:8000/ws');

                ws.onopen = function(event) {
                    output.innerHTML = '<h3>WebSocket Connected ✅</h3>';
                    ws.send(JSON.stringify({type: 'test', message: 'Hello from web interface!'}));
                };

                ws.onmessage = function(event) {
                    const data = JSON.parse(event.data);
                    output.innerHTML += '<div>Received: <pre>' + JSON.stringify(data, null, 2) + '</pre></div>';
                };

                ws.onerror = function(error) {
                    output.innerHTML = '<h3>WebSocket Error ❌</h3><pre>' + error + '</pre>';
                };
            }

            // Auto-test health on load
            document.addEventListener('DOMContentLoaded', testHealth);
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(
        "shellpilot.web.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )