from pydantic import BaseModel

class ErrorResponse(BaseModel):
    detail: str

    class Config:
        from_attributes = True