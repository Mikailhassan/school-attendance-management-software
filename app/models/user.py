from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .base import TenantModel

class User(TenantModel):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=True)
    date_of_birth = Column(Date, nullable=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    school = relationship("School", back_populates="users")
    fingerprint = relationship("Fingerprint", back_populates="user", uselist=False)
    parent_profile = relationship("Parent", back_populates="user", uselist=False)
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)
    student_profile = relationship("Student", back_populates="user", uselist=False)
    attendances = relationship("Attendance", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, role={self.role})>"

class RevokedToken(TenantModel):
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String, unique=True, nullable=False)
    revoked_at = Column(DateTime(timezone=True), server_default=func.now())
    school_id = Column(Integer, ForeignKey('schools.id'), nullable=False)

    # Define the school relationship
    school = relationship("School", back_populates="revoked_tokens")

    def __repr__(self):
        return f"<RevokedToken(id={self.id}, jti={self.jti}, revoked_at={self.revoked_at})>"