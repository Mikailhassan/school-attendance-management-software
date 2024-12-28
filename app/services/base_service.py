# app/services/base_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db

class BaseService:
    def __init__(self, db: AsyncSession):
        self.db = db