from typing import Generic, TypeVar, Optional
from pydantic.generics import GenericModel

T = TypeVar("T")

class ResponseModel(GenericModel, Generic[T]):
    statusCode: int = 200
    status: bool = True
    message: str = ""
    data: Optional[T] = None

    class Config:
        orm_mode = True