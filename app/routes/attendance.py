from fastapi import (
    APIRouter, 
    Depends, 
    HTTPException, 
    File, 
    UploadFile, 
    status
)
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date, datetime, timedelta
import csv
import io
import pandas as pd
import uuid

# Enums for standardized status and validation
class AttendanceStatus(str, Enum):
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"
    EXCUSED = "excused"

class AttendanceMode(str, Enum):
    MANUAL = "manual"
    BIOMETRIC = "biometric"
    QR_CODE = "qr_code"

class AttendanceRequest(BaseModel):
    """Comprehensive attendance marking request"""
    class_id: int
    students: List[Dict[str, Any]] = Field(
        ..., 
        min_items=1, 
        max_items=100, 
        description="List of student attendance details"
    )
    date: Optional[date] = Field(default_factory=date.today)
    mode: AttendanceMode = AttendanceMode.MANUAL
    
    @validator('students')
    def validate_student_data(cls, students):
        for student in students:
            # Ensure required fields are present
            if 'student_id' not in student:
                raise ValueError("Each student must have a student_id")
            
            # Validate status if provided
            if 'status' in student and student['status'] not in AttendanceStatus.__members__:
                raise ValueError(f"Invalid attendance status: {student['status']}")
        
        return students

class AttendanceRouter:
    def __init__(
        self, 
        attendance_service,
        notification_service,
        school_config_service
    ):
        self.attendance_service = attendance_service
        self.notification_service = notification_service
        self.school_config_service = school_config_service
    
    async def _validate_attendance_marking_permission(
        self, 
        user: User, 
        class_id: int
    ) -> bool:
        """
        Validate if user has permission to mark attendance for the given class
        """
        # Check if user is a teacher assigned to the class
        is_class_teacher = await self.attendance_service.is_teacher_of_class(
            user_id=user.id, 
            class_id=class_id
        )
        
        # Admins can mark attendance for all classes
        is_admin = user.role in ['admin', 'school_admin']
        
        return is_class_teacher or is_admin
    
    async def _process_attendance_record(
        self, 
        class_id: int, 
        student_data: Dict[str, Any], 
        marking_date: date
    ) -> Dict[str, Any]:
        """
        Process individual student attendance record
        """
        try:
            # Mark attendance for the student
            attendance_record = await self.attendance_service.mark_student_attendance(
                student_id=student_data['student_id'],
                class_id=class_id,
                status=student_data.get('status', AttendanceStatus.PRESENT),
                date=marking_date,
                notes=student_data.get('notes', '')
            )
            
            # Send notifications for absences
            if student_data.get('status') == AttendanceStatus.ABSENT:
                await self._notify_parent_of_absence(
                    student_id=student_data['student_id'],
                    absence_date=marking_date,
                    notes=student_data.get('notes', '')
                )
            
            return {
                "student_id": student_data['student_id'],
                "status": "success",
                "record": attendance_record
            }
        except Exception as e:
            return {
                "student_id": student_data['student_id'],
                "status": "failed",
                "error": str(e)
            }
    
    async def _notify_parent_of_absence(
        self, 
        student_id: int, 
        absence_date: date, 
        notes: Optional[str] = None
    ):
        """
        Send notification to parents about student absence
        """
        try:
            # Fetch student and parent details
            student = await self.attendance_service.get_student_details(student_id)
            
            # Compose notification message
            message = (
                f"Absence Notification: {student.name} was marked absent "
                f"on {absence_date.strftime('%Y-%m-%d')}. "
                f"{f'Notes: {notes}' if notes else ''}"
            )
            
            # Send notifications via multiple channels
            await self.notification_service.send_notifications(
                student_id=student_id,
                message=message,
                channels=['sms', 'email']
            )
        except Exception as e:
            logger.error(f"Failed to send absence notification: {str(e)}")
    
    @router.post("/mark", response_model=Dict[str, Any])
    async def mark_attendance(
        self,
        request: AttendanceRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
    ):
        """
        Comprehensive attendance marking endpoint
        
        - Supports multiple attendance modes
        - Validates user permissions
        - Processes individual student attendance
        - Sends notifications for absences
        """
        # Validate user's permission to mark attendance
        if not await self._validate_attendance_marking_permission(
            user=current_user, 
            class_id=request.class_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to mark attendance for this class"
            )
        
        # Validate attendance mode is supported
        supported_modes = await self.school_config_service.get_supported_attendance_modes(
            school_id=current_user.school_id
        )
        if request.mode not in supported_modes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Attendance mode {request.mode} is not supported"
            )
        
        # Process attendance for each student
        results = await asyncio.gather(
            *[
                self._process_attendance_record(
                    class_id=request.class_id,
                    student_data=student,
                    marking_date=request.date
                ) 
                for student in request.students
            ]
        )
        
        return {
            "message": "Attendance marked successfully",
            "results": results,
            "total_students": len(results),
            "successful_marks": sum(
                1 for result in results if result['status'] == 'success'
            )
        }
    
    @router.post("/upload", response_model=Dict[str, Any])
    async def bulk_upload_attendance(
        self,
        file: UploadFile = File(...),
        class_id: int = Form(...),
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
    ):
        """
        Bulk attendance upload via CSV/Excel
        
        - Supports CSV and Excel files
        - Validates file format and data
        - Processes attendance in batches
        """
        # Validate file type
        if file.content_type not in ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Please upload CSV or Excel file."
            )
        
        # Read file content
        try:
            # Read file based on content type
            if file.content_type == 'text/csv':
                df = pd.read_csv(io.BytesIO(await file.read()))
            else:
                df = pd.read_excel(io.BytesIO(await file.read()))
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Error reading file: {str(e)}"
            )
        
        # Validate DataFrame columns
        required_columns = ['student_id', 'status', 'notes']
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns. Required: {required_columns}"
            )
        
        # Convert DataFrame to list of dictionaries
        students = df.to_dict(orient='records')
        
        # Create attendance request
        attendance_request = AttendanceRequest(
            class_id=class_id,
            students=students,
            date=date.today()
        )
        
        # Mark attendance
        return await self.mark_attendance(
            request=attendance_request, 
            current_user=current_user,
            db=db
        )
    
    @router.get("/student/{student_id}/summary")
    async def get_student_attendance_summary(
        self,
        student_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db_session)
    ):
        """
        Generate attendance summary for a specific student
        
        - Supports date range filtering
        - Provides comprehensive attendance statistics
        """
        # Default to current academic term if no dates provided
        if not start_date or not end_date:
            academic_term = await self.attendance_service.get_current_academic_term()
            start_date = academic_term.start_date
            end_date = academic_term.end_date
        
        # Fetch attendance summary
        summary = await self.attendance_service.get_student_attendance_summary(
            student_id=student_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return {
            "student_id": student_id,
            "summary": {
                "total_days": summary.total_days,
                "present_days": summary.present_days,
                "absent_days": summary.absent_days,
                "late_days": summary.late_days,
                "attendance_percentage": summary.attendance_percentage
            },
            "detailed_records": summary.detailed_records
        }

# Router configuration
router = APIRouter(
    prefix="/attendance", 
    tags=["attendance"],
    dependencies=[Depends(authenticate_request)]
)