# app/modules/apt_groups/schemas.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
import enum

class APTGroupMotivationsEnum(str, enum.Enum):
    ESPIONAGE = "espionage"; FINANCIAL_GAIN = "financial_gain"; SABOTAGE = "sabotage"
    HACKTIVISM = "hacktivism"; UNKNOWN = "unknown"

class APTGroupSophisticationEnum(str, enum.Enum):
    HIGH = "high"; MEDIUM = "medium"; LOW = "low"; UNKNOWN = "unknown"

class APTGroupBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    aliases: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    sophistication: APTGroupSophisticationEnum = Field(default=APTGroupSophisticationEnum.UNKNOWN) # Змінено Optional на default
    primary_motivation: APTGroupMotivationsEnum = Field(default=APTGroupMotivationsEnum.UNKNOWN) # Змінено Optional на default
    target_sectors: List[str] = Field(default_factory=list)
    country_of_origin: Optional[str] = Field(None, max_length=100)
    first_observed: Optional[datetime] = None
    last_observed: Optional[datetime] = None
    references: List[HttpUrl] = Field(default_factory=list)

class APTGroupCreate(APTGroupBase): pass
class APTGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    aliases: Optional[List[str]] = None; description: Optional[str] = None
    sophistication: Optional[APTGroupSophisticationEnum] = None
    primary_motivation: Optional[APTGroupMotivationsEnum] = None
    target_sectors: Optional[List[str]] = None; country_of_origin: Optional[str] = None
    first_observed: Optional[datetime] = None; last_observed: Optional[datetime] = None
    references: Optional[List[HttpUrl]] = None

class APTGroupResponse(APTGroupBase):
    id: int
    created_at: datetime
    updated_at: datetime
    class Config: from_attributes = True; use_enum_values = True