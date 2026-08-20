"""
Sensor Reading Model
====================
Represents sensor data from Arduino hardware.

Fields:
- temperature: float (0-60°C)
- humidity: float (0-100%)
- methane: int (0-1023 ppm)
- other_gases: int (0-1023)
- exhaust_fan: bool (auto-calculated based on methane)
- timestamp: datetime (auto-generated)
"""

from datetime import datetime
from typing import Dict, Any, Optional, Tuple


class SensorReading:
    """Represents a single sensor data reading from Arduino"""
    
    def __init__(
        self,
        temperature: float,
        humidity: float,
        methane: int,
        other_gases: int,
        exhaust_fan: Optional[bool] = None,
        timestamp: Optional[datetime] = None,
        doc_id: Optional[str] = None
    ):
        """
        Initialize a sensor reading.
        
        Args:
            temperature: Temperature in Celsius (0-60)
            humidity: Humidity percentage (0-100)
            methane: Methane level in ppm (0-1023)
            other_gases: Other gases level (0-1023)
            exhaust_fan: Fan status (auto-calculated if None)
            timestamp: Reading timestamp (auto-generated if not provided)
            doc_id: Firestore document ID
        """
        self.temperature = float(temperature)
        self.humidity = float(humidity)
        self.methane = int(methane)
        self.other_gases = int(other_gases)
        # Auto-calc exhaust_fan if not explicitly provided
        if exhaust_fan is None:
            self.exhaust_fan = self.calculate_exhaust_fan_status()
        else:
            self.exhaust_fan = bool(exhaust_fan)
        self.timestamp = timestamp or datetime.utcnow()
        self.doc_id = doc_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for Firestore storage.
        
        Returns:
            Dictionary with all sensor data
        """
        return {
            'temperature': self.temperature,
            'humidity': self.humidity,
            'methane': self.methane,
            'other_gases': self.other_gases,
            'exhaust_fan': self.exhaust_fan,
            'timestamp': self.timestamp
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], doc_id: Optional[str] = None) -> 'SensorReading':
        """
        Create SensorReading from Firestore document.
        
        Args:
            data: Dictionary from Firestore
            doc_id: Document ID
            
        Returns:
            SensorReading instance
        """
        return SensorReading(
            temperature=data.get('temperature', 0.0),
            humidity=data.get('humidity', 0.0),
            methane=data.get('methane', 0),
            other_gases=data.get('other_gases', 0),
            exhaust_fan=data.get('exhaust_fan', None),
            timestamp=data.get('timestamp'),
            doc_id=doc_id
        )
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """
        Validate sensor values are within acceptable ranges.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Temperature validation (0-60°C is typical for agricultural sensors)
        if not isinstance(self.temperature, (int, float)):
            return False, "Temperature must be a number"
        if self.temperature < 0 or self.temperature > 60:
            return False, "Temperature must be between 0-60°C"
        
        # Humidity validation (0-100%)
        if not isinstance(self.humidity, (int, float)):
            return False, "Humidity must be a number"
        if self.humidity < 0 or self.humidity > 100:
            return False, "Humidity must be between 0-100%"
        
        # Methane validation (0-1023 from Arduino analog sensor)
        if not isinstance(self.methane, int):
            return False, "Methane must be an integer"
        if self.methane < 0 or self.methane > 1023:
            return False, "Methane must be between 0-1023"
        
        # Other gases validation
        if not isinstance(self.other_gases, int):
            return False, "Other gases must be an integer"
        if self.other_gases < 0 or self.other_gases > 1023:
            return False, "Other gases must be between 0-1023"
        
        return True, None
    
    def calculate_exhaust_fan_status(self, threshold: int = 200) -> bool:
        """
        Calculate if exhaust fan should be ON based on methane level.
        
        Args:
            threshold: Methane level threshold (default: 200 ppm)
            
        Returns:
            True if fan should be ON, False otherwise
        """
        return self.methane >= threshold
    
    def get_air_quality_status(self) -> str:
        """
        Get overall air quality status based on sensor readings.
        
        Returns:
            Status string: 'Good', 'Moderate', 'Poor', 'Hazardous'
        """
        # Calculate air quality based on methane and other gases
        if self.methane < 100 and self.other_gases < 200:
            return 'Good'
        elif self.methane < 200 and self.other_gases < 300:
            return 'Moderate'
        elif self.methane < 300 and self.other_gases < 400:
            return 'Poor'
        else:
            return 'Hazardous'
        
    def get_temperature_status(self) -> str:
        """
        Get human-readable temperature status.
        
        Returns:
            Status string: 'critical_high', 'warning_high', 'normal', 
                           'warning_low', 'critical_low'
        """
        from utils.thresholds import (
            TEMP_CRITICAL_MAX, TEMP_WARNING_MAX,
            TEMP_MIN, TEMP_WARNING_MIN
        )
        
        if self.temperature >= TEMP_CRITICAL_MAX:
            return 'critical_high'
        elif self.temperature >= TEMP_WARNING_MAX:
            return 'warning_high'
        elif self.temperature <= TEMP_MIN:
            return 'critical_low'
        elif self.temperature <= TEMP_WARNING_MIN:
            return 'warning_low'
        else:
            return 'normal'
    
    
    def get_humidity_status(self) -> str:
        """
        Get human-readable humidity status.
        
        Returns:
            Status string: 'critical_high', 'warning_high', 'normal',
                           'warning_low', 'critical_low'
        """
        from utils.thresholds import (
            HUMIDITY_CRITICAL_MAX, HUMIDITY_WARNING_MAX,
            HUMIDITY_MIN, HUMIDITY_WARNING_MIN
        )
        
        if self.humidity >= HUMIDITY_CRITICAL_MAX:
            return 'critical_high'
        elif self.humidity >= HUMIDITY_WARNING_MAX:
            return 'warning_high'
        elif self.humidity <= HUMIDITY_MIN:
            return 'critical_low'
        elif self.humidity <= HUMIDITY_WARNING_MIN:
            return 'warning_low'
        else:
            return 'normal'
    
    
    def get_methane_status(self) -> str:
        """
        Get human-readable methane level status.
        
        Returns:
            Status string: 'critical', 'warning', 'normal'
        """
        from utils.thresholds import METHANE_CRITICAL, METHANE_WARNING
        
        if self.methane >= METHANE_CRITICAL:
            return 'critical'
        elif self.methane >= METHANE_WARNING:
            return 'warning'
        else:
            return 'normal'
    
    
    def get_other_gases_status(self) -> str:
        """
        Get human-readable other gases level status.
        
        Returns:
            Status string: 'critical', 'warning', 'normal'
        """
        from utils.thresholds import OTHER_GASES_CRITICAL, OTHER_GASES_WARNING
        
        if self.other_gases >= OTHER_GASES_CRITICAL:
            return 'critical'
        elif self.other_gases >= OTHER_GASES_WARNING:
            return 'warning'
        else:
            return 'normal'     
        
    def __str__(self) -> str:
        """String representation of sensor reading"""
        return (
            f"SensorReading(temp={self.temperature}°C, "
            f"humidity={self.humidity}%, "
            f"methane={self.methane}ppm, "
            f"other_gases={self.other_gases}, "
            f"fan={'ON' if self.exhaust_fan else 'OFF'})"
        )
    
    def __repr__(self) -> str:
        """Developer-friendly representation"""
        return self.__str__()