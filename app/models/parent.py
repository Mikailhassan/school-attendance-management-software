from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship as orm_relationship
from app.database import Base
from .base import TenantModel

class Parent(Base, TenantModel):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    school_id = Column(Integer, ForeignKey('schools.id'), nullable=False)  # Add school_id foreign key
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    relationship_type = Column(String, nullable=False)

    # Relationships
    user = orm_relationship("User", back_populates="parent_profile")
    students = orm_relationship("Student", back_populates="parent")
    school = orm_relationship("School", back_populates="parents")  # Add relationship to School

    def __repr__(self):
        return f"<Parent(id={self.id}, name={self.name}, email={self.email})>"
