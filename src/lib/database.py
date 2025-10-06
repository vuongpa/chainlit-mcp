"""
Database configuration and connection management using SQLModel and PostgreSQL
"""

import os
from typing import Generator
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
from sqlalchemy import text
load_dotenv()

class DatabaseConfig:
    """Database configuration class"""
    
    def __init__(self):
        raw_database_url: str = os.getenv("DATABASE_MAIN_URL", "")
        if not raw_database_url:
            raise ValueError("DATABASE_MAIN_URL environment variable is required")
        
        # Remove schema from URL if present (PostgreSQL doesn't support it in URL)
        self.database_url = raw_database_url.split('?')[0] if '?' in raw_database_url else raw_database_url
        
        self.schema: str = os.getenv("OREKA_DB_SCHEMA", "public")
        
        # Connection pool settings
        self.pool_size: int = int(os.getenv("DB_POOL_SIZE", "10"))
        self.max_overflow: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.pool_timeout: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.pool_recycle: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))

# Global database configuration instance
db_config = DatabaseConfig()

# Create the engine
engine = create_engine(
    db_config.database_url,
    poolclass=QueuePool,
    pool_size=db_config.pool_size,
    max_overflow=db_config.max_overflow,
    pool_timeout=db_config.pool_timeout,
    pool_recycle=db_config.pool_recycle,
    echo=os.getenv("DB_ECHO", "false").lower() == "true"  # Set to True for SQL logging
)

def create_db_and_tables():
    """Create database tables based on SQLModel metadata"""
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """
    Dependency function to get a database session.
    Use this with FastAPI's Depends() or in your application logic.
    """
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

def get_session_context() -> Session:
    """
    Get a database session for use in context managers.
    
    Example:
        with get_session_context() as session:
            # Use session here
            pass
    """
    return Session(engine)

class DatabaseManager:
    @staticmethod
    def test_connection() -> bool:
        try:
            with Session(engine) as session:
                session.exec(text("SELECT 1"))
                return True
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
    
    @staticmethod
    def close_connections():
        """Close all database connections"""
        engine.dispose()