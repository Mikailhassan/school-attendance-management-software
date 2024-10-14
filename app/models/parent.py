from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship as orm_relationship
from app.database import Base
from .base import TenantModel

class Parent(Base, TenantModel):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    relationship_type = Column(String, nullable=False)

    user = orm_relationship("User", back_populates="parent_profile")
    students = orm_relationship("Student", back_populates="parent")

    def __repr__(self):
        return f"<Parent(id={self.id}, name={self.name}, email={self.email})>"