from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import User, School, Attendance
from app.schemas import SchoolCreate, UserCreate, AttendanceCreate
from app.database import SessionLocal
from app.services.auth_service import get_current_admin
from app.utils.email import send_email  # Assuming you have an email utility
from app.utils.sms import send_sms      # Assuming you have an SMS utility

router = APIRouter()

# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Admin Dashboard Route
@router.get("/dashboard", response_description="Admin Dashboard")
async def admin_dashboard(current_admin: User = Depends(get_current_admin)):
    return {"message": "Welcome to the Admin Dashboard!"}

# Create a new school (Super Admin only)
@router.post("/schools", response_model=School)
async def create_school(school: SchoolCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    if current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admins can create schools")
    
    db_school = db.query(School).filter(School.name == school.name).first()
    if db_school:
        raise HTTPException(status_code=400, detail="School already registered")
    
    new_school = School(**school.dict())
    db.add(new_school)
    db.commit()
    db.refresh(new_school)
    return new_school

# Create a new school admin (Under a specific school)
@router.post("/schools/{school_id}/admins", response_model=User)
async def create_school_admin(school_id: int, user: UserCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    if current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admins can create school admins")
    
    db_school = db.query(School).filter(School.id == school_id).first()
    if not db_school:
        raise HTTPException(status_code=404, detail="School not found")

    # Ensure the email is unique for the school admin
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_admin = User(**user.dict(), role='school_admin', school_id=school_id)
    db.add(new_admin)
    db.commit()
    db.refresh(new_admin)
    return new_admin

# List all schools
@router.get("/schools", response_model=list[School])
async def list_schools(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return db.query(School).all()

# List all users in the school
@router.get("/schools/{school_id}/users", response_model=list[User])
async def list_users(school_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    if current_admin.role != "school_admin":
        raise HTTPException(status_code=403, detail="Only school admins can view users")
    
    return db.query(User).filter(User.school_id == school_id).all()

# Send email to teachers
@router.post("/schools/{school_id}/send-email")
async def send_email_to_teachers(school_id: int, email_data: dict, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    if current_admin.role != "school_admin":
        raise HTTPException(status_code=403, detail="Only school admins can send emails")
    
    teachers = db.query(User).filter(User.role == 'teacher', User.school_id == school_id).all()
    for teacher in teachers:
        send_email(teacher.email, email_data['subject'], email_data['message'])
    
    return {"message": "Emails sent successfully"}

# Send SMS to parents
@router.post("/schools/{school_id}/send-sms")
async def send_sms_to_parents(school_id: int, sms_data: dict, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    if current_admin.role != "school_admin":
        raise HTTPException(status_code=403, detail="Only school admins can send SMS")
    
    parents = db.query(User).filter(User.role == 'parent', User.school_id == school_id).all()
    for parent in parents:
        send_sms(parent.phone, sms_data['message'])
    
    return {"message": "SMS sent successfully"}

# Create attendance record (Assuming the schema exists)
@router.post("/attendance", response_model=Attendance)
async def create_attendance(attendance_data: AttendanceCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    # Assuming attendance_data includes student_id and school_id
    db_attendance = Attendance(**attendance_data.dict())
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance

# View attendance records for a specific school
@router.get("/schools/{school_id}/attendance", response_model=list[Attendance])
async def view_attendance(school_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    if current_admin.role != "school_admin":
        raise HTTPException(status_code=403, detail="Only school admins can view attendance")
    
    return db.query(Attendance).filter(Attendance.school_id == school_id).all()

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
