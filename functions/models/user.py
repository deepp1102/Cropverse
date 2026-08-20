"""
User Model
==========
Represents user accounts and profiles.

User Roles:
- admin: Full access (can modify settings, resolve alerts, manage users)
- user: Read-only access (can view dashboard, analytics, chatbot)

Fields:
- email: User's email address (unique identifier)
- role: User role (admin or user)
- display_name: User's display name
- phone_number: Contact phone number (for SMS alerts)
- created_at: Account creation timestamp
- last_login: Last login timestamp
"""

from datetime import datetime
from typing import Dict, Any, Optional, Literal

# Type hint for user roles
UserRole = Literal['admin', 'user']


class User:
    """Represents a system user with role-based permissions"""
    
    def __init__(
        self,
        email: str,
        role: UserRole = 'user',
        display_name: Optional[str] = None,
        phone_number: Optional[str] = None,
        created_at: Optional[datetime] = None,
        last_login: Optional[datetime] = None,
        doc_id: Optional[str] = None
    ):
        """
        Initialize a user.
        
        Args:
            email: User's email address
            role: User role (admin or user)
            display_name: User's display name
            phone_number: Contact phone number
            created_at: Account creation timestamp (auto-generated if not provided)
            last_login: Last login timestamp
            doc_id: Firestore document ID
        """
        self.email = email.lower().strip()  # Normalize email
        self.role = role
        self.display_name = display_name or email.split('@')[0]  # Default to email prefix
        self.phone_number = phone_number
        self.created_at = created_at or datetime.utcnow()
        self.last_login = last_login
        self.doc_id = doc_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for Firestore storage.
        
        Returns:
            Dictionary with all user data
        """
        return {
            'email': self.email,
            'role': self.role,
            'display_name': self.display_name,
            'phone_number': self.phone_number,
            'created_at': self.created_at,
            'last_login': self.last_login
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any], doc_id: Optional[str] = None) -> 'User':
        """
        Create User from Firestore document.
        
        Args:
            data: Dictionary from Firestore
            doc_id: Document ID
            
        Returns:
            User instance
        """
        return User(
            email=data.get('email', ''),
            role=data.get('role', 'user'),
            display_name=data.get('display_name'),
            phone_number=data.get('phone_number'),
            created_at=data.get('created_at'),
            last_login=data.get('last_login'),
            doc_id=doc_id
        )
    
    def is_admin(self) -> bool:
        """
        Check if user has admin role.
        
        Returns:
            True if user is admin, False otherwise
        """
        return self.role == 'admin'
    
    def update_last_login(self) -> None:
        """
        Update last login timestamp to current time.
        Call this when user logs in.
        """
        self.last_login = datetime.utcnow()
    
    def can_modify_settings(self) -> bool:
        """
        Check if user can modify system settings.
        Only admins can modify settings.
        
        Returns:
            True if user can modify settings
        """
        return self.is_admin()
    
    def can_resolve_alerts(self) -> bool:
        """
        Check if user can resolve alerts.
        Only admins can resolve alerts.
        
        Returns:
            True if user can resolve alerts
        """
        return self.is_admin()
    
    def can_manage_users(self) -> bool:
        """
        Check if user can manage other users.
        Only admins can manage users.
        
        Returns:
            True if user can manage users
        """
        return self.is_admin()
    
    def can_view_dashboard(self) -> bool:
        """
        Check if user can view dashboard.
        All authenticated users can view dashboard.
        
        Returns:
            True (all users can view)
        """
        return True
    
    def can_view_analytics(self) -> bool:
        """
        Check if user can view analytics.
        All authenticated users can view analytics.
        
        Returns:
            True (all users can view)
        """
        return True
    
    def can_use_chatbot(self) -> bool:
        """
        Check if user can use AI chatbot.
        All authenticated users can use chatbot.
        
        Returns:
            True (all users can use)
        """
        return True
    
    def get_permissions(self) -> Dict[str, bool]:
        """
        Get all user permissions as dictionary.
        
        Returns:
            Dictionary of permission names and values
        """
        return {
            'view_dashboard': self.can_view_dashboard(),
            'view_analytics': self.can_view_analytics(),
            'use_chatbot': self.can_use_chatbot(),
            'modify_settings': self.can_modify_settings(),
            'resolve_alerts': self.can_resolve_alerts(),
            'manage_users': self.can_manage_users()
        }
    
    def get_account_age_days(self) -> int:
        """
        Get account age in days.
        
        Returns:
            Days since account was created
        """
        if self.created_at:
            delta = datetime.utcnow() - self.created_at
            return delta.days
        return 0
    
    def get_days_since_last_login(self) -> Optional[int]:
        """
        Get days since last login.
        
        Returns:
            Days since last login, or None if never logged in
        """
        if self.last_login:
            delta = datetime.utcnow() - self.last_login
            return delta.days
        return None
    
    def is_active_user(self, days_threshold: int = 30) -> bool:
        """
        Check if user is active (logged in recently).
        
        Args:
            days_threshold: Number of days to consider active (default: 30)
            
        Returns:
            True if user logged in within threshold days
        """
        days_since_login = self.get_days_since_last_login()
        if days_since_login is None:
            return False
        return days_since_login <= days_threshold
    
    def get_role_badge(self) -> str:
        """
        Get emoji badge for user role.
        
        Returns:
            Emoji string representing role
        """
        role_badges = {
            'admin': '👑',
            'user': '👤'
        }
        return role_badges.get(self.role, '❓')
    
    def format_for_display(self) -> str:
        """
        Format user information for display.
        
        Returns:
            Formatted user info string
        """
        badge = self.get_role_badge()
        return f"{badge} {self.display_name} ({self.email}) - {self.role.upper()}"
    
    def __str__(self) -> str:
        """String representation of user"""
        return f"User({self.display_name} <{self.email}> - {self.role})"
    
    def __repr__(self) -> str:
        """Developer-friendly representation"""
        return f"User(email='{self.email}', role='{self.role}', display_name='{self.display_name}')"