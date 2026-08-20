"""
Alert Service
=============
Threshold monitoring and alert generation service.

This service monitors sensor readings and generates alerts when values
exceed configured thresholds. Alerts are categorized by severity:
- INFO: Minor deviations, informational only
- WARNING: Attention needed, not critical
- CRITICAL: Immediate action required

Flow:
    Sensor Reading → check_thresholds() → Create Alerts → Trigger Notifications
    
Functions:
- check_thresholds(reading): Main threshold checking function
- create_alert(sensor_type, alert_type, message, value, threshold): Create alert
- resolve_alert(alert_id): Mark alert as resolved
- get_active_alerts(): Get all unresolved alerts
- get_unresolved_alerts(): Alias for get_active_alerts
- auto_resolve_old_alerts(days): Auto-resolve alerts older than X days
"""

from typing import List, Dict, Any, Optional, Union

from datetime import datetime, timedelta

from models import SensorReading, Alert
from utils.thresholds import (
    TEMP_MAX, TEMP_MIN, TEMP_WARNING_MAX, TEMP_WARNING_MIN,
    HUMIDITY_MAX, HUMIDITY_MIN, HUMIDITY_WARNING_MAX, HUMIDITY_WARNING_MIN,
    METHANE_CRITICAL, METHANE_WARNING,
    OTHER_GASES_CRITICAL, OTHER_GASES_WARNING,
    is_critical, is_warning, get_alert_type, get_status_message,
    ALERT_TYPE_INFO, ALERT_TYPE_WARNING, ALERT_TYPE_CRITICAL
)
from utils.logger import setup_logger
from .firestore_service import save_alert, get_recent_alerts, update_alert_status, get_setting

# Initialize logger
logger = setup_logger(__name__)


def check_thresholds(reading: Union[SensorReading, Dict[str, Any]]) -> List[Alert]:
    """
    Check sensor reading against all thresholds and generate alerts.

    Args:
        reading: Either a SensorReading object or a dict with keys:
                 temperature, humidity, methane, other_gases, timestamp, etc.

    Returns:
        List of Alert objects created (may be empty if no thresholds exceeded)
    """
    try:
        # Normalize input: support both SensorReading and dict
        if isinstance(reading, SensorReading):
            temperature = reading.temperature
            humidity = reading.humidity
            methane = reading.methane
            other_gases = reading.other_gases
            reading_repr = repr(reading)
        else:
            # assume dict-like
            temperature = reading.get('temperature')
            humidity = reading.get('humidity')
            methane = reading.get('methane')
            other_gases = reading.get('other_gases')
            reading_repr = f"dict({reading})"

        logger.info(f"Checking thresholds for reading: {reading_repr}")
        
        alerts_created: List[Alert] = []
        
        # Get dynamic thresholds from settings (fallback to constants)
        temp_max = _get_threshold_value('temp_max', TEMP_MAX)
        temp_min = _get_threshold_value('temp_min', TEMP_MIN)
        temp_warning_max = _get_threshold_value('temp_warning_max', TEMP_WARNING_MAX)
        temp_warning_min = _get_threshold_value('temp_warning_min', TEMP_WARNING_MIN)
        
        humidity_max = _get_threshold_value('humidity_max', HUMIDITY_MAX)
        humidity_min = _get_threshold_value('humidity_min', HUMIDITY_MIN)
        humidity_warning_max = _get_threshold_value('humidity_warning_max', HUMIDITY_WARNING_MAX)
        humidity_warning_min = _get_threshold_value('humidity_warning_min', HUMIDITY_WARNING_MIN)
        
        methane_critical = _get_threshold_value('methane_critical', METHANE_CRITICAL)
        methane_warning = _get_threshold_value('methane_warning', METHANE_WARNING)
        
        other_gases_critical = _get_threshold_value('other_gases_critical', OTHER_GASES_CRITICAL)
        other_gases_warning = _get_threshold_value('other_gases_warning', OTHER_GASES_WARNING)
        
        # 🔥 Use normalized vars instead of reading.temperature etc.

        # Check Temperature
        if temperature is not None:
            temp_alert = _check_temperature_threshold(
                temperature,
                temp_max, temp_min,
                temp_warning_max, temp_warning_min
            )
            if temp_alert:
                alerts_created.append(temp_alert)
        
        # Check Humidity
        if humidity is not None:
            humidity_alert = _check_humidity_threshold(
                humidity,
                humidity_max, humidity_min,
                humidity_warning_max, humidity_warning_min
            )
            if humidity_alert:
                alerts_created.append(humidity_alert)
        
        # Check Methane
        if methane is not None:
            methane_alert = _check_methane_threshold(
                methane,
                methane_critical,
                methane_warning
            )
            if methane_alert:
                alerts_created.append(methane_alert)
        
        # Check Other Gases
        if other_gases is not None:
            gases_alert = _check_other_gases_threshold(
                other_gases,
                other_gases_critical,
                other_gases_warning
            )
            if gases_alert:
                alerts_created.append(gases_alert)
        
        # Save all alerts to Firestore
        for alert in alerts_created:
            try:
                doc_id = save_alert(alert)
                alert.doc_id = doc_id
                logger.info(f"Alert created: {alert.alert_type} - {alert.sensor_type} (ID: {doc_id})")
            except Exception as e:
                logger.error(f"Failed to save alert: {str(e)}", exc_info=True)
        
        if alerts_created:
            logger.warning(f"Created {len(alerts_created)} alert(s) for reading")
        else:
            logger.info("No threshold violations detected")
        
        return alerts_created
        
    except Exception as e:
        logger.error(f"Error checking thresholds: {str(e)}", exc_info=True)
        return []



