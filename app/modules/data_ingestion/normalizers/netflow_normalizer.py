# app/modules/data_ingestion/normalizers/netflow_normalizer.py
import json
from typing import Dict, Optional, Any
from datetime import datetime, timedelta, timezone
from pydantic import ValidationError, IPvAnyAddress
import ipaddress  # Для конвертації цілочисельних IP

from .common_event_schema import CommonEventSchema

PROTOCOL_MAP = {1: "ICMP", 6: "TCP", 17: "UDP", 47: "GRE", 50: "ESP", 51: "AH", 89: "OSPF", 132: "SCTP"}
TCP_FLAGS_MAP = {0x01: "FIN", 0x02: "SYN", 0x04: "RST", 0x08: "PSH", 0x10: "ACK", 0x20: "URG", 0x40: "ECE", 0x80: "CWR"}


def json_converter_with_datetime(obj: Any) -> str:
    if isinstance(obj, (datetime, ipaddress.IPv4Address, ipaddress.IPv6Address)):  # Додано ipaddress
        return obj.isoformat() if isinstance(obj, datetime) else str(obj)
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


class NetflowNormalizer:
    def _convert_int_to_ip(self, ip_int: Optional[int]) -> Optional[IPvAnyAddress]:
        if ip_int is None:
            return None
        try:
            return ipaddress.ip_address(ip_int)
        except ValueError:
            print(f"NetflowNormalizer: Could not convert int '{ip_int}' to IP address.")
            return None

    def _format_tcp_flags(self, flags_int: Optional[int]) -> Optional[str]:
        if flags_int is None: return None
        active_flags = [name for bit, name in TCP_FLAGS_MAP.items() if flags_int & bit]
        return ",".join(active_flags) if active_flags else None

    def _calculate_flow_timestamps_v5(
            self,
            flow_switched_ms: int,
            router_uptime_ms_at_export: int,
            packet_export_epoch_secs: int
    ) -> Optional[datetime]:
        """Конвертує час з NetFlow v5 (мілісекунди аптайму) в datetime UTC."""
        if flow_switched_ms is None or router_uptime_ms_at_export is None or packet_export_epoch_secs is None:
            return None
        try:
            # Відносний час потоку до моменту експорту пакета (в мілісекундах)
            # Це значення буде від'ємним або нульовим, оскільки потік стався до або в момент експорту
            flow_time_relative_to_export_ms = flow_switched_ms - router_uptime_ms_at_export

            # Час експорту пакета в мілісекундах від Unix epoch
            export_time_epoch_ms = packet_export_epoch_secs * 1000

            # Абсолютний час події потоку в мілісекундах від Unix epoch
            event_time_epoch_ms = export_time_epoch_ms + flow_time_relative_to_export_ms

            return datetime.fromtimestamp(event_time_epoch_ms / 1000.0, tz=timezone.utc)
        except Exception as e:
            print(
                f"NetflowNormalizer: Error converting v5 timestamp - flow_switched_ms={flow_switched_ms}, router_uptime={router_uptime_ms_at_export}, export_secs={packet_export_epoch_secs}: {e}")
            return None

    def normalize(self, flow_data: Dict[str, Any]) -> Optional[CommonEventSchema]:
        if not flow_data: return None

        event_data_for_pydantic: Dict[str, Any] = {}
        raw_log_representation: str

        try:
            try:
                raw_log_representation = json.dumps(flow_data, default=json_converter_with_datetime, ensure_ascii=False)
            except Exception:
                raw_log_representation = str(flow_data)

            netflow_version = flow_data.get('netflow_version')

            # --- ЧАС ПОТОКУ ---
            flow_start_dt: Optional[datetime] = None
            flow_end_dt: Optional[datetime] = None
            duration_ms: Optional[int] = None
            event_timestamp: datetime

            if netflow_version == 5:
                router_uptime = flow_data.get('router_sys_uptime_ms')
                packet_secs = flow_data.get('packet_unix_secs')
                flow_start_dt = self._calculate_flow_timestamps_v5(flow_data.get('FIRST_SWITCHED'), router_uptime,
                                                                   packet_secs)
                flow_end_dt = self._calculate_flow_timestamps_v5(flow_data.get('LAST_SWITCHED'), router_uptime,
                                                                 packet_secs)
            elif netflow_version == 9 or netflow_version == 10:  # IPFIX
                # Для v9/IPFIX, бібліотека може надавати поля типу flowStartMilliseconds, flowEndMilliseconds (epoch ms)
                # або flowStartSeconds, flowEndSeconds (epoch sec). Або інші часові поля.
                # Потрібно дивитися, які саме поля повертає бібліотека для v9/IPFIX.
                # Припустимо, вона повертає 'flow_start_seconds' та 'flow_end_seconds' як epoch.
                start_sec = flow_data.get('flowStartSeconds') or flow_data.get(
                    'flow_start_seconds')  # Або інші можливі назви
                end_sec = flow_data.get('flowEndSeconds') or flow_data.get('flow_end_seconds')
                if start_sec is not None: flow_start_dt = datetime.fromtimestamp(float(start_sec), tz=timezone.utc)
                if end_sec is not None: flow_end_dt = datetime.fromtimestamp(float(end_sec), tz=timezone.utc)

            if flow_start_dt and flow_end_dt and flow_end_dt >= flow_start_dt:
                duration_ms = int((flow_end_dt - flow_start_dt).total_seconds() * 1000)

            event_timestamp = flow_end_dt if flow_end_dt else flow_data.get('event_ingestion_timestamp',
                                                                            datetime.now(timezone.utc))

            protocol_number = flow_data.get('PROTO')  # Для v5, або 'protocolIdentifier' для v9/IPFIX
            protocol_name = PROTOCOL_MAP.get(protocol_number,
                                             str(protocol_number)) if protocol_number is not None else None

            tcp_flags_int = flow_data.get('TCP_FLAGS')
            tcp_flags_str = self._format_tcp_flags(tcp_flags_int)
            tcp_flags_hex = f"0x{tcp_flags_int:02X}" if tcp_flags_int is not None else None

            input_if_id = flow_data.get('INPUT') or flow_data.get(
                'ingressInterface')  # v5: INPUT, v9/IPFIX: ingressInterface
            output_if_id = flow_data.get('OUTPUT') or flow_data.get(
                'egressInterface')  # v5: OUTPUT, v9/IPFIX: egressInterface

            event_data_for_pydantic = {
                "timestamp": event_timestamp,
                "ingestion_timestamp": flow_data.get('event_ingestion_timestamp', datetime.now(timezone.utc)),
                "reporter_ip": flow_data.get('exporter_ip'),
                "reporter_port": flow_data.get('exporter_port'),
                "hostname": None,
                "device_vendor": "Mikrotik",
                "device_product": "RouterOS",
                "event_category": "network",
                "event_type": "flow",
                "event_action": "traffic_flow",
                "event_outcome": "unknown",
                "flow_start_time": flow_start_dt,
                "flow_end_time": flow_end_dt,
                "flow_duration_milliseconds": duration_ms,

                "source_ip": self._convert_int_to_ip(flow_data.get('IPV4_SRC_ADDR')) or flow_data.get(
                    'sourceIPv4Address') or flow_data.get('sourceIPv6Address'),
                "source_port": flow_data.get('SRC_PORT') or flow_data.get('sourceTransportPort'),
                "destination_ip": self._convert_int_to_ip(flow_data.get('IPV4_DST_ADDR')) or flow_data.get(
                    'destinationIPv4Address') or flow_data.get('destinationIPv6Address'),
                "destination_port": flow_data.get('DST_PORT') or flow_data.get('destinationTransportPort'),

                "network_protocol": protocol_name,
                "network_protocol_number": protocol_number,

                "network_bytes_total": flow_data.get('IN_OCTETS') or flow_data.get('octetDeltaCount'),  # v5: IN_OCTETS
                "network_packets_total": flow_data.get('IN_PACKETS') or flow_data.get('packetDeltaCount'),
                # v5: IN_PACKETS

                "network_tcp_flags_str": tcp_flags_str,
                "network_tcp_flags_hex": tcp_flags_hex,
                "network_tos": flow_data.get('TOS') or flow_data.get('ipClassOfService'),  # v5: TOS

                "network_input_interface_id": str(input_if_id) if input_if_id is not None else None,
                "network_output_interface_id": str(output_if_id) if output_if_id is not None else None,

                "source_as": flow_data.get('SRC_AS') or flow_data.get('bgpSourceAsNumber'),
                "destination_as": flow_data.get('DST_AS') or flow_data.get('bgpDestinationAsNumber'),
                "source_mask_bits": flow_data.get('SRC_MASK') or flow_data.get(
                    'sourceIPv4PrefixLength') or flow_data.get('sourceIPv6PrefixLength'),
                "destination_mask_bits": flow_data.get('DST_MASK') or flow_data.get(
                    'destinationIPv4PrefixLength') or flow_data.get('destinationIPv6PrefixLength'),

                "raw_log": raw_log_representation,
                "tags": ["netflow", f"netflow_v{flow_data.get('netflow_version', 'unknown')}"],
                "additional_fields": {}
            }

            # Збір решти полів
            known_keys_in_event_data = set(event_data_for_pydantic.keys())
            processed_flow_data_keys = {  # Ключі, які ми вже обробили або вони є в event_data_for_pydantic
                'exporter_ip', 'exporter_port', 'event_ingestion_timestamp', 'netflow_version', 'observation_domain_id',
                'router_sys_uptime_ms', 'packet_unix_secs',  # Дані хедера
                'IPV4_SRC_ADDR', 'IPV4_DST_ADDR', 'SRC_PORT', 'DST_PORT', 'PROTO', 'IN_OCTETS', 'IN_PACKETS',
                'FIRST_SWITCHED', 'LAST_SWITCHED', 'TCP_FLAGS', 'TOS', 'INPUT', 'OUTPUT', 'SRC_AS', 'DST_AS',
                'SRC_MASK', 'DST_MASK', 'NEXT_HOP',
                # Додай сюди інші ключі з бібліотеки jathan/netflow для v5, якщо вони є
                # або ключі для v9/IPFIX, якщо будеш їх обробляти тут
                'srcaddr', 'dstaddr', 'srcport', 'dstport', 'prot', 'dOctets', 'dPkts', 'first', 'last',
                'tcp_flags', 'tos', 'input', 'output', 'src_as', 'dst_as', 'src_mask', 'dst_mask',
                'nexthop', 'engine_type', 'engine_id', 'sampling_interval', 'sampling_algorithm',
                # Ключі для v9/IPFIX, які може повернути jathan/netflow (приклади)
                'sourceIPv4Address', 'destinationIPv4Address', 'sourceTransportPort', 'destinationTransportPort',
                'protocolIdentifier', 'octetDeltaCount', 'packetDeltaCount', 'flowStartSeconds', 'flowEndSeconds',
                'ipClassOfService', 'ingressInterface', 'egressInterface', 'bgpSourceAsNumber',
                'bgpDestinationAsNumber',
                'sourceIPv4PrefixLength', 'destinationIPv4PrefixLength',
                'sourceIPv6Address', 'destinationIPv6Address', 'sourceIPv6PrefixLength', 'destinationIPv6PrefixLength',
                'ipNextHopIPv4Address', 'ipNextHopIPv6Address'
            }
            for key, value in flow_data.items():
                if key not in known_keys_in_event_data and key not in processed_flow_data_keys:
                    event_data_for_pydantic["additional_fields"][f"netflow_{key}"] = value
            if not event_data_for_pydantic["additional_fields"]: event_data_for_pydantic.pop("additional_fields")

            return CommonEventSchema(**event_data_for_pydantic)

        except ValidationError as e:
            print(f"NetflowNormalizer: Pydantic ValidationError: {e.errors()}")
            print(f"Problematic data for Pydantic model: {event_data_for_pydantic}")
            return None
        except Exception as e:
            print(f"NetflowNormalizer: Unexpected error: {e}")
            print(f"Problematic flow_data (original): {flow_data}")
            import traceback
            traceback.print_exc()
            return None


