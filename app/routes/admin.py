from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update
from typing import List, Optional
from datetime import date

from app.models import (
    School, Class, Stream, Session, User, Student, Parent,
    StudentAttendance
)
from app.schemas.school.requests import (
    SessionCreateRequest,
    ClassCreateRequest,
    StreamCreateRequest,
    SchoolCreateRequest,
    SchoolType,
    SchoolAdminRegistrationRequest,
    SessionUpdateRequest,
    SchoolUpdateRequest,
    StreamUpdateRequest,
    SessionUpdateRequest,
    ClassUpdateRequest
)
from app.schemas.school.responses import (
    SessionResponse,
    ClassResponse,
    StreamResponse,
    SchoolResponse    
)

from app.schemas.student import StudentRegistrationRequest, StudentUpdate
from app.core.database import get_db
from app.core.security import generate_temporary_password, get_password_hash
from app.core.dependencies import (
    get_current_super_admin,
    get_current_school_admin,
    verify_school_access
)
from app.schemas.auth.requests import UserInDB
from app.services.school_service import SchoolService
from app.utils.email_utils import send_email

router = APIRouter(tags=["Admin"])

# School Management Endpoints
@router.post("/schools")
async def create_school(
    school_data: SchoolCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_super_admin)
):
    """Create a new school and its admin account (super admin only)"""
    school_service = SchoolService(db)
    return await school_service.create_school(school_data, background_tasks)

