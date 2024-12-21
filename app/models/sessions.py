from sqlalchemy import Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship, declared_attr
from .base import Base

class Session(Base):
    __tablename__ = 'sessions'

    @declared_attr
    def id(cls):
        return Column(Integer, primary_key=True, index=True)

    @declared_attr
    def name(cls):
        return Column(String, index=True)

    @declared_attr
    def start_date(cls):
        return Column(Date)

    @declared_attr
    def end_date(cls):
        return Column(Date)

    @declared_attr
    def status(cls):
        return Column(String, default='Active')  # Example status: 'Active', 'Completed', 'Upcoming'

    @declared_attr
    def school_id(cls):
        return Column(Integer, ForeignKey('schools.id'))  # Each session belongs to a school

    @declared_attr
    def stream_id(cls):
        return Column(Integer, ForeignKey('streams.id'))  # Link to a stream (optional based on your needs)

    # Relationships
    @declared_attr
    def school(cls):
        return relationship("School", back_populates="sessions")

    @declared_attr
    def stream(cls):
        return relationship("Stream", back_populates="sessions")

    def __repr__(self):
        return f"<Session(name={self.name}, start_date={self.start_date}, end_date={self.end_date}, status={self.status})>"