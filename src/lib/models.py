from datetime import datetime, timezone, date
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Text, DateTime, Date
import uuid
import hashlib
import os
from enum import Enum

class ProviderEnum(str, Enum):
    local = "local"
    google = "google"
    facebook = "facebook"

class UserBase(SQLModel):
    storeId: Optional[uuid.UUID] = Field(default=None)
    username: str = Field(index=True, unique=True)
    nickname: Optional[str] = None
    role: str = Field(default="user", index=True)
    firstName: Optional[str] = Field(default=None)
    lastName: Optional[str] = Field(default=None)
    level: Optional[str] = None
    onboarding: Optional[int] = None
    provider: ProviderEnum = Field(default=ProviderEnum.local)
    email: Optional[str] = Field(default=None, index=True, unique=True)
    phone: Optional[str] = Field(default=None, index=True, unique=True)
    avatar: Optional[str] = Field(default=None, sa_column=Text)
    avatarBg: Optional[str] = Field(default=None, sa_column=Text)
    gender: Optional[int] = None
    birthday: Optional[date] = Field(default=None, sa_column=Date)
    language: str = Field(default="vi")
    introduction: Optional[str] = Field(default=None, sa_column=Text)
    isActive: bool = Field(default=True, index=True)
    verified: bool = Field(default=False, index=True)
    phoneVerified: bool = Field(default=False, index=True)
    identity: bool = Field(default=False, index=True)
    requestDeletedAt: Optional[datetime] = Field(default=None, sa_column=DateTime)
    deletedAt: Optional[datetime] = Field(default=None, sa_column=DateTime)
    profileId: Optional[str] = Field(default=None, index=True)
    nhanhVnBusinessId: Optional[str] = Field(default=None)

class User(UserBase, table=True):
    __tablename__ = "users"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    createdAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updatedAt: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    salt: Optional[str] = Field(default=None)
    password: Optional[str] = Field(default=None)
    
    @property
    def full_name(self) -> Optional[str]:
        if self.firstName or self.lastName:
            return f"{self.firstName or ''} {self.lastName or ''}".strip()
        return None
    
    def verify_password(self, password: str) -> bool:
        if not self.password or not self.salt:
            return False
        return self._encrypt_password(password, self.salt) == self.password
    
    @staticmethod
    def _encrypt_password(password: str, salt: str) -> str:
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def set_password(self, password: str):
        self.salt = os.urandom(16).hex()
        self.password = self._encrypt_password(password, self.salt)

class UserRead(SQLModel):
    id: uuid.UUID
    storeId: Optional[uuid.UUID]
    username: str
    nickname: Optional[str]
    role: str
    firstName: Optional[str]
    lastName: Optional[str]
    level: Optional[str]
    onboarding: Optional[int]
    provider: ProviderEnum
    email: Optional[str]
    phone: Optional[str]
    avatar: Optional[str]
    avatarBg: Optional[str]
    gender: Optional[int]
    birthday: Optional[date]
    language: str
    introduction: Optional[str]
    isActive: bool
    verified: bool
    phoneVerified: bool
    identity: bool
    profileId: Optional[str]
    nhanhVnBusinessId: Optional[str]
    createdAt: datetime
    updatedAt: datetime
    full_name: Optional[str] = None