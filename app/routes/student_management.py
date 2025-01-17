from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, File, UploadFile, status, Request
from sqlalchemy.orm import Session, joinedload, selectinload, load_only 
from sqlalchemy import func, select, update, or_
from typing import Dict, Any, Optional,List,Union
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.params import Query
from datetime import date,datetime
from app.schemas.enums import UserRole
from app.services.email_service import EmailService
from app.services.attendance_service import get_student_attendance_summary
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.sql import and_, func
import re
import math
from app.services.class_service import ClassService
from app.core.exceptions import DuplicateSchoolException, SchoolNotFoundException, ResourceNotFoundException
from app.schemas.school.responses import ClassDetailsResponse 
from app.schemas.school.requests import BulkClassCreateRequest
from app.schemas.parents import ParentResponse
from app.models import (
    School, Class, Stream, Session, User, Student, Parent,
    StudentAttendance
)

from app.schemas.user import UserResponse

from app.schemas.student import StudentRegistrationRequest, StudentUpdate
from app.schemas.student.responses import StudentResponse, PaginatedStudentResponse

from app.services.auth_service import AuthService, get_auth_service
from app.core.logging import logger
import pandas as pd
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

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["student_management"]
)

@router.post("/schools/{registration_number}/students")
async def register_student(
    registration_number: str,
    student_data: StudentRegistrationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Register a new student with class and stream assignment"""
    
    async with db.begin():
        try:
            # Get school
            result = await db.execute(
                select(School).where(School.registration_number == registration_number.strip('{}'))
            )
            school = result.scalar_one_or_none()
            
            if not school:
                raise HTTPException(status_code=404, detail="School not found")
            
            # Verify stream exists
            if student_data.stream_id:
                result = await db.execute(
                    select(Stream)
                    .where(
                        Stream.id == student_data.stream_id,
                        Stream.school_id == school.id,
                        Stream.class_id == student_data.class_id
                    )
                )
                if not result.scalar_one_or_none():
                    raise HTTPException(
                        status_code=404,
                        detail=f"Stream not found for class_id {student_data.class_id} and stream_id {student_data.stream_id}"
                    )

            # Generate student email and passwords
            student_email = f"student_{student_data.admission_number}@{school.registration_number}.edu"
            parent_temp_password = generate_temporary_password()
            student_temp_password = generate_temporary_password()
            
            # 1. Create student user first
            student_user = User(
                name=student_data.name,
                email=student_email,
                password_hash=get_password_hash(student_temp_password),
                role=UserRole.STUDENT,
                school_id=school.id,
                is_active=True,
                date_of_birth=student_data.date_of_birth
            )
            db.add(student_user)
            await db.flush()
            
            # 2. Create parent user
            parent_user = User(
                name=student_data.parent_name,
                email=student_data.parent_email,
                password_hash=get_password_hash(parent_temp_password),
                role=UserRole.PARENT,
                school_id=school.id,
                is_active=True,
                phone=student_data.parent_phone
            )
            db.add(parent_user)
            await db.flush()
            
            # 3. Create parent record
            parent = Parent(
                name=student_data.parent_name,
                user_id=parent_user.id,
                school_id=school.id,
                phone=student_data.parent_phone,
                email=student_data.parent_email,
                id_number=str(student_data.parent_id_number),
                relation_type=student_data.relation_type
            )
            db.add(parent)
            await db.flush()
            
            # 4. Create student record
            student = Student(
                name=student_data.name,
                admission_number=str(student_data.admission_number),
                class_id=student_data.class_id,
                stream_id=student_data.stream_id,
                parent_id=parent.id,
                user_id=student_user.id,
                date_of_birth=student_data.date_of_birth,
                date_of_joining=student_data.date_of_joining,
                school_id=school.id,
                gender=student_data.gender,
                address=student_data.address,
                photo=student_data.photo,
                fingerprint=student_data.fingerprint
            )
            db.add(student)
            await db.flush()

            # Schedule email sending tasks
            # background_tasks.add_task(
            #     send_email,
            #     recipient_email=parent_user.email,
            #     subject="School Management System - Parent Account Created",
            #     body=f"""
            #     Dear {student_data.parent_name},
                
            #     A parent account has been created for you in the School Management System.
            #     Your temporary password is: {parent_temp_password}
                
            #     Please change your password after first login.
                
            #     Best regards,
            #     School Management Team
            #     """
            # )

            # background_tasks.add_task(
            #     send_email,
            #     recipient_email=student_email,
            #     subject="School Management System - Student Account Created",
            #     body=f"""
            #     Dear {student_data.name},
                
            #     Your student account has been created in the School Management System.
            #     Your email: {student_email}
            #     Your temporary password is: {student_temp_password}
                
            #     Please change your password after first login.
                
            #     Best regards,
            #     School Management Team
            #     """
            # )
            
            return {
                "message": "Student registered successfully",
                "student_id": student.id,
                # "student_email": student_email,
                "admission_number": student.admission_number,
                "parent_id": parent.id
            }
            
        except IntegrityError as e:
            raise HTTPException(
                status_code=400,
                detail="Database integrity error. This could be due to duplicate admission number or email."
            )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Error creating student: {str(e)}"
            )
