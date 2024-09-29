# services/attendance_service.py
from app.models import Attendance, User
from app.database import SessionLocal
from fastapi import HTTPException
from datetime import datetime
from .fingerprint_service import FingerprintService

async def mark_attendance(user_id: int, check_type: str, scanner_type: str):
    db = SessionLocal()
    
    # Check if the user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Initialize the fingerprint service
    fingerprint_service = FingerprintService(scanner_type)
    
    # Capture the fingerprint
    fingerprint_template = fingerprint_service.capture_fingerprint()

    # Create or update attendance record
    attendance_record = db.query(Attendance).filter(Attendance.user_id == user_id).order_by(Attendance.id.desc()).first()

    if check_type == "check_in":
        if attendance_record and attendance_record.check_out_time is None:  # Already checked in
            raise HTTPException(status_code=400, detail="User already checked in")
        
        # Create new attendance record for check-in
        new_attendance = Attendance(
            user_id=user_id,
            check_in_time=datetime.utcnow(),
            fingerprint_template=fingerprint_template,
            is_present=True
        )
        db.add(new_attendance)

    elif check_type == "check_out":
        if not attendance_record or attendance_record.check_out_time is not None:  # Not checked in or already checked out
            raise HTTPException(status_code=400, detail="User has not checked in or already checked out")

        # Update the existing record with check-out time
        attendance_record.check_out_time = datetime.utcnow()

    db.commit()
    return {"message": "Attendance marked successfully"}

async def view_attendance_by_date(date: str):
    db = SessionLocal()
    
    # Convert string date to a datetime object
    date_obj = datetime.strptime(date, '%Y-%m-%d').date()

    # Retrieve attendance records for the specified date
    attendance_records = db.query(Attendance).filter(
        Attendance.check_in_time >= datetime.combine(date_obj, datetime.min.time()),
        Attendance.check_in_time < datetime.combine(date_obj, datetime.max.time())
    ).all()

    if not attendance_records:
        raise HTTPException(status_code=404, detail="No attendance records found for this date")

    # Format records for return
    formatted_records = []
    for record in attendance_records:
        formatted_records.append({
            "user_id": record.user_id,
            "check_in_time": record.check_in_time,
            "check_out_time": record.check_out_time,
            "is_present": record.is_present,
            "fingerprint_template": record.fingerprint_template  # Include fingerprint if needed
        })

    return {"date": date, "attendance_records": formatted_records}
