from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas import ParentCreate, ParentUpdate, ParentResponse, ParentRegistrationRequest, ParentCreateResponse, ParentUpdateResponse
from app.core.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.parent import Parent as ParentModel  # Ensure correct import
from app.models.user import User as UserModel  # Ensure the User model is available

router = APIRouter()

# Dependency to get the current user
def get_current_parent(current_user: ParentModel = Depends(get_current_active_user)):
    if current_user.role != "parent":
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return current_user

@router.post("/register", response_model=ParentCreateResponse)  # Use ParentCreateResponse for response
async def register_parent(parent: ParentCreate, db: Session = Depends(get_db)):
    db_user = UserModel(email=parent.email, password=parent.password, role="parent")
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Now, create the parent profile
    db_parent = ParentModel(
        name=parent.name,
        email=parent.email,
        phone=parent.phone,
        address=parent.address,
        student_id=parent.student_id,
        school_id=parent.school_id,
        user_id=db_user.id,  # Associate parent with the created user
    )
    db.add(db_parent)
    db.commit()
    db.refresh(db_parent)
    return db_parent  # Return the response model (ParentCreateResponse)

@router.get("/me", response_model=ParentResponse)  # Use ParentResponse for the current parent profile
async def read_current_parent(current_parent: ParentModel = Depends(get_current_parent)):
    return current_parent  # Return the parent profile details

@router.put("/me", response_model=ParentUpdateResponse)  # Use ParentUpdateResponse for updating
async def update_current_parent(
    parent_update: ParentUpdate,  # Use ParentUpdate for the request
    current_parent: ParentModel = Depends(get_current_parent),
    db: Session = Depends(get_db)
):
    # Update only the fields that have been set (exclude_unset=True)
    for key, value in parent_update.dict(exclude_unset=True).items():
        setattr(current_parent, key, value)

    db.commit()
    db.refresh(current_parent)
    return current_parent  # Return the updated parent profile details
