"""
Input Validation Functions
==========================
Validation functions for sensor data, user input, and configuration values.

All validators return a tuple: (is_valid: bool, error_message: str)
- If valid: (True, "")
- If invalid: (False, "Error message explaining why")
"""

import re
from typing import Tuple, Any


def validate_temperature(value: Any) -> Tuple[bool, str]:
    """
    Validate temperature value.
    
    Valid range: 0-60°C (typical for agricultural sensors)
    
    Args:
        value: Temperature value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_temperature(25.5)
        (True, "")
        >>> validate_temperature(100)
        (False, "Temperature must be between 0-60°C")
    """
    # Check type
    if not isinstance(value, (int, float)):
        return False, "Temperature must be a number"
    
    # Convert to float
    try:
        temp = float(value)
    except (ValueError, TypeError):
        return False, "Temperature must be a valid number"
    
    # Check range
    if temp < 0:
        return False, "Temperature cannot be negative"
    
    if temp > 60:
        return False, "Temperature must be between 0-60°C"
    
    return True, ""


def validate_humidity(value: Any) -> Tuple[bool, str]:
    """
    Validate humidity value.
    
    Valid range: 0-100% (percentage)
    
    Args:
        value: Humidity value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_humidity(65.5)
        (True, "")
        >>> validate_humidity(150)
        (False, "Humidity must be between 0-100%")
    """
    # Check type
    if not isinstance(value, (int, float)):
        return False, "Humidity must be a number"
    
    # Convert to float
    try:
        humidity = float(value)
    except (ValueError, TypeError):
        return False, "Humidity must be a valid number"
    
    # Check range
    if humidity < 0:
        return False, "Humidity cannot be negative"
    
    if humidity > 100:
        return False, "Humidity must be between 0-100%"
    
    return True, ""


def validate_methane(value: Any) -> Tuple[bool, str]:
    """
    Validate methane sensor value.
    
    Valid range: 0-1023 (Arduino analog sensor range)
    
    Args:
        value: Methane value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_methane(150)
        (True, "")
        >>> validate_methane(2000)
        (False, "Methane must be between 0-1023")
    """
    # Check type
    if not isinstance(value, (int, float)):
        return False, "Methane value must be a number"
    
    # Convert to int
    try:
        methane = int(value)
    except (ValueError, TypeError):
        return False, "Methane value must be a valid integer"
    
    # Check range
    if methane < 0:
        return False, "Methane value cannot be negative"
    
    if methane > 1023:
        return False, "Methane must be between 0-1023 (Arduino analog range)"
    
    return True, ""


