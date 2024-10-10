from fastapi import APIRouter, Depends, HTTPException
from app.services.auth_service import AuthService  # Import the AuthService class
from app.schemas import LoginRequest, RegisterRequest
from app.dependencies import get_current_user
from app.models import User  # Ensure the User model is imported

router = APIRouter()
auth_service = AuthService()  # Create an instance of AuthService

@router.post("/login")
async def login(request: LoginRequest):
    """
    Log in a user and return an authentication token.
    """
    token = await auth_service.login_user(request.email, request.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": token}

@router.post("/register")
async def register(request: RegisterRequest):
    """
    Register a new user in the system.
    """
    new_user = await auth_service.register_user(request.dict())  # Ensure you pass the required user data
    if not new_user:
        raise HTTPException(status_code=400, detail="User registration failed")
    return {"message": "User registered successfully", "user": new_user}

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """
    Log out the current user and invalidate their session.
    """
    await auth_service.logout_user(current_user)
    return {"message": "Logout successful"}
