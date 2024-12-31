#app/_init_.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from app.routes import auth, admin, teacher, student, parent, attendance
from app.core.database import init_db, close_db, get_db
from app.core.security import get_password_hash
from app.models.user import User
from app.models.school import School
from app.services.email_service import EmailService
from sqlalchemy.future import select
import logging

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)


# Initialize EmailService
email_service = EmailService()

def get_email_service():
    return email_service

def create_app() -> FastAPI:
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
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(teacher.router, prefix="/api/v1/teachers", tags=["Teachers"])
    app.include_router(student.router, prefix="/api/v1/students", tags=["Students"])
    app.include_router(parent.router, prefix="/api/v1/parents", tags=["Parents"])
    # app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["Attendance"])

    @app.on_event("startup")
    async def startup_event():
        await init_db()
        async for db in get_db():
            await create_system_school(db)
            await create_super_admin(db)
        logger.info("Application startup completed")

    @app.on_event("shutdown")
    async def shutdown_event():
        await close_db()
        logger.info("Application shutdown completed")

    return app

async def create_system_school(db):
    """Create a system-level school for administrative purposes."""
    stmt = select(School).filter(School.name == "System")
    result = await db.execute(stmt)
    system_school = result.scalar_one_or_none()

    if not system_school:
        # Create with all required fields
        system_school = School(
            name="System",
            email="system@school.local",
            phone="0000000000",
            address="System Address",
            county="System County",
            postal_code="00000",
            class_system="System",
            class_range={"start": 1, "end": 12},  # Changed to use class_range as JSON
            extra_info={}  # Optional: add any extra info as JSON
        )
        db.add(system_school)
        await db.commit()
        logger.info("System school created successfully")
    return system_school
async def create_super_admin(db):
    # First, get the system school
    stmt = select(School).filter(School.name == "System")
    result = await db.execute(stmt)
    system_school = result.scalar_one_or_none()

    if not system_school:
        logger.error("System school not found")
        return

    # Check if super admin exists
    stmt = select(User).filter(User.role == "super_admin")
    result = await db.execute(stmt)
    super_admin = result.scalar_one_or_none()

    if not super_admin:
        super_admin = User(
            name="Super Admin",
            email=settings.SUPER_ADMIN_EMAIL,
            role="super_admin",
            password_hash=get_password_hash(settings.SUPER_ADMIN_PASSWORD.get_secret_value()),
            school_id=system_school.id,
            is_active=True
        )
        db.add(super_admin)
        await db.commit()
        logger.info("Super admin created successfully")
    else:
        logger.info("Super admin already exists")