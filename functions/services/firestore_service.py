"""
Firestore Service
=================
Common Firestore database operations used across the application.

This service provides abstracted CRUD operations for all collections,
reducing code duplication and ensuring consistent database access patterns.

Collections:
- sensor_readings: Raw sensor data from Arduino
- alerts: System alerts and warnings
- users: User accounts and profiles
- settings: System configuration
- analytics_summary: Pre-calculated daily analytics

Functions:
- get_latest_readings(limit): Fetch recent sensor readings
- get_recent_alerts(limit, unresolved_only): Fetch alerts
- get_setting(key): Get configuration setting
- update_setting(key, value): Update setting
- get_all_settings(): Get all settings
- get_user_by_email(email): Get user by email
- create_user(user): Create new user
- update_user(uid, data): Update user data
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import firestore

from models import SensorReading, Alert, User, Setting, AnalyticsSummary
from utils.logger import setup_logger

# Initialize logger
logger = setup_logger(__name__)

# Initialize Firestore client
try:
    db = firestore.client()
    logger.info("Firestore client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Firestore client: {str(e)}")
    db = None


from datetime import datetime
import email.utils

def _normalize_timestamp(ts):
    """Return a naive datetime or None for Firestore timestamps / strings."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        # Strip timezone info to make it naive
        return ts.replace(tzinfo=None) if ts.tzinfo else ts
    # Firestore Timestamp-like objects may provide to_datetime()
    if hasattr(ts, 'to_datetime'):
        try:
            dt = ts.to_datetime()
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except Exception:
            pass
    # Common string formats: ISO or RFC-2822 (e.g. 'Tue, 02 Dec 2025 13:07:58 GMT')
    if isinstance(ts, str):
        try:
            # handle ISO with trailing 'Z'
            dt = datetime.fromisoformat(ts.rstrip('Z'))
            return dt.replace(tzinfo=None) if dt.tzinfo else dt
        except Exception:
            try:
                dt = email.utils.parsedate_to_datetime(ts)
                return dt.replace(tzinfo=None) if dt.tzinfo else dt
            except Exception:
                return None
    return None


# ============================================================================
# SENSOR READINGS
# ============================================================================

def get_latest_readings(limit: int = 10) -> List[SensorReading]:
    """
    Get the most recent sensor readings.
    
    Args:
        limit: Maximum number of readings to return (default: 10)
        
    Returns:
        List of SensorReading objects, ordered by timestamp (newest first)
        
    Raises:
        Exception: If database query fails
        
    Example:
        >>> readings = get_latest_readings(5)
        >>> for reading in readings:
        ...     print(f"Temp: {reading.temperature}°C at {reading.timestamp}")
    """
    try:
        logger.info(f"Fetching latest {limit} sensor readings")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        # Query sensor_readings collection, ordered by timestamp DESC
        docs = db.collection('sensor_readings') \
                 .order_by('timestamp', direction=firestore.Query.DESCENDING) \
                 .limit(limit) \
                 .stream()
        
        readings = []
        for doc in docs:
            raw_data = doc.to_dict()
            # Normalize timestamp before creating SensorReading
            if 'timestamp' in raw_data:
                raw_data['timestamp'] = _normalize_timestamp(raw_data['timestamp'])
            reading = SensorReading.from_dict(raw_data, doc.id)
            readings.append(reading)
        
        logger.info(f"Successfully fetched {len(readings)} sensor readings")
        return readings
        
    except Exception as e:
        logger.error(f"Failed to fetch latest readings: {str(e)}", exc_info=True)
        raise


