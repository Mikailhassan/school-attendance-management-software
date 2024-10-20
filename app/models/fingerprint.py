from sqlalchemy import Column, Integer, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from .base import TenantModel

class Fingerprint(TenantModel):
    __tablename__ = "fingerprints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)  # Add foreign key for School
    fingerprint_data = Column(LargeBinary, nullable=False)

    user = relationship("User", back_populates="fingerprint")
    school = relationship("School", back_populates="fingerprints")  # Add relationship with School

    def __repr__(self):
        return f"<Fingerprint(user_id={self.user_id}, school_id={self.school_id})>"
