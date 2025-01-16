# teacher_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy import and_
from app.models.teacher import Teacher
from app.models import School, User, AttendanceBase
from app.core.security import generate_temporary_password, get_password_hash
from app.core.logging import logging
from app.utils.email_utils import send_email
from app.schemas.enums import UserRole
from app.schemas.teacher import TeacherRegistrationRequest


logger = logging.getLogger(__name__)

class TeacherService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_school(self, registration_number: str) -> School:
        stmt = select(School).where(School.registration_number == registration_number)
        result = await self.db.execute(stmt)
        school = result.scalar_one_or_none()
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
        return school

    async def _validate_unique_tsc(self, tsc_number: str, exclude_teacher_id: Optional[int] = None) -> None:
        stmt = select(Teacher).where(Teacher.tsc_number == tsc_number)
        if exclude_teacher_id:
            stmt = stmt.where(Teacher.id != exclude_teacher_id)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="TSC number already registered")

    async def _validate_unique_email(self, email: str, exclude_user_id: Optional[int] = None) -> None:
        stmt = select(User).where(User.email == email)
        if exclude_user_id:
            stmt = stmt.where(User.id != exclude_user_id)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Email already registered")

    async def register_teacher(
            self,
            registration_number: str,
            teacher_data: TeacherRegistrationRequest,  
            background_tasks: BackgroundTasks
        ) -> Dict[str, Any]:
            school = await self._get_school(registration_number)
            await self._validate_unique_tsc(teacher_data.tsc_number)
            await self._validate_unique_email(teacher_data.email)

            temp_password = generate_temporary_password()
            
            try:
                # Create user
                teacher_user = User(
                    name=teacher_data.name,
                    email=teacher_data.email,
                    phone=teacher_data.phone,
                    date_of_birth=teacher_data.date_of_birth,
                    password_hash=get_password_hash(temp_password),
                    role=UserRole.TEACHER,
                    school_id=school.id,
                    is_active=True
                )
                self.db.add(teacher_user)
                await self.db.flush()

                # Create teacher profile
                new_teacher = Teacher(
                    name=teacher_data.name,
                    gender=teacher_data.gender,
                    email=teacher_data.email,
                    phone=teacher_data.phone,
                    date_of_joining=teacher_data.date_of_joining,
                    date_of_birth=teacher_data.date_of_birth,
                    tsc_number=teacher_data.tsc_number,
                    address=teacher_data.address,
                    user_id=teacher_user.id,
                    school_id=school.id
                )
                self.db.add(new_teacher)
                await self.db.flush()
                await self.db.refresh(new_teacher)

                # Schedule welcome email
                # background_tasks.add_task(
                #     send_email,
                #     recipient_email=new_teacher.email,
                #     subject="Welcome to School Management System - Teacher Account Created",
                #     body=self._generate_welcome_email(
                #         name=new_teacher.name,
                #         email=teacher_data.email,
                #         password=temp_password
                #     )
                # )

                # Convert to dict to avoid async issues
                return {
                    "id": new_teacher.id,
                    "name": new_teacher.name,
                    "gender": new_teacher.gender,
                    "email": new_teacher.email,
                    "phone": new_teacher.phone,
                    "date_of_joining": new_teacher.date_of_joining,
                    "date_of_birth": new_teacher.date_of_birth,
                    "tsc_number": new_teacher.tsc_number,
                    "address": new_teacher.address,
                    "created_at": new_teacher.created_at,
                    "updated_at": new_teacher.updated_at
                }

            except IntegrityError as e:
                logger.error(f"Database Integrity Error: {e}")
                raise HTTPException(
                    status_code=400,
                    detail="Database integrity error, please check the input data."
                )
            except Exception as e:
                logger.error(f"Error creating teacher: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail="An unexpected error occurred while creating the teacher."
                )

    async def list_teachers(self, registration_number: str) -> List[Teacher]:
        school = await self._get_school(registration_number)
        stmt = (
            select(Teacher)
            .where(Teacher.school_id == school.id)
            .order_by(Teacher.name)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_teacher_details(self, registration_number: str, teacher_id: int) -> Optional[Teacher]:
        school = await self._get_school(registration_number)
        stmt = (
            select(Teacher)
            .options(joinedload(Teacher.attendances))
            .where(
                and_(
                    Teacher.school_id == school.id,
                    Teacher.id == teacher_id
                )
            )
        )
        result = await self.db.execute(stmt)
        teacher = result.unique().scalar_one_or_none()

        if teacher:
            teacher.attendance_summary = await self._calculate_attendance_summary(teacher.attendances)

        return teacher

    async def update_teacher(self, registration_number: str, teacher_id: int, teacher_data: dict) -> Teacher:
        """
        Update teacher information.

        Args:
            registration_number: School registration number
            teacher_id: Teacher ID
            teacher_data: Dictionary containing teacher update data
        """
        school = await self._get_school(registration_number)

        # Get teacher with user data
        stmt = (
            select(Teacher)
            .options(joinedload(Teacher.user))
            .where(
                and_(
                    Teacher.school_id == school.id,
                    Teacher.id == teacher_id
                )
            )
        )
        result = await self.db.execute(stmt)
        teacher = result.unique().scalar_one_or_none()

        if not teacher:
            raise HTTPException(status_code=404, detail="Teacher not found")

        try:
            # Update user and teacher information
            if "name" in teacher_data:
                teacher.user.name = teacher_data["name"]
                teacher.name = teacher_data["name"]

            if "gender" in teacher_data:
                teacher.gender = teacher_data["gender"]

            if "phone" in teacher_data:
                teacher.phone = teacher_data["phone"]
                teacher.user.phone = teacher_data["phone"]

            if "address" in teacher_data:
                teacher.address = teacher_data["address"]

            await self.db.flush()
            return teacher

        except IntegrityError as e:
            logger.error(f"Database Integrity Error: {e}")
            raise HTTPException(
                status_code=400,
                detail="Database integrity error, please check the input data."
            )
        except Exception as e:
            logger.error(f"Error updating teacher: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while updating the teacher."
            )

    async def get_teacher_by_tsc(self, registration_number: str, tsc_number: str) -> Optional[Teacher]:
        school = await self._get_school(registration_number)
        stmt = (
            select(Teacher)
            .where(
                and_(
                    Teacher.school_id == school.id,
                    Teacher.tsc_number == tsc_number.upper()
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _calculate_attendance_summary(self, attendances: List[AttendanceBase]) -> dict:
        if not attendances:
            return {
                "total_sessions": 0,
                "attended_sessions": 0,
                "absent_sessions": 0,
                "attendance_percentage": 0.0,
            }

        total_sessions = len(attendances)
        attended_sessions = sum(1 for attendance in attendances if attendance.is_present)
        absent_sessions = total_sessions - attended_sessions
        attendance_percentage = (attended_sessions / total_sessions) * 100 if total_sessions else 0.0

        return {
            "total_sessions": total_sessions,
            "attended_sessions": attended_sessions,
            "absent_sessions": absent_sessions,
            "attendance_percentage": round(attendance_percentage, 2),
        }
