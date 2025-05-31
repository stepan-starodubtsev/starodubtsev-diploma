# app/database/postgres_models/ioc_source_models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
from datetime import datetime, timezone  # Додано timezone

from app.core.database import Base  # Імпортуємо Base з нашого db_setup
from app.modules.ioc_sources.schemas import IoCSourceTypeEnum  # <--- НОВИЙ ПРАВИЛЬНИЙ ІМПОРТ


class IoCSource(Base):
    __tablename__ = "ioc_sources"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True, nullable=False)

    # Зберігаємо значення Enum як рядки
    type = Column(SAEnum(IoCSourceTypeEnum, name="ioc_source_type_enum_db", native_enum=False), nullable=False)

    url = Column(String(2048), nullable=True)  # HttpUrl може бути довгим
    description = Column(String, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)

    last_fetched = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # Для onupdate використовуємо default=func.now() та onupdate=func.now() для сумісності
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<IoCSource(id={self.id}, name='{self.name}', type='{self.type.value}')>"
