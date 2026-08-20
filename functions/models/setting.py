"""
Setting Model
=============
Represents system configuration settings stored as key-value pairs.

Setting Categories:
- thresholds: Sensor threshold values (temp_max, humidity_max, methane_critical)
- notifications: Notification preferences (email_enabled, sms_enabled)
- system: System configuration (refresh_interval, data_retention_days)

Fields:
- key: Setting identifier (unique)
- value: Setting value (can be string, int, float, or bool)
- category: Setting category for organization
- description: Human-readable description of what the setting does
"""

from typing import Dict, Any, Optional, Union


class Setting:
    """Represents a system configuration setting"""
    
    def __init__(
        self,
        key: str,
        value: Union[str, int, float, bool],
        category: str = 'general',
        description: Optional[str] = None,
        doc_id: Optional[str] = None
    ):
        """
        Initialize a setting.
        
        Args:
            key: Setting identifier (e.g., 'temp_max', 'email_enabled')
            value: Setting value (string, int, float, or bool)
            category: Setting category (thresholds, notifications, system)
            description: Human-readable description
            doc_id: Firestore document ID
        """
        self.key = key
        self.value = value
        self.category = category
        self.description = description
        self.doc_id = doc_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for Firestore storage.
        
        Returns:
            Dictionary with all setting data
        """
        return {
            'key': self.key,
            'value': self.value,
            'category': self.category,
            'description': self.description
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], doc_id: Optional[str] = None) -> 'Setting':
        """
        Create Setting from Firestore document.
        
        Args:
            data: Dictionary from Firestore
            doc_id: Document ID
            
        Returns:
            Setting instance
        """
        return Setting(
            key=data.get('key', ''),
            value=data.get('value'),
            category=data.get('category', 'general'),
            description=data.get('description'),
            doc_id=doc_id
        )
    
    def get_value_as_int(self) -> Optional[int]:
        """
        Get value as integer.
        
        Returns:
            Value as int, or None if conversion fails
        """
        try:
            return int(self.value)
        except (ValueError, TypeError):
            return None
    
    def get_value_as_float(self) -> Optional[float]:
        """
        Get value as float.
        
        Returns:
            Value as float, or None if conversion fails
        """
        try:
            return float(self.value)
        except (ValueError, TypeError):
            return None
    
    def get_value_as_bool(self) -> bool:
        """
        Get value as boolean.
        Handles string representations: 'true', 'false', '1', '0', 'yes', 'no'
        
        Returns:
            Value as bool
        """
        if isinstance(self.value, bool):
            return self.value
        
        if isinstance(self.value, str):
            return self.value.lower() in ['true', '1', 'yes', 'on', 'enabled']
        
        return bool(self.value)
    
    def get_value_as_string(self) -> str:
        """
        Get value as string.
        
        Returns:
            Value as string
        """
        return str(self.value)
    
    def is_threshold_setting(self) -> bool:
        """
        Check if this is a threshold setting.
        
        Returns:
            True if category is 'thresholds'
        """
        return self.category == 'thresholds'
    
    def is_notification_setting(self) -> bool:
        """
        Check if this is a notification setting.
        
        Returns:
            True if category is 'notifications'
        """
        return self.category == 'notifications'
    
    def is_system_setting(self) -> bool:
        """
        Check if this is a system setting.
        
        Returns:
            True if category is 'system'
        """
        return self.category == 'system'
    
    def validate_threshold_value(self) -> tuple[bool, Optional[str]]:
        """
        Validate threshold setting values are within acceptable ranges.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.is_threshold_setting():
            return True, None
        
        # Temperature thresholds
        if 'temp' in self.key.lower():
            value = self.get_value_as_float()
            if value is None:
                return False, "Temperature threshold must be a number"
            if value < 0 or value > 60:
                return False, "Temperature threshold must be between 0-60°C"
        
        # Humidity thresholds
        elif 'humidity' in self.key.lower():
            value = self.get_value_as_float()
            if value is None:
                return False, "Humidity threshold must be a number"
            if value < 0 or value > 100:
                return False, "Humidity threshold must be between 0-100%"
        
        # Methane thresholds
        elif 'methane' in self.key.lower():
            value = self.get_value_as_int()
            if value is None:
                return False, "Methane threshold must be an integer"
            if value < 0 or value > 1023:
                return False, "Methane threshold must be between 0-1023"
        
        return True, None
    
    def format_for_display(self) -> str:
        """
        Format setting for user-friendly display.
        
        Returns:
            Formatted setting string
        """
        # Add units based on key name
        value_str = str(self.value)
        
        if 'temp' in self.key.lower():
            value_str += '°C'
        elif 'humidity' in self.key.lower():
            value_str += '%'
        elif 'methane' in self.key.lower():
            value_str += ' ppm'
        elif 'interval' in self.key.lower():
            value_str += ' seconds'
        elif 'days' in self.key.lower():
            value_str += ' days'
        
        return f"{self.key}: {value_str}"
    
    def get_category_emoji(self) -> str:
        """
        Get emoji for setting category.
        
        Returns:
            Emoji string
        """
        category_emojis = {
            'thresholds': '🎯',
            'notifications': '🔔',
            'system': '⚙️',
            'general': '📋'
        }
        return category_emojis.get(self.category, '📝')
    
    def __str__(self) -> str:
        """String representation of setting"""
        emoji = self.get_category_emoji()
        return f"{emoji} Setting({self.key}={self.value}) [{self.category}]"
    
    def __repr__(self) -> str:
        """Developer-friendly representation"""
        return f"Setting(key='{self.key}', value={self.value!r}, category='{self.category}')"