def validate_other_gases(value: Any) -> Tuple[bool, str]:
    """
    Validate other gases sensor value.
    
    Valid range: 0-1023 (Arduino analog sensor range)
    
    Args:
        value: Other gases value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_other_gases(180)
        (True, "")
        >>> validate_other_gases(-50)
        (False, "Other gases value cannot be negative")
    """
    # Check type
    if not isinstance(value, (int, float)):
        return False, "Other gases value must be a number"
    
    # Convert to int
    try:
        gases = int(value)
    except (ValueError, TypeError):
        return False, "Other gases value must be a valid integer"
    
    # Check range
    if gases < 0:
        return False, "Other gases value cannot be negative"
    
    if gases > 1023:
        return False, "Other gases must be between 0-1023 (Arduino analog range)"
    
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_email("user@example.com")
        (True, "")
        >>> validate_email("invalid-email")
        (False, "Invalid email format")
    """
    # Check type
    if not isinstance(email, str):
        return False, "Email must be a string"
    
    # Check not empty
    email = email.strip()
    if not email:
        return False, "Email cannot be empty"
    
    # Email regex pattern
    # Matches: username@domain.tld
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    
    if not re.match(pattern, email):
        return False, "Invalid email format. Expected: user@example.com"
    
    # Check length
    if len(email) > 254:  # RFC 5321
        return False, "Email address too long (max 254 characters)"
    
    return True, ""


def validate_phone_number(phone: str) -> Tuple[bool, str]:
    """
    Validate phone number format.
    
    Accepts formats:
    - +1234567890
    - +1 234 567 8900
    - +1-234-567-8900
    - 1234567890
    
    Args:
        phone: Phone number to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_phone_number("+1234567890")
        (True, "")
        >>> validate_phone_number("123")
        (False, "Phone number must be 10-15 digits")
    """
    # Check type
    if not isinstance(phone, str):
        return False, "Phone number must be a string"
    
    # Check not empty
    phone = phone.strip()
    if not phone:
        return False, "Phone number cannot be empty"
    
    # Remove common separators
    cleaned = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
    
    # Check for + prefix (international format)
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]
    
    # Check all digits
    if not cleaned.isdigit():
        return False, "Phone number must contain only digits (with optional + prefix)"
    
    # Check length (10-15 digits is standard for international numbers)
    if len(cleaned) < 10:
        return False, "Phone number must be at least 10 digits"
    
    if len(cleaned) > 15:
        return False, "Phone number must be 10-15 digits"
    
    return True, ""


def validate_sensor_reading_dict(data: dict) -> Tuple[bool, str]:
    """
    Validate a complete sensor reading dictionary.
    
    Expected fields: temperature, humidity, methane, other_gases
    
    Args:
        data: Dictionary with sensor data
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_sensor_reading_dict({
        ...     "temperature": 25.5,
        ...     "humidity": 65.0,
        ...     "methane": 150,
        ...     "other_gases": 180
        ... })
        (True, "")
    """
    # Check if data is a dictionary
    if not isinstance(data, dict):
        return False, "Sensor data must be a dictionary"
    
    # Required fields
    required_fields = ['temperature', 'humidity', 'methane', 'other_gases']
    
    # Check all required fields exist
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    # Validate each field
    is_valid, error = validate_temperature(data['temperature'])
    if not is_valid:
        return False, f"temperature: {error}"
    
    is_valid, error = validate_humidity(data['humidity'])
    if not is_valid:
        return False, f"humidity: {error}"
    
    is_valid, error = validate_methane(data['methane'])
    if not is_valid:
        return False, f"methane: {error}"
    
    is_valid, error = validate_other_gases(data['other_gases'])
    if not is_valid:
        return False, f"other_gases: {error}"
    
    return True, ""


def validate_date_range(start_date: str, end_date: str) -> Tuple[bool, str]:
    """
    Validate date range for analytics queries.
    
    Args:
        start_date: Start date in ISO format (YYYY-MM-DD)
        end_date: End date in ISO format (YYYY-MM-DD)
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Examples:
        >>> validate_date_range("2025-01-01", "2025-01-07")
        (True, "")
        >>> validate_date_range("2025-01-07", "2025-01-01")
        (False, "Start date must be before end date")
    """
    from datetime import datetime
    
    # Try parsing dates
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except (ValueError, TypeError):
        return False, "Invalid date format. Use YYYY-MM-DD"
    
    # Check start is before end
    if start > end:
        return False, "Start date must be before end date"
    
    # Check range is not too large (max 365 days)
    delta = end - start
    if delta.days > 365:
        return False, "Date range cannot exceed 365 days"
    
    return True, ""


def validate_setting_value(key: str, value: Any) -> Tuple[bool, str]:
    """
    Validate setting value based on setting key.
    
    Args:
        key: Setting key (e.g., "temp_max", "email_enabled")
        value: Setting value to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Temperature settings
    if 'temp' in key.lower():
        return validate_temperature(value)
    
    # Humidity settings
    elif 'humidity' in key.lower():
        return validate_humidity(value)
    
    # Methane settings
    elif 'methane' in key.lower():
        return validate_methane(value)
    
    # Boolean settings (enabled/disabled)
    elif 'enabled' in key.lower():
        if not isinstance(value, bool):
            return False, "Value must be true or false"
        return True, ""
    
    # Integer settings (intervals, counts, etc.)
    elif any(word in key.lower() for word in ['interval', 'count', 'days', 'limit']):
        if not isinstance(value, int):
            return False, "Value must be an integer"
        if value < 0:
            return False, "Value cannot be negative"
        return True, ""
    
    # Default: accept any value
    return True, ""