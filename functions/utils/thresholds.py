"""
Sensor Threshold Constants
==========================
Centralized threshold values for sensor monitoring and alert generation.

These values determine when alerts are triggered:
- Critical thresholds: Immediate action required (🚨 critical alerts)
- Warning thresholds: Attention needed (⚠️ warning alerts)
- Normal range: Between warning thresholds (ℹ️ info only)

Thresholds can be overridden by database settings (settings collection).
These are fallback defaults if database settings are unavailable.
"""

# =============================================================================
# TEMPERATURE THRESHOLDS (°C)
# =============================================================================

# Critical temperature limits
TEMP_MAX = 35.0
"""Maximum safe temperature (°C). Above this triggers CRITICAL alert."""

TEMP_MIN = 15.0
"""Minimum safe temperature (°C). Below this triggers CRITICAL alert."""

# Warning temperature limits
TEMP_WARNING_MAX = 32.0
"""High temperature warning threshold (°C). Above this triggers WARNING alert."""

TEMP_WARNING_MIN = 18.0
"""Low temperature warning threshold (°C). Below this triggers WARNING alert."""

# Optimal temperature range
TEMP_OPTIMAL_MIN = 20.0
"""Optimal minimum temperature for crops (°C)."""

TEMP_OPTIMAL_MAX = 28.0
"""Optimal maximum temperature for crops (°C)."""


# =============================================================================
# HUMIDITY THRESHOLDS (%)
# =============================================================================

# Critical humidity limits
HUMIDITY_MAX = 80.0
"""Maximum safe humidity (%). Above this triggers CRITICAL alert."""

HUMIDITY_MIN = 40.0
"""Minimum safe humidity (%). Below this triggers CRITICAL alert."""

# Warning humidity limits
HUMIDITY_WARNING_MAX = 75.0
"""High humidity warning threshold (%). Above this triggers WARNING alert."""

HUMIDITY_WARNING_MIN = 45.0
"""Low humidity warning threshold (%). Below this triggers WARNING alert."""

# Optimal humidity range
HUMIDITY_OPTIMAL_MIN = 50.0
"""Optimal minimum humidity for crops (%)."""

HUMIDITY_OPTIMAL_MAX = 70.0
"""Optimal maximum humidity for crops (%)."""


# =============================================================================
# METHANE THRESHOLDS (ppm - parts per million)
# =============================================================================

# Critical methane limit
METHANE_CRITICAL = 300
"""Critical methane level (ppm). Above this triggers CRITICAL alert."""

# Warning methane limit
METHANE_WARNING = 200
"""Warning methane level (ppm). Above this triggers WARNING alert."""

# Exhaust fan activation
METHANE_EXHAUST_FAN_THRESHOLD = 200
"""
Methane level to automatically activate exhaust fan (ppm).
When methane >= this value, exhaust_fan status is set to True.
"""

# Safe methane level
METHANE_SAFE = 100
"""Safe methane level (ppm). Below this is considered normal."""


# =============================================================================
# OTHER GASES THRESHOLDS (analog sensor value 0-1023)
# =============================================================================

# Critical other gases limit
OTHER_GASES_CRITICAL = 400
"""Critical other gases level. Above this triggers CRITICAL alert."""

# Warning other gases limit
OTHER_GASES_WARNING = 300
"""Warning other gases level. Above this triggers WARNING alert."""

# Safe other gases level
OTHER_GASES_SAFE = 200
"""Safe other gases level. Below this is considered normal."""


# =============================================================================
# ALERT TYPES
# =============================================================================

ALERT_TYPE_INFO = 'info'
"""Informational alert (ℹ️) - minor issues, no immediate action needed."""

ALERT_TYPE_WARNING = 'warning'
"""Warning alert (⚠️) - attention needed, monitor situation."""

ALERT_TYPE_CRITICAL = 'critical'
"""Critical alert (🚨) - immediate action required, safety risk."""


# =============================================================================
# THRESHOLD DICTIONARIES (for easy iteration)
# =============================================================================

TEMPERATURE_THRESHOLDS = {
    'critical_max': TEMP_MAX,
    'critical_min': TEMP_MIN,
    'warning_max': TEMP_WARNING_MAX,
    'warning_min': TEMP_WARNING_MIN,
    'optimal_max': TEMP_OPTIMAL_MAX,
    'optimal_min': TEMP_OPTIMAL_MIN
}
"""Dictionary of all temperature thresholds."""

