from datetime import datetime

from pydantic import BaseModel, Field, IPvAnyAddress # IPvAnyAddress тепер з pydantic
from typing import Optional, List, Dict, Any # Додано Dict, Any
from app.database.postgres_models.device_models import DeviceTypeEnum, DeviceStatusEnum

class DeviceBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=100, description="User-friendly name for the device")
    host: str = Field(..., description="Hostname or IP address of the device")
    port: int = Field(default=8728, gt=0, le=65535, description="API port of the device")
    username: str = Field(..., min_length=1, description="Username for device API access")
    device_type: DeviceTypeEnum = Field(default=DeviceTypeEnum.MIKROTIK_ROUTEROS, description="Type of the device")
    is_enabled: bool = Field(default=True, description="Is this device actively managed/monitored")

class DeviceCreate(DeviceBase):
    password: str = Field(..., min_length=1, description="Password for device API access (will be encrypted before DB storage)")

class DeviceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=100)
    host: Optional[str] = None
    port: Optional[int] = Field(None, gt=0, le=65535)
    username: Optional[str] = Field(None, min_length=1)
    password: Optional[str] = Field(None, min_length=1, description="New password, if changing")
    device_type: Optional[DeviceTypeEnum] = None
    is_enabled: Optional[bool] = None

class DeviceResponse(DeviceBase):
    id: int
    status: DeviceStatusEnum
    os_version: Optional[str] = None
    syslog_configured_by_siem: bool
    netflow_configured_by_siem: bool
    last_successful_connection: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Pydantic V2, було orm_mode
        use_enum_values = True

class SyslogConfigPayload(BaseModel):
    target_host: IPvAnyAddress = Field(..., description="IP address of the Syslog server")
    target_port: int = Field(default=514, gt=0, le=65535, description="Port of the Syslog server")
    action_name_prefix: str = Field(default="siem", description="Prefix for logging action and rule names on Mikrotik")
    topics: str = Field(default="!debug", description="Comma-separated list of topics to log")

class NetflowConfigPayload(BaseModel):
    target_host: IPvAnyAddress = Field(..., description="IP address of the Netflow collector")
    target_port: int = Field(default=2055, gt=0, le=65535, description="Port of the Netflow collector")
    interfaces: str = Field(default="all", description="Interfaces to monitor for Netflow (e.g., 'all', 'ether1,ether2')")
    version: int = Field(default=9, ge=5, le=10, description="Netflow version (e.g., 5, 9)")

class BlockIpPayload(BaseModel):
    list_name: str = Field(..., description="Name of the address list on Mikrotik")
    ip_address: IPvAnyAddress = Field(..., description="IP address to block")
    comment: Optional[str] = Field(None, description="Optional comment for the address list entry")
    # Можна додати параметри для правила файрволу, якщо потрібно більше гнучкості:
    firewall_chain: str = Field(default="forward", description="Firewall chain for the blocking rule")
    firewall_action: str = Field(default="drop", description="Action for the blocking rule (e.g., drop, reject)")
    rule_comment_prefix: Optional[str] = Field(default="SIEM_auto_block_for_")

class UnblockIpPayload(BaseModel):
    list_name: str = Field(..., description="Name of the address list on Mikrotik")
    ip_address: IPvAnyAddress = Field(..., description="IP address to unblock")
