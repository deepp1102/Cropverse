"""
Dashboard Routes
================
API endpoints for dashboard data and real-time monitoring.

Endpoints:
- GET /api/dashboard - Get complete dashboard data (readings, alerts, stats)
- GET /api/dashboard/readings - Get latest sensor readings
- GET /api/dashboard/alerts - Get active alerts
- GET /api/dashboard/status - Get system status summary

Security:
- All endpoints require Firebase Authentication in production
- Uses @login_required decorator (bypassed when TESTING_MODE=true)
"""

import os
from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from typing import Dict, Any, List

from utils.logger import setup_logger

# Testing mode bypass
TESTING_MODE = os.getenv('TESTING_MODE', 'false').lower() == 'true'

# Override login_required decorator in testing mode
if TESTING_MODE:
    def login_required(f):
        # No-op decorator in testing mode
        return f
else:
    # Only imported when not in testing mode
    from utils.decorators import login_required

from services.firestore_service import (
    get_latest_readings,
    get_recent_alerts,
    get_setting
)
from models.sensor_reading import SensorReading
from models.alert import Alert

logger = setup_logger(__name__)

# Create Blueprint
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')



def _calculate_system_status(latest_reading: SensorReading, active_alerts: List[Alert]) -> Dict[str, Any]:
    """
    Calculate overall system status based on readings and alerts.
    
    Args:
        latest_reading: Most recent sensor reading
        active_alerts: List of unresolved alerts
        
    Returns:
        Dictionary with system status information
    """
    # Count alerts by type
    critical_count = sum(1 for alert in active_alerts if alert.alert_type == 'critical')
    warning_count = sum(1 for alert in active_alerts if alert.alert_type == 'warning')
    info_count = sum(1 for alert in active_alerts if alert.alert_type == 'info')
    
    # Determine overall status
    if critical_count > 0:
        overall_status = 'critical'
        status_message = f'{critical_count} critical issue(s) require immediate attention'
        status_emoji = '🚨'
    elif warning_count > 0:
        overall_status = 'warning'
        status_message = f'{warning_count} warning(s) detected'
        status_emoji = '⚠️'
    elif info_count > 0:
        overall_status = 'info'
        status_message = f'{info_count} notification(s)'
        status_emoji = 'ℹ️'
    else:
        overall_status = 'optimal'
        status_message = 'All systems operating normally'
        status_emoji = '✅'
    
    # Air quality from latest reading
    air_quality = latest_reading.get_air_quality_status() if latest_reading else 'Unknown'
    
    return {
        'overall_status': overall_status,
        'status_message': status_message,
        'status_emoji': status_emoji,
        'air_quality': air_quality,
        'alert_counts': {
            'critical': critical_count,
            'warning': warning_count,
            'info': info_count,
            'total': len(active_alerts)
        },
        'exhaust_fan_active': latest_reading.exhaust_fan if latest_reading else False
    }


def _calculate_quick_stats(readings: List[SensorReading]) -> Dict[str, Any]:
    """
    Calculate quick statistics from recent readings.
    
    Args:
        readings: List of recent sensor readings
        
    Returns:
        Dictionary with statistics
    """
    if not readings:
        return {
            'avg_temperature': 0,
            'avg_humidity': 0,
            'avg_methane': 0,
            'readings_count': 0,
            'time_range_hours': 0
        }
    
    # Calculate averages
    avg_temp = sum(r.temperature for r in readings) / len(readings)
    avg_humidity = sum(r.humidity for r in readings) / len(readings)
    avg_methane = sum(r.methane for r in readings) / len(readings)
    
    # Calculate time range
    if len(readings) > 1:
        oldest = min(r.timestamp for r in readings)
        newest = max(r.timestamp for r in readings)
        time_range_hours = (newest - oldest).total_seconds() / 3600
    else:
        time_range_hours = 0
    
    return {
        'avg_temperature': round(avg_temp, 2),
        'avg_humidity': round(avg_humidity, 2),
        'avg_methane': round(avg_methane, 2),
        'readings_count': len(readings),
        'time_range_hours': round(time_range_hours, 2)
    }


