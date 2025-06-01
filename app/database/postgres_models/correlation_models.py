# app/database/postgres_models/correlation_models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ARRAY, Enum as SAEnum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB  # Залишаємо для JSONB полів
from datetime import datetime, timezone  # Переконайся, що timezone імпортовано

from app.core.database import Base
# Імпортуємо Enum зі схем для використання в моделі БД
from app.modules.correlation.schemas import EventFieldToMatchTypeEnum, IoCTypeToMatchEnum, OffenceStatusEnum, \
    OffenceSeverityEnum  # <--- ДОДАНО OffenceSeverityEnum


class CorrelationRule(Base):
    __tablename__ = "correlation_rules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)

    event_source_type = Column(ARRAY(String), nullable=True)
    event_field_to_match = Column(
        SAEnum(EventFieldToMatchTypeEnum, name="event_field_match_type_enum_db", native_enum=False), nullable=False)
    ioc_type_to_match = Column(SAEnum(IoCTypeToMatchEnum, name="ioc_type_match_enum_db", native_enum=False),
                               nullable=False)
    ioc_tags_match = Column(ARRAY(String), nullable=True)
    ioc_min_confidence = Column(Integer, nullable=True)

    generated_offence_title_template = Column(String, nullable=False)
    # --- ЗМІНА ТУТ ---
    generated_offence_severity = Column(
        SAEnum(OffenceSeverityEnum, name="offence_severity_enum_db", native_enum=False),  # Використовуємо новий Enum
        default=OffenceSeverityEnum.MEDIUM,
        nullable=False
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<CorrelationRule(id={self.id}, name='{self.name}')>"


class Offence(Base):
    __tablename__ = "offences"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    # --- ЗМІНА ТУТ ---
    severity = Column(
        SAEnum(OffenceSeverityEnum, name="offence_severity_enum_db", native_enum=False),
        # Використовуємо той самий Enum та ім'я типу в БД
        nullable=False
    )
    status = Column(
        SAEnum(OffenceStatusEnum, name="offence_status_enum_db", native_enum=False),
        default=OffenceStatusEnum.NEW,
        nullable=False
    )

    correlation_rule_id = Column(Integer, nullable=False)
    triggering_event_summary = Column(JSONB, nullable=True)
    matched_ioc_details = Column(JSONB, nullable=True)
    attributed_apt_group_ids = Column(ARRAY(Integer), nullable=True)
    detected_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                         nullable=False)  # Використовуємо timezone.utc
    notes = Column(Text, nullable=True)
    assigned_to_user_id = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Offence(id={self.id}, title='{self.title}', status='{self.status.value if self.status else None}')>"