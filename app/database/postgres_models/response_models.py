# app/database/postgres_models/response_models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SAEnum, ForeignKey, JSON
from sqlalchemy.sql import func

from app.core.database import Base
from app.modules.response.schemas import ResponseActionTypeEnum  # Імпортуємо Enum


class ResponseAction(Base):
    __tablename__ = "response_actions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    type = Column(SAEnum(ResponseActionTypeEnum, name="response_action_type_enum_db", native_enum=False),
                  nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    default_params = Column(JSON, nullable=True)  # Зберігаємо параметри як JSON

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

    # Зв'язок з PipelineActionLink (якщо потрібен для SQLAlchemy ORM)
    # pipeline_links = relationship("PipelineActionLink", back_populates="action")


class ResponsePipeline(Base):
    __tablename__ = "response_pipelines"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_enabled = Column(Boolean, default=True, nullable=False)

    trigger_correlation_rule_id = Column(Integer, ForeignKey("correlation_rules.id", ondelete="SET NULL"),
                                         nullable=True, index=True)
    # correlation_rule = relationship("CorrelationRule") # Якщо потрібен прямий зв'язок

    # actions_config буде зберігатися як JSONB, оскільки це список зі змінною структурою параметрів
    actions_config = Column(JSON, nullable=False, default=[])  # Список PipelineActionConfig

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now())

# Ми не будемо створювати окрему таблицю для PipelineActionConfig,
# а будемо зберігати список цих конфігурацій як JSONB у полі ResponsePipeline.actions_config.
# Це спрощує структуру для MVP. Якщо потрібні складніші зв'язки або запити по діях пайплайна,
# тоді можна було б створити асоціативну таблицю.