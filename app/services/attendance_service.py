from datetime import datetime, timedelta, date
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import List, Optional, Dict, Any  
from app.models import Attendance, User
from app.database import get_db
from .fingerprint_service import FingerprintService
from app.schemas import Attendance as AttendanceRecord 

class AttendanceService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db
        self.fingerprint_service = FingerprintService()

    async def initialize_fingerprint_scanner(self, current_admin: User) -> Dict[str, str]:
        if current_admin.role != "school_admin":
            raise HTTPException(status_code=403, detail="Only school admins can initialize the fingerprint scanner")
        try:
            await self.fingerprint_service.initialize_scanner()
            return {"message": "Fingerprint scanner initialized successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error initializing scanner: {str(e)}")

    async def mark_teacher_attendance(self, teacher_id: int, check_type: str, school_id: int) -> Dict[str, str]:
        teacher = self._get_user(teacher_id)
        
        try:
            fingerprint_template = await self.fingerprint_service.capture_fingerprint()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Fingerprint capture failed: {str(e)}")

        try:
            if check_type == "check_in":
                self._handle_teacher_check_in(teacher_id, fingerprint_template, school_id)
            elif check_type == "check_out":
                self._handle_teacher_check_out(teacher_id, school_id)
            else:
                raise HTTPException(status_code=400, detail="Invalid check type")

            self.db.commit()
            return {"message": "Attendance marked successfully for teacher"}
        except SQLAlchemyError as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    async def mark_student_attendance(self, student_id: int, is_present: bool, school_id: int) -> Dict[str, str]:
        student = self._get_user(student_id)
        try:
            attendance_record = Attendance(
                user_id=student_id,
                check_in_time=datetime.utcnow(),
                is_present=is_present,
                school_id=school_id
            )
            self.db.add(attendance_record)
            self.db.commit()
            return {"message": "Student attendance recorded successfully"}
        except SQLAlchemyError as e:
            self.db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    def _handle_teacher_check_in(self, teacher_id: int, fingerprint_template: str, school_id: int) -> None:
        latest_record = self._get_latest_attendance_record(teacher_id, school_id)
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

    def _handle_teacher_check_out(self, teacher_id: int, school_id: int) -> None:
        latest_record = self._get_latest_attendance_record(teacher_id, school_id)
        if not latest_record or latest_record.check_out_time is not None:
            raise HTTPException(status_code=400, detail="Teacher has not checked in or already checked out")
        latest_record.check_out_time = datetime.utcnow()

    def _get_user(self, user_id: int) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def _get_latest_attendance_record(self, user_id: int, school_id: int) -> Optional[Attendance]:
        return self.db.query(Attendance).filter(
            Attendance.user_id == user_id,
            Attendance.school_id == school_id
        ).order_by(Attendance.id.desc()).first()

    async def get_weekly_attendance(self, school_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
        if not start_date or not end_date:
            today = datetime.utcnow().date()
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=4)

        return await self.get_attendance_for_period(school_id, start_date, end_date)

    async def get_attendance_for_period(self, school_id: int, start_date: date, end_date: date) -> Dict[str, Any]:
        attendance_records = self._get_attendance_records_for_date_range(start_date, end_date, school_id)
        if not attendance_records:
            raise HTTPException(status_code=404, detail="No attendance records found for the selected period")

        formatted_records = self._format_attendance_records(attendance_records)
        return {
            "start_date": start_date,
            "end_date": end_date,
            "attendance_records": formatted_records
        }

    def _get_attendance_records_for_date_range(self, start_date: date, end_date: date, school_id: int) -> List[Attendance]:
        return self.db.query(Attendance).filter(
            Attendance.school_id == school_id,
            Attendance.check_in_time >= datetime.combine(start_date, datetime.min.time()),
            Attendance.check_in_time <= datetime.combine(end_date, datetime.max.time())
        ).all()

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