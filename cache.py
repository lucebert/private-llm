import redis
from typing import Optional, Any, Union
import json
import logging
from redis.exceptions import RedisError
from redis.backoff import ExponentialBackoff
from redis.retry import Retry

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheError(Exception):
    """Base exception for cache operations"""
    pass

class CacheConnectionError(CacheError):
    """Raised when Redis connection fails"""
    pass

class CacheSerializationError(CacheError):
    """Raised when JSON serialization/deserialization fails"""
    pass

def create_redis_client() -> redis.Redis:
    """Create Redis client with retry mechanism"""
    retry = Retry(ExponentialBackoff(), 3)  # Retry 3 times with exponential backoff
    
    return redis.Redis(
        host='localhost',
        port=6379,
        db=0,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        socket_keepalive=True,
        retry_on_timeout=True,
        retry=retry,
        health_check_interval=30
    )

redis_client = create_redis_client()

def validate_cache_key(key: str) -> None:
    """Validate cache key for length and safe characters"""
    if not isinstance(key, str):
        raise ValueError("Cache key must be a string")
    if not key:
        raise ValueError("Cache key cannot be empty")
    if len(key) > 512:  # Redis default max key length
        raise ValueError("Cache key exceeds maximum length")
    
    safe_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./:')
    if not all(c in safe_chars for c in key):
        raise ValueError("Cache key contains invalid characters")

def get_cache(key: str, timeout: int = 2) -> Optional[Any]:
    """Get value from Redis cache with improved error handling and timeout"""
    validate_cache_key(key)
    
    try:
        value = redis_client.get(key, timeout=timeout)
        if value is None:
            return None
            
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to deserialize cache value for key {key}: {e}")
            raise CacheSerializationError(f"Failed to deserialize cache value: {e}")
            
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
        raise CacheConnectionError(f"Failed to connect to Redis: {e}")
    except RedisError as e:
        logger.error(f"Redis error when getting key {key}: {e}")
        raise CacheError(f"Cache operation failed: {e}")

def set_cache(key: str, value: Any, expire: int = 3600, timeout: int = 2) -> bool:
    """Set value in Redis cache with expiration, validation and timeout"""
    validate_cache_key(key)
    
    if expire <= 0:
        raise ValueError("Expiration time must be positive")
    if expire > 2592000:  # 30 days in seconds
        raise ValueError("Expiration time cannot exceed 30 days")
        
    try:
        serialized = json.dumps(value)
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to serialize value for key {key}: {e}")
        raise CacheSerializationError(f"Failed to serialize value: {e}")
        
    try:
        return bool(redis_client.setex(key, expire, serialized, timeout=timeout))
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {e}")
        raise CacheConnectionError(f"Failed to connect to Redis: {e}")
    except RedisError as e:
        logger.error(f"Redis error when setting key {key}: {e}")
        raise CacheError(f"Cache operation failed: {e}")