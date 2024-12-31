from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from fastapi import HTTPException, status, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from jose import jwt, JWTError
from passlib.context import CryptContext
import uuid
from app.models import User, RevokedToken
from app.core.logging import logger
from app.core.config import get_jwt_settings

def set_auth_cookies(
    response: Response,
    request: Request,
    access_token: str,
    refresh_token: str,
    access_token_expire_minutes: int,
    refresh_token_expire_days: int
) -> None:
    """Set authentication cookies with proper settings"""
    secure = request.url.scheme == "https"
    response.set_cookie(
        key="access_token",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=access_token_expire_minutes * 60,
        expires=datetime.now(timezone.utc) + timedelta(minutes=access_token_expire_minutes)
    )
    response.set_cookie(
        key="refresh_token",
        value=f"Bearer {refresh_token}",
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=refresh_token_expire_days * 24 * 60 * 60,
        expires=datetime.now(timezone.utc) + timedelta(days=refresh_token_expire_days)
    )

def clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies"""
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token")

class AuthService:
    """Service for handling authentication and user management"""
    
    def __init__(self, db: AsyncSession):
        """Initialize auth service with database session and settings"""
        self.db = db
        self.jwt_settings = get_jwt_settings()
        self.secret_key = self.jwt_settings["secret_key"]
        self.algorithm = self.jwt_settings["algorithm"]
        self.access_token_expire_minutes = self.jwt_settings["access_token_expire_minutes"]
        self.refresh_token_expire_days = self.jwt_settings["refresh_token_expire_days"]
        
        # Configure password hashing
        self.pwd_context = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
            bcrypt__rounds=12
        )

    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return self.pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Retrieve user by email"""
        try:
            query = select(User).where(User.email == email)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error retrieving user by email: {str(e)}")
            return None

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Retrieve user by ID"""
        try:
            query = select(User).where(User.id == user_id)
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error retrieving user by ID: {str(e)}")
            return None

    async def create_access_token(
        self,
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create JWT access token"""
        try:
            to_encode = data.copy()
            expire = datetime.now(timezone.utc) + (
                expires_delta if expires_delta
                else timedelta(minutes=self.access_token_expire_minutes)
            )
            to_encode.update({
                "exp": expire,
                "type": "access",
                "jti": str(uuid.uuid4())
            })
            return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        except Exception as e:
            logger.error(f"Error creating access token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )

    async def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        try:
            to_encode = data.copy()
            expire = datetime.now(timezone.utc) + timedelta(days=self.refresh_token_expire_days)
            to_encode.update({
                "exp": expire,
                "type": "refresh",
                "jti": str(uuid.uuid4())
            })
            return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        except Exception as e:
            logger.error(f"Error creating refresh token: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create refresh token"
            )

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token with comprehensive error handling"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Validate token claims
            token_type = payload.get("type")
            exp = payload.get("exp")
            sub = payload.get("sub")
            
            if not all([token_type, exp, sub]):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format"
                )
                
            # Check expiration
            exp_datetime = datetime.fromtimestamp(exp, tz=timezone.utc)
            if exp_datetime < datetime.now(timezone.utc):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
                
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTClaimsError:
            logger.error("Invalid token claims")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims"
            )
        except JWTError as e:
            logger.error(f"Token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Unexpected token verification error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def revoke_token(self, token: str) -> bool:
        """Revoke a JWT token by storing its JTI"""
        try:
            payload = await self.verify_token(token)
            jti = payload.get('jti')
            
            if not jti:
                logger.error("Token does not contain JTI claim")
                return False
                
            revoked_token = RevokedToken(
                jti=jti,
                expiration=datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
            )
            self.db.add(revoked_token)
            await self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error revoking token: {str(e)}")
            await self.db.rollback()
            return False

    async def check_token_revocation(self, token: str) -> bool:
        """Check if token has been revoked using JTI"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            jti = payload.get('jti')
            
            if not jti:
                logger.warning("Token does not contain JTI claim")
                return False
            
            query = select(RevokedToken).where(
                and_(
                    RevokedToken.jti == jti,
                    RevokedToken.expiration > datetime.now(timezone.utc)
                )
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none() is not None
            
        except Exception as e:
            logger.error(f"Token revocation check error: {str(e)}")
            return False

    async def refresh_tokens(
        self,
        refresh_token: str,
        response: Response,
        request: Request
    ) -> Dict[str, Any]:
        """Refresh access and refresh tokens"""
        try:
            payload = await self.verify_token(refresh_token)
            
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            if await self.check_token_revocation(refresh_token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )

            user_id = int(payload["sub"])
            user = await self.get_user_by_id(user_id)
            
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User is inactive or does not exist"
                )

            # Create new token data
            token_data = {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "school_id": str(user.school_id) if user.school_id else None
            }

            new_access_token = await self.create_access_token(token_data)
            new_refresh_token = await self.create_refresh_token(token_data)

            # Revoke old refresh token
            await self.revoke_token(refresh_token)

            # Set new cookies
            set_auth_cookies(
                response,
                request,
                new_access_token,
                new_refresh_token,
                self.access_token_expire_minutes,
                self.refresh_token_expire_days
            )

            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not refresh tokens"
            )

    async def authenticate_user(
        self,
        email: str,
        password: str,
        response: Response,
        request: Request,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """Authenticate user and generate tokens"""
        try:
            user = await self.get_user_by_email(email)

            if not user:
                logger.warning(f"Authentication attempt for non-existent user: {email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials" if language == 'en' else "بيانات اعتماد غير صالحة"
                )

            if not await self.verify_password(password, user.password_hash):
                logger.warning(f"Failed authentication attempt for user: {email}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials" if language == 'en' else "بيانات اعتماد غير صالحة"
                )

            if not user.is_active:
                logger.warning(f"Authentication attempt for inactive user: {email}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is inactive" if language == 'en' else "الحساب غير نشط"
                )

            token_data = {
                "sub": str(user.id),
                "email": user.email,
                "role": user.role,
                "school_id": str(user.school_id) if user.school_id else None
            }

            access_token = await self.create_access_token(token_data)
            refresh_token = await self.create_refresh_token(token_data)

            # Set authentication cookies
            set_auth_cookies(
                response,
                request,
                access_token,
                refresh_token,
                self.access_token_expire_minutes,
                self.refresh_token_expire_days
            )
            
            logger.info(f"User authenticated successfully: {email}")
            
            return {
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "school_id": user.school_id,
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at
                },
                "access_token": access_token,
                "refresh_token": refresh_token,
                "role": user.role
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication failed" if language == 'en' else "فشل المصادقة"
            )

    async def get_current_user(self, token: str) -> Optional[User]:
        """Verify token and return current user"""
        try:
            payload = await self.verify_token(token)
            
            if not payload or "sub" not in payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )

            if await self.check_token_revocation(token):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )

            user_id = int(payload["sub"])
            user = await self.get_user_by_id(user_id)
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User is inactive"
                )
                
            return user
            
        except HTTPException:
            raise
        except ValueError as e:
            logger.error(f"User ID parsing error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user ID in token"
            )