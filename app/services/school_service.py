from datetime import datetime
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Optional
import re

from app.core.security import generate_temporary_password, get_password_hash
from app.utils.email_utils import send_email
from app.models import School, User
from app.schemas.school.requests import SchoolCreateRequest
from app.core.logging import logger

class SchoolService:
    def __init__(self, db: Session):
        self.db = db

    async def generate_registration_number(self) -> str:
        """Generate a unique school registration number in format SCH-YYYY-XXX"""
        current_year = datetime.utcnow().year
        
        # Get the last registration number for current year
        query = select(School).where(
            School.registration_number.like(f"SCH-{current_year}-%")
        ).order_by(School.registration_number.desc())
        result = await self.db.execute(query)
        last_school = result.scalar_one_or_none()
        
        if last_school:
            # Extract and increment sequence number
            match = re.search(r'SCH-\d{4}-(\d{3})', last_school.registration_number)
            if match:
                sequence = int(match.group(1)) + 1
            else:
                sequence = 1
        else:
            sequence = 1
            
        registration_number = f"SCH-{current_year}-{sequence:03d}"
        logger.info(f"Generated new school registration number: {registration_number}")
        return registration_number

    async def create_school(self, school_data: SchoolCreateRequest, background_tasks: BackgroundTasks) -> dict:
        """Create a new school with auto-generated registration number"""
        # Check for existing school
        existing_school = await self.db.execute(
            select(School).where(School.email == school_data.email)
        )
        if existing_school.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="School with this email already exists")

        # Generate unique registration number
        registration_number = await self.generate_registration_number()
        
        # Create school with generated registration number
        new_school = School(
            registration_number=registration_number,
            name=school_data.name,
            email=school_data.email,
            phone=school_data.phone,
            address=school_data.address,
            website=school_data.website,
            created_at=datetime.utcnow()
        )
        self.db.add(new_school)
        await self.db.commit()
        await self.db.refresh(new_school)

        # Generate secure temporary password for school admin
        temp_password = generate_temporary_password()
        
        # Create school admin account
        school_admin = User(
            email=school_data.email,
            password_hash=get_password_hash(temp_password),
            role='school_admin',
            school_id=new_school.id,
            is_active=True,
            must_change_password=True,
            first_name=school_data.name.split()[0],
            last_name="Admin"
        )
        
        self.db.add(school_admin)
        await self.db.commit()

        # Send credentials via email
        background_tasks.add_task(
            send_email,
            to_email=school_data.email,
            subject="School Registration Confirmation",
            body=self._get_welcome_email_template(
                school_data.name,
                registration_number,
                school_data.email,
                temp_password,
                school_data.website
            )
        )

        logger.info(f"Created new school: {school_data.name} with registration number: {registration_number}")
        return {
            "message": "School created successfully",
            "registration_number": registration_number,
            "school_id": new_school.id,
            "admin_email": school_data.email
        }

    async def get_school_by_registration(self, registration_number: str) -> School:
        """Get school by registration number"""
        query = select(School).where(School.registration_number == registration_number)
        result = await self.db.execute(query)
        school = result.scalar_one_or_none()
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
        return school

    async def get_school(self, school_id: int) -> School:
        """Get school by ID"""
        query = select(School).where(School.id == school_id)
        result = await self.db.execute(query)
        school = result.scalar_one_or_none()
        
        if not school:
            raise HTTPException(status_code=404, detail="School not found")
        return school

    async def list_schools(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        search: Optional[str] = None
    ) -> List[School]:
        """List schools with optional search and pagination"""
        query = select(School)
        
        if search:
            query = query.where(
                (School.name.ilike(f"%{search}%")) |
                (School.registration_number.ilike(f"%{search}%")) |
                (School.email.ilike(f"%{search}%"))
            )
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def update_school(
        self, 
        registration_number: str, 
        update_data: dict
    ) -> School:
        """Update school information"""
        school = await self.get_school_by_registration(registration_number)
        
        for field, value in update_data.items():
            if hasattr(school, field):
                setattr(school, field, value)
        
        await self.db.commit()
        await self.db.refresh(school)
        
        logger.info(f"Updated school: {registration_number}")
        return school

    def _get_welcome_email_template(
        self, 
        school_name: str, 
        registration_number: str,
        email: str, 
        password: str, 
        website: str
    ) -> str:
        return f"""
        Your school has been successfully registered in Yoventa.
        
        School Details:
        --------------
        Name: {school_name}
        Registration Number: {registration_number}
        Admin Email: {email}
        Temporary Password: {password}
        
        Please log in at {website or '[School Portal URL]'} using these credentials.
        
        Important Notes:
        - Keep your registration number safe as it will be required for various administrative tasks
        - For security reasons, you will be required to change your password upon first login
        - Please complete your school profile after logging in
        
        If you have any questions or need assistance, please contact our support team.
        """