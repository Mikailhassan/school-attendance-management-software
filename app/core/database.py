from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship, declared_attr
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=True)

AsyncSessionLocal = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

class Base:
    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    id = Column(Integer, primary_key=True, index=True)
    
    @declared_attr
    def school_id(cls):
        return Column(Integer, ForeignKey("school.id"), nullable=False)

    @declared_attr
    def school(cls):
        return relationship("School")

Base = declarative_base(cls=Base)

# Import models
import app.models.attendance
import app.models.fingerprint
import app.models.parent
import app.models.school
import app.models.stream
import app.models.student
import app.models.teacher
import app.models.user

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def reset_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await init_db()

async def close_db():
    await engine.dispose()