@dashboard_bp.route('', methods=['GET'])
#@login_required
def get_dashboard_data():
    """
    Get complete dashboard data including readings, alerts, and statistics.
    
    Query Parameters:
        readings_limit: int (optional, default=10) - Number of recent readings to fetch
        
    Response (200 OK):
        {
            "success": true,
            "data": {
                "latest_reading": {
                    "temperature": float,
                    "humidity": float,
                    "methane": int,
                    "other_gases": int,
                    "exhaust_fan": bool,
                    "timestamp": string,
                    "air_quality": string,
                    "temperature_status": string,
                    "humidity_status": string,
                    "methane_status": string
                },
                "recent_readings": [...],  // Last N readings
                "active_alerts": [...],     // Unresolved alerts
                "system_status": {
                    "overall_status": string,
                    "status_message": string,
                    "status_emoji": string,
                    "air_quality": string,
                    "alert_counts": {...},
                    "exhaust_fan_active": bool
                },
                "quick_stats": {
                    "avg_temperature": float,
                    "avg_humidity": float,
                    "avg_methane": float,
                    "readings_count": int,
                    "time_range_hours": float
                }
            },
            "timestamp": string
        }
    
    Example:
        GET /api/dashboard?readings_limit=20
    """
    try:
        # Get query parameters
        readings_limit = request.args.get('readings_limit', default=10, type=int)
        readings_limit = max(1, min(readings_limit, 100))  # Limit between 1-100
        
        user_id = getattr(request, 'user', {}).get('uid', 'test_user')
        logger.info(f"Fetching dashboard data for user {user_id} (limit={readings_limit})")
        
        # Fetch latest readings
        readings = get_latest_readings(limit=readings_limit)
        latest_reading = readings[0] if readings else None
        
        # Fetch active alerts (last 24 hours, unresolved)
        # Fetch unresolved alerts only
        active_alerts = get_recent_alerts(limit=100, unresolved_only=True)
        
        # Calculate system status
        system_status = _calculate_system_status(latest_reading, active_alerts)
        
        # Calculate quick stats from recent readings
        quick_stats = _calculate_quick_stats(readings)
        
        # Prepare response data
        response_data = {
            'latest_reading': latest_reading.to_dict() if latest_reading else None,
            'recent_readings': [r.to_dict() for r in readings],
            'active_alerts': [a.to_dict() for a in active_alerts],
            'system_status': system_status,
            'quick_stats': quick_stats
        }
        
        logger.info(f"Dashboard data fetched successfully: {len(readings)} readings, {len(active_alerts)} alerts")
        
        return jsonify({
            'success': True,
            'data': response_data,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch dashboard data: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch dashboard data',
            'message': 'An error occurred while retrieving dashboard information. Please try again.'
        }), 500


