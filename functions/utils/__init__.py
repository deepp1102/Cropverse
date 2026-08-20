"""
Utility Functions for CropVerse
================================
This package contains helper functions and utilities used across the application.

Modules:
- validators: Input validation functions
- thresholds: Sensor threshold constants
- decorators: Authentication and authorization decorators
- logger: Centralized logging configuration
"""

# Validators
from .validators import (
    validate_temperature,
    validate_humidity,
    validate_methane,
    validate_other_gases,
    validate_email,
    validate_phone_number
)

# Thresholds
from .thresholds import (
    TEMP_MAX,
    TEMP_MIN,
    TEMP_WARNING_MAX,
    TEMP_WARNING_MIN,
    HUMIDITY_MAX,
    HUMIDITY_MIN,
    HUMIDITY_WARNING_MAX,
    HUMIDITY_WARNING_MIN,
    METHANE_CRITICAL,
    METHANE_WARNING,
    METHANE_EXHAUST_FAN_THRESHOLD,
    OTHER_GASES_CRITICAL,
    OTHER_GASES_WARNING,
    ALERT_TYPE_INFO,
    ALERT_TYPE_WARNING,
    ALERT_TYPE_CRITICAL
)

# Decorators
from .decorators import (
    login_required,
    admin_required,
    optional_auth,
    rate_limit,
    get_current_user,
    is_current_user_admin
)

# Logger
from .logger import setup_logger

__all__ = [
    # Validators
    'validate_temperature',
    'validate_humidity',
    'validate_methane',
    'validate_other_gases',
    'validate_email',
    'validate_phone_number',
    
    # Thresholds
    'TEMP_MAX',
    'TEMP_MIN',
    'TEMP_WARNING_MAX',
    'TEMP_WARNING_MIN',
    'HUMIDITY_MAX',
    'HUMIDITY_MIN',
    'HUMIDITY_WARNING_MAX',
    'HUMIDITY_WARNING_MIN',
    'METHANE_CRITICAL',
    'METHANE_WARNING',
    'METHANE_EXHAUST_FAN_THRESHOLD',
    'OTHER_GASES_CRITICAL',
    'OTHER_GASES_WARNING',
    'ALERT_TYPE_INFO',
    'ALERT_TYPE_WARNING',
    'ALERT_TYPE_CRITICAL',
    
    # Decorators
    'login_required',
    'admin_required',
    'optional_auth',
    'rate_limit',
    'get_current_user',
    'is_current_user_admin',
    
    # Logger
    'setup_logger'
]

__version__ = '1.0.0'