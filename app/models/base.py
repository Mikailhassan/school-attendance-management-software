from sqlalchemy.ext.declarative import declared_attr, declarative_base
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from flask import g

class TenantModel:
    @declared_attr
    def school_id(cls):
        return Column(Integer, ForeignKey("schools.id"), nullable=False)

    @declared_attr
    def school(cls):
        return relationship("School")

class BaseModel:
    id = Column(Integer, primary_key=True, index=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if hasattr(self, 'school_id') and not self.school_id and hasattr(g, 'current_user'):
            self.school_id = g.current_user.school_id

Base = declarative_base(cls=BaseModel)