HUMIDITY_THRESHOLDS = {
    'critical_max': HUMIDITY_MAX,
    'critical_min': HUMIDITY_MIN,
    'warning_max': HUMIDITY_WARNING_MAX,
    'warning_min': HUMIDITY_WARNING_MIN,
    'optimal_max': HUMIDITY_OPTIMAL_MAX,
    'optimal_min': HUMIDITY_OPTIMAL_MIN
}
"""Dictionary of all humidity thresholds."""

METHANE_THRESHOLDS = {
    'critical': METHANE_CRITICAL,
    'warning': METHANE_WARNING,
    'exhaust_fan': METHANE_EXHAUST_FAN_THRESHOLD,
    'safe': METHANE_SAFE
}
"""Dictionary of all methane thresholds."""

OTHER_GASES_THRESHOLDS = {
    'critical': OTHER_GASES_CRITICAL,
    'warning': OTHER_GASES_WARNING,
    'safe': OTHER_GASES_SAFE
}
"""Dictionary of all other gases thresholds."""

ALL_THRESHOLDS = {
    'temperature': TEMPERATURE_THRESHOLDS,
    'humidity': HUMIDITY_THRESHOLDS,
    'methane': METHANE_THRESHOLDS,
    'other_gases': OTHER_GASES_THRESHOLDS
}
"""Master dictionary containing all threshold dictionaries."""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_threshold(sensor_type: str, threshold_name: str) -> float:
    """
    Get a specific threshold value.
    
    Args:
        sensor_type: Sensor type ('temperature', 'humidity', 'methane', 'other_gases')
        threshold_name: Threshold name ('critical_max', 'warning_min', etc.)
        
    Returns:
        Threshold value, or None if not found
        
    Examples:
        >>> get_threshold('temperature', 'critical_max')
        35.0
        >>> get_threshold('methane', 'warning')
        200
    """
    try:
        return ALL_THRESHOLDS[sensor_type][threshold_name]
    except KeyError:
        return None


def is_critical(sensor_type: str, value: float) -> bool:
    """
    Check if sensor value is in critical range.
    
    Args:
        sensor_type: Sensor type ('temperature', 'humidity', 'methane', 'other_gases')
        value: Sensor value
        
    Returns:
        True if value is in critical range
        
    Examples:
        >>> is_critical('temperature', 40.0)
        True
        >>> is_critical('temperature', 25.0)
        False
    """
    if sensor_type == 'temperature':
        return value > TEMP_MAX or value < TEMP_MIN
    elif sensor_type == 'humidity':
        return value > HUMIDITY_MAX or value < HUMIDITY_MIN
    elif sensor_type == 'methane':
        return value > METHANE_CRITICAL
    elif sensor_type == 'other_gases':
        return value > OTHER_GASES_CRITICAL
    return False


def is_warning(sensor_type: str, value: float) -> bool:
    """
    Check if sensor value is in warning range (but not critical).
    
    Args:
        sensor_type: Sensor type ('temperature', 'humidity', 'methane', 'other_gases')
        value: Sensor value
        
    Returns:
        True if value is in warning range
        
    Examples:
        >>> is_warning('temperature', 33.0)
        True
        >>> is_warning('temperature', 25.0)
        False
    """
    # First check if it's critical (critical overrides warning)
    if is_critical(sensor_type, value):
        return False
    
    if sensor_type == 'temperature':
        return value > TEMP_WARNING_MAX or value < TEMP_WARNING_MIN
    elif sensor_type == 'humidity':
        return value > HUMIDITY_WARNING_MAX or value < HUMIDITY_WARNING_MIN
    elif sensor_type == 'methane':
        return value > METHANE_WARNING
    elif sensor_type == 'other_gases':
        return value > OTHER_GASES_WARNING
    return False


