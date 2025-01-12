from redis import asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger

# Redis connection settings
REDIS_URL = settings.REDIS_URL or "redis://localhost:6379"
REDIS_SESSION_DB = 0  
SESSION_TTL = 3600  

redis_client = None

async def init_redis():
    """Initialize Redis connection"""
    global redis_client
    try:
        redis_client = await aioredis.from_url(
            REDIS_URL,
            db=REDIS_SESSION_DB,
            decode_responses=True 
        )
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established successfully")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        raise

async def close_redis():
    """Close Redis connection"""
    if redis_client:
        await redis_client.close()
        logger.info("Redis connection closed")

async def get_redis() -> aioredis.Redis:
    """Get Redis client instance"""
    if not redis_client:
        await init_redis()
    return redis_client