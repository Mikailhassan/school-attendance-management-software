# routes/auth.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.auth_service import login_user, register_user, logout_user
from app.schemas import LoginRequest, RegisterRequest
from app.dependencies import get_current_user

router = APIRouter()

@router.post("/login")
async def login(request: LoginRequest):
    return await login_user(request)

@router.post("/register")
async def register(request: RegisterRequest):
    return await register_user(request)

@router.post("/logout")
async def logout(current_user: str = Depends(get_current_user)):
    return await logout_user(current_user)
