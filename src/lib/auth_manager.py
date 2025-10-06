from typing import Optional

from .db_services import UserService
from lib.models import UserRead


class AuthManager:
    def __init__(self):
        self.user_service = UserService()
    
    def authenticate_user(self, username_or_email: str, password: str) -> Optional[UserRead]:
        user = self.user_service.authenticate_user(username_or_email, password)
        if user:
            return self.user_service.get_user_profile(user.id)
        return None
    
    def get_user_by_id(self, user_id: str) -> Optional[UserRead]:
        return self.user_service.get_user_profile(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[UserRead]:
        user = self.user_service.get_user_by_email(email)
        if user:
            return self.user_service.get_user_profile(user.id)
        return None
    
    def get_user_by_username(self, username: str) -> Optional[UserRead]:
        user = self.user_service.get_user_by_username(username)
        if user:
            return self.user_service.get_user_profile(user.id)
        return None