@dashboard_bp.route('/readings', methods=['GET'])
# @login_required
def get_readings():
    """
    Get latest sensor readings only.
    
    Query Parameters:
        limit: int (optional, default=10) - Number of readings to fetch
        
    Response (200 OK):
        {
            "success": true,
            "data": {
                "readings": [...],
                "count": int
            },
            "timestamp": string
        }
    
    Example:
        GET /api/dashboard/readings?limit=50
    """
    try:
        limit = request.args.get('limit', default=10, type=int)
        limit = max(1, min(limit, 1000))  # Limit between 1-1000
        
        user_id = getattr(request, 'user', {}).get('uid', 'test_user')
        logger.info(f"Fetching {limit} latest readings for user {user_id}")
        
        readings = get_latest_readings(limit=limit)
        
        return jsonify({
            'success': True,
            'data': {
                'readings': [r.to_dict() for r in readings],
                'count': len(readings)
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch readings: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch readings'
        }), 500


from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
#from flask_login import login_required
# make sure `logger` and `get_recent_alerts` are imported/available in this module

#dashboard_bp = Blueprint("dashboard", __name__)

@dashboard_bp.route('/alerts', methods=['GET'])
#@login_required
def get_alerts():
    """
    Get alerts with optional filtering.

    Query Parameters:
        hours: int (optional, default=24) - Hours to look back (1..720)
        resolved: bool (optional) - 'true' or 'false' (case-insensitive)
        alert_type: string (optional) - Filter by type (critical, warning, info)

    Response (200 OK):
        {
            "success": true,
            "data": {
                "alerts": [...],
                "count": int,
                "counts_by_type": {
                    "critical": int,
                    "warning": int,
                    "info": int
                }
            },
            "timestamp": string (ISO)
        }
    """
    try:
        # --- Parse query params ---
        hours = request.args.get('hours', default=24, type=int)
        hours = max(1, min(hours, 720))  # clamp between 1 and 720 (30 days)

        resolved_param = request.args.get('resolved')  # None | 'true' | 'false'
        if resolved_param is None:
            resolved = None
        else:
            resolved_param = resolved_param.strip().lower()
            if resolved_param in ('true', '1', 'yes'):
                resolved = True
            elif resolved_param in ('false', '0', 'no'):
                resolved = False
            else:
                return jsonify({
                    'success': False,
                    'error': "Invalid 'resolved' value. Use 'true' or 'false'."
                }), 400

        alert_type = request.args.get('alert_type')
        if alert_type:
            alert_type = alert_type.strip().lower()

        logger.info(f"Fetching alerts: hours={hours}, resolved={resolved}, type={alert_type}")

        # --- Fetch alerts from your storage / service ---
        # Assumes get_recent_alerts(limit: int, unresolved_only: bool) exists.
        # If you have a different API, adapt these calls.
        if resolved is None:
            # get both resolved and unresolved
            alerts = get_recent_alerts(limit=500, unresolved_only=False)
        elif resolved is False:
            # only unresolved alerts
            alerts = get_recent_alerts(limit=500, unresolved_only=True)
        else:
            # resolved == True -> fetch all then filter resolved ones
            all_alerts = get_recent_alerts(limit=500, unresolved_only=False)
            alerts = [a for a in all_alerts if getattr(a, 'is_resolved', False) is True]

        # --- Filter by time range ---
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        alerts = [a for a in alerts if getattr(a, 'created_at', None) is not None and a.created_at >= cutoff_time]

        # --- Filter by alert type (if specified) ---
        if alert_type:
            alerts = [a for a in alerts if getattr(a, 'alert_type', '').lower() == alert_type]

        # --- Counts by type ---
        counts_by_type = {
            'critical': sum(1 for a in alerts if getattr(a, 'alert_type', '').lower() == 'critical'),
            'warning' : sum(1 for a in alerts if getattr(a, 'alert_type', '').lower() == 'warning'),
            'info'    : sum(1 for a in alerts if getattr(a, 'alert_type', '').lower() == 'info'),
        }

        return jsonify({
            'success': True,
            'data': {
                'alerts': [a.to_dict() for a in alerts],
                'count': len(alerts),
                'counts_by_type': counts_by_type
            },
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }), 200

    except Exception as e:
        logger.error("Failed to fetch alerts", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch alerts'
        }), 500



@dashboard_bp.route('/status', methods=['GET'])
# @login_required
def get_status():
    """
    Get system status summary only (lightweight endpoint).
    
    Response (200 OK):
        {
            "success": true,
            "data": {
                "overall_status": string,
                "status_message": string,
                "status_emoji": string,
                "air_quality": string,
                "alert_counts": {...},
                "exhaust_fan_active": bool,
                "last_reading_time": string
            },
            "timestamp": string
        }
    
    Example:
        GET /api/dashboard/status
    """
    try:
        user_id = getattr(request, 'user', {}).get('uid', 'test_user')
        logger.info(f"Fetching system status for user {user_id}")
        
        # Get latest reading
        readings = get_latest_readings(limit=1)
        latest_reading = readings[0] if readings else None
        
        # Get active alerts (unresolved, last 24h)
        # Firestore service uses (limit, unresolved_only)
        active_alerts = get_recent_alerts(limit=100, unresolved_only=True)
        
        # Calculate status
        system_status = _calculate_system_status(latest_reading, active_alerts)
        
        # Add last reading time
        system_status['last_reading_time'] = latest_reading.timestamp.isoformat() if latest_reading else None
        
        return jsonify({
            'success': True,
            'data': system_status,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch status: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch system status'
        }), 500


# Error handlers for this blueprint
@dashboard_bp.errorhandler(401)
def unauthorized(error):
    """Handle 401 errors"""
    return jsonify({
        'success': False,
        'error': 'Authentication required',
        'code': 'UNAUTHORIZED'
    }), 401


@dashboard_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}", exc_info=True)
    return jsonify({
        'success': False,
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR'
    }), 500


# Module-level info
if __name__ == "__main__":
    print("Dashboard Routes Module")
    print("=" * 50)
    print("Endpoints:")
    print("- GET /api/dashboard - Complete dashboard data")
    print("- GET /api/dashboard/readings - Latest sensor readings")
    print("- GET /api/dashboard/alerts - Active alerts")
    print("- GET /api/dashboard/status - System status summary")
    print("\nAuthentication: Firebase Auth token required")