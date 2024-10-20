from fastapi import APIRouter, Depends, HTTPException
from app.schemas import ParentCreate, Parent, UserUpdate
from app.dependencies import get_current_active_user
from app.models.parent import Parent as ParentModel
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter()

# Dependency to get the current user
def get_current_parent(current_user: ParentModel = Depends(get_current_active_user)):
    if current_user.role != "parent":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

@router.post("/register", response_model=Parent)
async def register_parent(parent: ParentCreate, db: Session = Depends(get_db)):
    db_parent = ParentModel(**parent.dict())
    db.add(db_parent)
    db.commit()
    db.refresh(db_parent)
    return db_parent

@router.get("/me", response_model=Parent)
async def read_current_parent(current_parent: ParentModel = Depends(get_current_parent)):
    return current_parent

@router.put("/me", response_model=Parent)
async def update_current_parent(
    parent_update: UserUpdate, 
    current_parent: ParentModel = Depends(get_current_parent), 
    db: Session = Depends(get_db)
):
    for key, value in parent_update.dict(exclude_unset=True).items():
        setattr(current_parent, key, value)
    db.commit()
    db.refresh(current_parent)
    return current_parent

