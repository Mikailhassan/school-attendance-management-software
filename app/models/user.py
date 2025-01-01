from sqlalchemy import Column, Integer, String, Boolean, Date, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, declared_attr
from .base import TenantModel
from app.schemas.enums import UserRole


class User(TenantModel):
    __tablename__ = "users"

    @declared_attr
    def id(cls):
        return Column(Integer, primary_key=True, index=True)

    @declared_attr
    def name(cls):
        return Column(String, nullable=False)

    @declared_attr
    def role(cls):
        return Column(Enum(UserRole), nullable=False)

    @declared_attr
    def password_hash(cls):
        return Column(String, nullable=False)

    @declared_attr
    def is_active(cls):
        return Column(Boolean, default=True)

    @declared_attr
    def email(cls):
        return Column(String, unique=True, nullable=False)

    @declared_attr
    def phone(cls):
        return Column(String, nullable=True)

    @declared_attr
    def date_of_birth(cls):
        return Column(Date, nullable=True)

    @declared_attr
    def school_id(cls):
        return Column(Integer, ForeignKey("schools.id"), nullable=True)

    @declared_attr
    def created_at(cls):
        return Column(DateTime(timezone=True), server_default=func.now())

    @declared_attr
    def updated_at(cls):
        return Column(DateTime(timezone=True), onupdate=func.now())

    # School relationship
    @declared_attr
    def school(cls):
        return relationship("School", back_populates="users")

    # Fingerprint relationship
    @declared_attr
    def fingerprint(cls):
        return relationship("Fingerprint", back_populates="user", uselist=False)

    # Profile relationships
    @declared_attr
    def parent_profile(cls):
        return relationship("Parent", back_populates="user", uselist=False)

    @declared_attr
    def teacher_profile(cls):
        return relationship("Teacher", back_populates="user", uselist=False)

    @declared_attr
    def student_profile(cls):
        return relationship("Student", back_populates="user", uselist=False)

    # Attendance relationships - split into student and teacher attendance
    @declared_attr
    def student_attendances(cls):
        return relationship("StudentAttendance", back_populates="user")

    @declared_attr
    def teacher_attendances(cls):
        return relationship("TeacherAttendance", back_populates="user")

    # Failed login attempts relationship
    @declared_attr
    def failed_login_attempts(cls):
        return relationship("FailedLoginAttempt", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, role={self.role})>"


class RevokedToken(TenantModel):
    __tablename__ = "revoked_tokens"

    @declared_attr
    def id(cls):
        return Column(Integer, primary_key=True, index=True)

    @declared_attr
    def jti(cls):
        return Column(String, unique=True, nullable=False)

    @declared_attr
    def revoked_at(cls):
        return Column(DateTime(timezone=True), server_default=func.now())

    @declared_attr
    def school_id(cls):
        return Column(Integer, ForeignKey('schools.id'), nullable=False)

    @declared_attr
    def school(cls):
        return relationship("School", back_populates="revoked_tokens")

    def __repr__(self):
        return f"<RevokedToken(id={self.id}, jti={self.jti}, revoked_at={self.revoked_at})>"


class FailedLoginAttempt(TenantModel):
    __tablename__ = "failed_login_attempts"

    @declared_attr
    def id(cls):
        return Column(Integer, primary_key=True, index=True)

    @declared_attr
    def email(cls):
        return Column(String, nullable=False, index=True)

    @declared_attr
    def timestamp(cls):
        return Column(DateTime(timezone=True), server_default=func.now())

    @declared_attr
    def ip_address(cls):
        return Column(String, nullable=True)

    # Add user_id foreign key
    @declared_attr
    def user_id(cls):
        return Column(Integer, ForeignKey("users.id"), nullable=True)

    # Add user relationship
    @declared_attr
    def user(cls):
        return relationship("User", back_populates="failed_login_attempts")

    def __repr__(self):
        return f"<FailedLoginAttempt(id={self.id}, email={self.email}, timestamp={self.timestamp})>"