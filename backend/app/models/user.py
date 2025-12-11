"""User model for authentication and team features."""

from sqlalchemy import Column, String, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum

from app.models.base import Base, UUIDMixin, TimestampMixin


class UserRole(str, enum.Enum):
    """User roles for permissions."""
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"


class User(Base, UUIDMixin, TimestampMixin):
    """User model for authentication and team features."""
    
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    # Profile
    full_name = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    
    # Role
    role = Column(
        Enum(UserRole),
        default=UserRole.VIEWER,
        nullable=False,
    )
    
    # Settings and preferences
    settings = Column(JSONB, default=dict)
    
    def __repr__(self):
        return f"<User {self.email}>"

