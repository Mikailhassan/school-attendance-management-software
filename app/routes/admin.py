from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, update
from typing import Dict, Any, Optional,List
from sqlalchemy.ext.asyncio import AsyncSession 
from datetime import date,datetime
from app.schemas.enums import UserRole
from app.services.email_service import EmailService
import re
from app.core.exceptions import DuplicateSchoolException
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
from app.schemas.user import UserResponse

from app.schemas.student import StudentRegistrationRequest, StudentUpdate
from app.services.auth_service import AuthService, get_auth_service
from app.core.logging import logger
from app.core.database import get_db
from app.core.security import generate_temporary_password, get_password_hash
from app.core.dependencies import (
    get_current_super_admin,
    get_current_school_admin,
    verify_school_access,
    get_current_active_user,
)
from app.schemas.auth.requests import UserInDB
from app.services.school_service import SchoolService
from app.utils.email_utils import send_email


email_service = EmailService()

router = APIRouter(tags=["Admin"])

router = APIRouter(tags=["Users"])

router = APIRouter(tags=["Users"])

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get details of currently authenticated user."""
    return current_user

@router.get("/me/refresh", response_model=Dict[str, Any])
async def refresh_session(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh the current user session and verify the token is still valid.
    Returns fresh user data and session status.
    """
    try:
        # Get fresh user data with relationships
        query = (
            select(User)
            .options(
                selectinload(User.school),
                selectinload(User.parent_profile),
                selectinload(User.teacher_profile),
                selectinload(User.student_profile)
            )
            .where(User.id == current_user.id)
        )
        result = await db.execute(query)
        user = result.unique().scalar_one_or_none()

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User session is no longer valid"
            )

        # Verify current token
        token = await auth_service.get_token_from_request(request)
        await auth_service.verify_token(token, expected_type="access")

        # Convert user to response model
        user_response = UserResponse.from_orm(user)

        return {
            "status": "ok",
            "user": user_response,
            "message": "Session refreshed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error refreshing session: {str(e)}"
        )
# School Management Endpoints
@router.post("/schools")
async def create_school(
    school_data: SchoolCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_super_admin)
):
    """Create a new school and its admin account (super admin only)"""
    try:
        # Initialize the school service
        school_service = SchoolService(db, email_service)
        
        # Use the service to create the school
        result = await school_service.create_school(school_data, background_tasks)
        
        return result
        
    except DuplicateSchoolException as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating school: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating school"
        )

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

@router.get("/schools/profile", response_model=SchoolResponse)
async def get_school_profile(
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """
    Get the profile of the currently authenticated school admin's school.
    This endpoint allows school admins to view their own school's details.
    """
    try:
        # Get school with related data using the current user's school_id
        query = (
            select(School)
            .where(School.id == current_user.school_id)
            .options(
                joinedload(School.classes),
                joinedload(School.sessions),
                joinedload(School.classes).joinedload(Class.streams),
                joinedload(School.admins)
            )
        )
        
        result = await db.execute(query)
        school = result.unique().scalar_one_or_none()
        
        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="School profile not found"
            )
            
        # Add any computed fields or additional data
        response_data = SchoolResponse(
            id=school.id,
            name=school.name,
            registration_number=school.registration_number,
            email=school.email,
            phone=school.phone,
            address=school.address,
            school_type=school.school_type,
            website=school.website,
            county=school.county,
            class_system=school.class_system,
            class_range=school.class_range,
            postal_code=school.postal_code,
            extra_info=school.extra_info,
            status=school.status,
            is_active=school.is_active,
            created_at=school.created_at,
            updated_at=school.updated_at,
            # Include summary statistics
            total_students=len([student for class_ in school.classes 
                              for stream in class_.streams 
                              for student in stream.students]) if school.classes else 0,
            total_classes=len(school.classes) if school.classes else 0,
            total_streams=sum(len(class_.streams) for class_ in school.classes) if school.classes else 0,
            current_session=next((session for session in school.sessions 
                                if session.is_current), None) if school.sessions else None
        )
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving school profile: {str(e)}"
        )

