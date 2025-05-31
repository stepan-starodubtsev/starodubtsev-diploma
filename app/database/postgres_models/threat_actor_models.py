# app/database/postgres_models/threat_actor_models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum as SAEnum, ARRAY
from sqlalchemy.sql import func
from datetime import datetime, timezone

from app.core.database import Base
# Імпортуємо Enum зі схем для використання в моделі БД
from app.modules.apt_groups.schemas import APTGroupMotivationsEnum, APTGroupSophisticationEnum


class APTGroup(Base):
    __tablename__ = "apt_groups"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True, nullable=False)

    # Для списків рядків використовуємо ARRAY(String) для PostgreSQL
    aliases = Column(ARRAY(String), nullable=True)
    description = Column(Text, nullable=True)  # Text для довших описів

    sophistication = Column(
        SAEnum(APTGroupSophisticationEnum, name="apt_sophistication_enum_db", native_enum=False),
        # native_enum=False для VARCHAR + CHECK
        default=APTGroupSophisticationEnum.UNKNOWN,
        nullable=True
    )
    primary_motivation = Column(
        SAEnum(APTGroupMotivationsEnum, name="apt_motivation_enum_db", native_enum=False),
        default=APTGroupMotivationsEnum.UNKNOWN,
        nullable=True
    )

    target_sectors = Column(ARRAY(String), nullable=True)
    country_of_origin = Column(String(100), nullable=True)

    first_observed = Column(DateTime(timezone=True), nullable=True)
    last_observed = Column(DateTime(timezone=True), nullable=True)

    references = Column(ARRAY(String), nullable=True)  # Зберігаємо HttpUrl як рядки

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<APTGroup(id={self.id}, name='{self.name}')>"

# Примітка: Зв'язок з IoC (many-to-many) буде реалізовано окремо,
# можливо, через асоціативну таблицю або додаванням посилання в IoC документ в Elasticsearch.
