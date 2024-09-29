# routes/admin.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import User, School
from app.schemas import SchoolCreate, UserCreate
from app.database import SessionLocal
from app.services.auth_service import get_current_admin

router = APIRouter()

# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Admin Dashboard Route (Can return admin-specific stats or summaries)
@router.get("/dashboard", response_description="Admin Dashboard")
async def admin_dashboard(current_admin: User = Depends(get_current_admin)):
    return {"message": "Welcome to the Admin Dashboard!"}

# Create a new school
@router.post("/schools", response_model=School)
async def create_school(school: SchoolCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    db_school = db.query(School).filter(School.name == school.name).first()
    if db_school:
        raise HTTPException(status_code=400, detail="School already registered")
    new_school = School(**school.dict())
    db.add(new_school)
    db.commit()
    db.refresh(new_school)
    return new_school

# List all schools
@router.get("/schools", response_model=list[School])
async def list_schools(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return db.query(School).all()

# Create a new user (Admin can create teachers, students, parents)
@router.post("/users", response_model=User)
async def create_user(user: UserCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    new_user = User(**user.dict())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# List all users
@router.get("/users", response_model=list[User])
async def list_users(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return db.query(User).all()

# Delete a user
@router.delete("/users/{user_id}", response_description="Delete a user")
async def delete_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

# Delete a school
@router.delete("/schools/{school_id}", response_description="Delete a school")
async def delete_school(school_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    db.delete(school)
    db.commit()
    return {"message": "School deleted successfully"}
