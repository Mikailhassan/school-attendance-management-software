from sqlalchemy import Column, Integer, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from .base import Base

class Fingerprint(Base):
    __tablename__ = "fingerprints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    fingerprint_data = Column(LargeBinary, nullable=False)

    user = relationship("User", back_populates="fingerprint")

    def __repr__(self):
        return f"<Fingerprint(user_id={self.user_id})>"
