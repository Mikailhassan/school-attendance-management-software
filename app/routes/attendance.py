from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
from datetime import date, timedelta, datetime
import asyncio
import csv
import io
import os
import logging
from contextlib import asynccontextmanager

# Local imports
from app.services.attendance_service import AttendanceService
from app.utils.fingerprint import process_fingerprint, SupremaScanner, FingerprintScanner
from app.dependencies import get_current_teacher, get_current_school_admin
from app.schemas import (
    AttendanceRequest, 
    WeeklyAttendanceResponse, 
    PeriodAttendanceResponse,
    AttendanceResponse
)
from app.models import User
from app.utils.mock_fingerprint import MockFingerprint

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment configuration
DEV_MODE = os.getenv("APP_ENV", "development") == "development"
SCANNER_RETRY_LIMIT = int(os.getenv("SCANNER_RETRY_LIMIT", "3"))
SCANNER_RETRY_DELAY = int(os.getenv("SCANNER_RETRY_DELAY", "5"))

router = APIRouter(prefix="/attendance", tags=["attendance"])

# Global scanner instance
scanner_instance = None
scanning_task = None

class AttendanceException(HTTPException):
    """Custom exception for attendance-related errors"""
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=detail)

# Scanner management
@asynccontextmanager
async def get_scanner():
    """Context manager for scanner initialization and cleanup"""
    scanner = None
    try:
        if DEV_MODE:
            logger.info("Using mock fingerprint scanner (Development Mode)")
            scanner = MockFingerprint()
        else:
            for attempt in range(SCANNER_RETRY_LIMIT):
                try:
                    logger.info(f"Initializing production scanner (attempt {attempt + 1})")
                    scanner = SupremaScanner()
                    break
                except Exception as e:
                    if attempt < SCANNER_RETRY_LIMIT - 1:
                        logger.warning(f"Scanner initialization failed, retrying: {str(e)}")
                        await asyncio.sleep(SCANNER_RETRY_DELAY)
                    else:
                        raise
        yield scanner
    finally:
        if scanner and not DEV_MODE:
            await scanner.cleanup()

async def process_attendance_mark(
    user_id: str,
    check_type: str,
    attendance_service: AttendanceService
) -> Dict[str, Any]:
    """Process attendance marking with proper error handling"""
    try:
        result = await attendance_service.mark_attendance(user_id, check_type)
        logger.info(f"Marked {check_type} attendance for user {user_id}")
        return result
    except Exception as e:
        logger.error(f"Failed to mark attendance for user {user_id}: {str(e)}")
        raise AttendanceException(
            detail=f"Failed to mark attendance: {str(e)}",
            status_code=500
        )

async def continuous_scanning(
    attendance_service: AttendanceService
):
    """Continuous fingerprint scanning process"""
    logger.info(f"Starting continuous scanning in {'development' if DEV_MODE else 'production'} mode")
    
    while True:
        async with get_scanner() as scanner:
            try:
                if DEV_MODE:
                    await asyncio.sleep(5)
                    mock_data = await scanner.generate_mock_fingerprint_data()
                    await attendance_service.mark_attendance(
                        mock_data["template"]["user_id"],
                        "check_in"
                    )
                    logger.debug(f"Dev mode: Marked mock attendance for user {mock_data['template']['user_id']}")
                else:
                    fingerprint_data = await process_fingerprint(scanner)
                    if fingerprint_data and fingerprint_data.get("template"):
                        user_id = await attendance_service.match_fingerprint(fingerprint_data["template"])
                        if user_id:
                            current_hour = datetime.now().hour
                            check_type = "check_in" if current_hour < 12 else "check_out"
                            await attendance_service.mark_attendance(str(user_id), check_type)
            except Exception as e:
                if not DEV_MODE:
                    logger.error(f"Error in continuous scanning: {str(e)}")
                    await asyncio.sleep(SCANNER_RETRY_DELAY)
            finally:
                if not DEV_MODE:
                    await asyncio.sleep(1)

# Startup and shutdown events
@router.on_event("startup")
async def startup_event():
    """Initialize continuous scanning on startup"""
    try:
        attendance_service = AttendanceService()
        global scanning_task
        scanning_task = asyncio.create_task(continuous_scanning(attendance_service))
        logger.info("Successfully initialized continuous scanning")
    except Exception as e:
        logger.error(f"Failed to start continuous scanning: {str(e)}")

@router.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global scanning_task
    if scanning_task:
        scanning_task.cancel()
        try:
            await scanning_task
        except asyncio.CancelledError:
            pass
    logger.info("Shutdown complete")

# Route handlers
@router.post("/initialize-scanner", response_model=Dict[str, str])
async def initialize_scanner(
    current_admin: User = Depends(get_current_school_admin),
    attendance_service: AttendanceService = Depends(AttendanceService)
):
    """Initialize the fingerprint scanner"""
    return await attendance_service.initialize_fingerprint_scanner(current_admin)

