"""
API Module
==========
FastAPI server providing REST and WebSocket endpoints
for querying the Base Launch Detector.
"""

from api.server import create_app, APIServer

__all__ = ["create_app", "APIServer"]
