from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import joinedload
from typing import List, Optional, Tuple, Dict,Union,Any
from fastapi import HTTPException, status
from contextlib import asynccontextmanager
from datetime import datetime

from app.models import Class, School, Stream, Session
from app.schemas.school.requests import (
    ClassCreateRequest, 
    StreamCreateRequest,
    ClassUpdateRequest,
    StreamUpdateRequest
)
from app.schemas.school.responses import ClassResponse, StreamResponse, ClassDetailsResponse
from app.core.logging import logger
from app.core.exceptions import (
    ResourceNotFoundException,
    DuplicateResourceException,
    ValidationError
)

class ClassService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @asynccontextmanager
    async def transaction(self):
        """Context manager for transaction handling"""
        try:
            yield
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            raise e

    async def get_school_by_registration(self, registration_number: str) -> Optional[School]:
        """Get school by registration number with error handling"""
        try:
            result = await self.db.execute(
                select(School)
                .where(School.registration_number == registration_number.strip('{}'))
            )
            school = result.scalar_one_or_none()
            if not school:
                raise ResourceNotFoundException(f"School with registration number {registration_number} not found")
            return school
        except ResourceNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error fetching school: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while fetching school"
            )

    async def validate_class_name(self, school_id: int, name: str, exclude_id: Optional[int] = None) -> None:
        """Validate class name uniqueness within a school"""
        query = select(Class).where(
            and_(
                Class.school_id == school_id,
                Class.name == name
            )
        )
        if exclude_id:
            query = query.where(Class.id != exclude_id)
            
        existing = await self.db.execute(query)
        if existing.scalar_one_or_none():
            raise DuplicateResourceException(f"Class '{name}' already exists in this school")

    async def validate_stream_name(
        self, 
        school_id: int, 
        class_id: int, 
        name: str, 
        exclude_id: Optional[int] = None
    ) -> None:
        """Validate stream name uniqueness within a class"""
        query = select(Stream).where(
            and_(
                Stream.school_id == school_id,
                Stream.class_id == class_id,
                Stream.name == name
            )
        )
        if exclude_id:
            query = query.where(Stream.id != exclude_id)
            
        existing = await self.db.execute(query)
        if existing.scalar_one_or_none():
            raise DuplicateResourceException(f"Stream '{name}' already exists in this class")

    async def create_class(self, registration_number: str, class_data: ClassCreateRequest) -> Class:
        """Create a single class for a school with proper validation and error handling"""
        try:
            school = await self.get_school_by_registration(registration_number)
            await self.validate_class_name(school.id, class_data.name)
            
            new_class = Class(
                name=class_data.name,
                school_id=school.id,
            )
            self.db.add(new_class)
            await self.db.flush()
            await self.db.commit()  
            await self.db.refresh(new_class)  
            
            return new_class
                
        except ResourceNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"School with registration number {registration_number} not found"
            )
        except DuplicateResourceException as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Class with name {class_data.name} already exists in this school"
            )
        except Exception as e:
            logger.error(f"Error creating class: {type(e).__name__}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while creating class"
            )

    async def create_multiple_classes(
        self, 
        registration_number: str, 
        class_data: List[ClassCreateRequest]
    ) -> List[Class]:
        """Create multiple classes for a school with proper validation and error handling"""
        try:
            school = await self.get_school_by_registration(registration_number)
            
            # Validate all class names first
            for class_item in class_data:
                await self.validate_class_name(school.id, class_item.name)

            new_classes = []
            for class_item in class_data:
                new_class = Class(
                    name=class_item.name,
                    school_id=school.id
                )
                self.db.add(new_class)
                new_classes.append(new_class)

            await self.db.flush()
            
            # Refresh all new classes
            for new_class in new_classes:
                await self.db.refresh(new_class)
            
            return new_classes

        except (ResourceNotFoundException, DuplicateResourceException) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error creating multiple classes: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while creating classes"
            )
    async def get_class(self, class_id: int, school_id: int) -> Dict[str, Any]:
        query = (
            select(Class)
            .options(joinedload(Class.streams))
            .where(
                and_(
                    Class.id == class_id,
                    Class.school_id == school_id
                )
            )
        )
        
        result = await self.db.execute(query)
        class_obj = result.unique().scalar_one_or_none()
        
        if not class_obj:
            raise ResourceNotFoundException(f"Class with ID {class_id} not found")
            
        # Convert SQLAlchemy model to dict
        return {
            "id": class_obj.id,
            "name": class_obj.name,
            "streams": [
                {
                    "id": stream.id,
                    "name": stream.name,
                    "class_id": stream.class_id,
                    "school_id": stream.school_id
                }
                for stream in class_obj.streams
            ]
        }

    async def list_classes(
        self,
        registration_number: str,
        include_streams: bool = False
    ) -> List[Dict[str, Any]]:
        school = await self.get_school_by_registration(registration_number)
        
        query = select(Class).where(Class.school_id == school.id)
        if include_streams:
            query = query.options(joinedload(Class.streams))
            
        result = await self.db.execute(query)
        classes = result.scalars().all()
        
        return [
            {
                "id": class_.id,
                "name": class_.name,
                "school_id": class_.school_id,
                "streams": [
                    {
                        "id": stream.id,
                        "name": stream.name,
                        "class_id": stream.class_id,
                        "school_id": stream.school_id
                    }
                    for stream in class_.streams
                ] if include_streams else []
            }
            for class_ in classes
        ]
    async def update_class(
        self, 
        registration_number: str, 
        class_id: int, 
        update_data: ClassUpdateRequest
    ) -> Class:
        """Update a class with proper validation and error handling"""
        try:
            school = await self.get_school_by_registration(registration_number)
            class_obj = await self.get_class(class_id, school.id)
            
            if update_data.name and update_data.name != class_obj.name:
                await self.validate_class_name(school.id, update_data.name, class_id)

            async with self.transaction():
                update_dict = update_data.model_dump(exclude_unset=True)
                for field, value in update_dict.items():
                    setattr(class_obj, field, value)
                
                class_obj.updated_at = datetime.utcnow()
                await self.db.flush()
                await self.db.refresh(class_obj)
                
                return class_obj

        except (ResourceNotFoundException, DuplicateResourceException) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error updating class: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while updating class"
            )

    async def create_stream(
        self,
        registration_number: str,
        class_name: str,
        stream_data: StreamCreateRequest
    ) -> Stream:
        """Create a new stream within a class using class name instead of ID"""
        # Start a regular transaction instead of a nested one
        async with self.db.begin() as transaction:
            try:
                # Get school first
                school = await self.get_school_by_registration(registration_number)
                
                # Validate class name format
                if not class_name or not class_name.strip():
                    raise ValidationError("Class name cannot be empty")
                
                # Get class by name
                class_result = await self.db.execute(
                    select(Class).where(
                        Class.school_id == school.id,
                        Class.name == class_name
                    )
                )
                class_obj = class_result.scalar_one_or_none()
                if not class_obj:
                    raise ResourceNotFoundException(f"Class '{class_name}' not found")

                # Validate stream name
                if not stream_data.name or not stream_data.name.strip():
                    raise ValidationError("Stream name cannot be empty")

                # Format the stream name by combining class name and stream identifier
                stream_identifier = stream_data.name.strip()
                if stream_identifier.lower().startswith(class_name.lower()):
                    stream_identifier = stream_identifier[len(class_name):].strip()
                
                stream_identifier = stream_identifier.lstrip(' -_')
                formatted_stream_name = f"{class_name} {stream_identifier}"

                # Validate stream name uniqueness in this class (case insensitive)
                existing_stream = await self.db.execute(
                    select(Stream).where(
                        Stream.class_id == class_obj.id,
                        func.lower(Stream.name) == func.lower(formatted_stream_name)
                    )
                )
                if existing_stream.scalar_one_or_none():
                    raise DuplicateResourceException(
                        f"Stream '{formatted_stream_name}' already exists in class '{class_name}'"
                    )

                # Create the new stream with formatted name
                new_stream = Stream(
                    name=formatted_stream_name,
                    class_id=class_obj.id,
                    school_id=school.id
                )
                self.db.add(new_stream)
                await self.db.flush()
                await self.db.refresh(new_stream)
                
                # The transaction will be automatically committed if no exceptions occur
                return new_stream

            except (ValidationError, ResourceNotFoundException, DuplicateResourceException) as e:
                # No need to explicitly rollback - the context manager will handle it
                if isinstance(e, ValidationError):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=str(e)
                    )
                elif isinstance(e, ResourceNotFoundException):
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=str(e)
                    )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=str(e)
                    )
            except Exception as e:
                logger.error(f"Error creating stream: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Internal server error while creating stream"
                )
    async def get_stream(
        self, 
        stream_id: int, 
        class_id: int, 
        school_id: int
    ) -> Stream:
        """Get a stream by ID with relationships loaded"""
        try:
            result = await self.db.execute(
                select(Stream)
                .options(
                    joinedload(Stream.class_),
                    joinedload(Stream.students)
                )
                .where(
                    and_(
                        Stream.id == stream_id,
                        Stream.class_id == class_id,
                        Stream.school_id == school_id
                    )
                )
            )
            stream = result.unique().scalar_one_or_none()
            if not stream:
                raise ResourceNotFoundException(f"Stream with ID {stream_id} not found")
            return stream
        except ResourceNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error fetching stream: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while fetching stream"
            )
            
    async def list_streams(
        self,
        registration_number: str,
        class_id: int
    ) -> List[Stream]:
        """Get all streams for a specific class"""
        try:
            # First verify the school exists
            school = await self.get_school_by_registration(registration_number)
            
            # Then get all streams for the class
            result = await self.db.execute(
                select(Stream)
                .options(
                    joinedload(Stream.class_),
                    joinedload(Stream.students)
                )
                .where(
                    and_(
                        Stream.class_id == class_id,
                        Stream.school_id == school.id
                    )
                )
            )
            
            streams = result.unique().scalars().all()
            return streams
            
        except ResourceNotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error fetching streams for class {class_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while fetching streams"
            )
                
    async def get_class_with_streams(
        self,
        registration_number: str,
        class_id: int = None
    ) -> Union[Class, List[Class]]:
        """
        Fetch a single class or all classes with their associated streams.
        If class_id is provided, returns a single class, otherwise returns all classes.
        Includes proper error handling.
        """
        try:
            school = await self.get_school_by_registration(registration_number)
            
            # Build base query with stream relationships
            query = select(Class).options(
                joinedload(Class.streams),
                joinedload(Class.streams).joinedload(Stream.students)
            ).where(Class.school_id == school.id)
            
            # Add class_id filter if provided
            if class_id is not None:
                query = query.where(Class.id == class_id)
                
            result = await self.db.execute(query)
            
            if class_id is not None:
                # Return single class
                class_obj = result.unique().scalar_one_or_none()
                if not class_obj:
                    raise ResourceNotFoundException(f"Class with id {class_id} not found")
                return class_obj
            else:
                # Return all classes
                return result.unique().scalars().all()
                
        except ResourceNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error fetching class with streams: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while fetching class data"
            )

    async def update_stream(
        self, 
        registration_number: str, 
        class_id: int, 
        stream_id: int, 
        update_data: StreamUpdateRequest
    ) -> Stream:
        """Update a stream with proper validation and error handling"""
        try:
            school = await self.get_school_by_registration(registration_number)
            stream = await self.get_stream(stream_id, class_id, school.id)
            
            if update_data.name and update_data.name != stream.name:
                await self.validate_stream_name(school.id, class_id, update_data.name, stream_id)

            async with self.transaction():
                update_dict = update_data.model_dump(exclude_unset=True)
                for field, value in update_dict.items():
                    setattr(stream, field, value)
                
                stream.updated_at = datetime.utcnow()
                await self.db.flush()
                await self.db.refresh(stream)
                
                return stream

        except (ResourceNotFoundException, DuplicateResourceException) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error updating stream: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while updating stream"
            )

    async def get_class_statistics(
        self, 
        registration_number: str, 
        class_id: int
    ) -> Dict:
        """Get statistics for a specific class"""
        try:
            school = await self.get_school_by_registration(registration_number)
            class_obj = await self.get_class(class_id, school.id)

            # Get stream counts
            stream_count = await self.db.scalar(
                select(func.count(Stream.id))
                .where(
                    and_(
                        Stream.class_id == class_id,
                        Stream.school_id == school.id
                    )
                )
            )

            # Get student counts
            student_count = await self.db.scalar(
                select(func.count(Student.id))
                .join(Stream)
                .where(
                    and_(
                        Stream.class_id == class_id,
                        Stream.school_id == school.id
                    )
                )
            )

            return {
                "class_name": class_obj.name,
                "total_streams": stream_count,
                "total_students": student_count,
                "class_id": class_id,
                "school_id": school.id
            }

        except ResourceNotFoundException as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"Error getting class statistics: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error while getting class statistics"
            )