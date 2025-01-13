# app/core/exceptions.py

class BaseAppException(Exception):
    """Base exception class for the application"""
    pass

class TeacherNotFoundException(BaseAppException):
    """Raised when a teacher is not found in the system"""
    def __init__(self, message="Teacher not found"):
        self.message = message
        super().__init__(self.message)

class SchoolNotFoundException(BaseAppException):
    """Raised when a school is not found in the system"""
    def __init__(self, message="School not found"):
        self.message = message
        super().__init__(self.message)

class UserNotFoundException(BaseAppException):
    """Raised when a user is not found in the system"""
    def __init__(self, message="User not found"):
        self.message = message
        super().__init__(self.message)

class DuplicateTSCNumberException(BaseAppException):
    """Raised when attempting to register a teacher with an existing TSC number"""
    def __init__(self, message="TSC number already registered"):
        self.message = message
        super().__init__(self.message)

class InvalidCredentialsException(BaseAppException):
    """Raised when invalid credentials are provided"""
    def __init__(self, message="Invalid credentials"):
        self.message = message
        super().__init__(self.message)

class UnauthorizedAccessException(BaseAppException):
    """Raised when a user attempts to access unauthorized resources"""
    def __init__(self, message="Unauthorized access"):
        self.message = message
        super().__init__(self.message)

class ValidationException(BaseAppException):
    """Raised when data validation fails"""
    def __init__(self, message="Validation error"):
        self.message = message
        super().__init__(self.message)

class DatabaseOperationException(BaseAppException):
    """Raised when a database operation fails"""
    def __init__(self, message="Database operation failed"):
        self.message = message
        super().__init__(self.message)

class DuplicateSchoolException(Exception):
    """
    Exception raised when attempting to create a school with duplicate unique fields
    or when updating a school's fields to values that would create a duplicate
    """
    def __init__(self, message: str = "A school with these details already exists"):
        self.message = message
        super().__init__(self.message)

class InvalidOperationException(Exception):
    """
    Exception raised when attempting an operation that is not valid
    given the current state of the school
    """
    def __init__(self, message: str = "This operation cannot be performed in the current state"):
        self.message = message
        super().__init__(self.message)

class InvalidStateException(Exception):
    """
    Exception raised when the application is in an invalid state
    """
    def __init__(self, message: str = "Invalid application state"):
        self.message = message
        super().__init__(self.message)
        
 
class ResourceNotFoundException(Exception):
    """Raised when a requested resource is not found"""
    pass

class DuplicateResourceException(Exception):
    """Raised when attempting to create a duplicate resource"""
    pass

class ValidationError(Exception):
    """Raised when validation fails"""
    pass

class BusinessLogicError(Exception):
    """Raised when a business rule is violated"""
    pass

class DatabaseOperationError(Exception):
    """Raised when a database operation fails"""
    pass        