def get_readings_in_range(start_time: datetime, end_time: datetime) -> List[SensorReading]:
    """
    Get sensor readings within a time range.
    
    Args:
        start_time: Start of time range (inclusive)
        end_time: End of time range (inclusive)
        
    Returns:
        List of SensorReading objects within the time range
        
    Example:
        >>> from datetime import datetime, timedelta
        >>> end = datetime.utcnow()
        >>> start = end - timedelta(hours=24)
        >>> readings = get_readings_in_range(start, end)
    """
    try:
        logger.info(f"Fetching readings from {start_time} to {end_time}")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        docs = db.collection('sensor_readings') \
                 .where('timestamp', '>=', start_time) \
                 .where('timestamp', '<=', end_time) \
                 .order_by('timestamp') \
                 .stream()
        
        readings = []
        for doc in docs:
            raw_data = doc.to_dict()
            # Normalize timestamp before creating SensorReading
            if 'timestamp' in raw_data:
                raw_data['timestamp'] = _normalize_timestamp(raw_data['timestamp'])
            reading = SensorReading.from_dict(raw_data, doc.id)
            readings.append(reading)
        
        logger.info(f"Fetched {len(readings)} readings in time range")
        return readings
        
    except Exception as e:
        logger.error(f"Failed to fetch readings in range: {str(e)}", exc_info=True)
        raise


def save_sensor_reading(reading: SensorReading) -> str:
    """
    Save a sensor reading to Firestore.
    
    Args:
        reading: SensorReading object to save
        
    Returns:
        Document ID of the saved reading
        
    Example:
        >>> reading = SensorReading(temperature=25.5, humidity=65, methane=120, other_gases=180)
        >>> doc_id = save_sensor_reading(reading)
    """
    try:
        logger.info(f"Saving sensor reading: {reading}")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        # Add reading to collection
        doc_ref = db.collection('sensor_readings').add(reading.to_dict())
        doc_id = doc_ref[1].id
        
        logger.info(f"Sensor reading saved with ID: {doc_id}")
        return doc_id
        
    except Exception as e:
        logger.error(f"Failed to save sensor reading: {str(e)}", exc_info=True)
        raise


# ============================================================================
# ALERTS
# ============================================================================

def get_recent_alerts(limit: int = 50, unresolved_only: bool = False) -> List[Alert]:
    """
    Get recent alerts.
    
    Args:
        limit: Maximum number of alerts to return (default: 50)
        unresolved_only: If True, only return unresolved alerts (default: False)
        
    Returns:
        List of Alert objects, ordered by created_at (newest first)
        
    Example:
        >>> # Get all recent alerts
        >>> alerts = get_recent_alerts(limit=20)
        
        >>> # Get only unresolved alerts
        >>> active_alerts = get_recent_alerts(unresolved_only=True)
    """
    try:
        logger.info(f"Fetching alerts (limit={limit}, unresolved_only={unresolved_only})")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        # Build query
        query = db.collection('alerts')
        
        if unresolved_only:
            query = query.where('is_resolved', '==', False)
        
        query = query.order_by('created_at', direction=firestore.Query.DESCENDING) \
                     .limit(limit)
        
        docs = query.stream()
        
        alerts = []
        for doc in docs:
            alert = Alert.from_dict(doc.to_dict(), doc.id)
            alerts.append(alert)
        
        logger.info(f"Fetched {len(alerts)} alerts")
        return alerts
        
    except Exception as e:
        logger.error(f"Failed to fetch alerts: {str(e)}", exc_info=True)
        raise


def save_alert(alert: Alert) -> str:
    """
    Save an alert to Firestore.
    
    Args:
        alert: Alert object to save
        
    Returns:
        Document ID of the saved alert
        
    Example:
        >>> alert = Alert(
        ...     sensor_type='temperature',
        ...     alert_type='critical',
        ...     message='Temperature too high',
        ...     value=38.0,
        ...     threshold=35.0
        ... )
        >>> doc_id = save_alert(alert)
    """
    try:
        logger.info(f"Saving alert: {alert.alert_type} - {alert.sensor_type}")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        doc_ref = db.collection('alerts').add(alert.to_dict())
        doc_id = doc_ref[1].id
        
        logger.info(f"Alert saved with ID: {doc_id}")
        return doc_id
        
    except Exception as e:
        logger.error(f"Failed to save alert: {str(e)}", exc_info=True)
        raise