@router.post("/teachers/mark", response_model=AttendanceResponse)
async def mark_teacher_attendance_route(
    current_teacher: User = Depends(get_current_teacher),
    attendance_service: AttendanceService = Depends(AttendanceService)
):
    """Mark teacher attendance with fingerprint verification"""
    try:
        async with get_scanner() as scanner:
            if DEV_MODE:
                mock_data = await scanner.generate_mock_fingerprint_data()
                return await attendance_service.mark_teacher_attendance(
                    current_teacher.id,
                    "check_in",
                    current_teacher.school_id
                )
            
            fingerprint_data = await process_fingerprint(scanner)
            if not fingerprint_data:
                raise AttendanceException(detail="Failed to capture fingerprint")

            if not await attendance_service.verify_teacher_fingerprint(
                current_teacher.id, 
                fingerprint_data["template"]
            ):
                raise AttendanceException(detail="Invalid teacher fingerprint")
            
            current_hour = datetime.now().hour
            check_type = "check_in" if current_hour < 12 else "check_out"
            
            return await attendance_service.mark_teacher_attendance(
                current_teacher.id,
                check_type,
                current_teacher.school_id
            )
    except AttendanceException:
        raise
    except Exception as e:
        logger.error(f"Error marking teacher attendance: {str(e)}")
        raise AttendanceException(
            detail="Failed to mark teacher attendance",
            status_code=500
        )

@router.post("/students/mark", response_model=AttendanceResponse)
async def mark_student_attendance_route(
    request: AttendanceRequest,
    current_teacher: User = Depends(get_current_teacher),
    attendance_service: AttendanceService = Depends(AttendanceService)
):
    """Mark attendance for multiple students"""
    try:
        results = []
        for student_id in request.student_ids:
            result = await attendance_service.mark_student_attendance(
                student_id, 
                is_present=True,
                school_id=current_teacher.school_id
            )
            results.append(result)
        
        return {
            "message": "Student attendance marked successfully", 
            "results": results
        }
    except Exception as e:
        logger.error(f"Error marking student attendance: {str(e)}")
        raise AttendanceException(
            detail="Failed to mark student attendance",
            status_code=500
        )

@router.get("/view/daily/{date}", response_model=Dict[str, Any])
async def view_daily_attendance_route(
    date: date,
    current_admin: User = Depends(get_current_school_admin),
    attendance_service: AttendanceService = Depends(AttendanceService)
):
    """View attendance records for a specific date"""
    try:
        return await attendance_service.get_attendance_for_period(
            school_id=current_admin.school_id,
            start_date=date,
            end_date=date
        )
    except Exception as e:
        logger.error(f"Error viewing daily attendance: {str(e)}")
        raise AttendanceException(
            detail="Failed to view daily attendance",
            status_code=500
        )

@router.get("/view/weekly", response_model=WeeklyAttendanceResponse)
async def view_weekly_attendance_route(
    current_admin: User = Depends(get_current_school_admin),
    attendance_service: AttendanceService = Depends(AttendanceService)
):
    """View attendance records for the current week"""
    try:
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        friday = monday + timedelta(days=4)
        return await attendance_service.get_attendance_for_period(
            school_id=current_admin.school_id,
            start_date=monday,
            end_date=friday
        )
    except Exception as e:
        logger.error(f"Error viewing weekly attendance: {str(e)}")
        raise AttendanceException(
            detail="Failed to view weekly attendance",
            status_code=500
        )

@router.get("/view/range", response_model=PeriodAttendanceResponse)
async def view_attendance_for_period_route(
    start_date: date,
    end_date: date,
    current_admin: User = Depends(get_current_school_admin),
    attendance_service: AttendanceService = Depends(AttendanceService)
):
    """View attendance records for a specific date range"""
    if start_date > end_date:
        raise AttendanceException(detail="Start date must be before end date")
    
    try:
        return await attendance_service.get_attendance_for_period(
            school_id=current_admin.school_id,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        logger.error(f"Error viewing period attendance: {str(e)}")
        raise AttendanceException(
            detail="Failed to view period attendance",
            status_code=500
        )

@router.get("/download/csv")
async def download_attendance_csv(
    start_date: date,
    end_date: date,
    current_admin: User = Depends(get_current_school_admin),
    attendance_service: AttendanceService = Depends(AttendanceService)
):
    """Download attendance records as CSV file"""
    if start_date > end_date:
        raise AttendanceException(detail="Start date must be before end date")
    
    try:
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

        response = StreamingResponse(
            iter_csv(attendance_data),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    f"attachment; "
                    f"filename=attendance_{start_date}_to_{end_date}.csv"
                )
            }
        )
        return response
    except Exception as e:
        logger.error(f"Error downloading attendance CSV: {str(e)}")
        raise AttendanceException(
            detail="Failed to download attendance CSV",
            status_code=500
        )

@router.get("/status", response_model=Dict[str, Any])
async def get_scanner_status(
    current_admin: User = Depends(get_current_school_admin)
):
    """Get the current status of the fingerprint scanner"""
    try:
        async with get_scanner() as scanner:
            status = await scanner.get_status()
            return {
                "status": status,
                "mode": "development" if DEV_MODE else "production",
                "scanning_active": scanning_task is not None and not scanning_task.done()
            }
    except Exception as e:
        logger.error(f"Error getting scanner status: {str(e)}")
        raise AttendanceException(
            detail="Failed to get scanner status",
            status_code=500
        )