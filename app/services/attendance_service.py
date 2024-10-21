from datetime import datetime, timedelta, date
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.future import select
from typing import List, Optional, Dict, Any, Tuple
import logging
from app.models import Attendance, User
from app.core.database import get_db
from .fingerprint_service import FingerprintService
from app.schemas import Attendance as AttendanceRecord

logger = logging.getLogger(__name__)

class AttendanceService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.fingerprint_service = FingerprintService(db=self.db)

    async def mark_attendance(self, user_id: str, check_type: str) -> Dict[str, str]:
        """
        Generic method to mark attendance for any user type
        """
        try:
            user = await self._get_user(int(user_id))
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            if user.role == "teacher":
                return await self.mark_teacher_attendance(int(user_id), check_type, user.school_id)
            else:
                return await self.mark_student_attendance(int(user_id), True, user.school_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user ID format")
        except Exception as e:
            logger.error(f"Error marking attendance: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def verify_teacher_fingerprint(self, teacher_id: int, fingerprint_template: str) -> bool:
        """Verify teacher's fingerprint against stored template"""
        try:
            stored_template = await self._get_stored_fingerprint_template(teacher_id)
            if not stored_template:
                return False
            return await self.fingerprint_service.verify_fingerprint(
                stored_template, 
                fingerprint_template
            )
        except Exception as e:
            logger.error(f"Error verifying fingerprint: {str(e)}")
            return False

    async def initialize_fingerprint_scanner(self, current_admin: User) -> Dict[str, str]:
        if current_admin.role != "school_admin":
            raise HTTPException(status_code=403, detail="Only school admins can initialize the fingerprint scanner")
        try:
            await self.fingerprint_service.initialize_scanner()
            return {"message": "Fingerprint scanner initialized successfully"}
        except Exception as e:
            logger.error(f"Scanner initialization error: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to initialize scanner")

    async def mark_teacher_attendance(self, teacher_id: int, check_type: str, school_id: int) -> Dict[str, str]:
        try:
            teacher = await self._get_user(teacher_id)
            if not teacher or teacher.role != "teacher":
                raise HTTPException(status_code=404, detail="Teacher not found")

            fingerprint_template = await self.fingerprint_service.capture_fingerprint()
            
            if check_type == "check_in":
                await self._handle_teacher_check_in(teacher_id, fingerprint_template, school_id)
            elif check_type == "check_out":
                await self._handle_teacher_check_out(teacher_id, school_id)
            else:
                raise HTTPException(status_code=400, detail="Invalid check type")

            await self.db.commit()
            return {"message": f"Attendance {check_type} marked successfully for teacher"}
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error in mark_teacher_attendance: {str(e)}")
            raise HTTPException(status_code=500, detail="Database error occurred")
        except Exception as e:
            logger.error(f"Error in mark_teacher_attendance: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to mark teacher attendance")

    async def mark_student_attendance(self, student_id: int, is_present: bool, school_id: int) -> Dict[str, str]:
        try:
            student = await self._get_user(student_id)
            if not student or student.role != "student":
                raise HTTPException(status_code=404, detail="Student not found")

            # Check for existing attendance record today
            existing_record = await self._get_today_attendance_record(student_id, school_id)
            if existing_record:
                raise HTTPException(status_code=400, detail="Attendance already marked for today")

            attendance_record = Attendance(
                user_id=student_id,
                check_in_time=datetime.utcnow(),
                is_present=is_present,
                school_id=school_id
            )
            self.db.add(attendance_record)
            await self.db.commit()
            return {"message": "Student attendance recorded successfully"}
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error in mark_student_attendance: {str(e)}")
            raise HTTPException(status_code=500, detail="Database error occurred")

    async def generate_class_csv(self, school_id: int, start_date: date, end_date: date) -> List[List[str]]:
        """Generate CSV data for attendance records"""
        try:
            records = await self._get_attendance_records_for_date_range(start_date, end_date, school_id)
            csv_data = [["Date", "User ID", "Name", "Role", "Check In", "Check Out", "Present"]]
            
            for record in records:
                user = await self._get_user(record.user_id)
                csv_data.append([
                    record.check_in_time.strftime("%Y-%m-%d"),
                    str(user.id),
                    user.name,
                    user.role,
                    record.check_in_time.strftime("%H:%M:%S"),
                    record.check_out_time.strftime("%H:%M:%S") if record.check_out_time else "N/A",
                    "Yes" if record.is_present else "No"
                ])
            return csv_data
        except Exception as e:
            logger.error(f"Error generating CSV: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to generate attendance report")

    async def _handle_teacher_check_in(self, teacher_id: int, fingerprint_template: str, school_id: int) -> None:
        latest_record = await self._get_latest_attendance_record(teacher_id, school_id)
        if latest_record and latest_record.check_out_time is None:
            raise HTTPException(status_code=400, detail="Teacher already checked in")

        new_attendance = Attendance(
            user_id=teacher_id,
            check_in_time=datetime.utcnow(),
            fingerprint_template=fingerprint_template,
            is_present=True,
            school_id=school_id
        )
        self.db.add(new_attendance)

    async def _handle_teacher_check_out(self, teacher_id: int, school_id: int) -> None:
        latest_record = await self._get_latest_attendance_record(teacher_id, school_id)
        if not latest_record or latest_record.check_out_time is not None:
            raise HTTPException(status_code=400, detail="Teacher has not checked in or already checked out")
        latest_record.check_out_time = datetime.utcnow()

    async def _get_user(self, user_id: int) -> Optional[User]:
        result = await self.db.execute(select(User).filter(User.id == user_id))
        return result.scalars().first()

    async def _get_stored_fingerprint_template(self, user_id: int) -> Optional[str]:
        result = await self.db.execute(
            select(Attendance)
            .filter(Attendance.user_id == user_id)
            .order_by(Attendance.id.desc())
        )
        record = result.scalars().first()
        return record.fingerprint_template if record else None

    async def _get_latest_attendance_record(self, user_id: int, school_id: int) -> Optional[Attendance]:
        result = await self.db.execute(
            select(Attendance)
            .filter(
                Attendance.user_id == user_id,
                Attendance.school_id == school_id
            )
            .order_by(Attendance.id.desc())
        )
        return result.scalars().first()

    async def _get_today_attendance_record(self, user_id: int, school_id: int) -> Optional[Attendance]:
        today = datetime.utcnow().date()
        result = await self.db.execute(
            select(Attendance)
            .filter(
                Attendance.user_id == user_id,
                Attendance.school_id == school_id,
                Attendance.check_in_time >= datetime.combine(today, datetime.min.time()),
                Attendance.check_in_time < datetime.combine(today + timedelta(days=1), datetime.min.time())
            )
        )
        return result.scalars().first()

    async def _get_attendance_records_for_date_range(
        self, 
        start_date: date, 
        end_date: date, 
        school_id: int
    ) -> List[Attendance]:
        result = await self.db.execute(
            select(Attendance)
            .filter(
                Attendance.school_id == school_id,
                Attendance.check_in_time >= datetime.combine(start_date, datetime.min.time()),
                Attendance.check_in_time <= datetime.combine(end_date, datetime.max.time())
            )
            .order_by(Attendance.check_in_time)
        )
        return result.scalars().all()

    def _format_attendance_records(self, records: List[Attendance]) -> List[AttendanceRecord]:
        return [
            AttendanceRecord(
                user_id=record.user_id,
                check_in_time=record.check_in_time,
                check_out_time=record.check_out_time,
                is_present=record.is_present,
                fingerprint_template=record.fingerprint_template
            )
            for record in records
        ]