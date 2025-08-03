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
    """Create database engine with optimized connection pooling and monitoring"""
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=10,  # Increased for better concurrency
        max_overflow=20,  # Allow more overflow connections
        pool_timeout=60,  # Increased timeout for busy periods
        pool_recycle=3600,  # Recycle connections every hour
        pool_pre_ping=True,  # Enable connection health checks
        echo_pool=True  # Enable pool event logging
    )
    
    @event.listens_for(engine, 'connect')
    def connect(dbapi_connection, connection_record):
        logger.info(f"New database connection established. Total connections: {engine.pool.size() + engine.pool.overflow()}")
        if engine.pool.overflow() > 0:
            logger.warning(f"Using overflow connection. Current overflow: {engine.pool.overflow()}")

    @event.listens_for(engine, 'reset')
    def reset(dbapi_connection, connection_record):
        logger.info("Database connection reset")

    @event.listens_for(engine, 'checkin')
    def checkin(dbapi_connection, connection_record):
        logger.info(f"Database connection returned to pool. Available: {engine.pool.size()}")

    @event.listens_for(engine, 'close')
    def close(dbapi_connection, connection_record):
        logger.info("Database connection closed")

    @event.listens_for(engine, 'checkout')
    def checkout(dbapi_connection, connection_record, connection_proxy):
        logger.info(f"Database connection checked out from pool. Available connections: {engine.pool.size()}")
        if engine.pool.overflow() >= engine.pool._max_overflow * 0.8:
            logger.warning(f"Connection pool nearing capacity. Overflow: {engine.pool.overflow()}/{engine.pool._max_overflow}")

    @event.listens_for(engine, 'invalidate')
    def invalidate(dbapi_connection, connection_record, exception):
        logger.warning(f"Database connection invalidated due to error: {exception}")

    return engine

# Create engine with connection pooling and event handling
engine = create_db_engine()

# Create session factory with thread safety and performance optimizations
SessionLocal = scoped_session(
    sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False,  # Improve performance by not expiring objects
    )
)

Base = declarative_base()

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True)
    role = Column(String(50), nullable=False, index=True)  # Index for role-based queries
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)  # Index for time-based queries

    # Composite index for common query pattern
    __table_args__ = (
        Index('idx_role_timestamp', 'role', 'timestamp'),
    )

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

from functools import wraps
from typing import Optional, TypeVar, Callable, Any
from sqlalchemy.orm import Query

T = TypeVar('T')

def cache_query(ttl: int = 300) -> Callable:
    """Decorator to cache query results"""
    def decorator(f: Callable[..., T]) -> Callable[..., T]:
        @wraps(f)
        def wrapper(*args, **kwargs) -> T:
            cache_key = f"query:{f.__name__}:{str(args)}:{str(kwargs)}"
            result = get_cache(cache_key)
            if result is not None:
                return result
            result = f(*args, **kwargs)
            set_cache(cache_key, result, ttl)
            return result
        return wrapper
    return decorator

@contextmanager
def get_db() -> Generator[scoped_session, None, None]:
    """Get database session with improved error handling, automatic rollback, and query caching"""
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