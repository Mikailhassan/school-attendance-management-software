from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from app.services.attendance_service import AttendanceService
# from app.utils.fingerprint import capture_fingerprint
from app.dependencies import get_current_teacher, get_current_school_admin
from app.schemas import AttendanceRequest, WeeklyAttendanceResponse, PeriodAttendanceResponse
from app.models import User
from typing import List
from datetime import date, timedelta
import asyncio
import csv
import io

router = APIRouter()

# Dependency to get the Attendance Service
def get_attendance_service():
    return AttendanceService()

# Asynchronous continuous scanning for fingerprint recognition
async def continuous_scanning(background_tasks: BackgroundTasks, attendance_service: AttendanceService):
    while True:
        try:
            user_id, check_type = await capture_fingerprint()
            if user_id:
                background_tasks.add_task(attendance_service.mark_attendance, user_id, check_type)
        except Exception as e:
            # Log the error
            print(f"Error in continuous scanning: {str(e)}")
        finally:
            await asyncio.sleep(1)

@router.on_event("startup")
async def startup_event():
    attendance_service = get_attendance_service()
    background_tasks = BackgroundTasks()
    asyncio.create_task(continuous_scanning(background_tasks, attendance_service))

@router.post("/teachers/mark")
async def mark_teacher_attendance_route(
    current_teacher: User = Depends(get_current_teacher),
    attendance_service: AttendanceService = Depends(get_attendance_service)
):
    user_id, check_type = await capture_fingerprint()
    if user_id != current_teacher.id:
        raise HTTPException(status_code=400, detail="Invalid teacher fingerprint")
    
    return await attendance_service.mark_teacher_attendance(user_id, check_type)

@router.post("/students/mark")
async def mark_student_attendance_route(
    request: AttendanceRequest,
    current_teacher: User = Depends(get_current_teacher),
    attendance_service: AttendanceService = Depends(get_attendance_service)
):
    results = []
    for student_id in request.student_ids:
        result = await attendance_service.mark_student_attendance(
            student_id, is_present=True, school_id=current_teacher.school_id
        )
        results.append(result)
    
    return {"message": "Student attendance marked successfully", "results": results}

@router.get("/view/{date}")
async def view_attendance_route(
    date: date,
    current_admin: User = Depends(get_current_school_admin),
    attendance_service: AttendanceService = Depends(get_attendance_service)
):
    return await attendance_service.view_attendance_by_date(date, current_admin.school_id)

@router.get("/view/weekly", response_model=WeeklyAttendanceResponse)
async def view_weekly_attendance_route(
    current_admin: User = Depends(get_current_school_admin),
    attendance_service: AttendanceService = Depends(get_attendance_service)
):
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return await attendance_service.get_weekly_attendance(
        school_id=current_admin.school_id,
        start_date=monday,
        end_date=friday
    )

@router.get("/view/range", response_model=PeriodAttendanceResponse)
async def view_attendance_for_period_route(
    start_date: date,
    end_date: date,
    current_admin: User = Depends(get_current_school_admin),
    attendance_service: AttendanceService = Depends(get_attendance_service)
):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
    
    return await attendance_service.get_attendance_for_period(
        school_id=current_admin.school_id,
        start_date=start_date,
        end_date=end_date
    )

@router.get("/view/csv")
async def download_attendance_csv(
    start_date: date,
    end_date: date,
    current_admin: User = Depends(get_current_school_admin),
    attendance_service: AttendanceService = Depends(get_attendance_service)
):
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="Start date must be before end date")
    
    attendance_data = await attendance_service.generate_class_csv(
        school_id=current_admin.school_id,
        start_date=start_date,
        end_date=end_date
    )
    
    def iter_csv(data):
        output = io.StringIO()
        writer = csv.writer(output)
        for row in data:
            writer.writerow(row)
            yield output.getvalue()
            output.seek(0)
            output.truncate(0)

    response = StreamingResponse(iter_csv(attendance_data), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename=attendance_{start_date}_to_{end_date}.csv"
    return response