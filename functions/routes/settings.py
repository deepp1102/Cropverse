"""
Settings Routes
===============
API endpoints for system configuration and settings management.

Endpoints:
- GET /api/settings - Get all settings
- GET /api/settings/<key> - Get specific setting
- PUT /api/settings/<key> - Update setting (admin only)
- GET /api/settings/thresholds - Get threshold configuration
- PUT /api/settings/thresholds - Update thresholds (admin only)
- POST /api/settings/reset - Reset to default settings (admin only)

Security:
- GET endpoints require @login_required
- PUT/POST endpoints require @admin_required
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, Any

from utils.logger import setup_logger
from utils.decorators import login_required, admin_required
from utils.validators import validate_setting_value
from services.firestore_service import (
    get_setting,
    update_setting,
    get_all_settings
)
from models.setting import Setting, DEFAULT_SETTINGS
from utils import thresholds

logger = setup_logger(__name__)

# Create Blueprint
settings_bp = Blueprint('settings', __name__, url_prefix='/api/settings')


def _format_threshold_settings() -> Dict[str, Any]:
    """
    Format threshold constants into structured response.
    
    Returns:
        Dictionary with threshold configuration
    """
    return {
        'temperature': {
            'max': thresholds.TEMP_MAX,
            'min': thresholds.TEMP_MIN,
            'warning_max': thresholds.TEMP_WARNING_MAX,
            'warning_min': thresholds.TEMP_WARNING_MIN,
            'unit': '°C'
        },
        'humidity': {
            'max': thresholds.HUMIDITY_MAX,
            'min': thresholds.HUMIDITY_MIN,
            'warning_max': thresholds.HUMIDITY_WARNING_MAX,
            'warning_min': thresholds.HUMIDITY_WARNING_MIN,
            'unit': '%'
        },
        'methane': {
            'critical': thresholds.METHANE_CRITICAL,
            'warning': thresholds.METHANE_WARNING,
            'exhaust_fan_threshold': thresholds.METHANE_EXHAUST_FAN_THRESHOLD,
            'unit': 'ppm'
        },
        'other_gases': {
            'critical': thresholds.OTHER_GASES_CRITICAL,
            'warning': thresholds.OTHER_GASES_WARNING,
            'unit': 'ppm'
        }
    }


@settings_bp.route('', methods=['GET'])
@login_required
def get_all_settings_route():
    """
    Get all system settings.
    
    Query Parameters:
        category: string (optional) - Filter by category (thresholds, notifications, system)
        
    Response (200 OK):
        {
            "success": true,
            "data": {
                "settings": [
                    {
                        "key": string,
                        "value": any,
                        "category": string,
                        "description": string
                    }
                ],
                "count": int
            },
            "timestamp": string
        }
    
    Example:
        GET /api/settings?category=notifications
    """
    try:
        category = request.args.get('category')
        
        logger.info(f"Fetching all settings for user {request.user.get('uid')} (category={category})")
        
        # Get all settings
        settings = get_all_settings(category=category)
        
        return jsonify({
            'success': True,
            'data': {
                'settings': [s.to_dict() for s in settings],
                'count': len(settings)
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch settings: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch settings'
        }), 500


@settings_bp.route('/<key>', methods=['GET'])
@login_required
def get_setting_route(key: str):
    """
    Get specific setting by key.
    
    URL Parameters:
        key: Setting key (e.g., "TEMP_MAX", "EMAIL_NOTIFICATIONS_ENABLED")
        
    Response (200 OK):
        {
            "success": true,
            "data": {
                "key": string,
                "value": any,
                "category": string,
                "description": string
            },
            "timestamp": string
        }
    
    Response (404 Not Found):
        {
            "success": false,
            "error": "Setting not found"
        }
    
    Example:
        GET /api/settings/TEMP_MAX
    """
    try:
        logger.info(f"Fetching setting '{key}' for user {request.user.get('uid')}")
        
        # Get setting
        setting = get_setting(key)
        
        if not setting:
            return jsonify({
                'success': False,
                'error': 'Setting not found',
                'message': f"No setting found with key '{key}'"
            }), 404
        
        return jsonify({
            'success': True,
            'data': setting.to_dict(),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch setting: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch setting'
        }), 500


@settings_bp.route('/<key>', methods=['PUT'])
@admin_required
def update_setting_route(key: str):
    """
    Update specific setting (admin only).
    
    URL Parameters:
        key: Setting key
        
    Request Body (JSON):
        {
            "value": any  // New value for the setting
        }
    
    Response (200 OK):
        {
            "success": true,
            "message": "Setting updated successfully",
            "data": {
                "key": string,
                "value": any,
                "category": string,
                "description": string
            },
            "timestamp": string
        }
    
    Response (400 Bad Request):
        {
            "success": false,
            "error": "Invalid value"
        }
    
    Example:
        PUT /api/settings/TEMP_MAX
        Body: {"value": 36}
    """
    try:
        # Get request data
        data = request.get_json()
        if not data or 'value' not in data:
            return jsonify({
                'success': False,
                'error': 'Value is required in request body'
            }), 400
        
        new_value = data['value']
        
        logger.info(f"Admin {request.user.get('uid')} updating setting '{key}' to '{new_value}'")
        
        # Validate setting value
        is_valid, error_msg = validate_setting_value(key, new_value)
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Update setting
        updated_setting = update_setting(key, new_value)
        
        if not updated_setting:
            return jsonify({
                'success': False,
                'error': 'Failed to update setting'
            }), 500
        
        logger.info(f"Setting '{key}' updated successfully to '{new_value}'")
        
        return jsonify({
            'success': True,
            'message': 'Setting updated successfully',
            'data': updated_setting.to_dict(),
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to update setting: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to update setting'
        }), 500


@settings_bp.route('/thresholds', methods=['GET'])
@login_required
def get_thresholds():
    """
    Get all threshold configurations.
    
    Response (200 OK):
        {
            "success": true,
            "data": {
                "temperature": {
                    "max": float,
                    "min": float,
                    "warning_max": float,
                    "warning_min": float,
                    "unit": string
                },
                "humidity": {...},
                "methane": {...},
                "other_gases": {...}
            },
            "timestamp": string
        }
    
    Example:
        GET /api/settings/thresholds
    """
    try:
        logger.info(f"Fetching thresholds for user {request.user.get('uid')}")
        
        threshold_data = _format_threshold_settings()
        
        return jsonify({
            'success': True,
            'data': threshold_data,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch thresholds: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch thresholds'
        }), 500


@settings_bp.route('/thresholds', methods=['PUT'])
@admin_required
def update_thresholds():
    """
    Update threshold configurations (admin only).
    
    Request Body (JSON):
        {
            "TEMP_MAX": 36,
            "HUMIDITY_WARNING_MAX": 78,
            "METHANE_CRITICAL": 350,
            ...
        }
    
    Response (200 OK):
        {
            "success": true,
            "message": "Thresholds updated successfully",
            "updated_count": int,
            "data": {...}
        }
    
    Response (400 Bad Request):
        {
            "success": false,
            "error": "Invalid threshold values",
            "details": {...}
        }
    
    Example:
        PUT /api/settings/thresholds
        Body: {
            "TEMP_MAX": 36,
            "HUMIDITY_MAX": 85
        }
    """
    try:
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body is required'
            }), 400
        
        logger.info(f"Admin {request.user.get('uid')} updating thresholds: {list(data.keys())}")
        
        # Update each threshold
        updated_count = 0
        errors = {}
        
        for key, value in data.items():
            # Validate
            is_valid, error_msg = validate_setting_value(key, value)
            if not is_valid:
                errors[key] = error_msg
                continue
            
            # Update
            result = update_setting(key, value)
            if result:
                updated_count += 1
            else:
                errors[key] = "Failed to update"
        
        if errors:
            logger.warning(f"Some thresholds failed to update: {errors}")
            return jsonify({
                'success': False,
                'error': 'Some threshold updates failed',
                'updated_count': updated_count,
                'errors': errors
            }), 400
        
        logger.info(f"All {updated_count} thresholds updated successfully")
        
        # Return updated thresholds
        threshold_data = _format_threshold_settings()
        
        return jsonify({
            'success': True,
            'message': 'Thresholds updated successfully',
            'updated_count': updated_count,
            'data': threshold_data,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to update thresholds: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to update thresholds'
        }), 500


@settings_bp.route('/reset', methods=['POST'])
@admin_required
def reset_settings():
    """
    Reset all settings to default values (admin only).
    
    Response (200 OK):
        {
            "success": true,
            "message": "Settings reset to defaults",
            "reset_count": int
        }
    
    Example:
        POST /api/settings/reset
    """
    try:
        logger.warning(f"Admin {request.user.get('uid')} resetting all settings to defaults")
        
        # Reset all settings to defaults
        reset_count = 0
        for key, default_value in DEFAULT_SETTINGS.items():
            result = update_setting(key, default_value)
            if result:
                reset_count += 1
        
        logger.info(f"Reset {reset_count} settings to defaults")
        
        return jsonify({
            'success': True,
            'message': 'Settings reset to defaults',
            'reset_count': reset_count,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to reset settings: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to reset settings'
        }), 500


@settings_bp.route('/defaults', methods=['GET'])
@login_required
def get_default_settings():
    """
    Get default settings values (reference).
    
    Response (200 OK):
        {
            "success": true,
            "data": {
                "defaults": {
                    "TEMP_MAX": 35,
                    "HUMIDITY_MAX": 80,
                    ...
                }
            }
        }
    
    Example:
        GET /api/settings/defaults
    """
    try:
        return jsonify({
            'success': True,
            'data': {
                'defaults': DEFAULT_SETTINGS
            },
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Failed to fetch defaults: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch defaults'
        }), 500


# Error handlers for this blueprint
@settings_bp.errorhandler(401)
def unauthorized(error):
    """Handle 401 errors"""
    return jsonify({
        'success': False,
        'error': 'Authentication required',
        'code': 'UNAUTHORIZED'
    }), 401


@settings_bp.errorhandler(403)
def forbidden(error):
    """Handle 403 errors"""
    return jsonify({
        'success': False,
        'error': 'Admin access required',
        'code': 'FORBIDDEN',
        'message': 'You do not have permission to modify settings'
    }), 403


@settings_bp.errorhandler(500)
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
    print("Settings Routes Module")
    print("=" * 50)
    print("Endpoints:")
    print("- GET  /api/settings - Get all settings")
    print("- GET  /api/settings/<key> - Get specific setting")
    print("- PUT  /api/settings/<key> - Update setting (admin)")
    print("- GET  /api/settings/thresholds - Get thresholds")
    print("- PUT  /api/settings/thresholds - Update thresholds (admin)")
    print("- POST /api/settings/reset - Reset to defaults (admin)")
    print("- GET  /api/settings/defaults - Get default values")
    print("\nAuthentication: Firebase Auth token required")
    print("Admin required for PUT/POST operations")