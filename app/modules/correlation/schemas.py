# app/modules/correlation/schemas.py
from pydantic import BaseModel, Field, Json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone  # Переконайся, що datetime імпортовано
import enum

from app.modules.indicators.schemas import IoCResponse  # Для посилання на IoC


# --- Існуючі Enum (EventFieldToMatchTypeEnum, IoCTypeToMatchEnum, OffenceSeverityEnum, OffenceStatusEnum) ---
class EventFieldToMatchTypeEnum(str, enum.Enum):
    SOURCE_IP = "source_ip";
    DESTINATION_IP = "destination_ip"
    # Додамо поля, які можуть знадобитися для порогових правил
    USERNAME = "username"  # Для логінів
    HOSTNAME = "hostname"  # Для логінів/системних подій
    EVENT_MESSAGE = "message"  # Для пошуку ключових слів у повідомленні
    NETWORK_BYTES_TOTAL = "network_bytes_total"  # Для NetFlow


class IoCTypeToMatchEnum(str, enum.Enum):  # Залишається для IoC-правил
    IPV4_ADDR = "ipv4-addr";
    IPV6_ADDR = "ipv6-addr"


class OffenceSeverityEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class OffenceStatusEnum(str, enum.Enum):  # ... (без змін)
    NEW = "new"
    IN_PROGRESS = "in_progress"
    CLOSED_FALSE_POSITIVE = "closed_false_positive"
    CLOSED_TRUE_POSITIVE = "closed_true_positive"
    CLOSED_OTHER = "closed_other"


# --- НОВИЙ Enum для типів правил кореляції ---
class CorrelationRuleTypeEnum(str, enum.Enum):
    IOC_MATCH_IP = "ioc_match_ip"  # Зіставлення IP з IoC (поточний функціонал)
    # IOC_MATCH_DOMAIN = "ioc_match_domain" # Майбутні типи IoC-правил
    # IOC_MATCH_URL = "ioc_match_url"
    # IOC_MATCH_HASH = "ioc_match_hash"
    THRESHOLD_LOGIN_FAILURES = "threshold_login_failures"  # Порогове для невдалих логінів
    THRESHOLD_DATA_EXFILTRATION = "threshold_data_exfiltration"  # Порогове для ексфільтрації даних
    # SEQUENCE_OF_EVENTS = "sequence_of_events" # Для майбутніх послідовностей


class CorrelationRuleBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255, description="Назва правила кореляції")
    description: Optional[str] = Field(None, description="Детальний опис правила")
    is_enabled: bool = Field(default=True, description="Чи активне правило")
    rule_type: CorrelationRuleTypeEnum = Field(..., description="Тип правила кореляції")  # <--- НОВЕ ПОЛЕ

    # Поля для IoC-орієнтованих правил (стають опціональними)
    event_source_type: Optional[List[str]] = Field(default_factory=list,
                                                   description="Типи подій для перевірки (напр., ['netflow', 'syslog_firewall'])")
    event_field_to_match: Optional[EventFieldToMatchTypeEnum] = Field(None,
                                                                      description="Поле в події, яке перевіряємо (для IoC_MATCH_IP)")
    ioc_type_to_match: Optional[IoCTypeToMatchEnum] = Field(None,
                                                            description="Тип IoC, з яким зіставляємо (для IoC_MATCH_IP)")
    ioc_tags_match: Optional[List[str]] = Field(default_factory=list)
    ioc_min_confidence: Optional[int] = Field(None, ge=0, le=100)

    # ---- НОВІ ПОЛЯ для порогових правил (Threshold-based) ----
    # Загальні для порогових:
    threshold_count: Optional[int] = Field(None, gt=0, description="Порогове значення (N)")
    threshold_time_window_minutes: Optional[int] = Field(None, gt=0, description="Часове вікно в хвилинах (X)")

    # Поля для агрегації (які поля групувати для підрахунку)
    # Наприклад, для невдалих логінів це можуть бути ['username', 'destination_ip']
    # Для ексфільтрації: ['source_ip', 'destination_ip']
    aggregation_fields: Optional[List[EventFieldToMatchTypeEnum]] = Field(default_factory=list,
                                                                          description="Поля для групування перед підрахунком/сумуванням")

    # Специфічні для THRESHOLD_LOGIN_FAILURES:
    # event_type_for_login_failure: Optional[str] = Field(None, description="Значення event_type або ключове слово в message, що вказує на невдалий логін")
    # Поки що будемо покладатися на event_source_type (наприклад, "syslog_auth_failure")

    # Специфічні для THRESHOLD_DATA_EXFILTRATION:
    # threshold_bytes_sum: Optional[int] = Field(None, gt=0, description="Порогова сума байт (Y)") # Замість threshold_count
    # data_direction: Optional[str] = Field(None, enum=["outbound", "inbound"], description="Напрямок трафіку для ексфільтрації")
    # Поки що будемо використовувати threshold_count для суми байт, а напрямок визначатимемо логікою

    # -----------------------------------------------------------

    generated_offence_title_template: str = Field(..., description="Шаблон для назви офенса")
    generated_offence_severity: OffenceSeverityEnum = Field(default=OffenceSeverityEnum.MEDIUM,
                                                            description="Серйозність офенса, що генерується")


class CorrelationRuleCreate(CorrelationRuleBase):
    # Перевірка, що для певних типів правил вказані потрібні поля
    # Це можна реалізувати через @model_validator в Pydantic V2
    pass


class CorrelationRuleUpdate(BaseModel):  # Для часткового оновлення
    name: Optional[str] = None;
    description: Optional[str] = None
    is_enabled: Optional[bool] = None;
    rule_type: Optional[CorrelationRuleTypeEnum] = None
    event_source_type: Optional[List[str]] = None
    event_field_to_match: Optional[EventFieldToMatchTypeEnum] = None
    ioc_type_to_match: Optional[IoCTypeToMatchEnum] = None
    ioc_tags_match: Optional[List[str]] = None
    ioc_min_confidence: Optional[int] = Field(None, ge=0, le=100)
    threshold_count: Optional[int] = Field(None, gt=0)
    threshold_time_window_minutes: Optional[int] = Field(None, gt=0)
    aggregation_fields: Optional[List[EventFieldToMatchTypeEnum]] = None
    generated_offence_title_template: Optional[str] = None
    generated_offence_severity: Optional[OffenceSeverityEnum] = None


class CorrelationRuleResponse(CorrelationRuleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config: from_attributes = True; use_enum_values = True


# --- Схеми для Offence (OffenceStatusEnum, OffenceBase, OffenceCreate, OffenceUpdate, OffenceResponse - без змін) ---
# ... (код для схем Offence залишається таким же, як у попередній відповіді)


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
