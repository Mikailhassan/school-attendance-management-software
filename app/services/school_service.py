from datetime import datetime, timedelta
from fastapi import BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select, func, and_, or_, desc, update
from typing import List, Optional, Dict, Any
import re
import secrets
from pydantic import EmailStr

from app.core.security import generate_temporary_password, get_password_hash
from app.services.email_service import EmailService
from app.models import School, User, Class, Student
from app.schemas.school.requests import (
    SchoolCreateRequest,
    SchoolUpdateRequest,
    SchoolFilterParams
)
from app.schemas.enums import UserRole
from app.schemas.school.requests import SchoolStatus, SchoolType
from app.core.logging import logger
from app.core.exceptions import (
    SchoolNotFoundException,
    DuplicateSchoolException,
    InvalidOperationException
)

class SchoolService:
    def __init__(self, db: Session, email_service: EmailService):
        self.db = db
        self.email_service = email_service

    async def validate_school_data(self, school_data: SchoolCreateRequest) -> None:
        """
        Validate school data before creation
        
        Args:
            school_data (SchoolCreateRequest): The school data to validate
            
        Raises:
            DuplicateSchoolException: If a school with the same name, email, or phone already exists
        """
        # Check for duplicate name
        existing_name = await self.db.execute(
            select(School).where(School.name == school_data.name)
        )
        if existing_name.scalar_one_or_none():
            raise DuplicateSchoolException("School with this name already exists")

        # Check for duplicate email
        existing_email = await self.db.execute(
            select(School).where(School.email == school_data.email)
        )
        if existing_email.scalar_one_or_none():
            raise DuplicateSchoolException("School with this email already exists")

        # Check for duplicate phone if provided
        if school_data.phone:
            existing_phone = await self.db.execute(
                select(School).where(School.phone == school_data.phone)
            )
            if existing_phone.scalar_one_or_none():
                raise DuplicateSchoolException("School with this phone number already exists")

        # Validate class range if provided
        if school_data.class_range:
            lower_bound = school_data.class_range.get('lower_bound')
            upper_bound = school_data.class_range.get('upper_bound')
            
            if lower_bound is not None and upper_bound is not None:
                if lower_bound > upper_bound:
                    raise ValueError("Lower bound cannot be greater than upper bound in class range")
                if lower_bound < 1:
                    raise ValueError("Lower bound cannot be less than 1")

    async def generate_registration_number(self) -> str:
        """
        Generate a unique school registration number in format SCH-YYYY-XXX
        Uses a retry mechanism to handle concurrent insertions
        """
        current_year = datetime.utcnow().year
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Get the latest registration number for the current year
                query = select(School).where(
                    and_(
                        School.registration_number.like(f"SCH-{current_year}-%"),
                        School.registration_number.regexp_match(f"SCH-{current_year}-\\d{{3}}$")
                    )
                ).order_by(desc(School.registration_number)).limit(1)
                
                result = await self.db.execute(query)
                last_school = result.scalar_one_or_none()
                
                if last_school:
                    # Extract the sequence number and increment
                    match = re.search(r'SCH-\d{4}-(\d{3})', last_school.registration_number)
                    if match:
                        sequence = int(match.group(1)) + 1
                    else:
                        sequence = 1
                else:
                    sequence = 1
                
                new_reg_number = f"SCH-{current_year}-{sequence:03d}"
                
                # Verify the generated number doesn't exist (double-check)
                verify_query = select(School).where(
                    School.registration_number == new_reg_number
                )
                verify_result = await self.db.execute(verify_query)
                if verify_result.scalar_one_or_none() is None:
                    return new_reg_number
                
                # If we found a duplicate, increment and try again
                retry_count += 1
                
            except Exception as e:
                logger.error(f"Error generating registration number: {str(e)}")
                retry_count += 1
        
        # If we've exhausted our retries, generate a unique fallback
        timestamp = datetime.utcnow().strftime("%H%M%S")
        return f"SCH-{current_year}-{timestamp}"
    
    async def create_school(self, school_data: SchoolCreateRequest, background_tasks: BackgroundTasks) -> dict:
        """Create a new school with admin account"""
        await self.validate_school_data(school_data)
    
        registration_number = await self.generate_registration_number()
    
   
        # Generate admin temporary password
        temp_password = generate_temporary_password()
        
        website = str(school_data.website) if school_data.website else None

        # Create school instance
        new_school = School(
            registration_number=registration_number,
            name=school_data.name,
            email=school_data.email,
            phone=school_data.phone,
            address=school_data.address,
            website=website, 
            school_type=school_data.school_type,
            county=school_data.county,
            postal_code=school_data.postal_code,
            class_system=school_data.class_system,
            class_range=school_data.class_range,
            extra_info=school_data.extra_info,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        # Create admin instance
        school_admin = User(
            email=school_data.email,
            name=f"{school_data.name} Administrator",
            password_hash=get_password_hash(admin_password),
            role=UserRole.SCHOOL_ADMIN,
            is_active=True,
            phone=school_data.phone,
            created_at=datetime.utcnow()
        )

        try:
            # Add school and get its ID
            self.db.add(new_school)
            await self.db.flush()
            
            # Set school ID for admin and add admin
            school_admin.school_id = new_school.id
            self.db.add(school_admin)
            
            # Commit the transaction
            await self.db.commit()
            await self.db.refresh(new_school)
            
            # Send welcome email using EmailService
            email_sent = await self.email_service.send_school_admin_credentials(
                email=school_data.email,
                name=f"{school_data.name} Administrator",
                password=temp_password,
                school_name=school_data.name
            )

            if not email_sent:
                logger.warning(f"Failed to send welcome email to school: {school_data.name}")

            logger.info(f"Created new school: {school_data.name} with registration number: {registration_number}")
            
            return {
                "message": "School and admin account created successfully",
                "registration_number": registration_number,
                "school_id": new_school.id,
                "admin_email": school_data.email,
                "email_sent": email_sent
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create school: {str(e)}")
            raise

    async def get_school_by_registration(self, registration_number: str) -> School:
        """Get school by registration number"""
        query = select(School).where(School.registration_number == registration_number)
        result = await self.db.execute(query)
        school = result.scalar_one_or_none()
        
        if not school:
            raise SchoolNotFoundException(f"School with registration number {registration_number} not found")
        return school

    async def get_school(self, school_id: int) -> School:
        """Get school by ID"""
        query = select(School).where(School.id == school_id)
        result = await self.db.execute(query)
        school = result.scalar_one_or_none()
        
        if not school:
            raise SchoolNotFoundException(f"School with ID {school_id} not found")
        return school

    async def list_schools(
        self,
        filters: SchoolFilterParams,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[School], int]:
        """List schools with filtering and pagination"""
        query = select(School)
        
        if filters:
            conditions = []
            if filters.search:
                search_term = f"%{filters.search}%"
                conditions.append(
                    or_(
                        School.name.ilike(search_term),
                        School.registration_number.ilike(search_term),
                        School.email.ilike(search_term)
                    )
                )
            if filters.school_type:
                conditions.append(School.school_type == filters.school_type)
            if filters.county:
                conditions.append(School.county == filters.county)
            if filters.is_active is not None:
                conditions.append(School.is_active == filters.is_active)
            
            if conditions:
                query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(query)
        total = await self.db.execute(count_query)
        total_count = total.scalar()

        # Apply pagination
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        schools = result.scalars().all()
        
        return schools, total_count

    async def update_school(
        self,
        registration_number: str,
        update_data: SchoolUpdateRequest
    ) -> School:
        """Update school information"""
        school = await self.get_school_by_registration(registration_number)
        
        update_dict = update_data.dict(exclude_unset=True)
        
        # Check for duplicate email if email is being updated
        if 'email' in update_dict and update_dict['email'] != school.email:
            existing = await self.db.execute(
                select(School).where(School.email == update_dict['email'])
            )
            if existing.scalar_one_or_none():
                raise DuplicateSchoolException("School with this email already exists")
        
        for field, value in update_dict.items():
            setattr(school, field, value)
        
        school.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(school)
        
        logger.info(f"Updated school: {registration_number}")
        return school

    async def deactivate_school(self, registration_number: str) -> School:
        """Deactivate a school"""
        school = await self.get_school_by_registration(registration_number)
        
        if not school.is_active:
            raise InvalidOperationException("School is already inactive")
            
        school.is_active = False
        school.updated_at = datetime.utcnow()
        
        # Deactivate all users associated with the school
        await self.db.execute(
            update(User)
            .where(User.school_id == school.id)
            .values(is_active=False, updated_at=datetime.utcnow())
        )
        
        await self.db.commit()
        await self.db.refresh(school)
        
        logger.info(f"Deactivated school: {registration_number}")
        return school

    async def reactivate_school(self, registration_number: str) -> School:
        """Reactivate a school"""
        school = await self.get_school_by_registration(registration_number)
        
        if school.is_active:
            raise InvalidOperationException("School is already active")
            
        school.is_active = True
        school.updated_at = datetime.utcnow()
        
        # Reactivate only admin users
        await self.db.execute(
            update(User)
            .where(and_(
                User.school_id == school.id,
                User.role == UserRole.SCHOOL_ADMIN
            ))
            .values(is_active=True, updated_at=datetime.utcnow())
        )
        
        await self.db.commit()
        await self.db.refresh(school)
        
        logger.info(f"Reactivated school: {registration_number}")
        return school

    async def get_school_stats(self, school_id: int) -> Dict[str, Any]:
        """Get statistics for a school"""
        school = await self.get_school(school_id)
        
        # Get user counts by role
        students_query = select(func.count(User.id)).where(
            and_(
                User.school_id == school_id,
                User.role == UserRole.STUDENT,
                User.is_active == True
            )
        )
        teachers_query = select(func.count(User.id)).where(
            and_(
                User.school_id == school_id,
                User.role == UserRole.TEACHER,
                User.is_active == True
            )
        )
        parents_query = select(func.count(User.id)).where(
            and_(
                User.school_id == school_id,
                User.role == UserRole.PARENT,
                User.is_active == True
            )
        )
        classes_query = select(func.count(Class.id)).where(Class.school_id == school_id)
        
        students_count = await self.db.execute(students_query)
        teachers_count = await self.db.execute(teachers_query)
        parents_count = await self.db.execute(parents_query)
        classes_count = await self.db.execute(classes_query)
        
        return {
            "total_students": students_count.scalar(),
            "total_teachers": teachers_count.scalar(),
            "total_parents": parents_count.scalar(),
            "total_classes": classes_count.scalar(),
            "registration_date": school.created_at,
            "last_updated": school.updated_at,
            "is_active": school.is_active
        }

    async def get_school_users(
        self,
        school_id: int,
        role: Optional[UserRole] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[List[User], int]:
        """Get users for a school with optional filtering"""
        query = select(User).where(User.school_id == school_id)
        
        if role:
            query = query.where(User.role == role)
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        # Get total count
        count_query = select(func.count()).select_from(query)
        total = await self.db.execute(count_query)
        total_count = total.scalar()

        # Apply pagination
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        return users, total_count

    async def delete_school(self, registration_number: str) -> None:
        """
        Delete a school and all associated data.
        This is a dangerous operation and should be used with caution.
        """
        school = await self.get_school_by_registration(registration_number)
        
        try:
            # First deactivate the school to prevent any new operations
            await self.deactivate_school(registration_number)
            
            # Delete all associated users
            await self.db.execute(
                update(User)
                .where(User.school_id == school.id)
                .values(is_active=False, deleted_at=datetime.utcnow())
            )
            
            # Mark school as deleted
            school.is_active = False
            school.deleted_at = datetime.utcnow()
            
            await self.db.commit()
            
            logger.info(f"Deleted school: {registration_number}")
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete school {registration_number}: {str(e)}")
            raise

    async def validate_school_access(self, school_id: int, user_id: int) -> bool:
        """
        Validate if a user has access to a school
        """
        query = select(User).where(
            and_(
                User.id == user_id,
                User.school_id == school_id,
                User.is_active == True
            )
        )
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        return user is not None

    async def get_active_schools_count(self) -> int:
        """Get count of all active schools"""
        query = select(func.count(School.id)).where(School.is_active == True)
        result = await self.db.execute(query)
        return result.scalar()

    async def get_schools_by_type(self, school_type: SchoolType) -> List[School]:
        """Get all schools of a specific type"""
        query = select(School).where(
            and_(
                School.school_type == school_type,
                School.is_active == True
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_schools_in_county(self, county: str) -> List[School]:
        """Get all active schools in a specific county"""
        query = select(School).where(
            and_(
                School.county == county,
                School.is_active == True
            )
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_school_status(
        self,
        registration_number: str,
        status: SchoolStatus
    ) -> School:
        """Update school status"""
        school = await self.get_school_by_registration(registration_number)
        
        school.status = status
        school.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(school)
        
        logger.info(f"Updated status for school {registration_number} to {status}")
        return school

    async def get_school_registration_date(self, school_id: int) -> datetime:
        """Get the registration date of a school"""
        school = await self.get_school(school_id)
        return school.created_at

    async def verify_school_exists(self, registration_number: str) -> bool:
        """Verify if a school exists by registration number"""
        query = select(School).where(School.registration_number == registration_number)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None