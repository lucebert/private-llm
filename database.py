from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, OperationalError, DisconnectionError
import datetime
import logging
from typing import Generator
from contextlib import contextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseError(Exception):
    """Base exception for database operations"""
    pass

class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails"""
    pass

class DatabaseSessionError(DatabaseError):
    """Raised when session operations fail"""
    pass

def create_db_engine(database_url: str = 'sqlite:///chat_history.db'):
    """Create database engine with connection pooling and event handlers"""
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True  # Enable connection health checks
    )
    
    @event.listens_for(engine, 'connect')
    def connect(dbapi_connection, connection_record):
        logger.info("New database connection established")

    @event.listens_for(engine, 'checkout')
    def checkout(dbapi_connection, connection_record, connection_proxy):
        logger.debug("Database connection checked out from pool")

    @event.listens_for(engine, 'invalidate')
    def invalidate(dbapi_connection, connection_record, exception):
        logger.warning(f"Database connection invalidated due to error: {exception}")

    return engine

# Create engine with connection pooling and event handling
engine = create_db_engine()

# Create session factory with thread safety
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

Base = declarative_base()

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

    def __init__(self, role: str, content: str):
        self.validate_role(role)
        self.validate_content(content)
        super().__init__(role=role, content=content)

    @staticmethod
    def validate_role(role: str) -> None:
        valid_roles = {"user", "assistant", "system"}
        if not role or role not in valid_roles:
            raise ValueError(f"Invalid role: {role}. Must be one of {valid_roles}")

    @staticmethod
    def validate_content(content: str) -> None:
        if not content or not isinstance(content, str):
            raise ValueError("Content must be a non-empty string")
        if len(content) > 10000:  # Reasonable max length for SQLite TEXT
            raise ValueError("Content exceeds maximum length of 10000 characters")

try:
    # Create tables with proper error handling
    Base.metadata.create_all(bind=engine)
except SQLAlchemyError as e:
    logger.error(f"Failed to create database tables: {e}")
    raise DatabaseError(f"Database initialization failed: {e}")

@contextmanager
def get_db() -> Generator[scoped_session, None, None]:
    """Get database session with improved error handling and automatic rollback"""
    session = SessionLocal()
    try:
        yield session
    except OperationalError as e:
        session.rollback()
        logger.error(f"Database operational error: {e}")
        raise DatabaseConnectionError(f"Database connection failed: {e}")
    except SQLAlchemyError as e:
        session.rollback()
        logger.error(f"Database error: {e}")
        raise DatabaseSessionError(f"Database operation failed: {e}")
    finally:
        session.close()