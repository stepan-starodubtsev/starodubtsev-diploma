# app/modules/data_ingestion/parsers/netflow_parser.py
import ipaddress
from datetime import timezone, datetime
from typing import List, Dict, Any, Optional

try:
    # Згідно з __init__.py та utils.py бібліотеки bitkeks/python-netflow-v9-softflowd,
    # parse_packet імпортується так:
    from netflow import \
        parse_packet  # Це має бути from netflow.utils import parse_packet, якщо __init__.py експортує його звідти
    # Або, якщо __init__.py бібліотеки netflow робить from .utils import parse_packet,
    # то from netflow import parse_packet - правильно.
    # Судячи з твого файлу __init__.py: from .utils import parse_packet,
    # отже "from netflow import parse_packet" - КОРЕКТНО.

    # Класи пакетів імпортуються в utils.py з відповідних підмодулів.
    # Нам потрібен V5Packet для перевірки типу та доступу до хедера.
    from netflow.v5 import V5ExportPacket  # Використовуємо V5ExportPacket, як в utils.py

    NETFLOW_LIB_AVAILABLE = True
    print(
        "Successfully imported 'parse_packet' and 'V5ExportPacket' from 'bitkeks/python-netflow-v9-softflowd' (netflow pip package).")
except ImportError as e:
    print(
        f"WARNING: Could not import components from 'bitkeks/python-netflow-v9-softflowd'. Error: {e}. NetFlow v5 parsing will be disabled.")
    NETFLOW_LIB_AVAILABLE = False
    V5ExportPacket = type(None)  # Заглушка


    def parse_packet(*args, **kwargs):
        return None  # type: ignore [assignment]


class NetflowParser:
    def __init__(self):
        if not NETFLOW_LIB_AVAILABLE:
            raise ImportError("'bitkeks/python-netflow-v9-softflowd' library is required for NetflowParser.")
        # Для NetFlow v5 кешування темплейтів не потрібне
        print("NetflowParser (NetFlow v5 focused) initialized using 'bitkeks/python-netflow-v9-softflowd'.")

    def parse_packet(self, raw_packet: bytes, exporter_ip: str, exporter_port: int) -> List[Dict[str, Any]]:
        if not NETFLOW_LIB_AVAILABLE or not parse_packet or V5ExportPacket is None:
            return []

        parsed_flows_list = []

        try:
            # Для NetFlow v5 темплейти не потрібні, тому передаємо templates=None
            # (або порожній словник, якщо функція цього вимагає, але None має бути ОК)
            # Згідно з utils.py, parse_packet приймає templates, але для v5 він їх не використовує.
            export_packet_obj = parse_packet(raw_packet, templates=None)  # templates=None для v5

            # Перевіряємо, чи це дійсно V5 пакет
            if isinstance(export_packet_obj, V5ExportPacket):
                # export_packet_obj.flows - це список об'єктів V5DataRecord
                # Кожен V5DataRecord має поля як атрибути, а бібліотека також може надавати .data як словник.
                # З твоїх логів видно, що `flow_record.data` існує і є словником.
                if hasattr(export_packet_obj, 'flows') and isinstance(export_packet_obj.flows, list):
                    header_data = {}
                    if hasattr(export_packet_obj, 'header'):
                        # Дані з хедера NetFlow v5, потрібні для конвертації часу
                        header_data['router_sys_uptime_ms'] = export_packet_obj.header.uptime
                        header_data['packet_unix_secs'] = export_packet_obj.header.timestamp
                        # header_data['flow_sequence'] = export_packet_obj.header.sequence # Якщо потрібно

                    for flow_record in export_packet_obj.flows:
                        # Згідно з твоїми логами, flow_record - це DataRecord, у якого є атрибут .data (словник)
                        # Наприклад: <DataRecord with data {'IPV4_SRC_ADDR': ..., ...}>
                        # У бібліотеці bitkeks/python-netflow-v9-softflowd, V5ExportPacket.flows містить V5DataRecord,
                        # а V5DataRecord зберігає поля як атрибути. Метод .data може бути зручним представленням.
                        # Якщо `flow_record` сам є словником, то `flow_record.copy()`
                        # Якщо `flow_record` об'єкт, а дані в `flow_record.data`:
                        if hasattr(flow_record, 'data') and isinstance(flow_record.data, dict):
                            flow_data_dict = flow_record.data.copy()
                        else:
                            # Якщо .data немає, спробуємо зібрати атрибути (як для V5DataRecord з bitkeks)
                            flow_data_dict = {
                                k: v for k, v in flow_record.__dict__.items()
                                if not k.startswith('_')  # Пропускаємо службові атрибути
                            }
                            if not flow_data_dict:  # Якщо і так нічого не зібрали
                                print(
                                    f"NetflowParser: V5 Flow record from {exporter_ip} has unexpected structure: {type(flow_record)}")
                                continue

                        flow_data_dict['exporter_ip'] = exporter_ip
                        flow_data_dict['exporter_port'] = exporter_port
                        flow_data_dict['netflow_version'] = 5  # Ми очікуємо v5
                        flow_data_dict.update(header_data)  # Додаємо дані хедера до кожного потоку
                        parsed_flows_list.append(flow_data_dict)
                else:
                    print(f"NetflowParser: Parsed V5 packet from {exporter_ip} has no 'flows' list or it's not a list.")
            elif export_packet_obj is not None:
                # Якщо пакет розпарсився, але не v5
                version = getattr(export_packet_obj, 'header', None)
                version = getattr(version, 'version', 'unknown') if version else 'unknown'
                print(
                    f"NetflowParser: Received packet is not NetFlow V5 as expected. Actual version: {version}. Skipping.")
            # else: # parse_packet повернув None (порожній або пошкоджений пакет)
            # print(f"NetflowParser: parse_packet returned None for data from {exporter_ip}.")

        except Exception as e:
            print(
                f"NetflowParser: Error decoding V5 packet from {exporter_ip}:{exporter_port} - {type(e).__name__}: {e}")
            # import traceback # Для детальної діагностики
            # traceback.print_exc()

        return parsed_flows_list