def _get_threshold_value(key: str, default: float) -> float:
    """
    Get threshold value from settings or use default.
    
    Args:
        key: Setting key
        default: Default value if setting not found
        
    Returns:
        Threshold value
    """
    try:
        setting = get_setting(key)
        if setting:
            return setting.get_value_as_float() or default
        return default
    except Exception as e:
        logger.warning(f"Failed to get threshold {key}, using default: {default}")
        return default


def _check_temperature_threshold(
    temperature: float,
    temp_max: float,
    temp_min: float,
    temp_warning_max: float,
    temp_warning_min: float
) -> Optional[Alert]:
    """
    Check temperature against thresholds.
    
    Args:
        temperature: Current temperature value
        temp_max: Critical maximum threshold
        temp_min: Critical minimum threshold
        temp_warning_max: Warning maximum threshold
        temp_warning_min: Warning minimum threshold
        
    Returns:
        Alert object if threshold exceeded, None otherwise
    """
    try:
        # Check critical high
        if temperature > temp_max:
            message = f"CRITICAL: Temperature too high ({temperature}°C exceeds {temp_max}°C)"
            logger.warning(message)
            return Alert(
                sensor_type='temperature',
                alert_type=ALERT_TYPE_CRITICAL,
                message=message,
                value=temperature,
                threshold=temp_max
            )
        
        # Check critical low
        if temperature < temp_min:
            message = f"CRITICAL: Temperature too low ({temperature}°C below {temp_min}°C)"
            logger.warning(message)
            return Alert(
                sensor_type='temperature',
                alert_type=ALERT_TYPE_CRITICAL,
                message=message,
                value=temperature,
                threshold=temp_min
            )
        
        # Check warning high
        if temperature > temp_warning_max:
            message = f"WARNING: Temperature high ({temperature}°C exceeds {temp_warning_max}°C)"
            logger.info(message)
            return Alert(
                sensor_type='temperature',
                alert_type=ALERT_TYPE_WARNING,
                message=message,
                value=temperature,
                threshold=temp_warning_max
            )
        
        # Check warning low
        if temperature < temp_warning_min:
            message = f"WARNING: Temperature low ({temperature}°C below {temp_warning_min}°C)"
            logger.info(message)
            return Alert(
                sensor_type='temperature',
                alert_type=ALERT_TYPE_WARNING,
                message=message,
                value=temperature,
                threshold=temp_warning_min
            )
        
        return None
        
    except Exception as e:
        logger.error(f"Error checking temperature threshold: {str(e)}")
        return None