def update_alert_status(alert_id: str, is_resolved: bool) -> bool:
    """
    Update alert resolution status.
    
    Args:
        alert_id: Document ID of the alert
        is_resolved: New resolution status
        
    Returns:
        True if update successful
        
    Example:
        >>> # Resolve an alert
        >>> update_alert_status('alert_doc_id', True)
    """
    try:
        logger.info(f"Updating alert {alert_id} status to resolved={is_resolved}")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        update_data = {
            'is_resolved': is_resolved
        }
        
        if is_resolved:
            update_data['resolved_at'] = datetime.utcnow()
        
        db.collection('alerts').document(alert_id).update(update_data)
        
        logger.info(f"Alert {alert_id} status updated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update alert status: {str(e)}", exc_info=True)
        raise


# ============================================================================
# SETTINGS
# ============================================================================

def get_setting(key: str) -> Optional[Setting]:
    """
    Get a configuration setting by key.
    
    Args:
        key: Setting key (e.g., 'temp_max', 'email_enabled')
        
    Returns:
        Setting object if found, None otherwise
        
    Example:
        >>> setting = get_setting('temp_max')
        >>> if setting:
        ...     print(f"Max temperature: {setting.value}°C")
    """
    try:
        logger.info(f"Fetching setting: {key}")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        doc = db.collection('settings').document(key).get()
        
        if doc.exists:
            setting = Setting.from_dict(doc.to_dict(), doc.id)
            logger.info(f"Setting found: {key} = {setting.value}")
            return setting
        else:
            logger.warning(f"Setting not found: {key}")
            return None
        
    except Exception as e:
        logger.error(f"Failed to fetch setting {key}: {str(e)}", exc_info=True)
        raise


def update_setting(key: str, value: Any) -> bool:
    """
    Update a configuration setting.
    
    Args:
        key: Setting key
        value: New value
        
    Returns:
        True if update successful
        
    Example:
        >>> # Update temperature threshold
        >>> update_setting('temp_max', 40.0)
    """
    try:
        logger.info(f"Updating setting: {key} = {value}")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        db.collection('settings').document(key).set({
            'key': key,
            'value': value
        }, merge=True)
        
        logger.info(f"Setting {key} updated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update setting {key}: {str(e)}", exc_info=True)
        raise


def get_all_settings() -> Dict[str, Setting]:
    """
    Get all configuration settings.
    
    Returns:
        Dictionary mapping setting keys to Setting objects
        
    Example:
        >>> settings = get_all_settings()
        >>> temp_max = settings['temp_max'].value
        >>> humidity_max = settings['humidity_max'].value
    """
    try:
        logger.info("Fetching all settings")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        docs = db.collection('settings').stream()
        
        settings = {}
        for doc in docs:
            setting = Setting.from_dict(doc.to_dict(), doc.id)
            settings[setting.key] = setting
        
        logger.info(f"Fetched {len(settings)} settings")
        return settings
        
    except Exception as e:
        logger.error(f"Failed to fetch all settings: {str(e)}", exc_info=True)
        raise


# ============================================================================
# USERS
# ============================================================================

def get_user_by_email(email: str) -> Optional[User]:
    """
    Get user by email address.
    
    Args:
        email: User's email address
        
    Returns:
        User object if found, None otherwise
        
    Example:
        >>> user = get_user_by_email('admin@cropverse.com')
        >>> if user and user.is_admin():
        ...     print("User is admin")
    """
    try:
        logger.info(f"Fetching user by email: {email}")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        docs = db.collection('users').where('email', '==', email.lower()).limit(1).stream()
        
        for doc in docs:
            user = User.from_dict(doc.to_dict(), doc.id)
            logger.info(f"User found: {email}")
            return user
        
        logger.warning(f"User not found: {email}")
        return None
        
    except Exception as e:
        logger.error(f"Failed to fetch user by email: {str(e)}", exc_info=True)
        raise


def create_user(user: User) -> str:
    """
    Create a new user.
    
    Args:
        user: User object to create
        
    Returns:
        Document ID of the created user
        
    Example:
        >>> user = User(email='user@example.com', role='user', display_name='John Doe')
        >>> doc_id = create_user(user)
    """
    try:
        logger.info(f"Creating user: {user.email}")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        doc_ref = db.collection('users').add(user.to_dict())
        doc_id = doc_ref[1].id
        
        logger.info(f"User created with ID: {doc_id}")
        return doc_id
        
    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}", exc_info=True)
        raise


