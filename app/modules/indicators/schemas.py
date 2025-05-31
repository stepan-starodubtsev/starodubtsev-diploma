# app/modules/indicators/schemas.py
from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional, List
from datetime import datetime
import enum

class IoCTypeEnum(str, enum.Enum):
    IPV4_ADDR = "ipv4-addr"; IPV6_ADDR = "ipv6-addr"; DOMAIN_NAME = "domain-name"
    URL = "url"; MD5_HASH = "file-hash-md5"; SHA1_HASH = "file-hash-sha1"
    SHA256_HASH = "file-hash-sha256"; EMAIL_ADDR = "email-addr"

class IoCBase(BaseModel):
    value: str = Field(...)
    type: IoCTypeEnum
    description: Optional[str] = None
    source_name: Optional[str] = None
    is_active: bool = Field(default=True)
    confidence: Optional[int] = Field(None, ge=0, le=100)
    tags: List[str] = Field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    attributed_apt_group_ids: List[int] = Field(default_factory=list)

class IoCCreate(IoCBase): pass
class IoCUpdate(BaseModel):
    value: Optional[str] = None; type: Optional[IoCTypeEnum] = None
    description: Optional[str] = None; source_name: Optional[str] = None
    is_active: Optional[bool] = None; confidence: Optional[int] = Field(None, ge=0, le=100)
    tags: Optional[List[str]] = None; first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None; attributed_apt_group_ids: Optional[List[int]] = None

class IoCResponse(IoCBase):
    ioc_id: str # ES ID
    created_at: datetime # У нашій системі (ES)
    updated_at: datetime # У нашій системі (ES)
    class Config: from_attributes = True; use_enum_values = True

# Схема для відповіді з деталями APT, якщо потрібно
class APTGroupBasicInfo(BaseModel): # Проста схема для відображення в IoC деталях
    id: int
    name: str
    class Config: from_attributes = True

class AttributedIoCResponse(IoCResponse):
    attributed_apts: List[APTGroupBasicInfo] = Field(default_factory=list)