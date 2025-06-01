# app/modules/response/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import enum


# --- Типи дій реагування ---
class ResponseActionTypeEnum(str, enum.Enum):
    BLOCK_IP = "block_ip"
    UNBLOCK_IP = "unblock_ip"
    SEND_EMAIL = "send_email"
    CREATE_TICKET = "create_ticket"  # Наприклад, для TheHive в майбутньому
    ISOLATE_HOST = "isolate_host"  # Потребує відповідного конектора/сервісу
    # ... інші типи дій


class ResponseActionBase(BaseModel):
    name: str = Field(..., description="Назва конкретної дії, наприклад, 'Block IP on Main Firewall'")
    type: ResponseActionTypeEnum = Field(..., description="Тип дії реагування")
    description: Optional[str] = Field(None, description="Опис дії")
    is_enabled: bool = Field(default=True)
    # Параметри для дії будуть зберігатися як JSON або окремі поля залежно від типу
    # Для простоти MVP, поки що можемо зробити їх більш загальними або опустити складну параметризацію
    # Наприклад, для BLOCK_IP, параметри можуть бути device_id, list_name
    # Ці параметри можуть бути визначені в пайплайні або частково в самій дії
    default_params: Optional[Dict[str, Any]] = Field(default_factory=dict,
                                                     description="Параметри за замовчуванням для цієї дії")


class ResponseActionCreate(ResponseActionBase):
    pass


class ResponseActionUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[ResponseActionTypeEnum] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    default_params: Optional[Dict[str, Any]] = None


class ResponseActionResponse(ResponseActionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True


# --- Схеми для Пайплайнів Реагування ---
class PipelineActionConfig(BaseModel):
    action_id: int = Field(..., description="ID дії реагування (з таблиці ResponseAction)")
    order: int = Field(..., ge=0, description="Порядок виконання дії в пайплайні")
    # Параметри, специфічні для цього кроку пайплайна, можуть перевизначати default_params з ResponseAction
    # Наприклад, для BLOCK_IP тут може бути конкретний IP для блокування, отриманий з офенса
    # або плейсхолдер, який буде замінено значенням з офенса.
    # Поки що, для простоти, параметри будуть передаватися динамічно.
    # Ми можемо зберігати тут шаблон параметрів або плейсхолдери.
    action_params_template: Optional[Dict[str, Any]] = Field(default_factory=dict,
                                                             description="Шаблон параметрів для дії, може містити плейсхолдери")


class ResponsePipelineBase(BaseModel):
    name: str = Field(..., min_length=3, max_length=255, description="Назва пайплайна реагування")
    description: Optional[str] = Field(None)
    is_enabled: bool = Field(default=True)
    # Умова спрацювання: може бути ID правила кореляції, тип офенса, серйозність тощо.
    # Для MVP, зробимо прив'язку до ID правила кореляції.
    trigger_correlation_rule_id: Optional[int] = Field(None,
                                                       description="ID правила кореляції, яке запускає цей пайплайн")
    # Або можна мати більш гнучкі умови, наприклад, за тегами офенса, серйозністю тощо.
    # trigger_offence_severity: Optional[OffenceSeverityEnum] = None # Потрібно імпортувати OffenceSeverityEnum
    # trigger_offence_title_contains: Optional[str] = None


class ResponsePipelineCreate(ResponsePipelineBase):
    actions_config: List[PipelineActionConfig] = Field(default_factory=list,
                                                       description="Список дій та їх конфігурацій для цього пайплайна")


class ResponsePipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None
    trigger_correlation_rule_id: Optional[int] = None
    actions_config: Optional[List[PipelineActionConfig]] = None  # Дозволяє повністю замінити список дій


class ResponsePipelineResponse(ResponsePipelineBase):
    id: int
    actions_config: List[PipelineActionConfig]  # Завжди повертаємо список дій
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        use_enum_values = True