# Default system settings
DEFAULT_SETTINGS = {
    # Temperature thresholds
    'temp_max': Setting('temp_max', 35.0, 'thresholds', 'Maximum safe temperature (°C)'),
    'temp_min': Setting('temp_min', 15.0, 'thresholds', 'Minimum safe temperature (°C)'),
    'temp_warning_max': Setting('temp_warning_max', 32.0, 'thresholds', 'Warning temperature threshold (°C)'),
    'temp_warning_min': Setting('temp_warning_min', 18.0, 'thresholds', 'Warning low temperature threshold (°C)'),
    
    # Humidity thresholds
    'humidity_max': Setting('humidity_max', 80.0, 'thresholds', 'Maximum safe humidity (%)'),
    'humidity_min': Setting('humidity_min', 40.0, 'thresholds', 'Minimum safe humidity (%)'),
    'humidity_warning_max': Setting('humidity_warning_max', 75.0, 'thresholds', 'Warning high humidity threshold (%)'),
    'humidity_warning_min': Setting('humidity_warning_min', 45.0, 'thresholds', 'Warning low humidity threshold (%)'),
    
    # Methane thresholds
    'methane_critical': Setting('methane_critical', 300, 'thresholds', 'Critical methane level (ppm)'),
    'methane_warning': Setting('methane_warning', 200, 'thresholds', 'Warning methane level (ppm)'),
    'methane_exhaust_fan_threshold': Setting('methane_exhaust_fan_threshold', 200, 'thresholds', 'Methane level to activate exhaust fan (ppm)'),
    
    # Other gases thresholds
    'other_gases_critical': Setting('other_gases_critical', 400, 'thresholds', 'Critical other gases level'),
    'other_gases_warning': Setting('other_gases_warning', 300, 'thresholds', 'Warning other gases level'),
    
    # Notification settings
    'email_enabled': Setting('email_enabled', True, 'notifications', 'Enable email alerts'),
    'sms_enabled': Setting('sms_enabled', False, 'notifications', 'Enable SMS alerts (requires Twilio)'),
    'notification_critical_only': Setting('notification_critical_only', False, 'notifications', 'Send notifications only for critical alerts'),
    
    # System settings
    'refresh_interval': Setting('refresh_interval', 5, 'system', 'Dashboard refresh interval (seconds)'),
    'data_retention_days': Setting('data_retention_days', 90, 'system', 'Number of days to retain sensor data'),
    'max_alerts_display': Setting('max_alerts_display', 50, 'system', 'Maximum number of alerts to display'),
}


def get_default_settings() -> Dict[str, Setting]:
    """
    Get dictionary of all default settings.
    Use this to seed the database with initial settings.
    
    Returns:
        Dictionary mapping setting keys to Setting objects
    """
    return DEFAULT_SETTINGS.copy()