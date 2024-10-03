from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from app.models import Attendance, User
from app.database import get_db
from .fingerprint_service import FingerprintService

class AttendanceService:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    async def mark_attendance(self, user_id: int, check_type: str, scanner_type: str):
        user = self._get_user(user_id)
        fingerprint_service = FingerprintService(scanner_type)
        fingerprint_template = fingerprint_service.capture_fingerprint()

        if check_type == "check_in":
            self._handle_check_in(user_id, fingerprint_template)
        elif check_type == "check_out":
            self._handle_check_out(user_id)
        else:
            raise HTTPException(status_code=400, detail="Invalid check type")

        self.db.commit()
        return {"message": "Attendance marked successfully"}

    def _get_user(self, user_id: int) -> User:
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user

    def _handle_check_in(self, user_id: int, fingerprint_template: str):
        latest_record = self._get_latest_attendance_record(user_id)
        if latest_record and latest_record.check_out_time is None:
            raise HTTPException(status_code=400, detail="User already checked in")

        new_attendance = Attendance(
            user_id=user_id,
            check_in_time=datetime.utcnow(),
            fingerprint_template=fingerprint_template,
            is_present=True
        )
        self.db.add(new_attendance)

    def _handle_check_out(self, user_id: int):
        latest_record = self._get_latest_attendance_record(user_id)
        if not latest_record or latest_record.check_out_time is not None:
            raise HTTPException(status_code=400, detail="User has not checked in or already checked out")
        latest_record.check_out_time = datetime.utcnow()

    def _get_latest_attendance_record(self, user_id: int) -> Attendance:
        return self.db.query(Attendance).filter(Attendance.user_id == user_id).order_by(Attendance.id.desc()).first()

    async def view_attendance_by_date(self, date: str) -> dict:
        date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        attendance_records = self._get_attendance_records_for_date(date_obj)

        if not attendance_records:
            raise HTTPException(status_code=404, detail="No attendance records found for this date")

        formatted_records = self._format_attendance_records(attendance_records)
        return {"date": date, "attendance_records": formatted_records}

    def _get_attendance_records_for_date(self, date_obj: datetime.date) -> List[Attendance]:
        return self.db.query(Attendance).filter(
            Attendance.check_in_time >= datetime.combine(date_obj, datetime.min.time()),
            Attendance.check_in_time < datetime.combine(date_obj, datetime.max.time())
        ).all()

    def _format_attendance_records(self, records: List[Attendance]) -> List[dict]:
        return [
            {
                "user_id": record.user_id,
                "check_in_time": record.check_in_time,
                "check_out_time": record.check_out_time,
                "is_present": record.is_present,
                "fingerprint_template": record.fingerprint_template
            }
            for record in records
        ]



