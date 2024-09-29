# models/attendance.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
from datetime import datetime

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    check_in_time = Column(DateTime, default=datetime.utcnow)
    check_out_time = Column(DateTime, nullable=True)
    is_present = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="attendances")

    def __repr__(self):
        return f"<Attendance(user_id={self.user_id}, present={self.is_present})>"
