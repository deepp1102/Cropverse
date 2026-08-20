"""
Data Models for CropVerse
=========================
This package contains all Firestore document models.

Models:
- SensorReading: Sensor data from Arduino
- Alert: System alerts and warnings
- User: User accounts and roles
- Setting: System configuration settings
- AnalyticsSummary: Pre-calculated daily analytics
"""

from .sensor_reading import SensorReading
from .alert import Alert
from .user import User
from .setting import Setting
from .analytics_summary import AnalyticsSummary

__all__ = [
    'SensorReading',
    'Alert',
    'User',
    'Setting',
    'AnalyticsSummary'
]

__version__ = '1.0.0'