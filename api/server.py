"""
FastAPI Server for Base Launch Detector
========================================
Provides REST API and WebSocket streaming for monitored tokens.

Endpoints:
  GET  /api/v1/tokens           - List recent tokens
  GET  /api/v1/tokens/{addr}    - Token details
  GET  /api/v1/tokens/{addr}/analysis  - Analysis results
  GET  /api/v1/alerts           - Recent alerts
  GET  /api/v1/gems             - EARLY GEM tokens
  GET  /api/v1/stats            - System statistics
  GET  /api/v1/health           - Health check
  WS   /ws/live                 - Live event stream
"""

import asyncio
import json
import logging
import time
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from config.settings import settings

logger = logging.getLogger("APIServer")


class APIServer:
    """
    FastAPI server wrapper with shared state access.
    Connects to the monitor pipeline for live data.
    """

    def __init__(self):
        self.app = FastAPI(
            title="Base Launch Detector API",
            description="Real-time Base chain token monitoring and analysis",
            version="2.0.0",
            lifespan=self._lifespan,
        )

        # Add CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Shared state (populated by main_monitor)
        self.pair_monitor = None
        self.liquidity_monitor = None
        self.momentum_engine = None
        self.risk_scanner = None
        self.alert_manager = None

        # WebSocket connections
        self._ws_connections: List[WebSocket] = []

        # Token storage (in-memory cache)
        self._tokens: Dict[str, dict] = {}
        self._analyses: Dict[str, dict] = {}
        self._decisions: Dict[str, dict] = {}
        self._alerts: List[dict] = []

        # Register routes
        self._register_routes()

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """Lifespan context manager for startup/shutdown."""
        logger.info("API Server starting...")
        yield
        logger.info("API Server shutting down...")

    def _register_routes(self):
        """Register all API routes."""

        @self.app.get("/api/v1/health")
        async def health():
            """Health check endpoint."""
            stats = {}
            if self.pair_monitor:
                stats["pair_monitor"] = self.pair_monitor.get_stats()
            if self.liquidity_monitor:
                stats["liquidity_monitor"] = self.liquidity_monitor.get_stats()
            return {
                "status": "ok",
                "uptime_seconds": time.time() - getattr(self, "_start_time", time.time()),
                "monitors": stats,
            }

        @self.app.get("/api/v1/stats")
        async def system_stats():
            """Full system statistics."""
            stats = {"timestamp": time.time()}
            if self.pair_monitor:
                stats["pair_monitor"] = self.pair_monitor.get_stats()
            if self.liquidity_monitor:
                stats["liquidity_monitor"] = self.liquidity_monitor.get_stats()
            if self.momentum_engine:
                stats["momentum_engine"] = self.momentum_engine.get_stats()
            if self.alert_manager:
                stats["alerts"] = self.alert_manager.get_stats()
            stats["tokens_tracked"] = len(self._tokens)
            stats["analyses_completed"] = len(self._analyses)
            return stats

        @self.app.get("/api/v1/tokens")
        async def list_tokens(
            limit: int = Query(50, ge=1, le=200),
            dex: Optional[str] = Query(None, description="Filter by DEX"),
            min_liquidity: Optional[float] = Query(None, description="Min liquidity USD"),
        ):
            """List recently discovered tokens."""
            tokens = list(self._tokens.values())

            if dex:
                tokens = [t for t in tokens if t.get("dex") == dex]
            if min_liquidity:
                tokens = [t for t in tokens if t.get("liquidity_usd", 0) >= min_liquidity]

            # Sort by most recent first
            tokens.sort(key=lambda t: t.get("created_at", 0), reverse=True)
            return {
                "count": len(tokens),
                "total": len(self._tokens),
                "tokens": tokens[:limit],
            }

        @self.app.get("/api/v1/tokens/{address}")
        async def token_detail(address: str):
            """Get detailed info for a specific token."""
            token = self._tokens.get(address.lower())
            if not token:
                raise HTTPException(status_code=404, detail="Token not found")
            return {
                "token": token,
                "analysis": self._analyses.get(address.lower()),
                "decision": self._decisions.get(address.lower()),
            }

        @self.app.get("/api/v1/tokens/{address}/analysis")
        async def token_analysis(address: str):
            """Get analysis results for a specific token."""
            analysis = self._analyses.get(address.lower())
            if not analysis:
                raise HTTPException(status_code=404, detail="Analysis not found")
            return analysis

        @self.app.get("/api/v1/alerts")
        async def recent_alerts(
            limit: int = Query(50, ge=1, le=200),
            alert_type: Optional[str] = Query(None),
        ):
            """Get recent alerts."""
            if self.alert_manager:
                return {
                    "count": len(self._alerts),
                    "alerts": self.alert_manager.get_recent_alerts(limit, alert_type),
                }
            return {"count": 0, "alerts": []}

        @self.app.get("/api/v1/gems")
        async def list_gems(limit: int = Query(20, ge=1, le=50)):
            """List EARLY GEM tokens."""
            gems = [
                d for d in self._decisions.values()
                if d.get("decision") == "early_gem"
            ]
            gems.sort(key=lambda g: g.get("momentum_score", 0), reverse=True)
            return {"count": len(gems), "gems": gems[:limit]}

        @self.app.websocket("/ws/live")
        async def websocket_live(ws: WebSocket):
            """WebSocket endpoint for live event streaming."""
            await ws.accept()
            self._ws_connections.append(ws)
            logger.info(f"WebSocket client connected ({len(self._ws_connections)} total)")

            try:
                # Send initial state
                await ws.send_json({
                    "type": "connected",
                    "data": {
                        "tokens_tracked": len(self._tokens),
                        "analyses_completed": len(self._analyses),
                    },
                })

                # Keep connection alive
                while True:
                    try:
                        data = await asyncio.wait_for(ws.receive_text(), timeout=30.0)
                        # Handle client messages if needed
                    except asyncio.TimeoutError:
                        await ws.send_json({"type": "ping"})

            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
            finally:
                if ws in self._ws_connections:
                    self._ws_connections.remove(ws)

    async def broadcast(self, data: dict):
        """Broadcast data to all connected WebSocket clients."""
        disconnected = []
        for ws in self._ws_connections:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self._ws_connections.remove(ws)

    def add_token(self, token_data: dict):
        """Add a token to the in-memory cache."""
        key = token_data.get("token_address", "").lower()
        if key:
            self._tokens[key] = token_data

    def add_analysis(self, address: str, analysis_data: dict):
        """Add analysis results."""
        self._analyses[address.lower()] = analysis_data

    def add_decision(self, address: str, decision_data: dict):
        """Add classification decision."""
        self._decisions[address.lower()] = decision_data

    async def run(self, host: str = None, port: int = None):
        """Start the API server."""
        host = host or settings.api.host
        port = port or settings.api.port
        self._start_time = time.time()
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    async def start_in_background(self, host: str = None, port: int = None):
        """Start the API server as a background task."""
        host = host or settings.api.host
        port = port or settings.api.port
        self._start_time = time.time()
        config = uvicorn.Config(self.app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        asyncio.create_task(server.serve())
        logger.info(f"API Server starting on {host}:{port}")
        return server


def create_app() -> FastAPI:
    """Create a FastAPI app instance (for testing)."""
    server = APIServer()
    return server.app
