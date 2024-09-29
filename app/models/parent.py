# models/parent.py
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class Parent(Base):
    __tablename__ = "parents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Parent is also a user

    # Relationships
    user = relationship("User", foreign_keys=[user_id])  # Parent's user record
    children = relationship("Student", back_populates="parent")  # Parent has multiple children (students)

    def __repr__(self):
        return f"<Parent(user_id={self.user_id})>"