@router.get("/schools/{registration_number}/students", response_model=PaginatedStudentResponse)
async def get_students(
    registration_number: str,
    class_id: Optional[int] = Query(None, description="Filter students by class"),
    stream_id: Optional[int] = Query(None, description="Filter students by stream"),
    search: Optional[str] = Query(None, description="Search by student name or admission number"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Get paginated list of students"""
    try:
        clean_registration_number = registration_number.strip('{}')
        
        # Get school with proper await
        result = await db.execute(
            select(School).where(School.registration_number == clean_registration_number)
        )
        school = result.scalar_one_or_none()
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
            
        # Base query with proper joins
        query = (
            select(Student, Parent, Class, Stream)
            .outerjoin(Parent, Student.parent_id == Parent.id)
            .outerjoin(Class, Student.class_id == Class.id)
            .outerjoin(Stream, Student.stream_id == Stream.id)
            .where(Student.school_id == school.id)
        )

        # Apply filters
        if class_id:
            query = query.where(Student.class_id == class_id)
        if stream_id:
            query = query.where(Student.stream_id == stream_id)
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Student.name.ilike(search_term),
                    Student.admission_number.ilike(search_term)
                )
            )

        # Get total count with proper await
        count_stmt = select(func.count()).select_from(
            select(Student).where(Student.school_id == school.id)
        )
        total = await db.execute(count_stmt)
        total = total.scalar()

        # Apply pagination
        query = (
            query.offset((page - 1) * page_size)
            .limit(page_size)
            .order_by(Student.name)
        )
        
        # Execute query with proper await
        result = await db.execute(query)
        rows = result.unique().all()

        # Transform results
        student_responses = [
            {
                "id": student.id,
                "name": student.name,
                "admission_number": student.admission_number,
                "class_id": student.class_id,
                "stream_id": student.stream_id,
                "school_id": student.school_id,
                "parent_id": student.parent_id,
                "date_of_birth": student.date_of_birth,
                "gender": getattr(student, 'gender', None),
                "address": getattr(student, 'address', None),
                "photo": getattr(student, 'photo', None),
                "fingerprint": getattr(student, 'fingerprint', None),
                "date_of_joining": getattr(student, 'date_of_joining', None),
                "parent_name": parent.name if parent else None,
                "parent_phone": parent.phone if parent else None,
                "parent_email": parent.email if parent else None,
                "class_name": class_.name if class_ else None,
                "stream_name": stream.name if stream else None
            }
            for student, parent, class_, stream in rows
        ]

        return PaginatedStudentResponse(
            items=student_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size)
        )

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_students: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    
@router.get("/schools/{registration_number}/filter-options")
async def get_filter_options(
    registration_number: str,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Get available classes and streams for the school"""
    clean_registration_number = registration_number.strip('{}')
    
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    ).scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
        
    if school.id != current_user.school_id:
        raise HTTPException(status_code=403, detail="Access denied to this school's data")

    # Get classes and streams
    classes = await db.execute(
        select(Class).where(Class.school_id == school.id)
    ).scalars().all()

    streams = await db.execute(
        select(Stream).where(Stream.school_id == school.id)
    ).scalars().all()

    return {
        "classes": [{"id": c.id, "name": c.name} for c in classes],
        "streams": [{"id": s.id, "name": s.name} for s in streams]
    }

@router.get("/schools/{registration_number}/students/{student_id}", response_model=StudentResponse)
async def get_student_details(
    registration_number: str,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Get detailed information about a specific student"""
    clean_registration_number = registration_number.strip('{}')
    
    # Get student with related information
    result = await db.execute(
        select(Student, Parent, Class, Stream)
        .outerjoin(Parent, Student.parent_id == Parent.id)
        .outerjoin(Class, Student.class_id == Class.id)
        .outerjoin(Stream, Student.stream_id == Stream.id)
        .where(
            Student.id == student_id,
            Student.school_id == select(School.id)
            .where(School.registration_number == clean_registration_number)
            .scalar_subquery()
        )
    )
    
    row = result.unique().first()
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    
    student, parent, class_, stream = row
    
    # Get attendance summary
    attendance_summary = await get_student_attendance_summary(db, student.id)
    
    return StudentResponse(
        id=student.id,
        name=student.name,
        admission_number=student.admission_number,
        photo=student.photo,
        gender=student.gender.value if hasattr(student.gender, 'value') else student.gender,
        fingerprint=student.fingerprint,
        date_of_birth=student.date_of_birth,
        date_of_joining=student.date_of_joining,
        address=student.address,
        relation_type=parent.relation_type if parent else None,  # Fixed field name
        class_id=class_.id if class_ else None,
        parent_id=parent.id if parent else None,
        stream_id=stream.id if stream else None,
        school_id=student.school_id,
        parent_id_number=parent.id_number if parent else None,
        parent_name=parent.name if parent else None,
        parent_phone=parent.phone if parent else None,
        parent_email=parent.email if parent else None
        
        
       
    )
    
    # Return response with both student data and attendance summary
    return {
        "student": student_response,
        "attendance_summary": attendance_summary
    }

@router.delete("/schools/{registration_number}/students/{student_id}")
async def delete_student(
    registration_number: str,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Delete a student (soft delete)"""
    clean_registration_number = registration_number.strip('{}')
    
    student = await db.execute(
        select(Student)
        .join(School)
        .where(
            School.registration_number == clean_registration_number,
            Student.id == student_id
        )
    ).scalar_one_or_none()
    
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
        
    student.is_active = False
    
    if student.user_id:
        user = await db.execute(
            select(User).where(User.id == student.user_id)
        ).scalar_one_or_none()
        if user:
            user.is_active = False
    
    try:
        await db.commit()
        return {"message": "Student deleted successfully"}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"Error deleting student: {str(e)}")
    
    
  
@router.get("/schools/{registration_number}/students", response_model=PaginatedStudentResponse)
async def get_students(
    registration_number: str,
    class_id: Optional[int] = Query(None, description="Filter students by class"),
    stream_id: Optional[int] = Query(None, description="Filter students by stream"),
    search: Optional[str] = Query(None, description="Search by student name or admission number"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Get paginated list of students"""
    try:
        clean_registration_number = registration_number.strip('{}')
        
        # Get school
        school = await db.execute(
            select(School).where(School.registration_number == clean_registration_number)
        ).scalar_one_or_none()
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
            
        # Base query
        query = (
            select(Student)
            .options(joinedload(Student.parent))
            .where(Student.school_id == school.id)
        )

        # Apply filters
        if class_id:
            query = query.where(Student.class_id == class_id)
        if stream_id:
            query = query.where(Student.stream_id == stream_id)
        if search:
            search_term = f"%{search}%"
            query = query.where(
                or_(
                    Student.name.ilike(search_term),
                    Student.admission_number.ilike(search_term)
                )
            )

        # Get total count
        total = await db.execute(
            select(func.count()).select_from(query.subquery())
        ).scalar()

        # Apply pagination
        students = await db.execute(
            query.offset((page - 1) * page_size)
            .limit(page_size)
            .order_by(Student.name)
        )
        
        students = students.unique().scalars().all()

        students = [
            {
                "id": student.id,
                "name": student.name,
                "admission_number": student.admission_number,
                "class_id": student.class_id,
                "stream_id": student.stream_id,
                "school_id": student.school_id,
                "parent_id": student.parent_id,
                "date_of_birth": student.date_of_birth,
                "gender": getattr(student, 'gender', None),
                "address": getattr(student, 'address', None),
                "photo": getattr(student, 'photo', None),
                "fingerprint": getattr(student, 'fingerprint', None),
                "date_of_joining": getattr(student, 'date_of_joining', None),
                "parent_name": parent.name if parent else None,
                "parent_phone": parent.phone if parent else None,
                "parent_email": parent.email if parent else None,
                "class_name": class_.name if class_ else None,
                "stream_name": stream.name if stream else None
            }
            for student, parent, class_, stream in rows
        ]

        return PaginatedStudentResponse(
            items=student_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size)
        )

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_students: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")    
    

@router.post("/schools/{registration_number}/students/bulk-upload")
async def bulk_upload_students(
    registration_number: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Bulk upload students from CSV/Excel file"""
    clean_registration_number = registration_number.strip('{}')
    
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    ).scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    try:
        content = await file.read()
        
        if file.filename.endswith('.csv'):
            df = pd.read_csv(io.StringIO(content.decode('utf-8')))
        elif file.filename.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(io.BytesIO(content))
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format")
        
        required_columns = [
            'name', 'admission_number', 'class_id', 'stream_name',
            'parent_name', 'parent_email', 'parent_phone'
        ]
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(missing_columns)}"
            )
        
        success_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                student_data = StudentRegistrationRequest(
                    name=row['name'],
                    admission_number=row['admission_number'],
                    class_id=row['class_id'],
                    stream_name=row['stream_name'],
                    date_of_birth=row.get('date_of_birth', date.today()),
                    gender=row.get('gender', 'OTHER'),
                    parent_name=row['parent_name'],
                    parent_email=row['parent_email'],
                    parent_phone=row['parent_phone']
                )
                
                await register_student(
                    registration_number=clean_registration_number,
                    student_data=student_data,
                    background_tasks=BackgroundTasks(),
                    db=db,
                    current_user=current_user
                )
                
                success_count += 1
                
            except Exception as e:
                errors.append({
                    'row': index + 2,  # +2 for Excel row number (header + 1-based index)
                    'error': str(e)
                })
        
        return {
            "message": f"Processed {len(df)} records",
            "success_count": success_count,
            "error_count": len(errors),
            "errors": errors
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error processing file: {str(e)}")

@router.get("/schools/{registration_number}/student-statistics")
async def get_student_statistics(
    registration_number: str,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Get various statistics about students"""
    clean_registration_number = registration_number.strip('{}')
    
    school = await db.execute(
        select(School).where(School.registration_number == clean_registration_number)
    ).scalar_one_or_none()
    
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    
    # Get total active students count
    total_students = await db.execute(
        select(func.count(Student.id))
        .where(
            Student.school_id == school.id,
            Student.is_active == True
        )
    ).scalar()
    
    # Get gender distribution
    gender_dist = await db.execute(
        select(Student.gender, func.count(Student.id))
        .where(
            Student.school_id == school.id,
            Student.is_active == True
        )
        .group_by(Student.gender)
    ).all()
    gender_distribution = {str(gender): count for gender, count in gender_dist}
    
    # Get class distribution
    class_dist = await db.execute(
        select(Class.name, func.count(Student.id))
        .join(Student, Student.class_id == Class.id)
        .where(
            Student.school_id == school.id,
            Student.is_active == True
        )
        .group_by(Class.name)
    ).all()
    class_distribution = dict(class_dist)
    
    # Get stream distribution
    stream_dist = await db.execute(
        select(Stream.name, func.count(Student.id))
        .join(Student, Student.stream_id == Stream.id)
        .where(
            Student.school_id == school.id,
            Student.is_active == True
        )
        .group_by(Stream.name)
    ).all()
    stream_distribution = dict(stream_dist)
    
    # Get age distribution
    age_dist = await db.execute(
        select(
            func.date_part('year', func.age(func.current_date(), Student.date_of_birth)).label('age'),
            func.count(Student.id)
        )
        .where(
            Student.school_id == school.id,
            Student.is_active == True
        )
        .group_by('age')
        .order_by('age')
    ).all()
    age_distribution = {int(age): count for age, count in age_dist}
    
    return {
        "total_students": total_students,
        "gender_distribution": gender_distribution,
        "class_distribution": class_distribution,
        "stream_distribution": stream_distribution,
        "age_distribution": age_distribution,
        "average_students_per_class": total_students / len(class_distribution) if class_distribution else 0
    }
    
    
    
@router.get("/schools/{registration_number}/parents")
async def get_parents(
    registration_number: str,
    search: Optional[str] = Query(None, description="Search by parent name or email"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_school_admin)
):
    """Get paginated list of parents with their associated students"""
    try:
        clean_registration_number = registration_number.strip('{}')
        
        # Get school
        result = await db.execute(
            select(School).where(School.registration_number == clean_registration_number)
        )
        school = result.scalar_one_or_none()
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
            
        if school.id != current_user.school_id:
            raise HTTPException(status_code=403, detail="Access denied to this school's data")

        # Build base query
        stmt = (
            select(Parent, func.array_agg(Student.name).label('student_names'))
            .outerjoin(Student, Parent.id == Student.parent_id)
            .where(Parent.school_id == school.id)
            .group_by(Parent.id)
        )

        # Apply search filter if provided
        if search:
            search_term = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Parent.name.ilike(search_term),
                    Parent.email.ilike(search_term),
                    Parent.phone.ilike(search_term)
                )
            )

        # Get total count
        count_result = await db.execute(
            select(func.count()).select_from(stmt.subquery())
        )
        total_count = count_result.scalar()

        # Apply pagination
        stmt = (
            stmt.order_by(Parent.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        # Execute query
        result = await db.execute(stmt)
        rows = result.all()

        # Transform results
        parents = [
            ParentResponse(
                id=parent.id,
                name=parent.name,
                email=parent.email,
                phone=parent.phone,
                school_id=parent.school_id,
                user_id=parent.user_id,
                students=[name for name in student_names if name is not None]
            )
            for parent, student_names in rows
        ]

        return {
            "items": parents,
            "total": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total_count / page_size)
        }

    except SQLAlchemyError as e:
        logger.error(f"Database error in get_parents: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    
    
    
    
@router.get("/schools/{registration_number}/parents/{parent_id}")
async def get_parent_details(
    registration_number: str,
    parent_id: int,
    db: Session = Depends(get_db),
    current_user: UserInDB = Depends(get_current_active_user)
):
    """Get detailed information about a specific parent and their associated students"""
    try:
        clean_registration_number = registration_number.strip('{}')
        
        # Get parent with associated students and school verification
        result = await db.execute(
            select(Parent, School)
            .join(School, Parent.school_id == School.id)
            .where(
                Parent.id == parent_id,
                School.registration_number == clean_registration_number
            )
        )
        parent_row = result.first()
        
        if not parent_row:
            raise HTTPException(status_code=404, detail="Parent not found")
            
        parent, school = parent_row
        
        # Get all students associated with this parent
        students_result = await db.execute(
            select(Student, Class, Stream)
            .outerjoin(Class, Student.class_id == Class.id)
            .outerjoin(Stream, Student.stream_id == Stream.id)
            .where(Student.parent_id == parent_id)
        )
        student_rows = students_result.all()
        
        # Get parent user information
        user_result = await db.execute(
            select(User)
            .where(User.id == parent.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        # Format the response
        return {
            "parent": {
                "id": parent.id,
                "name": parent.name,
                "email": parent.email,
                "phone": parent.phone,
                "address": getattr(parent, 'address', None),
                "occupation": getattr(parent, 'occupation', None),
                "relationship_to_student": getattr(parent, 'relationship_to_student', None),
                "user_status": {
                    "is_active": user.is_active if user else None,
                    "last_login": getattr(user, 'last_login', None) if user else None
                }
            },
            "students": [
                {
                    "id": student.id,
                    "name": student.name,
                    "admission_number": student.admission_number,
                    "class": {
                        "id": class_.id,
                        "name": class_.name
                    } if class_ else None,
                    "stream": {
                        "id": stream.id,
                        "name": stream.name
                    } if stream else None,
                    "date_of_birth": student.date_of_birth,
                    "gender": getattr(student, 'gender', None)
                }
                for student, class_, stream in student_rows
            ],
            "school": {
                "id": school.id,
                "name": school.name,
                "registration_number": school.registration_number
            }
        }
        
    except SQLAlchemyError as e:
        logger.error(f"Database error in get_parent_details: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")    
    