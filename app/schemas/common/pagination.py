from pydantic import BaseModel
from typing import List, TypeVar, Generic

T = TypeVar('T')

class Page(Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int

    class Config:
        from_attributes = True
