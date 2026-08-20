"""
Arduino Routes
==============
API endpoints for Arduino sensor data submission.

Endpoints:
- POST /api/arduino/data - Receive and process sensor data from Arduino

Security:
- Uses API key authentication (ARDUINO_API_KEY)
- No Firebase Auth required for Arduino device
"""

import os
from flask import Blueprint, request, jsonify
from datetime import datetime

from utils.logger import setup_logger
from services.arduino_handler import process_sensor_data
from services.alert_service import check_thresholds
from services.notification_service import send_alert_notification

logger = setup_logger(__name__)

# Create Blueprint
arduino_bp = Blueprint('arduino', __name__, url_prefix='/api/arduino')

# Arduino API Key for authentication
ARDUINO_API_KEY = os.getenv('ARDUINO_API_KEY', 'cropverse_arduino_default_key')
TESTING_MODE = os.getenv('TESTING_MODE', 'false').lower() == 'true'


def verify_arduino_api_key():
    """
    Verify Arduino API key from request header.
    Skip verification if TESTING_MODE is enabled.
    
    Returns:
        Tuple of (is_valid: bool, error_response: dict or None)
    """
    # Skip API key check in testing mode
    if TESTING_MODE:
        logger.info("Testing mode enabled - skipping API key check")
        return True, None
    
    # Production mode - verify API key
    api_key = request.headers.get('X-API-Key')
    
    if not api_key:
        logger.warning("Arduino request missing API key")
        return False, {'error': 'Missing API key', 'code': 'MISSING_API_KEY'}
    
    if api_key != ARDUINO_API_KEY:
        logger.warning(f"Arduino request with invalid API key: {api_key[:10]}...")
        return False, {'error': 'Invalid API key', 'code': 'INVALID_API_KEY'}
    
    return True, None


@arduino_bp.route('/data', methods=['POST'])
def receive_sensor_data():
    """
    ... (docstring unchanged)
    """
    try:
        # Verify API key
        is_valid, error_response = verify_arduino_api_key()
        if not is_valid:
            return jsonify(error_response), 401
        
        # Get request data
        data = request.get_json()
        if not data:
            logger.warning("Arduino request with empty body")
            return jsonify({
                'error': 'Request body is required',
                'code': 'EMPTY_BODY'
            }), 400
        
        logger.info(
            "Received Arduino data: temp=%s, humidity=%s, methane=%s",
            data.get('temperature'),
            data.get('humidity'),
            data.get('methane')
        )
        
        # Process sensor data (validate, save to Firestore)
        result = process_sensor_data(data)
        
        if not result.get('success'):
            logger.error(f"Failed to process sensor data: {result.get('error')}")
            return jsonify({
                'error': result.get('error', 'Unknown error'),
                'code': 'PROCESSING_FAILED',
                'details': result.get('validation_errors', {})
            }), 400
        
        # ⬇️ NOW TREAT `reading` AS A DICT
        reading = result['reading']          # dict, not object
        reading_id = result['reading_id']
        
        # Make timestamp safe for both datetime and string
        ts = reading.get('timestamp')
        if ts is None:
            timestamp_str = None
        elif hasattr(ts, 'isoformat'):
            # datetime-like
            timestamp_str = ts.isoformat()
        else:
            # assume already string
            timestamp_str = str(ts)
        
        # If process_sensor_data already calculated air_quality, use it
        air_quality = reading.get('air_quality')
        
        # Check thresholds and generate alerts (now expects dict)
        alerts = check_thresholds(reading)
        alerts_generated = len(alerts)
        
        if alerts_generated > 0:
            logger.info(f"Generated {alerts_generated} alerts from sensor reading")
            
            for alert in alerts:
                try:
                    notification_results = send_alert_notification(alert)
                    logger.info(
                        "Alert notification sent: email=%s, sms=%s",
                        notification_results.get('email'),
                        notification_results.get('sms')
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification for alert: {str(e)}")
                    # keep going even if notification fails
        
        # ⬇️ NOTE: exhaust_fan comes from the result dict
        exhaust_fan = result.get('exhaust_fan', reading.get('exhaust_fan', False))
        
        # Prepare response
        response = {
            'success': True,
            'message': 'Sensor data processed successfully',
            'exhaust_fan': exhaust_fan,             # Control instruction for Arduino
            'reading_id': reading_id,
            'alerts_generated': alerts_generated,
            'timestamp': timestamp_str,
            'air_quality': air_quality,
        }
        
        logger.info(
            "Arduino request processed successfully: reading_id=%s, fan=%s, alerts=%s",
            reading_id,
            exhaust_fan,
            alerts_generated
        )
        
        return jsonify(response), 200
        
    except ValueError as e:
        logger.warning(f"Validation error in Arduino request: {str(e)}")
        return jsonify({
            'error': str(e),
            'code': 'VALIDATION_ERROR'
        }), 400
        
    except Exception as e:
        logger.error(f"Unexpected error processing Arduino data: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR',
            'message': 'Failed to process sensor data. Please try again.'
        }), 500



@arduino_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for Arduino to verify API availability.
    
    Response (200 OK):
        {
            "status": "healthy",
            "service": "arduino-api",
            "timestamp": string
        }
    
    Example:
        GET /api/arduino/health
    """
    return jsonify({
        'status': 'healthy',
        'service': 'arduino-api',
        'timestamp': datetime.now().isoformat()
    }), 200


@arduino_bp.route('/test', methods=['POST'])
def test_connection():
    """
    Test endpoint for Arduino to verify authentication and connectivity.
    
    Request Headers:
        X-API-Key: Arduino API key
    
    Response (200 OK):
        {
            "success": true,
            "message": "Authentication successful",
            "timestamp": string
        }
    
    Response (401 Unauthorized):
        {
            "error": "Invalid API key",
            "code": "INVALID_API_KEY"
        }
    
    Example:
        POST /api/arduino/test
        Headers: X-API-Key: your_arduino_api_key
    """
    # Verify API key
    is_valid, error_response = verify_arduino_api_key()
    if not is_valid:
        return jsonify(error_response), 401
    
    logger.info("Arduino test connection successful")
    
    return jsonify({
        'success': True,
        'message': 'Authentication successful',
        'timestamp': datetime.now().isoformat()
    }), 200


# Error handlers for this blueprint
@arduino_bp.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'error': 'Endpoint not found',
        'code': 'NOT_FOUND'
    }), 404


@arduino_bp.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        'error': 'Method not allowed',
        'code': 'METHOD_NOT_ALLOWED',
        'allowed_methods': ['POST']
    }), 405


@arduino_bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}", exc_info=True)
    return jsonify({
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR'
    }), 500


# Module-level info
if __name__ == "__main__":
    print("Arduino Routes Module")
    print("=" * 50)
    print("Endpoints:")
    print("- POST /api/arduino/data - Receive sensor data")
    print("- GET  /api/arduino/health - Health check")
    print("- POST /api/arduino/test - Test authentication")
    print("\nAuthentication: X-API-Key header required")