from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.orm import relationship as orm_relationship
from sqlalchemy.sql import func
from .base import Base, TenantModel

class User(Base, TenantModel):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    school = orm_relationship("School", back_populates="users")
    fingerprint = orm_relationship("Fingerprint", back_populates="user", uselist=False)
    parent_profile = orm_relationship("Parent", back_populates="user", uselist=False)
    teacher_profile = orm_relationship("Teacher", back_populates="user", uselist=False)
    student_profile = orm_relationship("Student", back_populates="user", uselist=False)
    attendances = orm_relationship("Attendance", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, role={self.role}, school_id={self.school_id})>"

class RevokedToken(Base):
    __tablename__ = "revoked_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, unique=True, nullable=False)
    revoked_at = Column(DateTime, default=func.now())
    
    def __repr__(self):
        return f"<RevokedToken(id={self.id}, jti={self.jti}, revoked_at={self.revoked_at})>"