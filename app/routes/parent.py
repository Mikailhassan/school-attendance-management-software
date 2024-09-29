# routes/parent.py
from fastapi import APIRouter, Depends
from app.services.registration_service import register_parent, list_parents, get_parent
from app.schemas import ParentRegisterRequest
from app.dependencies import get_current_school_admin

router = APIRouter()

@router.post("/register")
async def register_parent_route(request: ParentRegisterRequest, current_admin: str = Depends(get_current_school_admin)):
    return await register_parent(request, current_admin)

@router.get("/all")
async def list_all_parents(current_admin: str = Depends(get_current_school_admin)):
    return await list_parents()

@router.get("/{parent_id}")
async def get_parent_details(parent_id: int, current_admin: str = Depends(get_current_school_admin)):
    return await get_parent(parent_id)
