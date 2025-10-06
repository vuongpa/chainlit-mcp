"""
Database service layer for user authentication only
"""

from typing import Optional, Union
from sqlmodel import select
import uuid

from .models import User, UserRead
from .database import get_session_context


class UserService:
    """Service class for User authentication operations"""
    
    @staticmethod
    def get_user(user_id: Union[str, uuid.UUID]) -> Optional[User]:
        """Get user by ID"""
        with get_session_context() as session:
            # Convert string to UUID if needed
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)
            return session.get(User, user_id)
    
    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """Get user by email"""
        with get_session_context() as session:
            statement = select(User).where(User.email == email)
            return session.exec(statement).first()
    
    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """Get user by username"""
        with get_session_context() as session:
            statement = select(User).where(User.username == username)
            return session.exec(statement).first()
    
    @staticmethod
    def authenticate_user(username_or_email: str, password: str) -> Optional[User]:
        """Authenticate user with username/email and password"""
        with get_session_context() as session:
            # Try to find user by email or username
            statement = select(User).where(
                (User.email == username_or_email) | (User.username == username_or_email)
            )
            user = session.exec(statement).first()
            if user and user.verify_password(password):
                return user
            return None
    
    @staticmethod
    def get_user_profile(user_id: Union[str, uuid.UUID]) -> Optional[UserRead]:
        """Get user profile data for reading"""
        user = UserService.get_user(user_id)
        if user:
            return UserRead(
                id=user.id,
                storeId=user.storeId,
                username=user.username,
                nickname=user.nickname,
                role=user.role,
                firstName=user.firstName,
                lastName=user.lastName,
                level=user.level,
                onboarding=user.onboarding,
                provider=user.provider,
                email=user.email,
                phone=user.phone,
                avatar=user.avatar,
                avatarBg=user.avatarBg,
                gender=user.gender,
                birthday=user.birthday,
                language=user.language,
                introduction=user.introduction,
                isActive=user.isActive,
                verified=user.verified,
                phoneVerified=user.phoneVerified,
                identity=user.identity,
                profileId=user.profileId,
                nhanhVnBusinessId=user.nhanhVnBusinessId,
                createdAt=user.createdAt,
                updatedAt=user.updatedAt,
                full_name=user.full_name
            )
        return None