def _check_humidity_threshold(
    humidity: float,
    humidity_max: float,
    humidity_min: float,
    humidity_warning_max: float,
    humidity_warning_min: float
) -> Optional[Alert]:
    """
    Check humidity against thresholds.
    
    Args:
        humidity: Current humidity value
        humidity_max: Critical maximum threshold
        humidity_min: Critical minimum threshold
        humidity_warning_max: Warning maximum threshold
        humidity_warning_min: Warning minimum threshold
        
    Returns:
        Alert object if threshold exceeded, None otherwise
    """
    try:
        # Check critical high
        if humidity > humidity_max:
            message = f"CRITICAL: Humidity too high ({humidity}% exceeds {humidity_max}%)"
            logger.warning(message)
            return Alert(
                sensor_type='humidity',
                alert_type=ALERT_TYPE_CRITICAL,
                message=message,
                value=humidity,
                threshold=humidity_max
            )
        
        # Check critical low
        if humidity < humidity_min:
            message = f"CRITICAL: Humidity too low ({humidity}% below {humidity_min}%)"
            logger.warning(message)
            return Alert(
                sensor_type='humidity',
                alert_type=ALERT_TYPE_CRITICAL,
                message=message,
                value=humidity,
                threshold=humidity_min
            )
        
        # Check warning high
        if humidity > humidity_warning_max:
            message = f"WARNING: Humidity high ({humidity}% exceeds {humidity_warning_max}%)"
            logger.info(message)
            return Alert(
                sensor_type='humidity',
                alert_type=ALERT_TYPE_WARNING,
                message=message,
                value=humidity,
                threshold=humidity_warning_max
            )
        
        # Check warning low
        if humidity < humidity_warning_min:
            message = f"WARNING: Humidity low ({humidity}% below {humidity_warning_min}%)"
            logger.info(message)
            return Alert(
                sensor_type='humidity',
                alert_type=ALERT_TYPE_WARNING,
                message=message,
                value=humidity,
                threshold=humidity_warning_min
            )
        
        return None
        
    except Exception as e:
        logger.error(f"Error checking humidity threshold: {str(e)}")
        return None


def _check_methane_threshold(
    methane: int,
    methane_critical: int,
    methane_warning: int
) -> Optional[Alert]:
    """
    Check methane level against thresholds.
    
    Args:
        methane: Current methane level
        methane_critical: Critical threshold
        methane_warning: Warning threshold
        
    Returns:
        Alert object if threshold exceeded, None otherwise
    """
    try:
        # Check critical
        if methane > methane_critical:
            message = f"CRITICAL: Methane level too high ({methane} ppm exceeds {methane_critical} ppm)"
            logger.warning(message)
            return Alert(
                sensor_type='methane',
                alert_type=ALERT_TYPE_CRITICAL,
                message=message,
                value=float(methane),
                threshold=float(methane_critical)
            )
        
        # Check warning
        if methane > methane_warning:
            message = f"WARNING: Methane level elevated ({methane} ppm exceeds {methane_warning} ppm)"
            logger.info(message)
            return Alert(
                sensor_type='methane',
                alert_type=ALERT_TYPE_WARNING,
                message=message,
                value=float(methane),
                threshold=float(methane_warning)
            )
        
        return None
        
    except Exception as e:
        logger.error(f"Error checking methane threshold: {str(e)}")
        return None


