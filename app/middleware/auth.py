from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from app.core.dependencies import get_auth_service
from app.core.logging import logger
from app.core.errors import AuthenticationError, get_error_message

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        exclude_paths: set[str] = None,
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or {
            '/api/v1/auth/login',
            '/api/v1/auth/register',
            '/api/v1/auth/refresh-token',  # Important: this must be excluded
            '/api/v1/auth/forgot-password',
            '/api/v1/auth/reset-password',
            '/api/v1/auth/health',
            '/api/v1/auth/validate-token',
            '/api/health',
            '/docs',
            '/redoc',
            '/openapi.json'
        }

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        
        # First check if path is excluded
        if path in self.exclude_paths:
            return await call_next(request)
            
        # Important: Check path prefix BEFORE trying to validate token
        if path.startswith('/api/v1/auth/'):
            return await call_next(request)

        # For all other routes, verify token
        token = await self._extract_token(request)
        
        if not token:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "No token provided",
                    "code": "NO_TOKEN"
                }
            )

        try:
            auth_service = await get_auth_service(request)
            payload = await auth_service.verify_token(token)
            
            if not payload:
                raise AuthenticationError("Invalid token")

            request.state.token_payload = payload
            return await call_next(request)
            
        except Exception as e:
            logger.error(f"Auth error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "detail": "Invalid or expired token",
                    "code": "INVALID_TOKEN"
                }
            )