def update_user(uid: str, data: Dict[str, Any]) -> bool:
    """
    Update user data.
    
    Args:
        uid: User document ID
        data: Dictionary of fields to update
        
    Returns:
        True if update successful
        
    Example:
        >>> update_user('user_doc_id', {'display_name': 'Jane Doe', 'phone_number': '+1234567890'})
    """
    try:
        logger.info(f"Updating user: {uid}")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        db.collection('users').document(uid).update(data)
        
        logger.info(f"User {uid} updated successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update user: {str(e)}", exc_info=True)
        raise



def get_user_by_uid(uid: str) -> Optional[User]:
    """
    Get user by Firestore document ID (UID).

    Args:
        uid: User document ID (same as auth UID if you store it that way)

    Returns:
        User object if found, None otherwise
    """
    try:
        logger.info(f"Fetching user by uid: {uid}")

        if db is None:
            raise Exception("Firestore client not initialized")

        doc = db.collection('users').document(uid).get()

        if doc.exists:
            user = User.from_dict(doc.to_dict(), doc.id)
            logger.info(f"User found for uid: {uid}")
            return user

        logger.warning(f"User not found for uid: {uid}")
        return None

    except Exception as e:
        logger.error(f"Failed to fetch user by uid {uid}: {str(e)}", exc_info=True)
        raise


def update_user_last_login(uid: str) -> bool:
    """
    Update the last_login / last_active timestamps for a user.

    Args:
        uid: User document ID

    Returns:
        True if update successful
    """
    try:
        logger.info(f"Updating last login for user: {uid}")

        if db is None:
            raise Exception("Firestore client not initialized")

        now = datetime.utcnow()
        db.collection('users').document(uid).update({
            'last_login': now,
            'last_active': now
        })

        logger.info(f"Last login updated for user: {uid}")
        return True

    except Exception as e:
        logger.error(f"Failed to update last login for user {uid}: {str(e)}", exc_info=True)
        raise


# ============================================================================
# ANALYTICS SUMMARY
# ============================================================================

def get_analytics_summary(date: str) -> Optional[AnalyticsSummary]:
    """
    Get analytics summary for a specific date.
    
    Args:
        date: Date string in ISO format (YYYY-MM-DD)
        
    Returns:
        AnalyticsSummary object if found, None otherwise
        
    Example:
        >>> summary = get_analytics_summary('2025-01-15')
        >>> if summary:
        ...     print(f"Avg temp: {summary.avg_temperature}°C")
    """
    try:
        logger.info(f"Fetching analytics summary for date: {date}")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        doc = db.collection('analytics_summary').document(date).get()
        
        if doc.exists:
            summary = AnalyticsSummary.from_dict(doc.to_dict(), doc.id)
            logger.info(f"Analytics summary found for {date}")
            return summary
        else:
            logger.warning(f"Analytics summary not found for {date}")
            return None
        
    except Exception as e:
        logger.error(f"Failed to fetch analytics summary: {str(e)}", exc_info=True)
        raise


def save_analytics_summary(summary: AnalyticsSummary) -> bool:
    """
    Save or update analytics summary.
    
    Args:
        summary: AnalyticsSummary object to save
        
    Returns:
        True if save successful
        
    Example:
        >>> from datetime import date
        >>> summary = AnalyticsSummary(
        ...     summary_date=date(2025, 1, 15),
        ...     avg_temperature=25.3,
        ...     max_temperature=32.1,
        ...     min_temperature=18.7,
        ...     # ... other fields
        ... )
        >>> save_analytics_summary(summary)
    """
    try:
        date_str = summary.summary_date.isoformat()
        logger.info(f"Saving analytics summary for date: {date_str}")
        
        if db is None:
            raise Exception("Firestore client not initialized")
        
        db.collection('analytics_summary').document(date_str).set(summary.to_dict())
        
        logger.info(f"Analytics summary saved for {date_str}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to save analytics summary: {str(e)}", exc_info=True)
        raise