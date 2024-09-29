# services/registration_service.py
from app.models import User, Fingerprint, Attendance
from app.database import SessionLocal
from app.utils.fingerprint import capture_fingerprint
from fastapi import HTTPException
from datetime import datetime
from app.services.auth_service import hash_password

async def register_user(request):
    db = SessionLocal()
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Step 1: Create a new user
    user = User(
        name=request.name,
        role=request.role,
        email=request.email,
        phone=request.phone,
        password_hash=hash_password(request.password),  # Use the hash_password function from auth_service.py
    )

    # Step 2: Capture fingerprint data
    fingerprint_template, _ = await capture_fingerprint()  # Capture the fingerprint template

    # Step 3: Create Fingerprint entry
    fingerprint = Fingerprint(
        user=user,
        fingerprint_template=fingerprint_template,  # Store the fingerprint template
    )

    # Step 4: Store in the database
    db.add(user)
    db.add(fingerprint)
    db.commit()
    db.refresh(user)
    db.refresh(fingerprint)

    return user

async def register_teacher(request):
    db = SessionLocal()
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Step 1: Create a new teacher user
    user = User(
        name=request.name,
        role="teacher",  # Set the role as teacher
        email=request.email,
        phone=request.phone,
        password_hash=hash_password(request.password),
        tsc_number=request.tsc_number,  # Specific field for teachers
    )

    # Step 2: Capture fingerprint data
    fingerprint_template, _ = await capture_fingerprint()  # Capture the fingerprint template

    # Step 3: Create Fingerprint entry
    fingerprint = Fingerprint(
        user=user,
        fingerprint_template=fingerprint_template,
    )

    # Step 4: Store in the database
    db.add(user)
    db.add(fingerprint)
    db.commit()
    db.refresh(user)
    db.refresh(fingerprint)

    return user

async def register_student(request):
    db = SessionLocal()
    
    # Check if admission number already exists
    existing_student = db.query(User).filter(User.admission_number == request.admission_number).first()
    if existing_student:
        raise HTTPException(status_code=400, detail="Admission number already registered")

    # Step 1: Create a new student user
    user = User(
        name=request.name,
        role="student",  # Set the role as student
        admission_number=request.admission_number,
        date_of_birth=request.date_of_birth,
        password_hash=hash_password(request.password),  # Hash the student's password
    )

    # Step 2: Capture fingerprint data
    fingerprint_template, _ = await capture_fingerprint()  # Capture the fingerprint template

    # Step 3: Create Fingerprint entry
    fingerprint = Fingerprint(
        user=user,
        fingerprint_template=fingerprint_template,
    )

    # Step 4: Store in the database
    db.add(user)
    db.add(fingerprint)
    db.commit()
    db.refresh(user)
    db.refresh(fingerprint)

    return user

async def register_parent(request):
    db = SessionLocal()
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Step 1: Create a new parent user
    user = User(
        name=request.name,
        role="parent",  # Set the role as parent
        email=request.email,
        phone=request.phone,
        password_hash=hash_password(request.password),  # Hash the parent's password
    )

    # Step 2: Capture fingerprint data (optional, if required for parents)
    fingerprint_template, _ = await capture_fingerprint()  # Capture the fingerprint template

    # Step 3: Create Fingerprint entry
    fingerprint = Fingerprint(
        user=user,
        fingerprint_template=fingerprint_template,
    )

    # Step 4: Store in the database
    db.add(user)
    db.add(fingerprint)
    db.commit()
    db.refresh(user)
    db.refresh(fingerprint)

    return user