# Блок для тестування (if __name__ == '__main__'):
if __name__ == '__main__':
    if NETFLOW_LIB_AVAILABLE:
        parser = NetflowParser()
        print("NetflowParser (V5 focused) initialized with 'bitkeks/python-netflow-v9-softflowd'.")

        # Приклад дуже спрощеного NetFlow V5 пакета (лише для демонстрації, значення не реалістичні)
        # Header (24 bytes): version (2B)=5, count (2B)=1, uptime (4B), unix_secs (4B),
        #                     unix_nsecs (4B), flow_seq (4B), engine_type (1B),
        #                     engine_id (1B), sampling (2B)
        # Для простоти, зробимо багато нулів, але це вплине на розрахунок часу.
        import struct

        header_version = 5
        header_count = 1
        header_uptime_ms = 10000000  # Наприклад, 10 000 секунд аптайму
        header_unix_secs = int(datetime.now(timezone.utc).timestamp())  # Поточний час
        header_unix_nsecs = 0
        header_flow_sequence = 1
        header_engine_type = 0
        header_engine_id = 0
        header_sampling_info = 0  # sampling_interval (2b) << 16 | sampling_algorithm (2b)

        sample_v5_header_bytes = struct.pack("!HHIIIBBH",
                                             header_version, header_count, header_uptime_ms, header_unix_secs,
                                             header_unix_nsecs,
                                             header_flow_sequence, header_engine_type, header_engine_id,
                                             header_sampling_info
                                             )

        # Flow Record (48 bytes)
        flow_src_addr = int(ipaddress.IPv4Address("10.0.0.1"))
        flow_dst_addr = int(ipaddress.IPv4Address("10.0.0.2"))
        flow_nexthop = 0
        flow_input_if = 1
        flow_output_if = 2
        flow_packets = 10
        flow_octets = 1000
        flow_first_switched = header_uptime_ms - 2000  # 2 секунди тому відносно аптайму
        flow_last_switched = header_uptime_ms - 1000  # 1 секунду тому
        flow_src_port = 12345
        flow_dst_port = 80
        flow_tcp_flags = 16  # ACK
        flow_protocol = 6  # TCP
        flow_tos = 0
        flow_src_as = 0
        flow_dst_as = 0
        flow_src_mask = 24
        flow_dst_mask = 32

        sample_v5_flow_bytes = struct.pack("!IIIIHHIIHHBBBBHHBBH",  # Зверни увагу на BBH в кінці для масок і pad
                                           flow_src_addr, flow_dst_addr, flow_nexthop,
                                           flow_packets, flow_octets,  # dPkts, dOctets
                                           flow_input_if, flow_output_if,  # input, output
                                           flow_first_switched, flow_last_switched,  # First, Last
                                           flow_src_port, flow_dst_port,  # srcport, dstport
                                           0,  # pad1 (1B) - бібліотека може очікувати його як частину flow_tcp_flags
                                           flow_tcp_flags,  # tcp_flags (1B)
                                           flow_protocol,  # prot (1B)
                                           flow_tos,  # tos (1B)
                                           flow_src_as, flow_dst_as,  # src_as, dst_as (each 2B)
                                           flow_src_mask, flow_dst_mask,  # src_mask, dst_mask (each 1B)
                                           0  # pad2 (2B) - бібліотека може очікувати це як частину останніх полів
                                           )  # Цей struct може бути не зовсім точним для бібліотеки, вона має свій внутрішній розбір

        # Правильна структура для пакування V5 потоку згідно з RFC (але бібліотека може мати свою обгортку)
        # Для тесту краще використовувати реальні байти, захоплені з мережі.
        # Цей тестовий пакет, швидше за все, не буде коректно розпарсений бібліотекою,
        # оскільки вона очікує певну структуру об'єктів.

        # print(f"Тестовий пакет (довжина {len(sample_v5_packet_bytes)}): {sample_v5_packet_bytes.hex()}")
        # print("Тестування з реальним пакетом було б краще.")

        # Щоб протестувати, потрібен реальний `raw_packet`
        # test_raw_packet = b"..." # сюди підстав реальні байти, які ти логував раніше
        # if 'test_raw_packet' in locals() and test_raw_packet:
        #     flows = parser.parse_packet(test_raw_packet, "192.168.88.1", 2055)
        #     if flows:
        #         print(f"\nParsed {len(flows)} V5 flows:")
        #         for i, flow in enumerate(flows):
        #             print(f"Flow {i+1}: {flow}")
        #     else:
        #         print("No V5 flows parsed from test packet.")
        # else:
        #     print("Test raw_packet not defined.")

    else:
        print(
            "'bitkeks/python-netflow-v9-softflowd' library or its components could not be imported, NetflowParser test skipped.")