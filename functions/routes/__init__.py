"""
Routes Package
==============
API endpoint handlers for CropVerse backend.

This package contains Flask route handlers that expose services via HTTP endpoints.

Modules:
- arduino.py - Arduino sensor data endpoints
- dashboard.py - Dashboard data endpoints
- analytics.py - Analytics and trends endpoints
- chatbot.py - AI chatbot endpoints
- settings.py - Configuration endpoints
- auth.py - Authentication endpoints

All routes use Firebase Authentication for security (except arduino endpoint which uses API key).
"""

from .arduino import arduino_bp
from .dashboard import dashboard_bp
from .analytics import analytics_bp
from .chatbot import chatbot_bp
from .settings import settings_bp
from .auth import auth_bp

__all__ = [
    'arduino_bp',
    'dashboard_bp',
    'analytics_bp',
    'chatbot_bp',
    'settings_bp',
    'auth_bp'
]