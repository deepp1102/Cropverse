"""
Alert Model
===========
Represents system alerts triggered by threshold violations.

Alert Types:
- info: Informational alerts (minor issues)
- warning: Warning alerts (attention needed)
- critical: Critical alerts (immediate action required)

Fields:
- sensor_type: Which sensor triggered the alert (temperature, humidity, methane)
- alert_type: Severity level (info, warning, critical)
- message: Human-readable alert message
- value: Current sensor value that triggered the alert
- threshold: The threshold value that was exceeded
- is_resolved: Whether the alert has been acknowledged
- created_at: When the alert was created
- resolved_at: When the alert was resolved (if resolved)
"""

from datetime import datetime
from typing import Dict, Any, Optional, Literal

# Type hint for alert types
AlertType = Literal['info', 'warning', 'critical']


class Alert:
    """Represents a system alert triggered by sensor threshold violations"""
    
    def __init__(
        self,
        sensor_type: str,
        alert_type: AlertType,
        message: str,
        value: float,
        threshold: float,
        is_resolved: bool = False,
        created_at: Optional[datetime] = None,
        resolved_at: Optional[datetime] = None,
        doc_id: Optional[str] = None
    ):
        """
        Initialize an alert.
        
        Args:
            sensor_type: Type of sensor (temperature, humidity, methane, other_gases)
            alert_type: Severity level (info, warning, critical)
            message: Human-readable alert message
            value: Current sensor value that triggered alert
            threshold: Threshold value that was exceeded
            is_resolved: Whether alert has been acknowledged
            created_at: Alert creation timestamp (auto-generated if not provided)
            resolved_at: Alert resolution timestamp
            doc_id: Firestore document ID
        """
        self.sensor_type = sensor_type
        self.alert_type = alert_type
        self.message = message
        self.value = float(value)
        self.threshold = float(threshold)
        self.is_resolved = is_resolved
        self.created_at = created_at or datetime.utcnow()
        self.resolved_at = resolved_at
        self.doc_id = doc_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for Firestore storage.
        
        Returns:
            Dictionary with all alert data
        """
        return {
            'sensor_type': self.sensor_type,
            'alert_type': self.alert_type,
            'message': self.message,
            'value': self.value,
            'threshold': self.threshold,
            'is_resolved': self.is_resolved,
            'created_at': self.created_at,
            'resolved_at': self.resolved_at
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], doc_id: Optional[str] = None) -> 'Alert':
        """
        Create Alert from Firestore document.
        
        Args:
            data: Dictionary from Firestore
            doc_id: Document ID
            
        Returns:
            Alert instance
        """
        return Alert(
            sensor_type=data.get('sensor_type', ''),
            alert_type=data.get('alert_type', 'info'),
            message=data.get('message', ''),
            value=data.get('value', 0.0),
            threshold=data.get('threshold', 0.0),
            is_resolved=data.get('is_resolved', False),
            created_at=data.get('created_at'),
            resolved_at=data.get('resolved_at'),
            doc_id=doc_id
        )
    
    def resolve(self) -> None:
        """
        Mark alert as resolved.
        Sets is_resolved to True and records resolution timestamp.
        """
        self.is_resolved = True
        self.resolved_at = datetime.utcnow()
    
    def get_severity_emoji(self) -> str:
        """
        Get emoji representation of alert severity.
        
        Returns:
            Emoji string
        """
        emoji_map = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'critical': '🚨'
        }
        return emoji_map.get(self.alert_type, '❓')
    
    def get_priority_score(self) -> int:
        """
        Get numeric priority score for sorting alerts.
        Higher score = higher priority.
        
        Returns:
            Priority score (1-3)
        """
        priority_map = {
            'info': 1,
            'warning': 2,
            'critical': 3
        }
        return priority_map.get(self.alert_type, 0)
    
    def is_critical(self) -> bool:
        """Check if alert is critical severity"""
        return self.alert_type == 'critical'
    
    def is_warning(self) -> bool:
        """Check if alert is warning severity"""
        return self.alert_type == 'warning'
    
    def is_info(self) -> bool:
        """Check if alert is info severity"""
        return self.alert_type == 'info'
    
    def get_age_minutes(self) -> int:
        """
        Get alert age in minutes.
        
        Returns:
            Minutes since alert was created
        """
        if self.created_at:
            delta = datetime.utcnow() - self.created_at
            return int(delta.total_seconds() / 60)
        return 0
    
    def format_for_sms(self) -> str:
        """
        Format alert message for SMS notifications.
        Keeps message under 160 characters.
        
        Returns:
            SMS-formatted string
        """
        emoji = self.get_severity_emoji()
        return (
            f"{emoji} CropVerse Alert\n"
            f"{self.sensor_type.upper()}: {self.value}\n"
            f"Threshold: {self.threshold}\n"
            f"{self.message[:80]}"
        )
    
    def format_for_email(self) -> Dict[str, str]:
        """
        Format alert for email notifications.
        
        Returns:
            Dictionary with subject and body
        """
        emoji = self.get_severity_emoji()
        severity_text = self.alert_type.upper()
        
        subject = f"{emoji} {severity_text} ALERT: {self.sensor_type}"
        
        body = f"""
CropVerse Alert System
{'=' * 50}

Alert Type: {severity_text}
Sensor: {self.sensor_type}

Current Value: {self.value}
Threshold: {self.threshold}

Message:
{self.message}

Time: {self.created_at.strftime('%Y-%m-%d %H:%M:%S UTC') if self.created_at else 'Unknown'}
Status: {'Resolved' if self.is_resolved else 'Active'}

{'=' * 50}
This is an automated alert from CropVerse monitoring system.
        """
        
        return {
            'subject': subject,
            'body': body
        }
    
    def __str__(self) -> str:
        """String representation of alert"""
        status = "✓ Resolved" if self.is_resolved else "⚠ Active"
        return (
            f"Alert[{self.alert_type.upper()}]({self.sensor_type}): "
            f"{self.message} | Value: {self.value} > Threshold: {self.threshold} | {status}"
        )
    
    def __repr__(self) -> str:
        """Developer-friendly representation"""
        return (
            f"Alert(sensor_type='{self.sensor_type}', "
            f"alert_type='{self.alert_type}', "
            f"value={self.value}, "
            f"threshold={self.threshold}, "
            f"is_resolved={self.is_resolved})"
        )