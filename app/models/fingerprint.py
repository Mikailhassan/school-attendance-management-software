# models/fingerprint.py
from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base

class Fingerprint(Base):
    __tablename__ = "fingerprints"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Link to the user
    fingerprint_template = Column(String, nullable=False)  # Store fingerprint data securely (e.g., hash or template)

    # Relationships
    user = relationship("User", back_populates="fingerprint")

    def __repr__(self):
        return f"<Fingerprint(user_id={self.user_id})>"
