# app/modules/ioc_management/schemas.py
from pydantic import BaseModel, Field, HttpUrl, IPvAnyAddress
from typing import Optional, List, Dict, Any
from datetime import datetime
import enum


# --- Типи IoC (IoCTypeEnum - без змін) ---
class IoCTypeEnum(str, enum.Enum):
    IPV4_ADDR = "ipv4-addr"
    IPV6_ADDR = "ipv6-addr"
    DOMAIN_NAME = "domain-name"
    URL = "url"
    MD5_HASH = "file-hash-md5"
    SHA1_HASH = "file-hash-sha1"
    SHA256_HASH = "file-hash-sha256"
    EMAIL_ADDR = "email-addr"


class IoCBase(BaseModel):
    value: str = Field(..., description="Значення індикатора")
    type: IoCTypeEnum = Field(..., description="Тип індикатора")
    description: Optional[str] = Field(None, description="Опис індикатора")
    source_name: Optional[str] = Field(None, description="Назва джерела IoC")
    is_active: bool = Field(default=True, description="Чи активний індикатор")
    confidence: Optional[int] = Field(None, ge=0, le=100, description="Рівень впевненості (0-100)")
    tags: List[str] = Field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    # --- НОВЕ ПОЛЕ для зв'язку з APT ---
    attributed_apt_group_ids: List[int] = Field(default_factory=list,
                                                description="Список ID APT-угруповань, з якими пов'язаний IoC")


class IoCCreate(IoCBase):
    pass  # attributed_apt_group_ids успадковується і може бути переданий при створенні


class IoCUpdate(BaseModel):
    value: Optional[str] = None
    type: Optional[IoCTypeEnum] = None
    description: Optional[str] = None
    source_name: Optional[str] = None
    is_active: Optional[bool] = None
    confidence: Optional[int] = Field(None, ge=0, le=100)
    tags: Optional[List[str]] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    # --- НОВЕ ПОЛЕ для оновлення зв'язку з APT ---
    attributed_apt_group_ids: Optional[List[int]] = None  # Дозволяє оновити весь список


class IoCResponse(IoCBase):
    ioc_id: str = Field(..., description="Унікальний ID індикатора з Elasticsearch")
    created_at: datetime
    updated_at: datetime

    # attributed_apt_group_ids вже є в IoCBase

    class Config: from_attributes = True use_enum_values = True


# --- Схеми для Джерел IoC (IoCSource... - без змін) ---
class IoCSourceTypeEnum(str, enum.Enum):  # ...
    MISP = "misp"
    OPENCTI = "opencti"
    STIX_FEED = "stix_feed"
    CSV_URL = "csv_url"
    INTERNAL = "internal"


class IoCSourceBase(BaseModel):  # ...
    name: str = Field(..., min_length=3, max_length=100)
    type: IoCSourceTypeEnum
    url: Optional[HttpUrl] = None
    description: Optional[str] = None
    is_enabled: bool = True


class IoCSourceCreate(IoCSourceBase): pass


class IoCSourceUpdate(BaseModel):  # ...
    name: Optional[str] = None
    type: Optional[IoCSourceTypeEnum] = None
    url: Optional[HttpUrl] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None


class IoCSourceResponse(IoCSourceBase):  # ...
    id: int
    last_fetched: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config: from_attributes = True use_enum_values = True


# --- Схеми для APT-угруповань (APTGroup... - без змін) ---
class APTGroupMotivationsEnum(str, enum.Enum):  # ...
    ESPIONAGE = "espionage"
    FINANCIAL_GAIN = "financial_gain"
    SABOTAGE = "sabotage"
    HACKTIVISM = "hacktivism"
    UNKNOWN = "unknown"


class APTGroupSophisticationEnum(str, enum.Enum):  # ...
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNKNOWN = "unknown"


class APTGroupBase(BaseModel):  # ...
    name: str = Field(..., min_length=2, max_length=100)
    aliases: List[str] = Field(default_factory=list)  # Змінено Optional[...] на List[...]
    description: Optional[str] = None
    sophistication: Optional[APTGroupSophisticationEnum] = APTGroupSophisticationEnum.UNKNOWN
    primary_motivation: Optional[APTGroupMotivationsEnum] = APTGroupMotivationsEnum.UNKNOWN
    target_sectors: List[str] = Field(default_factory=list)  # Змінено Optional[...] на List[...]
    country_of_origin: Optional[str] = Field(None, max_length=100)
    first_observed: Optional[datetime] = None
    last_observed: Optional[datetime] = None
    references: List[HttpUrl] = Field(default_factory=list)  # Змінено Optional[...] на List[...]


class APTGroupCreate(APTGroupBase): pass


class APTGroupUpdate(BaseModel):  # ...
    name: Optional[str] = None
    aliases: Optional[List[str]] = None
    description: Optional[str] = None
    sophistication: Optional[APTGroupSophisticationEnum] = None
    primary_motivation: Optional[APTGroupMotivationsEnum] = None
    target_sectors: Optional[List[str]] = None
    country_of_origin: Optional[str] = None
    first_observed: Optional[datetime] = None
    last_observed: Optional[datetime] = None
    references: Optional[List[HttpUrl]] = None


class APTGroupResponse(APTGroupBase):  # ...
    id: int
    created_at: datetime
    updated_at: datetime

    class Config: from_attributes = True use_enum_values = True


# --- Схеми для операцій зв'язування ---
class LinkIoCToAPTRequest(BaseModel):
    # Ми будемо оновлювати IoC, додаючи до нього ID APT-угруповання.
    # Тому ця схема може бути не потрібна, якщо ми оновлюємо поле attributed_apt_group_ids через IoCUpdate.
    # Або, якщо ми хочемо окремий ендпоінт:
    apt_group_id: int


class BulkLinkIoCsToAPTRequest(BaseModel):
    ioc_elasticsearch_ids: List[str]
    apt_group_id: int


class AttributedIoCResponse(IoCResponse):  # Може бути корисною для відображення IoC з деталями APT
    attributed_apts: Optional[List[APTGroupResponse]] = Field(default_factory=list)