# Optional: Add an endpoint for updating the school profile
@router.patch("/schools/profile", response_model=SchoolResponse)
async def update_school_profile(
    update_data: SchoolUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """
    Update the profile of the currently authenticated school admin's school.
    Only certain fields can be updated by school admins.
    """
    try:
        # Get current school
        query = (
            select(School)
            .where(School.id == current_user.school_id)
            .options(
                joinedload(School.classes),
                joinedload(School.sessions),
                joinedload(School.classes).joinedload(Class.streams)
            )
        )
        
        result = await db.execute(query)
        school = result.unique().scalar_one_or_none()
        
        if not school:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="School not found"
            )
        
        # Update allowed fields
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if field not in ['registration_number', 'status', 'is_active']:  # Protected fields
                setattr(school, field, value)
        
        school.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(school)
        
        # Return updated profile using the same response model
        return SchoolResponse.from_orm(school)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating school profile: {str(e)}"
        )

@router.get("/schools/{registration_number}/classes")
async def list_classes(
    registration_number: str,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """List all classes in a school"""
    clean_registration_number = registration_number.strip('{}')
    
    # Execute the query first, then call unique() on the Result object
    result = await db.execute(
        select(School)
        .where(School.registration_number == clean_registration_number)
        .options(
            joinedload(School.classes).joinedload(Class.streams)
        )
    )
    school = result.unique().scalar_one_or_none() 
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    return school.classes

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
    
    # Use a single query to get both school and class
    result = await db.execute(
        select(School, Class)
        .join(Class, School.id == Class.school_id)
        .where(
            School.registration_number == clean_registration_number,
            Class.id == class_id
        )
    )
    school_and_class = result.first()
    
    if not school_and_class:
        raise HTTPException(status_code=404, detail="School or class not found")
    
    school, class_obj = school_and_class
    
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
    
    # Optimize query to check both school and streams in one go
    streams = await db.execute(
        select(Stream)
        .join(School, Stream.school_id == School.id)
        .where(
            School.registration_number == clean_registration_number,
            Stream.class_id == class_id
        )
    )
    
    result = streams.scalars().all()
    if not result:
        # Verify if the school exists before returning empty results
        school = await db.execute(
            select(School).where(School.registration_number == clean_registration_number)
        )
        if not school.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="School not found")
    
    return result

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
    
    # Get school
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # Verify stream exists and get its ID
    stream = await db.execute(
        select(Stream)
        .join(Class)
        .where(
            Stream.school_id == school.id,
            Class.id == student_data.class_id,
            Stream.name == student_data.stream_name
        )
    )
    stream = stream.scalar_one_or_none()

    if not stream:
        raise HTTPException(
            status_code=404,
            detail=f"Stream not found for class_id {student_data.class_id} and stream {student_data.stream_name}"
        )

    # Create student user account
    student_user = User(
        name=student_data.name,
        email=student_data.email,
        password_hash=get_password_hash(student_data.password),
        role=UserRole.STUDENT,
        school_id=school.id,
        is_active=True
    )
    db.add(student_user)
    await db.flush()

    # Generate temporary password for parent account
    parent_temp_password = generate_temporary_password()
    
    # Create parent user account
    parent_user = User(
        name=f"Parent of {student_data.name}",
        email=student_data.parent_email,  # Assuming this is added to StudentRegistrationRequest
        password_hash=get_password_hash(parent_temp_password),
        role=UserRole.PARENT,
        school_id=school.id,
        is_active=True
    )
    db.add(parent_user)
    await db.flush()
    
    # Create parent record
    parent = Parent(
        name=f"Parent of {student_data.name}",
        user_id=parent_user.id,
        school_id=school.id,
        phone=student_data.parent_phone,  
        email=student_data.parent_email   
    )
    db.add(parent)
    await db.flush()
    
    # Create student profile
    student = Student(
        name=student_data.name,
        admission_number=student_data.admission_number,
        class_id=student_data.class_id,
        stream_id=stream.id,
        user_id=student_user.id,
        parent_id=parent.id,
        date_of_birth=student_data.date_of_birth or date.today(),
        school_id=school.id
    )
    db.add(student)
    
    try:
        await db.commit()
        await db.refresh(student)
        
        # Send email to parent with temporary password
        background_tasks.add_task(
            send_email,
            recipient_email=parent_user.email,
            subject="School Management System - Parent Account Created",
            body=f"""
            Dear Parent,
            
            A parent account has been created for you in the School Management System.
            Your temporary password is: {parent_temp_password}
            
            Please change your password after first login.
            
            Best regards,
            School Management Team
            """
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Error creating student: {str(e)}"
        )
    
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