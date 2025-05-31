# app/modules/ioc_sources/schemas.py
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
import enum

class IoCSourceTypeEnum(str, enum.Enum):
    MISP = "misp"
    OPENCTI = "opencti"
    STIX_FEED = "stix_feed"
    CSV_URL = "csv_url"
    INTERNAL = "internal" # Для IoC, доданих вручну або з JSON файлу як у нас
    MOCK_APT_REPORT = "mock_apt_report" # Спеціальний тип для нашого JSON

class IoCSourceBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, description="Унікальна назва джерела IoC")
    type: IoCSourceTypeEnum = Field(..., description="Тип джерела IoC")
    url: Optional[HttpUrl] = Field(None, description="URL для доступу до джерела (API endpoint, feed URL)")
    description: Optional[str] = Field(None)
    is_enabled: bool = Field(default=True, description="Чи активне це джерело для отримання IoC")

class IoCSourceCreate(IoCSourceBase):
    pass

class IoCSourceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    type: Optional[IoCSourceTypeEnum] = None
    url: Optional[HttpUrl] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None

class IoCSourceResponse(IoCSourceBase):
    id: int
    last_fetched: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Pydantic V2
        use_enum_values = True