def is_optimal(sensor_type: str, value: float) -> bool:
    """
    Check if sensor value is in optimal range.
    
    Args:
        sensor_type: Sensor type ('temperature', 'humidity', 'methane', 'other_gases')
        value: Sensor value
        
    Returns:
        True if value is in optimal range
        
    Examples:
        >>> is_optimal('temperature', 25.0)
        True
        >>> is_optimal('temperature', 35.0)
        False
    """
    if sensor_type == 'temperature':
        return TEMP_OPTIMAL_MIN <= value <= TEMP_OPTIMAL_MAX
    elif sensor_type == 'humidity':
        return HUMIDITY_OPTIMAL_MIN <= value <= HUMIDITY_OPTIMAL_MAX
    elif sensor_type == 'methane':
        return value < METHANE_SAFE
    elif sensor_type == 'other_gases':
        return value < OTHER_GASES_SAFE
    return False


def get_alert_type(sensor_type: str, value: float) -> str:
    """
    Determine alert type based on sensor value.
    
    Args:
        sensor_type: Sensor type ('temperature', 'humidity', 'methane', 'other_gases')
        value: Sensor value
        
    Returns:
        Alert type: 'critical', 'warning', or 'info'
        
    Examples:
        >>> get_alert_type('temperature', 40.0)
        'critical'
        >>> get_alert_type('temperature', 33.0)
        'warning'
        >>> get_alert_type('temperature', 25.0)
        'info'
    """
    if is_critical(sensor_type, value):
        return ALERT_TYPE_CRITICAL
    elif is_warning(sensor_type, value):
        return ALERT_TYPE_WARNING
    else:
        return ALERT_TYPE_INFO


def should_activate_exhaust_fan(methane_level: int) -> bool:
    """
    Determine if exhaust fan should be activated based on methane level.
    
    Args:
        methane_level: Current methane level (ppm)
        
    Returns:
        True if exhaust fan should be ON
        
    Examples:
        >>> should_activate_exhaust_fan(250)
        True
        >>> should_activate_exhaust_fan(150)
        False
    """
    return methane_level >= METHANE_EXHAUST_FAN_THRESHOLD


def get_status_message(sensor_type: str, value: float) -> str:
    """
    Get human-readable status message for sensor value.
    
    Args:
        sensor_type: Sensor type ('temperature', 'humidity', 'methane', 'other_gases')
        value: Sensor value
        
    Returns:
        Status message string
        
    Examples:
        >>> get_status_message('temperature', 25.0)
        'Temperature is optimal (25.0°C)'
        >>> get_status_message('temperature', 40.0)
        'CRITICAL: Temperature too high (40.0°C)'
    """
    alert_type = get_alert_type(sensor_type, value)
    
    # Add units
    unit = ''
    if sensor_type == 'temperature':
        unit = '°C'
    elif sensor_type == 'humidity':
        unit = '%'
    elif sensor_type in ['methane', 'other_gases']:
        unit = ' ppm'
    
    # Build message
    if alert_type == ALERT_TYPE_CRITICAL:
        if sensor_type == 'temperature':
            if value > TEMP_MAX:
                return f"CRITICAL: Temperature too high ({value}{unit})"
            else:
                return f"CRITICAL: Temperature too low ({value}{unit})"
        elif sensor_type == 'humidity':
            if value > HUMIDITY_MAX:
                return f"CRITICAL: Humidity too high ({value}{unit})"
            else:
                return f"CRITICAL: Humidity too low ({value}{unit})"
        else:
            return f"CRITICAL: {sensor_type.replace('_', ' ').title()} level too high ({value}{unit})"
    
    elif alert_type == ALERT_TYPE_WARNING:
        if sensor_type == 'temperature':
            if value > TEMP_WARNING_MAX:
                return f"WARNING: Temperature high ({value}{unit})"
            else:
                return f"WARNING: Temperature low ({value}{unit})"
        elif sensor_type == 'humidity':
            if value > HUMIDITY_WARNING_MAX:
                return f"WARNING: Humidity high ({value}{unit})"
            else:
                return f"WARNING: Humidity low ({value}{unit})"
        else:
            return f"WARNING: {sensor_type.replace('_', ' ').title()} level elevated ({value}{unit})"
    
    else:
        if is_optimal(sensor_type, value):
            return f"{sensor_type.replace('_', ' ').title()} is optimal ({value}{unit})"
        else:
            return f"{sensor_type.replace('_', ' ').title()} is normal ({value}{unit})"