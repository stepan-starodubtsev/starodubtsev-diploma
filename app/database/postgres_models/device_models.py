# app/database/postgres_models/device_models.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.sql import func
import enum

from app.core.database import Base  # <--- ОСЬ ЦЯ ЗМІНА: імпортуємо Base з нового файлу


# Enum класи залишаються тут або можуть бути винесені в schemas, якщо використовуються там теж
class DeviceStatusEnum(enum.Enum):
    REACHABLE = "reachable"
    UNREACHABLE = "unreachable"
    ERROR = "error"
    CONFIGURING = "configuring"
    UNKNOWN = "unknown"


class DeviceTypeEnum(enum.Enum):
    MIKROTIK_ROUTEROS = "mikrotik_routeros"


class Device(Base):  # Тепер успадковується від імпортованого Base
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # ... решта полів моделі залишаються без змін ...
    name = Column(String, index=True, nullable=False)
    host = Column(String, nullable=False, unique=True)
    port = Column(Integer, default=8728, nullable=False)
    username = Column(String, nullable=False)
    encrypted_password = Column(String, nullable=False)
    device_type = Column(SAEnum(DeviceTypeEnum, name="device_type_enum_db", native_enum=True), nullable=False,
                         default=DeviceTypeEnum.MIKROTIK_ROUTEROS)
    status = Column(SAEnum(DeviceStatusEnum, name="device_status_enum_db", native_enum=True),
                    default=DeviceStatusEnum.UNKNOWN, nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)
    os_version = Column(String, nullable=True)
    last_successful_connection = Column(DateTime(timezone=True), nullable=True)
    last_status_update = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    syslog_configured_by_siem = Column(Boolean, default=False, nullable=False)
    netflow_configured_by_siem = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    def __repr__(self):
        return f"<Device(id={self.id}, name='{self.name}', host='{self.host}')>"