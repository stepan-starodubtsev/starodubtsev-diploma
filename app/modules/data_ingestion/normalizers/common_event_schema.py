# app/modules/data_ingestion/normalizers/common_event_schema.py
from pydantic import BaseModel, Field, IPvAnyAddress
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone


class CommonEventSchema(BaseModel):
    # Часові мітки
    timestamp: datetime = Field(..., description="Час події (зазвичай час завершення потоку для NetFlow), UTC")
    ingestion_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc),
                                          description="Час прийому події системою (UTC)")

    # Інформація про джерело логу / репортер (експортер NetFlow)
    reporter_ip: Optional[IPvAnyAddress] = Field(None,
                                                 description="IP-адреса пристрою, що надіслав дані (експортер NetFlow)")
    reporter_port: Optional[int] = Field(None, description="Порт пристрою, що надіслав дані")
    hostname: Optional[str] = Field(None, description="Ім'я хоста експортера (якщо відомо)")

    # Інформація про пристрій/продукт
    device_vendor: Optional[str] = Field(None)
    device_product: Optional[str] = Field(None)
    device_version: Optional[str] = Field(None)  # Версія ОС експортера

    # Категоризація події
    event_category: str = Field(default="network", description="Категорія події (network для NetFlow)")
    event_type: str = Field(default="flow", description="Тип події (flow для NetFlow)")
    event_action: Optional[str] = Field(None, description="Дія (наприклад, для firewall логів, тут може бути N/A)")
    event_outcome: Optional[str] = Field(None)

    # Деталі Syslog (не застосовно для NetFlow, залишаємо Optional=None)
    syslog_facility: Optional[int] = None
    syslog_severity_code: Optional[int] = None
    syslog_severity_name: Optional[str] = None
    process_name: Optional[str] = None
    process_id: Optional[str] = None

    # Основне повідомлення (для NetFlow може бути згенероване або відсутнє)
    message: Optional[str] = Field(None, description="Згенерований опис потоку або відсутнє")

    # ---- Мережеві деталі потоку (ключове для NetFlow) ----
    flow_start_time: Optional[datetime] = Field(None, description="Час початку потоку (UTC)")
    flow_end_time: Optional[datetime] = Field(None,
                                              description="Час завершення потоку (UTC)")  # Це може бути == timestamp
    flow_duration_milliseconds: Optional[int] = Field(None, description="Тривалість потоку в мілісекундах")

    source_ip: Optional[IPvAnyAddress] = Field(None, alias="ipsrc")  # Додаємо alias для ipsrc
    source_port: Optional[int] = Field(None, ge=0, le=65535)
    source_mac: Optional[str] = None
    # source_geo: Optional[Dict[str, Any]] = None

    destination_ip: Optional[IPvAnyAddress] = Field(None, alias="ipdst")  # Додаємо alias для ipdst
    destination_port: Optional[int] = Field(None, ge=0, le=65535)
    destination_mac: Optional[str] = None
    # destination_geo: Optional[Dict[str, Any]] = None

    network_protocol: Optional[str] = Field(None, description="Мережевий протокол (TCP, UDP, ICMP тощо, або номер)")
    network_protocol_number: Optional[int] = Field(None, description="Номер протоколу IP")  # Зберігаємо і номер

    network_bytes_total: Optional[int] = Field(None, description="Загальна кількість байт у потоці (IN_BYTES для v5)")
    network_packets_total: Optional[int] = Field(None,
                                                 description="Загальна кількість пакетів у потоці (IN_PKTS для v5)")
    # Для v9/IPFIX можуть бути окремі лічильники для src->dst та dst->src

    network_tcp_flags_str: Optional[str] = Field(None,
                                                 description="Прапори TCP як рядок (SYN, ACK, FIN, RST, PSH, URG)")
    network_tcp_flags_hex: Optional[str] = Field(None, description="Прапори TCP як шістнадцяткове значення")

    network_tos: Optional[int] = Field(None, description="Type of Service (ToS) IP-пакета")

    network_input_interface_id: Optional[str] = Field(None, description="SNMP індекс вхідного інтерфейсу (inputIf)")
    network_output_interface_id: Optional[str] = Field(None, description="SNMP індекс вихідного інтерфейсу (outputIf)")

    # Поля для AS (Автономні системи)
    source_as: Optional[int] = Field(None, description="Номер AS джерела")
    destination_as: Optional[int] = Field(None, description="Номер AS призначення")

    # Маски мережі (рідко використовуються для IoC, але є в NetFlow v5)
    source_mask_bits: Optional[int] = Field(None, description="Довжина маски підмережі джерела")
    destination_mask_bits: Optional[int] = Field(None, description="Довжина маски підмережі призначення")

    # --- Кінець мережевих деталей потоку ---

    tags: List[str] = Field(default_factory=list, description="Теги для класифікації або фільтрації")
    raw_log: str = Field(..., description="Представлення сирого потоку даних або оригінального NetFlow запису")
    additional_fields: Optional[Dict[str, Any]] = Field(default_factory=dict)

    class Config:
        from_attributes = True
        use_enum_values = True
        populate_by_name = True  # Дозволяє використовувати alias (ipsrc, ipdst) при створенні моделі