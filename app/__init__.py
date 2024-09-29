from fastapi import FastAPI
from app.routes import auth_router, admin_router, teacher_router, student_router, parent_router, attendance_router, payment_router

def create_app() -> FastAPI:
    app = FastAPI(title="School Attendance Management System")

    # Include the routers from different modules
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    app.include_router(admin_router, prefix="/admin", tags=["Admin"])
    app.include_router(teacher_router, prefix="/teachers", tags=["Teachers"])
    app.include_router(student_router, prefix="/students", tags=["Students"])
    app.include_router(parent_router, prefix="/parents", tags=["Parents"])
    app.include_router(attendance_router, prefix="/attendance", tags=["Attendance"])
    # app.include_router(payment_router, prefix="/payments", tags=["Payments"])

    return app
