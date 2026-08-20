"""
Arduino Data Handler Service
=============================
Processes incoming sensor data from Arduino hardware.

This service handles the complete data ingestion pipeline:
1. Validate incoming JSON data
2. Check sensor value ranges
3. Calculate exhaust fan status based on methane level
4. Save sensor reading to Firestore
5. Return confirmation and fan control instruction to Arduino

Flow:
    Arduino → POST /api/arduino/data → arduino_handler → Firestore
                                     ↓
                          Response: {status, exhaust_fan, alerts}

Functions:
- process_sensor_data(data): Main processing function
- validate_arduino_data(data): Validate incoming data
- calculate_exhaust_fan(methane): Determine fan status
"""

from typing import Dict, Any, Tuple
from datetime import datetime

from models import SensorReading
from utils.validators import validate_sensor_reading_dict
from utils.thresholds import should_activate_exhaust_fan, METHANE_EXHAUST_FAN_THRESHOLD
from utils.logger import setup_logger
from .firestore_service import save_sensor_reading

# Initialize logger
logger = setup_logger(__name__)


def validate_arduino_data(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate incoming Arduino sensor data.
    
    Checks that all required fields are present and values are within
    acceptable ranges.
    
    Args:
        data: Dictionary with sensor data
              Expected keys: temperature, humidity, methane, other_gases
              
    Returns:
        Tuple of (is_valid: bool, error_message: str)
        
    Example:
        >>> data = {"temperature": 25.5, "humidity": 65, "methane": 150, "other_gases": 180}
        >>> is_valid, error = validate_arduino_data(data)
        >>> if is_valid:
        ...     print("Data is valid")
    """
    try:
        logger.debug(f"Validating Arduino data: {data}")
        
        # Check if data is a dictionary
        if not isinstance(data, dict):
            return False, "Data must be a JSON object"
        
        # Use validator from utils
        is_valid, error = validate_sensor_reading_dict(data)
        
        if not is_valid:
            logger.warning(f"Arduino data validation failed: {error}")
            return False, error
        
        logger.debug("Arduino data validation passed")
        return True, ""
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}", exc_info=True)
        return False, f"Validation error: {str(e)}"


def calculate_exhaust_fan(methane_level: int) -> bool:
    """
    Calculate if exhaust fan should be activated.
    
    The fan is activated when methane level reaches or exceeds the threshold
    (default: 200 ppm) to ensure safe air quality.
    
    Args:
        methane_level: Current methane level in ppm (0-1023)
        
    Returns:
        True if fan should be ON, False if fan should be OFF
        
    Example:
        >>> calculate_exhaust_fan(250)
        True
        >>> calculate_exhaust_fan(150)
        False
    """
    try:
        fan_status = should_activate_exhaust_fan(methane_level)
        
        if fan_status:
            logger.info(f"Exhaust fan activated: methane={methane_level} ppm (threshold={METHANE_EXHAUST_FAN_THRESHOLD})")
        else:
            logger.debug(f"Exhaust fan off: methane={methane_level} ppm")
        
        return fan_status
        
    except Exception as e:
        logger.error(f"Error calculating exhaust fan status: {str(e)}", exc_info=True)
        # Default to OFF in case of error (safer)
        return False


def process_sensor_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process incoming sensor data from Arduino.
    
    This is the main entry point for Arduino data ingestion.
    
    Steps:
    1. Validate data format and ranges
    2. Create SensorReading object
    3. Calculate exhaust fan status
    4. Save to Firestore
    5. Return response with fan control instruction
    
    Args:
        data: Dictionary with sensor data
              Required keys: temperature, humidity, methane, other_gases
              Optional keys: exhaust_fan (will be calculated if not provided)
              
    Returns:
        Dictionary with response data:
        {
            'success': True/False,
            'message': 'Status message',
            'reading': {sensor data dict},
            'exhaust_fan': True/False,
            'timestamp': ISO timestamp,
            'reading_id': Firestore document ID (if saved)
        }
        
    Raises:
        ValueError: If data validation fails
        Exception: If database save fails
        
    Example:
        >>> data = {
        ...     "temperature": 28.5,
        ...     "humidity": 62.0,
        ...     "methane": 180,
        ...     "other_gases": 220
        ... }
        >>> result = process_sensor_data(data)
        >>> print(f"Exhaust fan: {'ON' if result['exhaust_fan'] else 'OFF'}")
    """
    try:
        logger.info("Processing Arduino sensor data")
        logger.debug(f"Raw data received: {data}")
        
        # Step 1: Validate incoming data
        is_valid, error_message = validate_arduino_data(data)
        
        if not is_valid:
            logger.warning(f"Arduino data rejected: {error_message}")
            return {
                'success': False,
                'message': error_message,
                'error': 'validation_failed',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        # Step 2: Extract sensor values
        temperature = float(data['temperature'])
        humidity = float(data['humidity'])
        methane = int(data['methane'])
        other_gases = int(data['other_gases'])
        
        logger.info(
            f"Sensor values - Temp: {temperature}°C, Humidity: {humidity}%, "
            f"Methane: {methane} ppm, Other gases: {other_gases}"
        )
        
        # Step 3: Calculate exhaust fan status
        exhaust_fan = calculate_exhaust_fan(methane)
        
        # Step 4: Create SensorReading object
        reading = SensorReading(
            temperature=temperature,
            humidity=humidity,
            methane=methane,
            other_gases=other_gases,
            exhaust_fan=exhaust_fan,
            timestamp=datetime.utcnow()
        )
        
        # Validate reading (double-check)
        is_valid, validation_error = reading.validate()
        if not is_valid:
            logger.error(f"SensorReading validation failed: {validation_error}")
            return {
                'success': False,
                'message': validation_error,
                'error': 'validation_failed',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        # Step 5: Save to Firestore
        try:
            doc_id = save_sensor_reading(reading)
            logger.info(f"Sensor reading saved successfully with ID: {doc_id}")
        except Exception as save_error:
            logger.error(f"Failed to save sensor reading: {str(save_error)}", exc_info=True)
            return {
                'success': False,
                'message': 'Failed to save sensor data to database',
                'error': 'database_error',
                'timestamp': datetime.utcnow().isoformat()
            }
        
        # Step 6: Build response for Arduino
        response = {
            'success': True,
            'message': 'Sensor data processed successfully',
            'reading': {
                'temperature': reading.temperature,
                'humidity': reading.humidity,
                'methane': reading.methane,
                'other_gases': reading.other_gases,
                'air_quality': reading.get_air_quality_status()
            },
            'exhaust_fan': exhaust_fan,
            'timestamp': reading.timestamp.isoformat(),
            'reading_id': doc_id,   # <-- key expected by routes.arduino
            'doc_id': doc_id        # <-- kept for backwards compatibility (optional)
        }
        
        logger.info(f"Arduino data processing completed successfully. Fan: {'ON' if exhaust_fan else 'OFF'}")
        return response
        
    except KeyError as e:
        logger.error(f"Missing required field: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f'Missing required field: {str(e)}',
            'error': 'missing_field',
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except ValueError as e:
        logger.error(f"Invalid data type: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': f'Invalid data type: {str(e)}',
            'error': 'invalid_type',
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Unexpected error processing Arduino data: {str(e)}", exc_info=True)
        return {
            'success': False,
            'message': 'Internal server error',
            'error': 'server_error',
            'details': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }


def get_data_quality_report(reading: SensorReading) -> Dict[str, Any]:
    """
    Generate a data quality report for a sensor reading.
    
    Useful for debugging and monitoring sensor health.
    
    Args:
        reading: SensorReading object
        
    Returns:
        Dictionary with quality indicators
        
    Example:
        >>> reading = SensorReading(temperature=25, humidity=65, methane=150, other_gases=180)
        >>> report = get_data_quality_report(reading)
        >>> print(f"Data quality: {report['overall_quality']}")
    """
    try:
        report = {
            'timestamp': reading.timestamp.isoformat() if reading.timestamp else None,
            'values': {
                'temperature': reading.temperature,
                'humidity': reading.humidity,
                'methane': reading.methane,
                'other_gases': reading.other_gases
            },
            'validation': {
                'is_valid': reading.validate()[0],
                'error': reading.validate()[1] or None
            },
            'air_quality': reading.get_air_quality_status(),
            'exhaust_fan': reading.exhaust_fan,
            'warnings': []
        }
        
        # Check for unusual values (not invalid, but unusual)
        if reading.temperature < 10 or reading.temperature > 50:
            report['warnings'].append(f"Unusual temperature: {reading.temperature}°C")
        
        if reading.humidity < 20 or reading.humidity > 95:
            report['warnings'].append(f"Unusual humidity: {reading.humidity}%")
        
        if reading.methane > METHANE_EXHAUST_FAN_THRESHOLD:
            report['warnings'].append(f"Elevated methane: {reading.methane} ppm")
        
        # Overall quality score
        if not report['validation']['is_valid']:
            report['overall_quality'] = 'INVALID'
        elif report['warnings']:
            report['overall_quality'] = 'FAIR'
        else:
            report['overall_quality'] = 'GOOD'
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating data quality report: {str(e)}", exc_info=True)
        return {
            'error': str(e),
            'overall_quality': 'UNKNOWN'
        }


def format_arduino_response(success: bool, exhaust_fan: bool, message: str = "") -> str:
    """
    Format response for Arduino in simple string format.
    
    Arduino may prefer a simpler response format than JSON.
    
    Args:
        success: Whether processing was successful
        exhaust_fan: Fan status (True = ON, False = OFF)
        message: Optional status message
        
    Returns:
        Formatted string response
        
    Example:
        >>> response = format_arduino_response(True, True, "Data saved")
        >>> print(response)
        OK:FAN_ON:Data saved
    """
    try:
        status = "OK" if success else "ERROR"
        fan = "FAN_ON" if exhaust_fan else "FAN_OFF"
        
        if message:
            return f"{status}:{fan}:{message}"
        else:
            return f"{status}:{fan}"
            
    except Exception as e:
        logger.error(f"Error formatting Arduino response: {str(e)}", exc_info=True)
        return "ERROR:FAN_OFF:Response formatting failed"


def batch_process_readings(readings_data: list) -> Dict[str, Any]:
    """
    Process multiple sensor readings in batch.
    
    Useful for cases where Arduino sends buffered data.
    
    Args:
        readings_data: List of sensor data dictionaries
        
    Returns:
        Dictionary with batch processing results
        
    Example:
        >>> batch_data = [
        ...     {"temperature": 25, "humidity": 65, "methane": 150, "other_gases": 180},
        ...     {"temperature": 26, "humidity": 63, "methane": 155, "other_gases": 175}
        ... ]
        >>> result = batch_process_readings(batch_data)
        >>> print(f"Processed: {result['successful']}/{result['total']}")
    """
    try:
        logger.info(f"Batch processing {len(readings_data)} readings")
        
        results = {
            'total': len(readings_data),
            'successful': 0,
            'failed': 0,
            'readings': [],
            'errors': []
        }
        
        for i, data in enumerate(readings_data):
            try:
                result = process_sensor_data(data)
                
                if result['success']:
                    results['successful'] += 1
                    results['readings'].append(result)
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'index': i,
                        'error': result.get('message', 'Unknown error'),
                        'data': data
                    })
                    
            except Exception as e:
                logger.error(f"Error processing reading {i}: {str(e)}")
                results['failed'] += 1
                results['errors'].append({
                    'index': i,
                    'error': str(e),
                    'data': data
                })
        
        logger.info(f"Batch processing completed: {results['successful']}/{results['total']} successful")
        return results
        
    except Exception as e:
        logger.error(f"Batch processing failed: {str(e)}", exc_info=True)
        return {
            'total': len(readings_data) if isinstance(readings_data, list) else 0,
            'successful': 0,
            'failed': len(readings_data) if isinstance(readings_data, list) else 0,
            'error': str(e)
        }