# ... (if __name__ == '__main__' блок для тестування) ...
if __name__ == '__main__':
    normalizer = NetflowNormalizer()
    sample_v5_flow_data_from_parser = {
        'exporter_ip': '192.168.88.1', 'exporter_port': 2055, 'netflow_version': 5,
        'router_sys_uptime_ms': 7200000,  # 2 години в мс
        'packet_unix_secs': int(datetime.now(timezone.utc).timestamp()),  # Час експорту пакета
        'IPV4_SRC_ADDR': 3232235777,  # 192.168.1.1
        'IPV4_DST_ADDR': 134744072,  # 8.8.8.8
        'NEXT_HOP': 3232235521,  # 192.168.0.1
        'INPUT': 2,  # SNMP індекс
        'OUTPUT': 3,
        'IN_PACKETS': 100,
        'IN_OCTETS': 15000,
        'FIRST_SWITCHED': 7190000,  # За 10 секунд до експорту
        'LAST_SWITCHED': 7195000,  # За 5 секунд до експорту
        'SRC_PORT': 54321,
        'DST_PORT': 53,
        'TCP_FLAGS': 0,  # Не TCP
        'PROTO': 17,  # UDP
        'TOS': 0,
        'SRC_AS': 0,
        'DST_AS': 15169,  # Google AS
        'SRC_MASK': 24,
        'DST_MASK': 0,
        'event_ingestion_timestamp': datetime.now(timezone.utc)  # Додано сервісом
    }
    normalized = normalizer.normalize(sample_v5_flow_data_from_parser)
    if normalized:
        print("\n--- Normalized NetFlow Event (V5 Example) ---")
        print(normalized.model_dump_json(indent=2, exclude_none=True))
    else:
        print("NetFlow normalization failed for V5 sample data.")