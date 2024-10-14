from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.routes import auth_router, admin_router, teacher_router, student_router, parent_router, attendance_router
from app.database import engine, Base, get_db
from app.models import School, User, RevokedToken
from app.core.config import settings
from app.core.security import get_password_hash
from app.dependencies import create_db_and_tables

app = FastAPI(
    title=settings.APP_NAME,
    description="API for managing school attendance using biometric authentication",
    version=settings.VERSION,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(teacher_router, prefix="/api/v1/teachers", tags=["Teachers"])
app.include_router(student_router, prefix="/api/v1/students", tags=["Students"])
app.include_router(parent_router, prefix="/api/v1/parents", tags=["Parents"])
app.include_router(attendance_router, prefix="/api/v1/attendance", tags=["Attendance"])

@app.on_event("startup")
async def startup_event():
    await create_db_and_tables()
    await create_super_admin()

async def create_super_admin():
    async with get_db() as db:
        if not await db.query(User).filter(User.role == "super_admin").first():
            super_admin = User(
                name="Super Admin",
                email=settings.SUPER_ADMIN_EMAIL,
                role="super_admin",
                password_hash=get_password_hash(settings.SUPER_ADMIN_PASSWORD)
            )
            db.add(super_admin)
            await db.commit()