def _check_other_gases_threshold(
    other_gases: int,
    other_gases_critical: int,
    other_gases_warning: int
) -> Optional[Alert]:
    """
    Check other gases level against thresholds.
    
    Args:
        other_gases: Current other gases level
        other_gases_critical: Critical threshold
        other_gases_warning: Warning threshold
        
    Returns:
        Alert object if threshold exceeded, None otherwise
    """
    try:
        # Check critical
        if other_gases > other_gases_critical:
            message = f"CRITICAL: Other gases level too high ({other_gases} exceeds {other_gases_critical})"
            logger.warning(message)
            return Alert(
                sensor_type='other_gases',
                alert_type=ALERT_TYPE_CRITICAL,
                message=message,
                value=float(other_gases),
                threshold=float(other_gases_critical)
            )
        
        # Check warning
        if other_gases > other_gases_warning:
            message = f"WARNING: Other gases level elevated ({other_gases} exceeds {other_gases_warning})"
            logger.info(message)
            return Alert(
                sensor_type='other_gases',
                alert_type=ALERT_TYPE_WARNING,
                message=message,
                value=float(other_gases),
                threshold=float(other_gases_warning)
            )
        
        return None
        
    except Exception as e:
        logger.error(f"Error checking other gases threshold: {str(e)}")
        return None


def create_alert(
    sensor_type: str,
    alert_type: str,
    message: str,
    value: float,
    threshold: float
) -> Optional[Alert]:
    """
    Manually create and save an alert.
    
    Useful for creating custom alerts or alerts from external sources.
    
    Args:
        sensor_type: Sensor that triggered alert (temperature, humidity, methane, other_gases)
        alert_type: Alert severity (info, warning, critical)
        message: Human-readable alert message
        value: Current sensor value
        threshold: Threshold that was exceeded
        
    Returns:
        Alert object with doc_id, or None if save failed
        
    Example:
        >>> alert = create_alert(
        ...     sensor_type='temperature',
        ...     alert_type='critical',
        ...     message='Temperature critical',
        ...     value=40.0,
        ...     threshold=35.0
        ... )
    """
    try:
        logger.info(f"Creating manual alert: {alert_type} - {sensor_type}")
        
        alert = Alert(
            sensor_type=sensor_type,
            alert_type=alert_type,
            message=message,
            value=value,
            threshold=threshold
        )
        
        doc_id = save_alert(alert)
        alert.doc_id = doc_id
        
        logger.info(f"Alert created successfully with ID: {doc_id}")
        return alert
        
    except Exception as e:
        logger.error(f"Failed to create alert: {str(e)}", exc_info=True)
        return None


def resolve_alert(alert_id: str) -> bool:
    """
    Mark an alert as resolved.
    
    Admin users can manually resolve alerts to acknowledge them.
    
    Args:
        alert_id: Document ID of the alert to resolve
        
    Returns:
        True if successfully resolved, False otherwise
        
    Example:
        >>> resolve_alert('alert_doc_id_123')
        True
    """
    try:
        logger.info(f"Resolving alert: {alert_id}")
        
        success = update_alert_status(alert_id, is_resolved=True)
        
        if success:
            logger.info(f"Alert {alert_id} resolved successfully")
        else:
            logger.warning(f"Failed to resolve alert {alert_id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error resolving alert {alert_id}: {str(e)}", exc_info=True)
        return False


def get_active_alerts() -> List[Alert]:
    """
    Get all active (unresolved) alerts.
    
    Returns:
        List of unresolved Alert objects, ordered by created_at (newest first)
        
    Example:
        >>> active_alerts = get_active_alerts()
        >>> print(f"Active alerts: {len(active_alerts)}")
    """
    try:
        logger.info("Fetching active alerts")
        
        alerts = get_recent_alerts(limit=100, unresolved_only=True)
        
        logger.info(f"Found {len(alerts)} active alerts")
        return alerts
        
    except Exception as e:
        logger.error(f"Error fetching active alerts: {str(e)}", exc_info=True)
        return []


def get_unresolved_alerts() -> List[Alert]:
    """
    Alias for get_active_alerts().
    
    Returns:
        List of unresolved Alert objects
    """
    return get_active_alerts()


