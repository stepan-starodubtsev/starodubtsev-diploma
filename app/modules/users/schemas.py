# app/modules/users/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from app.database.postgres_models.user_models import UserRoleEnum

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = Field(None, max_length=100)
    role: UserRoleEnum

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=6)
    role: Optional[UserRoleEnum] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True
        use_enum_values = True