from datetime import datetime, timezone
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from app.core.dependencies import get_auth_service
from app.core.logging import logger
from app.core.errors import AuthenticationError

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.exclude_paths = {
            '/api/v1/auth/login',
            '/api/v1/auth/register',
            '/api/v1/auth/refresh-token',
            '/api/v1/auth/forgot-password',
            '/api/v1/auth/reset-password',
            '/api/v1/auth/health',
            '/api/v1/auth/validate-token',
            '/api/health',
            '/api/docs',
            '/api/redoc',
            '/openapi.json'
        }

    async def _extract_token(self, request: Request) -> str | None:
        """Extract token from Authorization header or cookies"""
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.replace('Bearer ', '')
        
        # Fallback to cookie
        token = request.cookies.get('access_token')
        return token.replace('Bearer ', '') if token else None

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """Process the request and handle authentication"""

        # Skip middleware for excluded paths and OPTIONS requests
        if request.method == "OPTIONS" or request.url.path in self.exclude_paths:
            return await call_next(request)

        try:
            # Extract token
            token = await self._extract_token(request)
            if not token:
                logger.warning("No authentication token provided")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "detail": {
                            "valid": False,
                            "message": "Authentication required",
                            "redirect": "/login"
                        }
                    }
                )

            # Get auth service
            auth_service = await get_auth_service(request)
            
            try:
                # Validate token and set up request state
                token_payload = await auth_service.validate_token(token)
                
                # Store token and payload in request state
                request.state.access_token = token
                request.state.token_payload = token_payload
                request.state.user_id = token_payload.get('sub')
                request.state.user_role = token_payload.get('role')
                request.state.session_id = token_payload.get('jti')

                # Process request
                response = await call_next(request)

                # Set session cookie if not present
                if not request.cookies.get('session'):
                    session_id = token_payload.get('jti')
                    response.set_cookie(
                        key='session',
                        value=session_id,
                        httponly=True,
                        secure=True,
                        samesite='lax',
                        max_age=3600  # 1 hour
                    )

                return response

            except AuthenticationError as auth_err:
                logger.warning(f"Authentication failed: {str(auth_err)}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "detail": {
                            "valid": False,
                            "message": str(auth_err),
                            "redirect": "/login"
                        }
                    }
                )

        except Exception as e:
            logger.error(f"Auth middleware error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": {
                        "message": "Internal server error",
                        "code": "SERVER_ERROR"
                    }
                }
            )

    def _log_request_debug(self, request: Request, token: str | None) -> None:
        """Log debug information about the request"""
        debug_info = {
            "path": request.url.path,
            "method": request.method,
            "has_token": bool(token),
            "headers": dict(request.headers),
            "cookies": dict(request.cookies)
        }
        logger.debug(f"Request debug info: {debug_info}")