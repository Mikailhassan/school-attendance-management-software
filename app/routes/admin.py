from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import User, School, Attendance
from app.schemas import (
    SchoolCreate, 
    UserCreate, 
    AttendanceCreate, 
    FingerprintCreate,
    FingerprintResponse,
    School as SchoolSchema,
    UserResponse, 
    Attendance as AttendanceSchema,
    UserRole
)
from app.core.database import get_db
from app.dependencies import get_current_admin
from app.utils.email_utils import send_email
from app.utils.sms import InfobipSMSService
from datetime import date, datetime
from typing import Optional, List

router = APIRouter()

def check_role(user: User, allowed_roles: List[UserRole]):
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=403, 
            detail=f"Only {', '.join(map(str, allowed_roles))} can perform this action"
        )

# Super Admin Routes
@router.post("/schools", response_model=SchoolSchema)
async def create_school(
    school: SchoolCreate, 
    db: AsyncSession = Depends(get_db), 
    current_admin: User = Depends(get_current_admin)
):
    check_role(current_admin, [UserRole.SUPER_ADMIN])
    
    result = await db.execute(select(School).filter(School.name == school.name))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="School already registered")
    
    new_school = School(**school.dict())
    db.add(new_school)
    await db.commit()
    await db.refresh(new_school)
    return new_school

@router.post("/schools/{school_id}/admins", response_model=UserResponse)
async def create_school_admin(
    school_id: int, 
    user: UserCreate, 
    db: AsyncSession = Depends(get_db), 
    current_admin: User = Depends(get_current_admin)
):
    check_role(current_admin, [UserRole.SUPER_ADMIN])
    
    school = await db.execute(select(School).filter(School.id == school_id))
    if not school.scalars().first():
        raise HTTPException(status_code=404, detail="School not found")

    existing_user = await db.execute(select(User).filter(User.email == user.email))
    if existing_user.scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    new_admin = User(**user.dict(), role=UserRole.SCHOOL_ADMIN, school_id=school_id)
    db.add(new_admin)
    await db.commit()
    await db.refresh(new_admin)
    return new_admin

@router.delete("/schools/{school_id}")
async def delete_school(
    school_id: int, 
    db: AsyncSession = Depends(get_db), 
    current_admin: User = Depends(get_current_admin)
):
    check_role(current_admin, [UserRole.SUPER_ADMIN])

    school = await db.execute(select(School).filter(School.id == school_id))
    if not school.scalars().first():
        raise HTTPException(status_code=404, detail="School not found")
    
    # Cascade delete related records
    await db.execute(f"DELETE FROM users WHERE school_id = {school_id}")
    await db.execute(f"DELETE FROM attendance WHERE school_id = {school_id}")
    await db.execute(f"DELETE FROM schools WHERE id = {school_id}")
    
    await db.commit()
    return {"message": "School and all related data deleted successfully"}

@router.get("/schools", response_model=List[SchoolSchema])
async def list_all_schools(
    db: AsyncSession = Depends(get_db), 
    current_admin: User = Depends(get_current_admin)
):
    check_role(current_admin, [UserRole.SUPER_ADMIN])
    result = await db.execute(select(School))
    return result.scalars().all()

# School Admin Routes
@router.post("/schools/{school_id}/fingerprints", response_model=FingerprintResponse)
async def register_fingerprint(
    school_id: int,
    fingerprint: FingerprintCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    check_role(current_admin, [UserRole.SCHOOL_ADMIN])
    
    # Note: You'll need to import and define Fingerprint model
    from app.models import Fingerprint

    if current_admin.school_id != school_id:
        raise HTTPException(status_code=403, detail="Not authorized for this school")
    
    user = await db.execute(
        select(User).filter(
            User.id == fingerprint.user_id,
            User.school_id == school_id
        )
    )
    if not user.scalars().first():
        raise HTTPException(status_code=404, detail="User not found in this school")
    
    new_fingerprint = Fingerprint(
        user_id=fingerprint.user_id,
        fingerprint_data=fingerprint.fingerprint_data
    )
    db.add(new_fingerprint)
    await db.commit()
    await db.refresh(new_fingerprint)
    return new_fingerprint

@router.get("/schools/{school_id}/attendance", response_model=List[AttendanceSchema])
async def view_school_attendance(
    school_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    check_role(current_admin, [UserRole.SCHOOL_ADMIN])
    if current_admin.school_id != school_id:
        raise HTTPException(status_code=403, detail="Not authorized for this school")
    
    query = select(Attendance).filter(Attendance.school_id == school_id)
    
    if start_date:
        query = query.filter(Attendance.check_in_time >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        query = query.filter(Attendance.check_in_time <= datetime.combine(end_date, datetime.max.time()))
    if user_id:
        query = query.filter(Attendance.user_id == user_id)
    
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/schools/{school_id}/attendance", response_model=AttendanceSchema)
async def record_attendance(
    school_id: int,
    attendance: AttendanceCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    check_role(current_admin, [UserRole.SCHOOL_ADMIN])
    if current_admin.school_id != school_id:
        raise HTTPException(status_code=403, detail="Not authorized for this school")
    
    user = await db.execute(
        select(User).filter(
            User.id == attendance.user_id,
            User.school_id == school_id
        )
    )
    if not user.scalars().first():
        raise HTTPException(status_code=404, detail="User not found in this school")
    
    new_attendance = Attendance(**attendance.dict(), school_id=school_id)
    db.add(new_attendance)
    await db.commit()
    await db.refresh(new_attendance)
    return new_attendance

@router.get("/schools/{school_id}/users", response_model=List[UserResponse])
async def list_school_users(
    school_id: int,
    role: Optional[UserRole] = None,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    check_role(current_admin, [UserRole.SCHOOL_ADMIN])
    if current_admin.school_id != school_id:
        raise HTTPException(status_code=403, detail="Not authorized for this school")
    
    query = select(User).filter(User.school_id == school_id)
    if role:
        query = query.filter(User.role == role)
    
    result = await db.execute(query)
    return result.scalars().all()