# base.py
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()

class TenantModel(Base):
    """
    A base mixin for multi-tenant architecture.
    This ensures models have a school_id foreign key.
    """
    __abstract__ = True

    # Simple foreign key to schools - relationships is defined in child classes
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)