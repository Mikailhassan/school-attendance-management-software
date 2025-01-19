from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Request
from sqlalchemy.orm import Session, joinedload, selectinload, load_only 
from sqlalchemy import func, select, update, or_, extract 
from typing import Dict, Any, Optional,List,Union
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.params import Query
from datetime import date,datetime
from app.schemas.enums import UserRole
from app.services.email_service import EmailService
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.sql import and_
import re
import math
from app.services.class_service import ClassService
from app.core.exceptions import DuplicateSchoolException, SchoolNotFoundException, ResourceNotFoundException
from app.schemas.school.responses import ClassDetailsResponse 
from app.schemas.school.requests import BulkClassCreateRequest
from app.core.dependencies import get_class_service
from app.core.dependencies import get_school_service
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
    SchoolResponse,
    ClassStatisticsResponse,
    ErrorResponse,
    SchoolAdminResponse,
    ClassWithStreamsResponse,
    ClassDetailsResponse,
    ClassListResponse
)
from app.schemas.user import UserResponse

from app.schemas.student import StudentRegistrationRequest, StudentUpdate
from app.schemas.student.responses import StudentResponse, PaginatedStudentResponse

from app.services.auth_service import AuthService, get_auth_service
from app.core.logging import logger
from app.core.database import get_db
from app.core.security import generate_temporary_password, get_password_hash
from app.core.dependencies import (
    get_current_super_admin,
    get_current_school_admin,
    verify_school_access,
    get_current_active_user,
    get_current_user
    
)
from app.schemas.auth.requests import UserInDB
from app.services.school_service import SchoolService
from app.utils.email_utils import send_email


email_service = EmailService()
async def get_class_service(db: AsyncSession = Depends(get_db)) -> ClassService:
    return ClassService(db)

router = APIRouter(tags=["Admin"])

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

