# app/modules/indicators/schemas.py
from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional, List, Dict, Any # Додано Dict, Any для можливого використання
from datetime import datetime
import enum

class IoCTypeEnum(str, enum.Enum):
    IPV4_ADDR = "ipv4-addr"
    IPV6_ADDR = "ipv6-addr"
    DOMAIN_NAME = "domain-name"
    URL = "url"
    MD5_HASH = "file-hash-md5"
    SHA1_HASH = "file-hash-sha1"
    SHA256_HASH = "file-hash-sha256"
    EMAIL_ADDR = "email-addr"
    # Додай інші типи за потреби

class IoCBase(BaseModel):
    value: str = Field(..., description="Значення індикатора (IP, домен, хеш тощо)")
    type: IoCTypeEnum = Field(..., description="Тип індикатора")
    description: Optional[str] = Field(None, description="Опис індикатора")
    source_name: Optional[str] = Field(None, description="Назва джерела, з якого отримано IoC")
    is_active: bool = Field(default=True, description="Чи активний індикатор для перевірок")
    confidence: Optional[int] = Field(None, ge=0, le=100, description="Рівень впевненості (0-100)")
    tags: List[str] = Field(default_factory=list, description="Теги для класифікації або фільтрації")
    first_seen: Optional[datetime] = Field(None, description="Час першого виявлення індикатора")
    last_seen: Optional[datetime] = Field(None, description="Час останнього виявлення індикатора")
    attributed_apt_group_ids: List[int] = Field(default_factory=list, description="Список ID APT-угруповань, з якими пов'язаний IoC")

class IoCCreate(IoCBase):
    # Можна додати поля, специфічні тільки для створення, якщо потрібно
    pass

class IoCUpdate(BaseModel): # Окремо для оновлення, щоб не всі поля були обов'язковими
    value: Optional[str] = None
    type: Optional[IoCTypeEnum] = None
    description: Optional[str] = None
    source_name: Optional[str] = None
    is_active: Optional[bool] = None
    confidence: Optional[int] = Field(None, ge=0, le=100)
    tags: Optional[List[str]] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    attributed_apt_group_ids: Optional[List[int]] = None # Дозволяє оновити весь список

class IoCResponse(IoCBase):
    ioc_id: str = Field(..., description="Унікальний ID індикатора з Elasticsearch")
    created_at: datetime # Час додавання в нашу SIEM систему
    updated_at: datetime # Час останнього оновлення в нашій SIEM системі
    # attributed_apt_group_ids вже є в IoCBase

    class Config:
        from_attributes = True # Pydantic V2 (було orm_mode)
        use_enum_values = True # Для коректної серіалізації Enum в їх значення (рядки)

# Схема для відповіді з деталями APT, якщо потрібно буде відображати в IoC деталях
class APTGroupBasicInfo(BaseModel):
    id: int
    name: str
    class Config:
        from_attributes = True

# Розширена схема відповіді IoC, що може включати деталі APT (якщо знадобиться)
class AttributedIoCResponse(IoCResponse):
    attributed_apts: List[APTGroupBasicInfo] = Field(default_factory=list)

# Схема для тіла запиту при зв'язуванні IoC з APT (якщо потрібен окремий ендпоінт)
# Наразі не використовується, оскільки зв'язування відбувається через attributed_apt_group_ids в IoCCreate/IoCUpdate
# class LinkIoCToAPTRequest(BaseModel):
#     apt_group_id: int