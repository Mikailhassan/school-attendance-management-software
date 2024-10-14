from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Query
from app.config import settings
# from flask import g

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)

class SchoolTenantQuery(Query):
    def get(self, ident):
        # Always filter by the current user's school_id
        return super(SchoolTenantQuery, self).filter_by(school_id=g.current_user.school_id).get(ident)

    def __iter__(self):
        return super(SchoolTenantQuery, self).filter_by(school_id=g.current_user.school_id).__iter__()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, query_cls=SchoolTenantQuery)
db_session = scoped_session(SessionLocal)

Base = declarative_base()
Base.query = db_session.query_property()

def get_db():
    """Get a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize the database by creating all tables."""
    import app.models  # Import models to ensure they are registered
    Base.metadata.create_all(bind=engine)

# Function to drop the existing tables and create them anew
def reset_db():
    """Drop all tables and recreate them."""
    Base.metadata.drop_all(bind=engine)  # Drop all tables
    init_db()  # Recreate tables
