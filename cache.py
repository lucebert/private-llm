import redis
from typing import Optional, Any
import json

redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True,
    socket_timeout=5,
    socket_connect_timeout=5,
    socket_keepalive=True,
    retry_on_timeout=True,
    health_check_interval=30
)

def get_cache(key: str) -> Optional[Any]:
    """Get value from Redis cache"""
    try:
        value = redis_client.get(key)
        return json.loads(value) if value else None
    except:
        return None

def set_cache(key: str, value: Any, expire: int = 3600) -> bool:
    """Set value in Redis cache with expiration"""
    try:
        return redis_client.setex(
            key,
            expire,
            json.dumps(value)
        )
    except:
        return False