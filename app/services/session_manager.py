# app/services/session_manager.py
from datetime import datetime, timezone, timedelta
import asyncio
from typing import Dict, Any, Optional,Tuple
import logging
import uuid
import json
from app.core.errors import AuthenticationError
import redis.asyncio as aioredis


logger = logging.getLogger(__name__)

       
class SessionManager:
    def __init__(self, redis_url: str = "redis://localhost:6379", session_expire_minutes: int = 60):
        self._session_expire_minutes = session_expire_minutes
        self._redis: Optional[aioredis.Redis] = None
        self._redis_url = redis_url

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self._redis = await aioredis.from_url(
                self._redis_url,
                decode_responses=True
            )
            await self._redis.ping()
            logger.info("Redis connection established successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    async def close(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis connection closed")

    async def _create_session(self, user_id: str, token_data: Dict[str, Any]) -> str:
        """Create a new session with Redis storage"""
        try:
            session_id = str(uuid.uuid4())
            current_time = datetime.now(timezone.utc)
            expires_at = current_time + timedelta(minutes=self._session_expire_minutes)
            
            # Sanitize and prepare session data
            device_info = token_data.get("device_info", {}) or {}  # Handle None case
            session_data = {
                "user_id": str(user_id),
                "created_at": current_time.isoformat(),
                "last_activity": current_time.isoformat(),
                "expires_at": expires_at.isoformat(),
                "token_data": json.dumps(token_data or {}),  # Handle None case
                "device_info": json.dumps(device_info),
                "ip_address": str(device_info.get("ip", "")) or ""  # Handle None case
            }
            
            # Store in Redis
            await self._redis.hset(f"session:{session_id}", mapping=session_data)
            
            # Set expiration
            await self._redis.expire(
                f"session:{session_id}", 
                int(timedelta(minutes=self._session_expire_minutes).total_seconds())
            )
            
            logger.debug(
                "Session created",
                extra={
                    "session_id": session_id,
                    "user_id": user_id,
                    "expires_at": expires_at.isoformat()
                }
            )
            
            return session_id
                
        except Exception as e:
            logger.error(
                "Session creation failed",
                exc_info=True,
                extra={
                    "error_type": type(e).__name__,
                    "user_id": user_id
                }
            )
            raise AuthenticationError(
                message="Failed to create session",
                error_code="SESSION_CREATION_ERROR"
            )

    async def _validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate session with Redis storage"""
        try:
            if not session_id:
                logger.debug("No session ID provided")
                return None
            
            # Get session from Redis
            session_data = await self._redis.hgetall(f"session:{session_id}")
            
            if not session_data:
                logger.warning(f"Session not found: {session_id}")
                return None
            
            # Parse timestamps
            current_time = datetime.now(timezone.utc)
            expires_at = datetime.fromisoformat(session_data["expires_at"])
            
            # Check expiration
            if current_time > expires_at:
                logger.info(
                    "Session expired",
                    extra={
                        "session_id": session_id,
                        "expired_at": expires_at.isoformat()
                    }
                )
                await self._end_session(session_id)
                return None
            
            # Update session
            new_expires_at = current_time + timedelta(minutes=self._session_expire_minutes)
            
            # Update last activity and expiration in Redis
            update_data = {
                "last_activity": current_time.isoformat(),
                "expires_at": new_expires_at.isoformat()
            }
            await self._redis.hset(f"session:{session_id}", mapping=update_data)
            
            # Reset TTL
            await self._redis.expire(
                f"session:{session_id}", 
                int(timedelta(minutes=self._session_expire_minutes).total_seconds())
            )
            
            # Parse stored JSON data
            session_data.update(update_data)
            session_data["token_data"] = json.loads(session_data["token_data"])
            session_data["device_info"] = json.loads(session_data["device_info"])
            
            logger.debug(
                "Session validated and updated",
                extra={
                    "session_id": session_id,
                    "new_expiry": new_expires_at.isoformat()
                }
            )
            
            return session_data
                        
        except Exception as e:
            logger.error(
                "Session validation error",
                exc_info=True,
                extra={
                    "session_id": session_id,
                    "error_type": type(e).__name__
                }
            )
            return None

    async def _end_session(self, session_id: str) -> None:
        """End session with Redis cleanup"""
        try:
            # Get session data before deletion for logging
            session_data = await self._redis.hgetall(f"session:{session_id}")
            
            if session_data:
                # Delete session
                await self._redis.delete(f"session:{session_id}")
                
                created_at = datetime.fromisoformat(session_data["created_at"])
                duration = (datetime.now(timezone.utc) - created_at).total_seconds()
                
                logger.info(
                    "Session ended",
                    extra={
                        "session_id": session_id,
                        "duration_seconds": duration,
                        "user_id": session_data.get("user_id")
                    }
                )
        except Exception as e:
            logger.error(
                "Failed to end session",
                exc_info=True,
                extra={
                    "session_id": session_id,
                    "error_type": type(e).__name__
                }
            )