def auto_resolve_old_alerts(days: int = 7) -> int:
    """
    Automatically resolve alerts older than specified days.
    
    Useful for cleanup of old unresolved alerts.
    
    Args:
        days: Age threshold in days (default: 7)
        
    Returns:
        Number of alerts resolved
        
    Example:
        >>> # Resolve all alerts older than 7 days
        >>> count = auto_resolve_old_alerts(7)
        >>> print(f"Resolved {count} old alerts")
    """
    try:
        logger.info(f"Auto-resolving alerts older than {days} days")
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Get unresolved alerts
        alerts = get_active_alerts()
        
        resolved_count = 0
        for alert in alerts:
            if alert.created_at and alert.created_at < cutoff_date:
                if resolve_alert(alert.doc_id):
                    resolved_count += 1
        
        logger.info(f"Auto-resolved {resolved_count} alerts")
        return resolved_count
        
    except Exception as e:
        logger.error(f"Error auto-resolving alerts: {str(e)}", exc_info=True)
        return 0


def get_alerts_by_severity(severity: str, limit: int = 50) -> List[Alert]:
    """
    Get alerts filtered by severity level.
    
    Args:
        severity: Alert type (info, warning, critical)
        limit: Maximum number of alerts to return
        
    Returns:
        List of Alert objects matching severity
        
    Example:
        >>> critical_alerts = get_alerts_by_severity('critical', limit=20)
        >>> for alert in critical_alerts:
        ...     print(f"{alert.sensor_type}: {alert.message}")
    """
    try:
        logger.info(f"Fetching {severity} alerts")
        
        all_alerts = get_recent_alerts(limit=limit * 2)  # Fetch more, then filter
        
        filtered_alerts = [
            alert for alert in all_alerts 
            if alert.alert_type == severity
        ][:limit]
        
        logger.info(f"Found {len(filtered_alerts)} {severity} alerts")
        return filtered_alerts
        
    except Exception as e:
        logger.error(f"Error fetching alerts by severity: {str(e)}", exc_info=True)
        return []


def get_alert_summary() -> Dict[str, Any]:
    """
    Get summary statistics of current alerts.
    
    Returns:
        Dictionary with alert counts and statistics
        
    Example:
        >>> summary = get_alert_summary()
        >>> print(f"Total active: {summary['active_count']}")
        >>> print(f"Critical: {summary['by_severity']['critical']}")
    """
    try:
        logger.info("Generating alert summary")
        
        active_alerts = get_active_alerts()
        
        summary = {
            'active_count': len(active_alerts),
            'by_severity': {
                'critical': 0,
                'warning': 0,
                'info': 0
            },
            'by_sensor': {
                'temperature': 0,
                'humidity': 0,
                'methane': 0,
                'other_gases': 0
            },
            'oldest_alert_age_minutes': 0
        }
        
        for alert in active_alerts:
            # Count by severity
            if alert.alert_type in summary['by_severity']:
                summary['by_severity'][alert.alert_type] += 1
            
            # Count by sensor
            if alert.sensor_type in summary['by_sensor']:
                summary['by_sensor'][alert.sensor_type] += 1
        
        # Calculate oldest alert age
        if active_alerts:
            oldest_alert = min(active_alerts, key=lambda a: a.created_at or datetime.utcnow())
            age = oldest_alert.get_age_minutes()
            summary['oldest_alert_age_minutes'] = age
        
        logger.info(f"Alert summary: {summary['active_count']} active alerts")
        return summary
        
    except Exception as e:
        logger.error(f"Error generating alert summary: {str(e)}", exc_info=True)
        return {
            'active_count': 0,
            'by_severity': {'critical': 0, 'warning': 0, 'info': 0},
            'by_sensor': {'temperature': 0, 'humidity': 0, 'methane': 0, 'other_gases': 0},
            'error': str(e)
        }