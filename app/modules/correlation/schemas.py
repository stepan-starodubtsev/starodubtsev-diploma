# app/modules/correlation/schemas.py
from pydantic import BaseModel, Field, Json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone  # Переконайся, що datetime імпортовано
import enum

from app.modules.indicators.schemas import IoCResponse  # Для посилання на IoC


# from app.modules.apt_groups.schemas import APTGroupResponse # Якщо потрібно для OffenceResponse

# --- Новий Enum для серйозності офенса ---
class OffenceSeverityEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"  # Додамо ще один рівень для гнучкості


# --- Існуючі Enum (EventFieldToMatchTypeEnum, IoCTypeToMatchEnum) - без змін ---
class EventFieldToMatchTypeEnum(str, enum.Enum):
    SOURCE_IP = "source_ip"
    DESTINATION_IP = "destination_ip"


class IoCTypeToMatchEnum(str, enum.Enum):
    IPV4_ADDR = "ipv4-addr"
    IPV6_ADDR = "ipv6-addr"


class CorrelationRuleBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255, description="Назва правила кореляції")
    description: Optional[str] = Field(None, description="Детальний опис правила")
    is_enabled: bool = Field(default=True, description="Чи активне правило")

    event_source_type: Optional[List[str]] = Field(default_factory=list,
                                                   description="Типи подій для перевірки (напр., ['netflow', 'syslog_firewall'])")
    event_field_to_match: EventFieldToMatchTypeEnum = Field(...,
                                                            description="Поле в події, яке перевіряємо (напр., source_ip)")
    ioc_type_to_match: IoCTypeToMatchEnum = Field(..., description="Тип IoC, з яким зіставляємо (напр., ipv4-addr)")
    ioc_tags_match: Optional[List[str]] = Field(default_factory=list,
                                                description="Теги IoC, які мають бути присутні (AND логіка)")
    ioc_min_confidence: Optional[int] = Field(None, ge=0, le=100, description="Мінімальна впевненість IoC")

    generated_offence_title_template: str = Field(..., description="Шаблон для назви офенса")
    # --- ЗМІНА ТУТ ---
    generated_offence_severity: OffenceSeverityEnum = Field(default=OffenceSeverityEnum.MEDIUM,
                                                            description="Серйозність офенса, що генерується")


class CorrelationRuleCreate(CorrelationRuleBase):
    pass


class CorrelationRuleUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    event_source_type: Optional[List[str]] = None
    event_field_to_match: Optional[EventFieldToMatchTypeEnum] = None
    ioc_type_to_match: Optional[IoCTypeToMatchEnum] = None
    ioc_tags_match: Optional[List[str]] = None
    ioc_min_confidence: Optional[int] = Field(None, ge=0, le=100)
    generated_offence_title_template: Optional[str] = None
    # --- ЗМІНА ТУТ ---
    generated_offence_severity: Optional[OffenceSeverityEnum] = None


class CorrelationRuleResponse(CorrelationRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    # generated_offence_severity вже є в CorrelationRuleBase і буде типу OffenceSeverityEnum

    class Config:
        from_attributes = True  # Pydantic V2 (було orm_mode)
        use_enum_values = True  # Важливо для серіалізації Enum в їх значення (рядки)


# --- Схеми для Offence (змінюємо поле severity) ---
class OffenceStatusEnum(str, enum.Enum):
    NEW = "new";
    IN_PROGRESS = "in_progress";
    CLOSED_FALSE_POSITIVE = "closed_false_positive"
    CLOSED_TRUE_POSITIVE = "closed_true_positive";
    CLOSED_OTHER = "closed_other"


class OffenceBase(BaseModel):
    title: str = Field(..., description="Заголовок/назва офенса")
    description: Optional[str] = Field(None, description="Детальний опис офенса")
    # --- ЗМІНА ТУТ ---
    severity: OffenceSeverityEnum = Field(..., description="Серйозність офенса")
    status: OffenceStatusEnum = Field(default=OffenceStatusEnum.NEW, description="Статус офенса")

    correlation_rule_id: int = Field(..., description="ID правила кореляції, що спрацювало")
    triggering_event_summary: Optional[Dict[str, Any]] = Field(None,
                                                               description="Стислий виклад події, що спричинила офенс")  # JSONB у БД
    matched_ioc_details: Optional[Dict[str, Any]] = Field(None,
                                                          description="Деталі IoC, що спрацював (зберігатимемо як JSONB)")
    attributed_apt_group_ids: Optional[List[int]] = Field(default_factory=list,
                                                          description="ID пов'язаних APT-угруповань")
    notes: Optional[str] = Field(None, description="Нотатки аналітика")
    assigned_to_user_id: Optional[int] = Field(None, description="ID користувача, якому призначено офенс")


class OffenceCreate(OffenceBase):
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))  # Переконайся, що timezone імпортовано


class OffenceUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    # --- ЗМІНА ТУТ ---
    severity: Optional[OffenceSeverityEnum] = None
    status: Optional[OffenceStatusEnum] = None
    notes: Optional[str] = None
    assigned_to_user_id: Optional[int] = None


class OffenceResponse(OffenceBase):
    id: int
    detected_at: datetime
    created_at: datetime
    updated_at: datetime

    # severity вже є в OffenceBase і буде типу OffenceSeverityEnum

    class Config:
        from_attributes = True
        use_enum_values = True