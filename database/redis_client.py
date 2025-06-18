"""
Redis client connection and basic operations for the Karaoke Backend.
Handles connection pooling, basic CRUD operations, and job state management.
"""

import redis
import json
from typing import Any, Dict, List, Optional, Union
from contextlib import contextmanager
import pickle

from config import settings
from utils.logger import get_logger

logger = get_logger("redis_client")


class RedisClient:
    """Redis client wrapper with connection pooling and error handling."""
    
    def __init__(self):
        """Initialize Redis connection pool."""
        self._pool = None
        self._client = None
        self.connect()
    
    def connect(self):
        """Establish Redis connection with connection pooling."""
        try:
            # Create connection pool
            self._pool = redis.ConnectionPool(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
                decode_responses=True,
                max_connections=20,
                retry_on_timeout=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Create Redis client
            self._client = redis.Redis(connection_pool=self._pool)
            
            # Test connection
            self._client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            raise ConnectionError(f"Could not connect to Redis: {e}")
    
    def disconnect(self):
        """Close Redis connections."""
        if self._pool:
            self._pool.disconnect()
            logger.info("Redis connection closed")
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance."""
        if not self._client:
            self.connect()
        return self._client
    
    def ping(self) -> bool:
        """Test Redis connection."""
        try:
            return self.client.ping()
        except Exception as e:
            logger.error("Redis ping failed", error=str(e))
            return False
    
    def set(self, key: str, value: Any, ex: int = None) -> bool:
        """Set a key-value pair with optional expiration."""
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            return self.client.set(key, value, ex=ex)
        except Exception as e:
            logger.error("Redis SET failed", key=key, error=str(e))
            return False
    
    def get(self, key: str, parse_json: bool = True) -> Optional[Any]:
        """Get value by key with optional JSON parsing."""
        try:
            value = self.client.get(key)
            if value is None:
                return None
            
            if parse_json:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        except Exception as e:
            logger.error("Redis GET failed", key=key, error=str(e))
            return None
    
    def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        try:
            return self.client.delete(*keys)
        except Exception as e:
            logger.error("Redis DELETE failed", keys=keys, error=str(e))
            return 0
    
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error("Redis EXISTS failed", key=key, error=str(e))
            return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration time on a key."""
        try:
            return self.client.expire(key, seconds)
        except Exception as e:
            logger.error("Redis EXPIRE failed", key=key, error=str(e))
            return False
    
    def ttl(self, key: str) -> int:
        """Get time to live for a key."""
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error("Redis TTL failed", key=key, error=str(e))
            return -1
    
    def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern."""
        try:
            return self.client.keys(pattern)
        except Exception as e:
            logger.error("Redis KEYS failed", pattern=pattern, error=str(e))
            return []
    
    def hset(self, name: str, mapping: Dict[str, Any]) -> int:
        """Set hash fields."""
        try:
            # Convert values to JSON strings if needed
            processed_mapping = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    processed_mapping[key] = json.dumps(value)
                elif value is None:
                    processed_mapping[key] = ""  # Store None as empty string
                elif hasattr(value, 'value'):  # Handle Enum types
                    processed_mapping[key] = value.value
                else:
                    processed_mapping[key] = str(value)
            
            return self.client.hset(name, mapping=processed_mapping)
        except Exception as e:
            logger.error("Redis HSET failed", name=name, error=str(e))
            return 0
    
    def hget(self, name: str, key: str, parse_json: bool = True) -> Optional[Any]:
        """Get hash field value."""
        try:
            value = self.client.hget(name, key)
            if value is None:
                return None
            
            if parse_json:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        except Exception as e:
            logger.error("Redis HGET failed", name=name, key=key, error=str(e))
            return None
    
    def hgetall(self, name: str, parse_json: bool = True) -> Dict[str, Any]:
        """Get all hash fields and values."""
        try:
            data = self.client.hgetall(name)
            if not data:
                return {}
            
            if parse_json:
                processed_data = {}
                for key, value in data.items():
                    if value == "":  # Handle empty strings as None
                        processed_data[key] = None
                    else:
                        try:
                            processed_data[key] = json.loads(value)
                        except (json.JSONDecodeError, TypeError):
                            # Try to convert to appropriate types
                            if value.lower() in ('true', 'false'):
                                processed_data[key] = value.lower() == 'true'
                            elif value.isdigit():
                                processed_data[key] = int(value)
                            elif value.replace('.', '').isdigit():
                                processed_data[key] = float(value)
                            else:
                                processed_data[key] = value
                return processed_data
            return data
        except Exception as e:
            logger.error("Redis HGETALL failed", name=name, error=str(e))
            return {}
    
    def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        try:
            return self.client.hdel(name, *keys)
        except Exception as e:
            logger.error("Redis HDEL failed", name=name, keys=keys, error=str(e))
            return 0
    
    def lpush(self, name: str, *values: Any) -> int:
        """Push values to the left of a list."""
        try:
            processed_values = []
            for value in values:
                if isinstance(value, (dict, list)):
                    processed_values.append(json.dumps(value))
                else:
                    processed_values.append(str(value))
            
            return self.client.lpush(name, *processed_values)
        except Exception as e:
            logger.error("Redis LPUSH failed", name=name, error=str(e))
            return 0
    
    def rpop(self, name: str, parse_json: bool = True) -> Optional[Any]:
        """Pop value from the right of a list."""
        try:
            value = self.client.rpop(name)
            if value is None:
                return None
            
            if parse_json:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            return value
        except Exception as e:
            logger.error("Redis RPOP failed", name=name, error=str(e))
            return None
    
    def llen(self, name: str) -> int:
        """Get list length."""
        try:
            return self.client.llen(name)
        except Exception as e:
            logger.error("Redis LLEN failed", name=name, error=str(e))
            return 0


# Global Redis client instance
redis_client = RedisClient()


@contextmanager
def get_redis_client():
    """Context manager for Redis client."""
    try:
        yield redis_client
    finally:
        pass  # Connection pooling handles cleanup


def test_redis_connection() -> bool:
    """Test Redis connection and basic operations."""
    try:
        logger.info("Testing Redis connection...")
        
        # Test ping
        if not redis_client.ping():
            logger.error("Redis ping failed")
            return False
        
        # Test basic operations
        test_key = "test:connection"
        test_value = {"test": True, "timestamp": "now"}
        
        # Test SET/GET
        if not redis_client.set(test_key, test_value, ex=60):
            logger.error("Redis SET test failed")
            return False
        
        retrieved_value = redis_client.get(test_key)
        if retrieved_value != test_value:
            logger.error("Redis GET test failed", expected=test_value, got=retrieved_value)
            return False
        
        # Test DELETE
        if not redis_client.delete(test_key):
            logger.error("Redis DELETE test failed")
            return False
        
        logger.info("Redis connection test successful")
        return True
        
    except Exception as e:
        logger.error("Redis connection test failed", error=str(e))
        return False 