# app/__init__.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import auth, admin, teacher, student, parent, attendance
from app.database import init_db, close_db
from app.config import settings
from app.core.security import get_password_hash
from app.models import User

def create_app():
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

    # routers
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    app.include_router(teacher.router, prefix="/api/v1/teachers", tags=["Teachers"])
    app.include_router(student.router, prefix="/api/v1/students", tags=["Students"])
    app.include_router(parent.router, prefix="/api/v1/parents", tags=["Parents"])
    app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["Attendance"])

    @app.on_event("startup")
    async def startup_event():
        await init_db()
        await create_super_admin()

    @app.on_event("shutdown")
    async def shutdown_event():
        await close_db()

    return app

async def create_super_admin():
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        super_admin = await session.query(User).filter(User.role == "super_admin").first()
        if not super_admin:
            super_admin = User(
                name="Super Admin",
                email=settings.SUPER_ADMIN_EMAIL,
                role="super_admin",
                password_hash=get_password_hash(settings.SUPER_ADMIN_PASSWORD)
            )
            session.add(super_admin)
            await session.commit()

# Ensure create_app is explicitly exported
__all__ = ['create_app']