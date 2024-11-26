from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import date, timedelta, datetime

from app.services.auth_service import AuthService
from app.services.attendance_service import AttendanceService
from app.dependencies import get_current_user, get_db
from app.schemas import UserCreate, UserResponse, AttendanceAnalytics
from app.models.user import User

router = APIRouter(tags=["authentication"])

attendance_service = AttendanceService()

@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(form_data.username, form_data.password)  # `username` contains email here
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = await auth_service.create_access_token(
        data={"sub": str(user.id)}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    
    # Check for existing user
    query = select(User).where(User.username == user_data.username)
    result = await db.execute(query)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    hashed_password = await auth_service.hash_password(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return user

@router.post("/register-fingerprint")
async def register_fingerprint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    result = await auth_service.register_fingerprint(current_user.id)
    return result

@router.post("/verify-fingerprint")
async def verify_fingerprint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    auth_service = AuthService(db)
    fingerprint_verified = await auth_service.authenticate_with_fingerprint(current_user.id)
    
    if not fingerprint_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Fingerprint verification failed"
        )
    
    access_token = await auth_service.create_access_token(
        data={"sub": str(current_user.id)}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: User = Depends(get_current_user)
):
    return current_user

@router.get("/profile/student/{student_id}", response_model=UserResponse)
async def get_student_profile(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.id == student_id, User.role == 'student')
    result = await db.execute(query)
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    attendance_summary = await attendance_service.get_student_attendance_summary(student_id)

    return {
        "student_info": student,
        "attendance_summary": attendance_summary
    }

@router.get("/profile/teacher/{teacher_id}/weekly", response_model=AttendanceAnalytics)
async def get_teacher_weekly_profile(
    teacher_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.id == teacher_id, User.role == 'teacher')
    result = await db.execute(query)
    teacher = result.scalar_one_or_none()
    
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=4)
    
    weekly_analysis = await attendance_service.get_teacher_attendance_analysis(
        teacher_id, start_of_week, end_of_week
    )
    
    return {
        "teacher_info": teacher,
        "weekly_analysis": weekly_analysis
    }

@router.get("/profile/teacher/{teacher_id}/monthly", response_model=AttendanceAnalytics)
async def get_teacher_monthly_profile(
    teacher_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.id == teacher_id, User.role == 'teacher')
    result = await db.execute(query)
    teacher = result.scalar_one_or_none()
    
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    today = date.today()
    start_of_month = today.replace(day=1)
    end_of_month = (today.replace(month=today.month % 12 + 1, day=1) - timedelta(days=1))

    monthly_analysis = await attendance_service.get_teacher_attendance_analysis(
        teacher_id, start_of_month, end_of_month
    )
    
    return {
        "teacher_info": teacher,
        "monthly_analysis": monthly_analysis
    }

@router.get("/profile/teacher/{teacher_id}/term", response_model=AttendanceAnalytics)
async def get_teacher_term_profile(
    teacher_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.id == teacher_id, User.role == 'teacher')
    result = await db.execute(query)
    teacher = result.scalar_one_or_none()
    
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    today = date.today()
    term_start = date(today.year, 1, 1)
    term_end = date(today.year, 6, 30)

    term_analysis = await attendance_service.get_teacher_attendance_analysis(
        teacher_id, term_start, term_end
    )
    
    return {
        "teacher_info": teacher,
        "term_analysis": term_analysis
    }

@router.get("/profile/student/{student_id}/monthly", response_model=AttendanceAnalytics)
async def get_student_monthly_profile(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.id == student_id, User.role == 'student')
    result = await db.execute(query)
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    today = date.today()
    start_of_month = today.replace(day=1)
    end_of_month = (today.replace(month=today.month % 12 + 1, day=1) - timedelta(days=1))

    monthly_analysis = await attendance_service.get_student_attendance_summary(
        student_id, start_of_month, end_of_month
    )
    
    return {
        "student_info": student,
        "monthly_analysis": monthly_analysis
    }

@router.get("/profile/student/{student_id}/term", response_model=AttendanceAnalytics)
async def get_student_term_profile(
    student_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = select(User).where(User.id == student_id, User.role == 'student')
    result = await db.execute(query)
    student = result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    today = date.today()
    term_start = date(today.year, 1, 1)
    term_end = date(today.year, 6, 30)

    term_analysis = await attendance_service.get_student_attendance_summary(
        student_id, term_start, term_end
    )
    
    return {
        "student_info": student,
        "term_analysis": term_analysis
    }