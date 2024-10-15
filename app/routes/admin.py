from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, School, Attendance
from app.schemas import SchoolCreate, UserCreate, AttendanceCreate, School as SchoolSchema, UserResponse, Attendance as AttendanceSchema
from app.database import get_db
from app.dependencies import get_current_admin
from app.utils.email import send_email
from app.utils.sms import send_sms
from datetime import date

router = APIRouter()

# Utility function to check role permissions
def check_role(user: User, role: str):
    if user.role != role:
        raise HTTPException(status_code=403, detail=f"Only {role}s can perform this action")

# Admin Dashboard Route
@router.get("/dashboard", response_description="Admin Dashboard")
async def admin_dashboard(current_admin: User = Depends(get_current_admin)):
    return {"message": "Welcome to the Admin Dashboard!"}

# Create a new school (Super Admin only)
@router.post("/schools", response_model=SchoolSchema)
async def create_school(school: SchoolCreate, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    check_role(current_admin, "super_admin")
    
    result = await db.execute(select(School).filter(School.name == school.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="School already registered")
    
    new_school = School(**school.dict())
    db.add(new_school)
    await db.commit()
    await db.refresh(new_school)
    return new_school

# Create a new school admin (Under a specific school)
@router.post("/schools/{school_id}/admins", response_model=UserResponse)
async def create_school_admin(school_id: int, user: UserCreate, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    check_role(current_admin, "super_admin")
    
    result = await db.execute(select(School).filter(School.id == school_id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="School not found")

    result = await db.execute(select(User).filter(User.email == user.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_admin = User(**user.dict(), role='school_admin', school_id=school_id)
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)
    return new_admin

# List all schools
@router.get("/schools", response_model=list[SchoolSchema])
async def list_schools(db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    result = await db.execute(select(School))
    return result.scalars().all()

# List all users in the school
@router.get("/schools/{school_id}/users", response_model=list[UserResponse])
async def list_users(school_id: int, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    check_role(current_admin, "school_admin")
    
    result = await db.execute(select(User).filter(User.school_id == school_id))
    return result.scalars().all()

# Send email to teachers
@router.post("/schools/{school_id}/send-email")
async def send_email_to_teachers(school_id: int, email_data: dict, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    check_role(current_admin, "school_admin")
    
    result = await db.execute(select(User).filter(User.role == 'teacher', User.school_id == school_id))
    teachers = result.scalars().all()
    for teacher in teachers:
        send_email(teacher.email, email_data['subject'], email_data['message'])
    
    return {"message": "Emails sent successfully"}

# Send SMS to parents
@router.post("/schools/{school_id}/send-sms")
async def send_sms_to_parents(school_id: int, sms_data: dict, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    check_role(current_admin, "school_admin")
    
    result = await db.execute(select(User).filter(User.role == 'parent', User.school_id == school_id))
    parents = result.scalars().all()
    for parent in parents:
        send_sms(parent.phone, sms_data['message'])
    
    return {"message": "SMS sent successfully"}

# Create attendance record
@router.post("/attendance", response_model=AttendanceSchema)
async def create_attendance(attendance_data: AttendanceCreate, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    result = await db.execute(select(User).filter(User.id == attendance_data.user_id, User.school_id == attendance_data.school_id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="User or school not found")

    db_attendance = Attendance(**attendance_data.dict())
    db.add(db_attendance)
    await db.commit()
    await db.refresh(db_attendance)
    return db_attendance

# View attendance records for a specific school (with date filtering)
@router.get("/schools/{school_id}/attendance", response_model=list[AttendanceSchema])
async def view_attendance(school_id: int, start_date: date = None, end_date: date = None, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    check_role(current_admin, "school_admin")
    
    query = select(Attendance).filter(Attendance.school_id == school_id)
    
    if start_date and end_date:
        query = query.filter(Attendance.check_in_time >= start_date, Attendance.check_in_time <= end_date)
    
    result = await db.execute(query)
    return result.scalars().all()

# Calculate attendance percentage for a user
@router.get("/schools/{school_id}/users/{user_id}/attendance-percentage")
async def calculate_attendance_percentage(school_id: int, user_id: int, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    check_role(current_admin, "school_admin")
    
    total_query = select(Attendance).filter(Attendance.school_id == school_id, Attendance.user_id == user_id)
    present_query = total_query.filter(Attendance.is_present == True)
    
    total_result = await db.execute(total_query)
    present_result = await db.execute(present_query)
    
    total_days = len(total_result.scalars().all())
    present_days = len(present_result.scalars().all())
    
    if total_days == 0:
        raise HTTPException(status_code=404, detail="No attendance records found for this user.")
    
    attendance_percentage = (present_days / total_days) * 100
    return {"attendance_percentage": attendance_percentage}

# Delete a user
@router.delete("/users/{user_id}", response_description="Delete a user")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    return {"message": "User deleted successfully"}

# Delete a school by superadmin
@router.delete("/schools/{school_id}", response_description="Delete a school")
async def delete_school(school_id: int, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    check_role(current_admin, "super_admin")

    result = await db.execute(select(School).filter(School.id == school_id))
    school = result.scalars().first()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    await db.delete(school)
    await db.commit()
    return {"message": "School deleted successfully"}