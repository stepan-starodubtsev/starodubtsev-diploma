# app/database/postgres_models/correlation_models.py
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ARRAY, Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
# from datetime import datetime, timezone # Вже імпортовано вище, якщо є

from app.core.database import Base
from app.modules.correlation.schemas import (  # Імпортуємо всі потрібні Enum
    EventFieldToMatchTypeEnum,
    IoCTypeToMatchEnum,
    CorrelationRuleTypeEnum,  # <--- НОВИЙ
    OffenceStatusEnum,
    OffenceSeverityEnum
)


class CorrelationRule(Base):
    __tablename__ = "correlation_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)

    # --- НОВЕ ПОЛЕ ТИПУ ПРАВИЛА ---
    rule_type = Column(SAEnum(CorrelationRuleTypeEnum, name="correlation_rule_type_enum_db", native_enum=False),
                       nullable=False)

    # Поля для IoC-зіставлення (можуть бути NULL для інших типів правил)
    event_source_type = Column(ARRAY(String), nullable=True)
    event_field_to_match = Column(
        SAEnum(EventFieldToMatchTypeEnum, name="event_field_match_type_enum_db", native_enum=False), nullable=True)
    ioc_type_to_match = Column(SAEnum(IoCTypeToMatchEnum, name="ioc_type_match_enum_db", native_enum=False),
                               nullable=True)
    ioc_tags_match = Column(ARRAY(String), nullable=True)
    ioc_min_confidence = Column(Integer, nullable=True)

    # --- НОВІ ПОЛЯ для порогових правил (можуть бути NULL) ---
    threshold_count = Column(Integer, nullable=True)
    threshold_time_window_minutes = Column(Integer, nullable=True)
    aggregation_fields = Column(
        ARRAY(SAEnum(EventFieldToMatchTypeEnum, name="aggregation_event_field_enum_db", native_enum=False)),
        nullable=True)
    # Примітка: ARRAY(SAEnum(...)) може потребувати створення типу Enum окремо або іншого підходу,
    # залежно від діалекту БД та SQLAlchemy. Для PostgreSQL це має працювати.
    # `name` для Enum в ARRAY має бути унікальним, якщо він створює тип в БД.
    # Якщо `native_enum=False`, то це буде `ARRAY(VARCHAR)`.

    generated_offence_title_template = Column(String, nullable=False)
    generated_offence_severity = Column(
        SAEnum(OffenceSeverityEnum, name="offence_severity_enum_db", native_enum=False),
        default=OffenceSeverityEnum.MEDIUM,
        nullable=False
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CorrelationRule(id={self.id}, name='{self.name}', type='{self.rule_type.value}')>"


# --- Модель Offence (без змін у структурі, але переконайся, що імпорти Enum коректні) ---
class Offence(Base):
    # ... (код моделі Offence залишається таким же, як у попередній відповіді)
    __tablename__ = "offences";
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False);
    description = Column(Text, nullable=True)
    severity = Column(SAEnum(OffenceSeverityEnum, name="offence_severity_enum_db", native_enum=False), nullable=False)
    status = Column(SAEnum(OffenceStatusEnum, name="offence_status_enum_db", native_enum=False),
                    default=OffenceStatusEnum.NEW, nullable=False)
    correlation_rule_id = Column(Integer, nullable=False)
    triggering_event_summary = Column(JSONB, nullable=True);
    matched_ioc_details = Column(JSONB, nullable=True)
    attributed_apt_group_ids = Column(ARRAY(Integer), nullable=True)
    detected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    notes = Column(Text, nullable=True);
    assigned_to_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(
            self): return f"<Offence(id={self.id}, title='{self.title}', status='{self.status.value if self.status else None}')>"
