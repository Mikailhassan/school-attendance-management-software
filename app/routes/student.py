# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session

# from app.services.registration_service import RegistrationService
# from app.core.dependencies import get_current_school_admin, get_db
# from app.schemas import StudentRegistrationRequest, StudentResponse

# router = APIRouter(tags=["students"])
# registration_service = RegistrationService()  # Create an instance of the service

# @router.post("/register")
# async def register_student_route(
#     request: StudentRegistrationRequest, 
#     current_admin: str = Depends(get_current_school_admin)
# ):
#     """
#     Register a new student. Only accessible by school admins.
#     """
#     return await registration_service.register_student(request)  # Call the service method

# @router.get("/all")
# async def list_all_students(
#     current_admin: str = Depends(get_current_school_admin)
# ):
#     """
#     List all students in the school. Accessible by school admins.
#     """
#     return await registration_service.list_students(current_admin)

# @router.get("/{student_id}")
# async def get_student_details(
#     student_id: int, 
#     current_admin: str = Depends(get_current_school_admin),
#     db: Session = Depends(get_db)
# ):
#     """
#     Get the details of a specific student by ID, including attendance summary. 
#     Accessible by school admins.
#     """
#     # Fetch the student's profile
#     student = await registration_service.get_student(student_id, current_admin)
    
#     if not student:
#         raise HTTPException(status_code=404, detail="Student not found")

#     # Fetch the student's attendance summary
#     attendance_summary = await registration_service.get_student_attendance_summary(student_id, db)

#     # Return the student profile with attendance summary
#     return {
#         "student_info": student,
#         "attendance_summary": attendance_summary
#     }