@router.get(
    "/schools/{registration_number}",
    response_model=SchoolResponse,
    responses={
        404: {"model": ErrorResponse, "description": "School not found"},
        403: {"model": ErrorResponse, "description": "Not authorized"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_school_details(
    registration_number: str,
    school_service: SchoolService = Depends(get_school_service),  # Using the fixed dependency
    current_user: UserInDB = Depends(get_current_school_admin)
) -> SchoolResponse:
    try:
        school = await school_service.get_school_by_registration(registration_number)
        
        # Check authorization
        if current_user.role != "super_admin" and current_user.school.registration_number != registration_number:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this school"
            )
        
        return SchoolResponse.from_orm(school)
        
    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error fetching school: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while fetching school"
        )
        
        

        
@router.patch("/schools/profile", response_model=SchoolResponse)
async def update_school_profile(
    update_data: SchoolUpdateRequest,
    service: SchoolService = Depends(get_school_service),
    current_user: UserInDB = Depends(get_current_school_admin)
) -> SchoolResponse:
    """Update the profile of the currently authenticated school admin's school"""
    try:
        # Update school
        updated_school = await service.update_school(
            school_id=current_user.school_id,
            update_data=update_data
        )
        
        # Convert to response model
        return SchoolResponse(
            id=updated_school.id,
            name=updated_school.name,
            registration_number=updated_school.registration_number,
            email=updated_school.email,
            phone=updated_school.phone,
            address=updated_school.address,
            school_type=updated_school.school_type,
            website=updated_school.website,
            county=updated_school.county,
            class_system=updated_school.class_system,
            class_range=updated_school.class_range,
            postal_code=updated_school.postal_code,
            extra_info=updated_school.extra_info,
            status=updated_school.status,
            is_active=updated_school.is_active,
            created_at=updated_school.created_at,
            updated_at=updated_school.updated_at,
            total_students=len([student for class_ in updated_school.classes 
                              for stream in class_.streams 
                              for student in stream.students]) if updated_school.classes else 0,
            total_classes=len(updated_school.classes) if updated_school.classes else 0,
            total_streams=sum(len(class_.streams) for class_ in updated_school.classes) if updated_school.classes else 0,
            current_session=next((session for session in updated_school.sessions 
                                if session.is_current), None) if updated_school.sessions else None
        )
        
    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except SQLAlchemyError as e:
        logger.error(f"Database error while updating school: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating school profile: {str(e)}"
        )
@router.post("/{registration_number}/classes", response_model=ClassResponse)
async def create_class(
    registration_number: str,
    class_data: ClassCreateRequest,
    class_service: ClassService = Depends(get_class_service)
) -> ClassResponse:
    """
    Create a new class for a school
    
    Args:
        registration_number: School registration number
        class_data: Class creation data
        class_service: Injected class service
        
    Returns:
        ClassResponse: Created class data
        
    Raises:
        HTTPException: If school not found or class name already exists
    """
    db_class = await class_service.create_class(registration_number, class_data)
    
    return ClassResponse(
        id=db_class.id,
        name=db_class.name,
        
    )


@router.get(
    "/schools/{registration_number}/classes",
    response_model=List[ClassWithStreamsResponse],
    responses={
        404: {"model": ErrorResponse, "description": "School not found"},
        403: {"model": ErrorResponse, "description": "Not authorized to access this school"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def list_classes(
    registration_number: str,
    service: ClassService = Depends(get_class_service),
    current_user: UserInDB = Depends(get_current_school_admin)
) -> List[ClassWithStreamsResponse]:
    try:
        # Get school and verify access
        school = await service.get_school_by_registration(registration_number)
        if not school:
            raise ResourceNotFoundException(f"School {registration_number} not found")
            
        if current_user.school_id != school.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this school's classes"
            )
        
        # Get classes with streams
        classes = await service.list_classes_with_streams(school.id)
        
        try:
            return [ClassWithStreamsResponse.from_orm(class_obj) for class_obj in classes]
        except Exception as e:
            # Add specific error handling for serialization errors
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error serializing class data: {str(e)}"
            )
        
    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing classes: {str(e)}"
        )


@router.get(
    "/schools/{registration_number}/classes",
    response_model=List[ClassWithStreamsResponse],
    responses={
        404: {"model": ErrorResponse, "description": "School not found"},
        403: {"model": ErrorResponse, "description": "Not authorized to access this school"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def list_classes(
    registration_number: str,
    service: ClassService = Depends(get_class_service),
    current_user: UserInDB = Depends(get_current_school_admin)
) -> List[ClassWithStreamsResponse]:
    try:
        # Get school and verify access
        school = await service.get_school_by_registration(registration_number)
        if current_user.school_id != school.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this school's classes"
            )
        
        # Get classes with streams in a single query
        classes_data = await service.list_classes_with_streams(registration_number)
        
        return [ClassWithStreamsResponse(**class_data) for class_data in classes_data]
        
    except ResourceNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing classes: {str(e)}"
        )

@router.patch(
    "/schools/{registration_number}/classes/{class_id}",
    response_model=ClassResponse
)
async def update_class(
    registration_number: str,
    class_id: int,
    update_data: ClassUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Update a specific class"""
    class_service = ClassService(db)
    return await class_service.update_class(registration_number, class_id, update_data)

@router.get(
    "/schools/{registration_number}/classes/{class_id}/statistics",
    response_model=ClassStatisticsResponse
)
async def get_class_statistics(
    registration_number: str,
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Get statistics for a specific class"""
    class_service = ClassService(db)
    return await class_service.get_class_statistics(registration_number, class_id)

@router.post(
    "/schools/{registration_number}/classes/{class_name}/streams",
    response_model=StreamResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        404: {"description": "School or class not found"},
        409: {"description": "Stream already exists"},
        500: {"description": "Internal server error"}
    }
)

async def create_stream(
    registration_number: str,
    class_name: str,
    stream_data: StreamCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """
    Create a new stream within a class
    
    Parameters:
    - registration_number: School registration number
    - class_name: Name of the class (e.g., 'Form 18')
    - stream_data: Stream details including name (e.g., '18A')
    """
    class_service = ClassService(db)
    return await class_service.create_stream(registration_number, class_name, stream_data)



@router.get(
    "/schools/{registration_number}/classes/{class_id}/streams",
    response_model=List[StreamResponse]
)
async def get_streams(
    registration_number: str,
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """List all streams in a class"""
    class_service = ClassService(db)
    return await class_service.list_streams(registration_number, class_id)

@router.patch(
    "/schools/{registration_number}/classes/{class_id}/streams/{stream_id}",
    response_model=StreamResponse
)

@router.get(
    "/schools/{registration_number}/classes/{class_id}/streams",
    response_model=List[StreamResponse],
    status_code=status.HTTP_200_OK,
    tags=["admin", "streams"]
)
async def get_streams(
    registration_number: str,
    class_id: int,
    class_service: ClassService = Depends(get_class_service)
) -> List[StreamResponse]:
    """
    Get all streams for a specific class in a school
    """
    try:
        streams = await class_service.list_streams(registration_number, class_id)
        return [StreamResponse.from_orm(stream) for stream in streams]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

async def update_stream(
    registration_number: str,
    class_id: int,
    stream_id: int,
    update_data: StreamUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Update a specific stream"""
    class_service = ClassService(db)
    return await class_service.update_stream(registration_number, class_id, stream_id, update_data)

@router.delete(
    "/schools/{registration_number}/classes/{class_id}/streams/{stream_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        400: {"description": "Bad request - Stream has active students"},
        404: {"description": "School, class or stream not found"},
        500: {"description": "Internal server error"}
    }
)
async def delete_stream(
    registration_number: str,
    class_id: int,
    stream_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """
    Delete a stream
    
    Parameters:
    - registration_number: School registration number
    - class_id: ID of the class
    - stream_id: ID of the stream to delete
    
    Notes:
    - Stream must not have any active students
    - This is a soft delete operation
    """
    class_service = ClassService(db)
    await class_service.delete_stream(registration_number, class_id, stream_id)
    
    
# # Student Management Endpoints
# @router.post("/schools/{registration_number}/students")
# async def register_student(
#     registration_number: str,
#     student_data: StudentRegistrationRequest,
#     background_tasks: BackgroundTasks,
#     db: Session = Depends(get_db),
#     current_user: UserInDB = Depends(get_current_school_admin)
# ):
#     """Register a new student with class and stream assignment"""
#     clean_registration_number = registration_number.strip('{}')
    
#     # Get school
#     school = await db.execute(
#         select(School).where(School.registration_number == clean_registration_number)
#     )
#     school = school.scalar_one_or_none()
    
#     if not school:
#         raise HTTPException(status_code=404, detail="School not found")
    
#     # Verify stream exists and get its ID
#     stream = await db.execute(
#         select(Stream)
#         .join(Class)
#         .where(
#             Stream.school_id == school.id,
#             Class.id == student_data.class_id,
#             Stream.name == student_data.stream_name
#         )
#     )
#     stream = stream.scalar_one_or_none()

#     if not stream:
#         raise HTTPException(
#             status_code=404,
#             detail=f"Stream not found for class_id {student_data.class_id} and stream {student_data.stream_name}"
#         )

#     # Create student user account
#     student_user = User(
#         name=student_data.name,
#         email=student_data.email,
#         password_hash=get_password_hash(student_data.password),
#         role=UserRole.STUDENT,
#         school_id=school.id,
#         is_active=True
#     )
#     db.add(student_user)
#     await db.flush()

#     # Generate temporary password for parent account
#     parent_temp_password = generate_temporary_password()
    
#     # Create parent user account
#     parent_user = User(
#         name=f"Parent of {student_data.name}",
#         email=student_data.parent_email,  # Assuming this is added to StudentRegistrationRequest
#         password_hash=get_password_hash(parent_temp_password),
#         role=UserRole.PARENT,
#         school_id=school.id,
#         is_active=True
#     )
#     db.add(parent_user)
#     await db.flush()
    
#     # Create parent record
#     parent = Parent(
#         name=f"Parent of {student_data.name}",
#         user_id=parent_user.id,
#         school_id=school.id,
#         phone=student_data.parent_phone,  
#         email=student_data.parent_email   
#     )
#     db.add(parent)
#     await db.flush()
    
#     # Create student profile
#     student = Student(
#         name=student_data.name,
#         admission_number=student_data.admission_number,
#         class_id=student_data.class_id,
#         stream_id=stream.id,
#         user_id=student_user.id,
#         parent_id=parent.id,
#         date_of_birth=student_data.date_of_birth or date.today(),
#         school_id=school.id
#     )
#     db.add(student)
    
#     try:
#         await db.commit()
#         await db.refresh(student)
        
#         # Send email to parent with temporary password
#         background_tasks.add_task(
#             send_email,
#             recipient_email=parent_user.email,
#             subject="School Management System - Parent Account Created",
#             body=f"""
#             Dear Parent,
            
#             A parent account has been created for you in the School Management System.
#             Your temporary password is: {parent_temp_password}
            
#             Please change your password after first login.
            
#             Best regards,
#             School Management Team
#             """
#         )
#     except Exception as e:
#         await db.rollback()
#         raise HTTPException(
#             status_code=400,
#             detail=f"Error creating student: {str(e)}"
#         )
    
#     return {
#         "message": "Student registered successfully",
#         "student_id": student.id,
#         "admission_number": student.admission_number
#     }
    
# @router.get("/schools/{registration_number}/students", response_model=PaginatedStudentResponse)
# async def get_students(
#     registration_number: str,
#     class_id: Optional[int] = Query(None, description="Filter students by class"),
#     stream_id: Optional[int] = Query(None, description="Filter students by stream"),
#     search: Optional[str] = Query(None, description="Search by student name or admission number"),
#     page: int = Query(1, ge=1, description="Page number"),
#     page_size: int = Query(50, ge=1, le=100, description="Items per page"),
#     db: Session = Depends(get_db),
#     current_user: UserInDB = Depends(get_current_school_admin)
# ):
#     """
#     Get students with optional filtering by class and stream.
#     Implements pagination and search functionality.
#     Ensures school-level data isolation for multi-tenancy.
#     """
#     try:
#         clean_registration_number = registration_number.strip('{}')
        
#         # Get school and verify access
#         stmt = select(School).where(School.registration_number == clean_registration_number)
#         school = await db.execute(stmt)
#         school = school.scalar_one_or_none()
        
#         if not school:
#             raise HTTPException(status_code=404, detail="School not found")
            
#         if school.id != current_user.school_id:
#             raise HTTPException(status_code=403, detail="Access denied to this school's data")

#         # Build base query with all needed relationships
#         stmt = (
#             select(Student, Parent, Class, Stream)
#             .outerjoin(Parent, Student.parent_id == Parent.id)
#             .outerjoin(Class, Student.class_id == Class.id)
#             .outerjoin(Stream, Student.stream_id == Stream.id)
#             .where(Student.school_id == school.id)
#         )

#         # Apply filters
#         if class_id:
#             stmt = stmt.where(Student.class_id == class_id)

#         if stream_id:
#             stmt = stmt.where(Student.stream_id == stream_id)

#         if search:
#             search_term = f"%{search}%"
#             stmt = stmt.where(
#                 or_(
#                     Student.name.ilike(search_term),
#                     Student.admission_number.ilike(search_term)
#                 )
#             )

#         # Get total count
#         count_stmt = select(func.count()).select_from(
#             select(Student).where(Student.school_id == school.id)
#             .where(stmt.whereclause if stmt.whereclause is not None else True)
#             .subquery()
#         )
#         total_count = await db.execute(count_stmt)
#         total_count = total_count.scalar()

#         # Apply pagination
#         stmt = (
#             stmt.order_by(Student.name)
#             .offset((page - 1) * page_size)
#             .limit(page_size)
#         )

#         # Execute query
#         result = await db.execute(stmt)
#         rows = result.unique().all()

#         # Transform the results into the expected format
#         students = []
#         for student, parent, class_, stream in rows:
#             student_dict = {
#                 "id": student.id,
#                 "name": student.name,
#                 "admission_number": student.admission_number,
#                 "class_id": student.class_id,
#                 "stream_id": student.stream_id,
#                 "school_id": student.school_id,
#                 "date_of_birth": student.date_of_birth,
#                 "parent_name": parent.name if parent else None,
#                 "parent_phone": parent.phone if parent else None,
#                 "parent_email": parent.email if parent else None,
#                 "class_name": class_.name if class_ else None,
#                 "stream_name": stream.name if stream else None
#             }
#             students.append(student_dict)

#         # Create response using PaginatedStudentResponse
#         return PaginatedStudentResponse(
#             items=students,
#             total=total_count,
#             page=page,
#             page_size=page_size,
#             total_pages=math.ceil(total_count / page_size)
#         )

#     except SQLAlchemyError as e:
#         logger.error(f"Database error in get_students: {str(e)}", exc_info=True)
#         raise HTTPException(status_code=500, detail="Internal server error")
    
# # Helper endpoint to get available classes and streams for filtering
# @router.get("/schools/{registration_number}/filter-options")
# async def get_filter_options(
#     registration_number: str,
#     db: Session = Depends(get_db),
#     current_user: UserInDB = Depends(get_current_school_admin)
# ):
#     """Get available classes and streams for the school"""
#     clean_registration_number = registration_number.strip('{}')
    
#     school = await db.execute(
#         select(School).where(School.registration_number == clean_registration_number)
#     )
#     school = school.scalar_one_or_none()
    
#     if not school:
#         raise HTTPException(status_code=404, detail="School not found")
        
#     if school.id != current_user.school_id:
#         raise HTTPException(status_code=403, detail="Access denied to this school's data")

#     # Get classes
#     classes_query = select(Class).where(Class.school_id == school.id)
#     classes = await db.execute(classes_query)
#     classes = classes.scalars().all()

#     # Get streams
#     streams_query = select(Stream).where(Stream.school_id == school.id)
#     streams = await db.execute(streams_query)
#     streams = streams.scalars().all()

#     return {
#         "classes": [{"id": c.id, "name": c.name} for c in classes],
#         "streams": [{"id": s.id, "name": s.name} for s in streams]
#     }    


@router.post("/schools/{registration_number}/sessions", response_model=SessionResponse)
async def create_session(
    registration_number: str,
    session_data: SessionCreateRequest,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Create a new academic session for a school"""
    try:
        clean_registration_number = registration_number.strip('{}')
        
        # Verify school exists
        school = await db.execute(
            select(School).where(School.registration_number == clean_registration_number)
        )
        school = school.scalar_one_or_none()
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
        
        # Check authorization
        if current_user.school_id != school.id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to create sessions for this school"
            )
        
        # Validate dates
        if session_data.end_date < session_data.start_date:
            raise HTTPException(
                status_code=400,
                detail="End date must be on or after start date"
            )
        
        # Validate times
        if (
            session_data.end_date == session_data.start_date and 
            session_data.end_time <= session_data.start_time
        ):
            raise HTTPException(
                status_code=400,
                detail="End time must be after start time if on the same day"
            )
        
        # Normalize weekdays to uppercase
        weekdays = [day.upper() for day in session_data.weekdays]
        valid_days = {"MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"}
        if not set(weekdays).issubset(valid_days):
            raise HTTPException(
                status_code=400,
                detail=f"Weekdays must be one of {', '.join(valid_days)}"
            )
        
        # Create new session
        new_session = Session(
            name=session_data.name,
            start_date=session_data.start_date,
            end_date=session_data.end_date,
            start_time=session_data.start_time,
            end_time=session_data.end_time,
            weekdays=weekdays,
            description=session_data.description,
            is_active=True,
            school_id=school.id
        )
        
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        
        return new_session
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("Unexpected error in create_session")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while creating session"
        )

@router.get("/schools/{registration_number}/sessions", response_model=List[SessionResponse])
async def list_sessions(
    registration_number: str,
    show_inactive: bool = False,
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
    
    query = select(Session).where(Session.school_id == school.id)
    
    if not show_inactive:
        query = query.where(Session.is_active == True)
    
    query = query.order_by(Session.start_date.desc(), Session.start_time.asc())
    
    sessions = await db.execute(query)
    return sessions.scalars().all()

@router.get("/schools/{registration_number}/sessions/active", response_model=List[SessionResponse])
async def get_active_sessions(
    registration_number: str,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Get all active sessions for a school"""
    clean_registration_number = registration_number.strip('{}')
    
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    sessions = await db.execute(
        select(Session)
        .where(
            and_(
                Session.school_id == school.id,
                Session.is_active == True
            )
        )
        .order_by(Session.start_time.asc())
    )
    return sessions.scalars().all()

@router.patch("/schools/{registration_number}/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    registration_number: str,
    session_id: int,
    session_data: SessionUpdateRequest,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Update an existing session"""
    clean_registration_number = registration_number.strip('{}')
    
    # Verify school and session exist
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    )
    school = school.scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
        
    session = await db.execute(
        select(Session).where(
            and_(
                Session.id == session_id,
                Session.school_id == school.id
            )
        )
    )
    session = session.scalar_one_or_none()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Validate time updates if provided
    if session_data.start_time and session_data.end_time:
        if session_data.end_time <= session_data.start_time:
            raise HTTPException(
                status_code=400,
                detail="End time must be after start time"
            )
            
        # Check for overlaps with other sessions
        overlapping = await db.execute(
            select(Session).where(
                and_(
                    Session.school_id == school.id,
                    Session.id != session_id,
                    Session.start_date <= (session_data.end_date or session.end_date),
                    Session.end_date >= (session_data.start_date or session.start_date),
                    Session.start_time < session_data.end_time,
                    Session.end_time > session_data.start_time,
                    Session.is_active == True
                )
            )
        )
        if overlapping.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Updated session times would overlap with an existing active session"
            )
    
    # Update session
    update_data = session_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(session, key, value)
    
    await db.commit()
    await db.refresh(session)
    
    return session
    
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