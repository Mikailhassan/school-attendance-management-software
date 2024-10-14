from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models import User, School, Attendance
from app.schemas import SchoolCreate, UserCreate, AttendanceCreate, School as SchoolResponse, UserResponse, Attendance as AttendanceResponse
from app.database import SessionLocal
from app.dependencies import get_current_admin
from app.utils.email import send_email  
from app.utils.sms import send_sms      
from datetime import date

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
@router.post("/schools", response_model=SchoolResponse)
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
@router.post("/schools/{school_id}/admins", response_model=UserResponse)
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
@router.get("/schools", response_model=list[SchoolResponse])
async def list_schools(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    return db.query(School).all()

# List all users in the school
@router.get("/schools/{school_id}/users", response_model=list[UserResponse])
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
@router.post("/attendance", response_model=AttendanceResponse)
async def create_attendance(attendance_data: AttendanceCreate, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    # Assuming attendance_data includes student_id and school_id
    db_attendance = Attendance(**attendance_data.dict())
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance

# View attendance records for a specific school (with date filtering)
@router.get("/schools/{school_id}/attendance", response_model=list[AttendanceResponse])
async def view_attendance(school_id: int, start_date: date = None, end_date: date = None, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    if current_admin.role != "school_admin":
        raise HTTPException(status_code=403, detail="Only school admins can view attendance")
    
    query = db.query(Attendance).filter(Attendance.school_id == school_id)
    
    if start_date and end_date:
        query = query.filter(Attendance.date >= start_date, Attendance.date <= end_date)
    
    return query.all()

# Calculate attendance percentage for a student
@router.get("/schools/{school_id}/students/{student_id}/attendance-percentage")
async def calculate_attendance_percentage(school_id: int, student_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    if current_admin.role != "school_admin":
        raise HTTPException(status_code=403, detail="Only school admins can view attendance")
    
    total_days = db.query(Attendance).filter(Attendance.school_id == school_id, Attendance.student_id == student_id).count()
    present_days = db.query(Attendance).filter(Attendance.school_id == school_id, Attendance.student_id == student_id, Attendance.status == "Present").count()
    
    if total_days == 0:
        raise HTTPException(status_code=404, detail="No attendance records found for this student.")
    
    attendance_percentage = (present_days / total_days) * 100
    return {"attendance_percentage": attendance_percentage}

# Delete a user
@router.delete("/users/{user_id}", response_description="Delete a user")
async def delete_user(user_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}

# Delete a school by superadmin
@router.delete("/schools/{school_id}", response_description="Delete a school")
async def delete_school(school_id: int, db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    if current_admin.role != "super_admin":
        raise HTTPException(status_code=403, detail="Only super admins can delete schools")

    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    db.delete(school)
    db.commit()
    return {"message": "School deleted successfully"}
