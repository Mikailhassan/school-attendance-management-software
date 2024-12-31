from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.schemas import (
    ParentCreate, ParentUpdate, ParentResponse, 
    ParentRegistrationRequest, ParentCreateResponse, 
    ParentUpdateResponse
)
from app.core.dependencies import get_current_active_user, get_db
from app.models.parent import Parent as ParentModel
from app.models.user import User as UserModel
from app.services.registration_service import ParentRegistrationService

router = APIRouter()

def get_current_parent(current_user: ParentModel = Depends(get_current_active_user)):
    if current_user.role != "parent":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

@router.post("/register", response_model=ParentCreateResponse)
async def register_parent(
    parent: ParentCreate, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    service = ParentRegistrationService(db)
    return await service.create_parent_account(parent)

@router.post("/resend-credentials")
async def resend_parent_credentials(
    email: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    service = ParentRegistrationService(db)
    return await service.resend_credentials(email)

@router.get("/me", response_model=ParentResponse)
async def read_current_parent(current_parent: ParentModel = Depends(get_current_parent)):
    return current_parent

@router.get("/me/children")
async def get_parent_children(
    current_parent: ParentModel = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    service = ParentRegistrationService(db)
    return await service.get_children(current_parent.id)

@router.put("/me", response_model=ParentUpdateResponse)
async def update_current_parent(
    parent_update: ParentUpdate,
    current_parent: ParentModel = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    # Update only the fields that have been set
    for key, value in parent_update.dict(exclude_unset=True).items():
        setattr(current_parent, key, value)

    db.commit()
    db.refresh(current_parent)
    return current_parent