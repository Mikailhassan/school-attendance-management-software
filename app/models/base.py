from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship

Base = declarative_base()

class TenantModel(Base):
    """Base model for all tenant-specific models in the system."""
    
    __abstract__ = True

    @declared_attr
    def school_id(cls):
        """Every tenant model must belong to a school"""
        return Column(Integer, ForeignKey('schools.id'), nullable=False)

   
   