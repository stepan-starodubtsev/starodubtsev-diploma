# app/modules/data_ingestion/service.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from .listeners.syslog_udp_listener import SyslogUDPListener
from .parsers.syslog_parser import parse_syslog_message_rfc3164_like
from .normalizers.syslog_normalizer import SyslogNormalizer

from .listeners.netflow_udp_collector import NetflowUDPCollector
from .parsers.netflow_parser import NetflowParser, NETFLOW_LIB_AVAILABLE
from .normalizers.netflow_normalizer import NetflowNormalizer

from .writers.elasticsearch_writer import ElasticsearchWriter  # <--- Розкоментуй/додай імпорт
from .normalizers.common_event_schema import CommonEventSchema  # <--- Імпорт для "мертвої черги"

from app.core.config import settings


class DataIngestionService:
    def __init__(self,
                 syslog_host="0.0.0.0", syslog_port=1514,
                 netflow_host="0.0.0.0", netflow_port=2055
                 ):
        self.syslog_normalizer = SyslogNormalizer()

        # ---> Ініціалізація ElasticsearchWriter <---
        self.elasticsearch_writer: Optional[ElasticsearchWriter] = None
        try:
            # Припускаємо, що ELASTICSEARCH_HOST та ELASTICSEARCH_PORT_API визначені в settings
            # і вказують на твій локальний Elasticsearch, прокинутий Docker'ом.
            es_host_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT_API}"
            self.elasticsearch_writer = ElasticsearchWriter(es_hosts=[es_host_url])
        except ConnectionError as e:
            print(f"FATAL: Could not connect to Elasticsearch during service initialization: {e}")
            # Сервіс може продовжити роботу, але не зможе зберігати дані.
        except Exception as e_other:  # Інші можливі помилки при ініціалізації ES
            print(f"FATAL: Unexpected error initializing ElasticsearchWriter: {e_other}")

        self.syslog_listener = SyslogUDPListener(
            host=syslog_host,
            port=syslog_port,
            message_handler_callback=self._handle_raw_syslog_message
        )

        self.netflow_parser: Optional[NetflowParser] = None
        self.netflow_collector: Optional[NetflowUDPCollector] = None
        self.netflow_normalizer: Optional[NetflowNormalizer] = None

        if NETFLOW_LIB_AVAILABLE:
            try:
                self.netflow_parser = NetflowParser()
                self.netflow_normalizer = NetflowNormalizer()
                self.netflow_collector = NetflowUDPCollector(
                    host=netflow_host,
                    port=netflow_port,
                    message_handler_callback=self._handle_raw_netflow_packet
                )
                print(f"Netflow components initialized for {netflow_host}:{netflow_port}.")
            except Exception as e:
                print(f"ERROR: Failed to initialize Netflow components: {e}")
                self.netflow_parser = None
                self.netflow_collector = None
                self.netflow_normalizer = None
        else:
            print("WARNING: NetFlow processing is disabled (library not available).")

    def _handle_raw_syslog_message(self, raw_message_bytes: bytes, client_address: tuple):
        try:
            raw_message_str = raw_message_bytes.decode('utf-8', errors='replace').strip()
            if not raw_message_str: return

            parsed_data = parse_syslog_message_rfc3164_like(raw_message_str)

            if parsed_data:
                parsed_data['reporter_ip'] = client_address[0]
                parsed_data['reporter_port'] = client_address[1]
                parsed_data['raw_log'] = raw_message_str
                normalized_event = self.syslog_normalizer.normalize(parsed_data)

                if normalized_event:
                    # print(f"NORMALIZED SYSLOG (from {client_address[0]}): {normalized_event.model_dump_json(indent=2, exclude_none=True)}")
                    if self.elasticsearch_writer:
                        if not self.elasticsearch_writer.write_event(normalized_event,
                                                                     index_prefix="siem-syslog-events"):
                            print(f"Failed to write SYSLOG event from {client_address[0]} to Elasticsearch.")
                    else:
                        print("Elasticsearch writer not available. SYSLOG event not written.")
                else:
                    print(f"Failed to normalize parsed syslog: {parsed_data.get('raw_log', raw_message_str)[:200]}")
                    self._write_to_dead_letter_queue(raw_message_str, client_address[0], "syslog_normalization_failed")
            else:
                print(f"Failed to parse Syslog: {raw_message_str[:200]}")
                self._write_to_dead_letter_queue(raw_message_str, client_address[0], "syslog_parsing_failed")
        except Exception as e:
            print(f"Error processing raw syslog from {client_address}: {e}\nMsg: {raw_message_bytes[:200]}")
            self._write_to_dead_letter_queue(raw_message_bytes.decode('utf-8', errors='replace'), client_address[0],
                                             "syslog_processing_error", error_details=str(e))

    def _handle_raw_netflow_packet(self, raw_packet_bytes: bytes, client_address: tuple):
        if not self.netflow_parser or not self.netflow_normalizer:
            return

        exporter_ip = client_address[0]
        exporter_port = client_address[1]

        try:
            # NetflowParser тепер додає 'router_sys_uptime_ms' та 'packet_unix_secs' до flow_data для v5
            parsed_flows: List[Dict[str, Any]] = self.netflow_parser.parse_packet(raw_packet_bytes, exporter_ip,
                                                                                  exporter_port)

            if parsed_flows:
                for i, flow_data in enumerate(parsed_flows):
                    flow_data['event_ingestion_timestamp'] = datetime.now(timezone.utc)  # Додаємо час прийому

                    normalized_event = self.netflow_normalizer.normalize(
                        flow_data)  # flow_data вже містить дані хедера

                    if normalized_event:
                        # Розкоментуй, щоб бачити нормалізовані дані
                        # print(f"  NORMALIZED NETFLOW {i+1} (Exporter: {exporter_ip}): {normalized_event.model_dump_json(indent=2, exclude_none=True)}")
                        if self.elasticsearch_writer:
                            if not self.elasticsearch_writer.write_event(normalized_event,
                                                                         index_prefix="siem-netflow-events"):
                                print(
                                    f"Failed to write NETFLOW event from {exporter_ip} (flow {i + 1}) to Elasticsearch.")
                        else:
                            print("Elasticsearch writer not available. NETFLOW event not written.")
                    else:
                        print(
                            f"  Failed to normalize NetFlow data for flow. Raw flow data snippet: {str(flow_data)[:200]}")
                        self._write_to_dead_letter_queue(str(flow_data), exporter_ip,
                                                         "netflow_normalization_failed")
            # else:
            #     # Це може бути темплейт пакет або порожній пакет, не обов'язково помилка
            #     pass


        except Exception as e:
            print(f"Error processing NetFlow packet from {exporter_ip}:{exporter_port}: {type(e).__name__} - {e}")
            import traceback
            traceback.print_exc()
            self._write_to_dead_letter_queue(f"Raw packet size: {len(raw_packet_bytes)}", exporter_ip,
                                             "netflow_processing_error", error_details=str(e))

    # ...

    def _write_to_dead_letter_queue(self, raw_data: str, reporter_ip: str, error_type: str,
                                    error_details: Optional[str] = None):
        """Записує не оброблені дані в окремий індекс для аналізу."""
        if self.elasticsearch_writer:
            dead_letter_event = CommonEventSchema(
                timestamp=datetime.now(timezone.utc),  # Час помилки
                raw_log=raw_data[:10000],  # Обмеження довжини сирих даних
                reporter_ip=reporter_ip,
                event_category="error_log",
                event_type=error_type,
                message=f"Failed to process log/flow. Type: {error_type}",
                additional_fields={"error_details": error_details} if error_details else {}
            )
            self.elasticsearch_writer.write_event(dead_letter_event, index_prefix="siem-dead-letter-queue")
        else:
            print(
                f"DEAD-LETTER (ES not available): Type: {error_type}, Reporter: {reporter_ip}, Data: {raw_data[:200]}")

    def start_listeners(self):
        if self.elasticsearch_writer is None:
            print("WARNING: Elasticsearch writer is not initialized. Events will not be stored in Elasticsearch.")
        self.syslog_listener.start()
        if self.netflow_collector:
            self.netflow_collector.start()
        print("Data Ingestion Service: All possible listeners started.")

    def stop_listeners(self):
        self.syslog_listener.stop()
        if self.netflow_collector:
            self.netflow_collector.stop()
        if self.elasticsearch_writer:  # <--- Розкоментуй/додай
            self.elasticsearch_writer.close()
        print("Data Ingestion Service: All possible listeners stopped.")


if __name__ == '__main__':
    SYSLOG_LISTEN_PORT = 1514
    NETFLOW_LISTEN_PORT = 2055
    service = DataIngestionService(syslog_port=SYSLOG_LISTEN_PORT, netflow_port=NETFLOW_LISTEN_PORT)
    try:
        service.start_listeners()
        print(
            f"Data Ingestion Service running. Syslog on port {SYSLOG_LISTEN_PORT}, NetFlow on port {NETFLOW_LISTEN_PORT}.")
        print("Press Ctrl+C to stop Data Ingestion Service.")
        while True: import time; time.sleep(1)
    except KeyboardInterrupt:
        print("\nData Ingestion Service shutdown requested by user...")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback

        traceback.print_exc()
    finally:
        service.stop_listeners()
        print("Data Ingestion Service shut down completely.")
