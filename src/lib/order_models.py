from datetime import datetime
from sqlmodel import SQLModel, Field
import uuid


class Balance(SQLModel, table=True):
    __tablename__ = "v2_balances"
    
    userId: uuid.UUID = Field(primary_key=True)
    balance: int = Field(...)
    point: int = Field(...)
    createdAt: datetime = Field(default_factory=datetime.utcnow)
    updatedAt: datetime = Field(default_factory=datetime.utcnow)


class BalanceRead(SQLModel):
    """Balance model for reading data"""
    userId: uuid.UUID
    balance: int
    point: int
    createdAt: datetime
    updatedAt: datetime
    
    @property
    def balance_formatted(self) -> str:
        return f"{self.balance:,}"
    
    @property
    def point_formatted(self) -> str:
        return f"{self.point:,}"


class Transaction(SQLModel, table=True):
    __tablename__ = "v2_transactions"
    
    id: uuid.UUID = Field(primary_key=True)
    walletId: uuid.UUID = Field(...)
    newBalance: int = Field(...)

class Payment(SQLModel, table=True):
    __tablename__ = "v2_payments"
    
    id: uuid.UUID = Field(primary_key=True)
    amount: int = Field(...)


class Deposit(SQLModel, table=True):
    __tablename__ = "v2_deposits"
    
    id: uuid.UUID = Field(primary_key=True)
    amount: int = Field(...)


class Withdraw(SQLModel, table=True):
    __tablename__ = "v2_withdraws"
    
    id: uuid.UUID = Field(primary_key=True)  
    amount: int = Field(...)