@router.get("/schools/{registration_number}")
async def get_school_details(
    registration_number: str,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Get detailed information about a specific school"""
    clean_registration_number = registration_number.strip('{}')
    
    school = await db.execute(
        select(School)
        .where(School.registration_number == clean_registration_number)
        .options(
            joinedload(School.classes),
            joinedload(School.sessions)
        )
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    if current_user.role != "super_admin" and current_user.school.registration_number != clean_registration_number:
        raise HTTPException(status_code=403, detail="Not authorized to access this school")
    
    return school

# Class Management Endpoints
@router.post("/schools/{registration_number}/classes")
async def create_class(
    registration_number: str,
    class_data: ClassCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Create a new class in a school"""
    clean_registration_number = registration_number.strip('{}')
    
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    new_class = Class(
        name=class_data.name,
        school_id=school.id
    )
    db.add(new_class)
    await db.commit()
    await db.refresh(new_class)
    return new_class

@router.get("/schools/{registration_number}/classes")
async def list_classes(
    registration_number: str,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """List all classes in a school"""
    clean_registration_number = registration_number.strip('{}')
    
    school = await db.execute(
        select(School)
        .where(School.registration_number == clean_registration_number)
        .options(
            joinedload(School.classes).joinedload(Class.streams)
        )
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    return school.classes

# Stream Management Endpoints
@router.post("/schools/{registration_number}/classes/{class_id}/streams")
async def create_stream(
    registration_number: str,
    class_id: int,
    stream_data: StreamCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Create a new stream within a class"""
    clean_registration_number = registration_number.strip('{}')
    
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    class_obj = await db.execute(
        select(Class).where(
            Class.id == class_id,
            Class.school_id == school.id
        )
    )
    class_obj = class_obj.scalar_one_or_none()
    
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")
    
    new_stream = Stream(
        name=stream_data.name,
        class_id=class_id,
        school_id=school.id
    )
    db.add(new_stream)
    await db.commit()
    await db.refresh(new_stream)
    return new_stream

@router.get("/schools/{registration_number}/classes/{class_id}/streams")
async def list_streams(
    registration_number: str,
    class_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """List all streams in a class"""
    clean_registration_number = registration_number.strip('{}')
    
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    streams = await db.execute(
        select(Stream)
        .where(
            Stream.class_id == class_id,
            Stream.school_id == school.id
        )
    )
    return streams.scalars().all()

# Student Management Endpoints
@router.post("/schools/{registration_number}/students")
async def register_student(
    registration_number: str,
    student_data: StudentRegistrationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Register a new student with class and stream assignment"""
    clean_registration_number = registration_number.strip('{}')
    
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # Verify stream exists
    stream = await db.execute(
        select(Stream)
        .join(Class)
        .where(
            Stream.school_id == school.id,
            Class.name == student_data.class_name,
            Stream.name == student_data.stream_name
        )
    )
    stream = stream.scalar_one_or_none()
    
    if not stream:
        raise HTTPException(status_code=404, detail="Stream not found")
    
    # Create user account
    user = User(
        email=student_data.email,
        password=get_password_hash(student_data.password),
        role='student',
        school_id=school.id,
        is_active=True
    )
    db.add(user)
    await db.flush()
    
    # Create student profile
    student = Student(
        name=student_data.name,
        admission_number=student_data.admission_number,
        stream_id=stream.id,
        user_id=user.id,
        date_of_birth=student_data.date_of_birth or date.today(),
        school_id=school.id
    )
    db.add(student)
    await db.commit()
    await db.refresh(student)
    
    return {
        "message": "Student registered successfully",
        "student_id": student.id,
        "admission_number": student.admission_number
    
}



@router.post("/schools/{registration_number}/sessions", response_model=SessionResponse)
async def create_session(
    registration_number: str,
    session_data: SessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Create a new academic session for a school"""
    clean_registration_number = registration_number.strip('{}')
    
    # Verify school exists
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # Validate dates
    if session_data.end_date <= session_data.start_date:
        raise HTTPException(
            status_code=400,
            detail="End date must be after start date"
        )
    
    # Check for date overlaps with existing sessions
    existing_session = await db.execute(
        select(Session).where(
            and_(
                Session.school_id == school.id,
                Session.start_date <= session_data.end_date,
                Session.end_date >= session_data.start_date
            )
        )
    )
    if existing_session.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Session dates overlap with an existing session"
        )
    
    # If this session is marked as current, unmark other current sessions
    if session_data.is_current:
        await db.execute(
            update(Session)
            .where(Session.school_id == school.id)
            .values(is_current=False)
        )
    
    # Create new session
    new_session = Session(
        name=session_data.name,
        start_date=session_data.start_date,
        end_date=session_data.end_date,
        is_current=session_data.is_current,
        description=session_data.description,
        school_id=school.id
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)
    
    return new_session

@router.get("/schools/{registration_number}/sessions", response_model=List[SessionResponse])
async def list_sessions(
    registration_number: str,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """List all sessions for a school"""
    clean_registration_number = registration_number.strip('{}')
    
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    sessions = await db.execute(
        select(Session)
        .where(Session.school_id == school.id)
        .order_by(Session.start_date.desc())
    )
    return sessions.scalars().all()

@router.get("/schools/{registration_number}/sessions/current", response_model=SessionResponse)
async def get_current_session(
    registration_number: str,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Get the current active session for a school"""
    clean_registration_number = registration_number.strip('{}')
    
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    current_session = await db.execute(
        select(Session)
        .where(
            and_(
                Session.school_id == school.id,
                Session.is_current == True
            )
        )
    )
    current_session = current_session.scalar_one_or_none()
    
    if not current_session:
        raise HTTPException(
            status_code=404,
            detail="No current session found"
        )
    
    return current_session

@router.patch("/schools/{registration_number}/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    registration_number: str,
    session_id: str,
    session_data: SessionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Update an existing session"""
    clean_registration_number = registration_number.strip('{}')
    clean_session_id = session_id.strip('{}')
    
    try:
        session_id_int = int(clean_session_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid session ID format"
        )
    
    # Verify school exists
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # Get existing session
    session = await db.execute(
        select(Session).where(
            and_(
                Session.id == session_id_int,
                Session.school_id == school.id
            )
        )
    )
    session = session.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Update session fields
    update_data = session_data.dict(exclude_unset=True)
    
    if 'start_date' in update_data or 'end_date' in update_data:
        start_date = update_data.get('start_date', session.start_date)
        end_date = update_data.get('end_date', session.end_date)
        
        if end_date <= start_date:
            raise HTTPException(
                status_code=400,
                detail="End date must be after start date"
            )
        
        # Check for date overlaps with other sessions
        overlapping_session = await db.execute(
            select(Session).where(
                and_(
                    Session.school_id == school.id,
                    Session.id != session_id_int,
                    Session.start_date <= end_date,
                    Session.end_date >= start_date
                )
            )
        )
        if overlapping_session.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Session dates overlap with an existing session"
            )
    
    if update_data.get('is_current'):
        # Unmark other current sessions
        await db.execute(
            update(Session)
            .where(and_(
                Session.school_id == school.id,
                Session.id != session_id_int
            ))
            .values(is_current=False)
        )
    
    for key, value in update_data.items():
        setattr(session, key, value)
    
    await db.commit()
    await db.refresh(session)
    
    return session