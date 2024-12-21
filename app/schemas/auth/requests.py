from pydantic import BaseModel, EmailStr, validator
from typing import Optional
from app.schemas.user.role import UserRoleEnum  # Assuming the UserRoleEnum is defined in the 'role.py' file

# Register Request Model - For registering a new user (with optional role)
class RegisterRequest(BaseModel):
    email: EmailStr  # Email address
    password: str  # User's password
    full_name: str  # User's full name
    role: Optional[UserRoleEnum] = None  # Optional role (could be 'admin', 'teacher', 'student', etc.)

    class Config:
        from_attributes = True

# Login Request Model - For logging in a user
class LoginRequest(BaseModel):
    email: EmailStr  # Email address
    password: str  # User's password

    class Config:
        from_attributes = True

# Password Reset Request Model - For resetting a user's password
class PasswordResetRequest(BaseModel):
    email: EmailStr  # Email address
    new_password: str  # New password
    confirm_password: str  # Confirm new password

    class Config:
        from_attributes = True

# Password Change Model - For changing a user's password
class PasswordChange(BaseModel):
    current_password: str  # Current password
    new_password: str  # New password

    class Config:
        from_attributes = True

    # Validator to ensure new password and confirm password match
    @validator("confirm_password")
    def passwords_match(cls, confirm_password, values):
        if "new_password" in values and confirm_password != values["new_password"]:
            raise ValueError("Passwords do not match")
        return confirm_password

# User In Database Model - For returning user details from the database
class UserInDB(BaseModel):
    id: int  # User's unique ID
    email: EmailStr  # User's email address
    name: str  # User's full name
    role: UserRoleEnum  # User's role (using enum for defined roles)
    is_active: bool = True  # Whether the user is active or not
    school_id: Optional[int] = None  # School ID if the user is linked to a specific school
    hashed_password: str  # Hashed password (for secure password storage)

    class Config:
        from_attributes = True
