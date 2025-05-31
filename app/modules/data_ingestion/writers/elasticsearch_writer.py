# app/modules/data_ingestion/writers/elasticsearch_writer.py
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from typing import Optional, List, Dict, Any  # Змінено List на Optional[List[str]] для es_hosts
from datetime import datetime, timezone  # Додано timezone

from app.core.config import settings


# from ..normalizers.common_event_schema import CommonEventSchema # Імпортується там, де потрібно

class ElasticsearchWriter:
    def __init__(self,
                 es_hosts: Optional[List[str]] = None,
                 es_cloud_id: Optional[str] = None,
                 es_api_key: Optional[str] = None,
                 ):

        self.attempted_es_connection_info: str = "N/A"
        client_params: Dict[str, Any] = {}

        # --- Встановлюємо заголовки для сумісності з ES 8.x ---
        # Це має вирішити проблему "Accept version must be either version 8 or 7, but found 9"
        headers = {
            'Accept': 'application/vnd.elasticsearch+json;compatible-with=8',
            'Content-Type': 'application/vnd.elasticsearch+json;compatible-with=8'
        }
        client_params['headers'] = headers
        # ---------------------------------------------------------

        if es_cloud_id and es_api_key:
            self.attempted_es_connection_info = f"Elastic Cloud (ID: {es_cloud_id})"
            client_params['cloud_id'] = es_cloud_id
            if isinstance(es_api_key, tuple) and len(es_api_key) == 2:
                client_params['api_key'] = es_api_key
            elif isinstance(es_api_key, str):
                client_params['api_key'] = es_api_key
            else:
                # Якщо помилка тут, то виняток буде піднято до ConnectionError нижче
                raise ValueError("Invalid api_key format for Elastic Cloud.")
        elif es_hosts:
            self.attempted_es_connection_info = str(es_hosts)
            client_params['hosts'] = es_hosts
        else:
            es_host_setting = getattr(settings, "ELASTICSEARCH_HOST", "localhost")
            es_port_setting = getattr(settings, "ELASTICSEARCH_PORT_API", 9200)
            es_scheme = getattr(settings, "ELASTICSEARCH_SCHEME", "http")
            default_es_url = f"{es_scheme}://{es_host_setting}:{es_port_setting}"

            self.attempted_es_connection_info = default_es_url
            client_params['hosts'] = [default_es_url]
            print(f"ElasticsearchWriter: Attempting to connect to default Elasticsearch URL: {default_es_url}")

        print(f"ElasticsearchWriter: Initializing client with params: {client_params}")  # Для відладки

        try:
            self.es_client = Elasticsearch(**client_params)

            # Перевірка з'єднання за допомогою info()
            cluster_info = self.es_client.info()
            if cluster_info and isinstance(cluster_info, dict) and cluster_info.get('cluster_name'):
                print(
                    f"ElasticsearchWriter: Successfully connected to Elasticsearch cluster '{cluster_info.get('cluster_name')}' at {self.attempted_es_connection_info}.")
            else:
                # info() міг повернути щось неочікуване, але не кинути виняток
                # Якщо cluster_info порожній або не містить cluster_name, це може бути проблемою.
                # Однак, якщо info() не кинув виняток, базовий зв'язок є.
                print(
                    f"ElasticsearchWriter: Connected to Elasticsearch at {self.attempted_es_connection_info}, but info() response was unexpected or incomplete: {cluster_info}")

        # Обробка конкретних винятків від клієнта Elasticsearch
        except es_exceptions.AuthenticationException as e_auth:
            print(
                f"FATAL ElasticsearchWriter: Authentication failed for {self.attempted_es_connection_info}. Details: {e_auth}")
            raise ConnectionError(
                f"Authentication failed for Elasticsearch at {self.attempted_es_connection_info}. Details: {e_auth}")
        except es_exceptions.ConnectionError as e_conn:  # Це може бути ConnectionTimeout, SSLError тощо.
            print(
                f"FATAL ElasticsearchWriter: Connection failed to {self.attempted_es_connection_info}. Details: {e_conn}")
            raise ConnectionError(
                f"Failed to connect to Elasticsearch using configuration: {self.attempted_es_connection_info}. Details: {e_conn}")
        except ValueError as ve:  # Наприклад, неправильний формат api_key
            print(f"FATAL ElasticsearchWriter: Configuration error for Elasticsearch. Details: {ve}")
            raise ConnectionError(f"Configuration error for Elasticsearch. Details: {ve}")
        except Exception as e:  # Інші можливі помилки при ініціалізації клієнта або info()
            print(
                f"FATAL ElasticsearchWriter: An unexpected error occurred while trying to connect/get info from Elasticsearch ({self.attempted_es_connection_info}): {e}")
            raise ConnectionError(
                f"An unexpected error occurred while trying to connect/get info from Elasticsearch ({self.attempted_es_connection_info}): {e}")

    # ... (решта методів _generate_index_name, write_event, close - без змін) ...
    # Переконайся, що CommonEventSchema імпортується там, де використовується write_event
    def _generate_index_name(self, base_name: str, event_timestamp: datetime) -> str:
        return f"{base_name}-{event_timestamp.strftime('%Y.%m.%d')}"

    def write_event(self, event: Any, index_prefix: str = "siem-events") -> bool:
        if not event:
            print("ElasticsearchWriter: Received empty event, skipping write.")
            return False

        event_dict: Dict[str, Any]
        timestamp_for_index: datetime

        if hasattr(event, 'model_dump') and callable(event.model_dump):
            event_dict = event.model_dump(mode='json')
            timestamp_for_index = event.timestamp if hasattr(event, 'timestamp') and isinstance(event.timestamp,
                                                                                                datetime) else datetime.now(
                timezone.utc)
        elif hasattr(event, 'dict') and callable(event.dict):
            event_dict = event.dict()
            timestamp_for_index = event.timestamp if hasattr(event, 'timestamp') and isinstance(event.timestamp,
                                                                                                datetime) else datetime.now(
                timezone.utc)
        elif isinstance(event, dict):
            event_dict = event
            ts_val = event.get('timestamp') or event.get('@timestamp')
            if isinstance(ts_val, datetime):
                timestamp_for_index = ts_val
            elif isinstance(ts_val, str):
                try:
                    timestamp_for_index = datetime.fromisoformat(ts_val.replace('Z', '+00:00'))
                except ValueError:
                    timestamp_for_index = datetime.now(timezone.utc)
            else:
                timestamp_for_index = datetime.now(timezone.utc)
        else:
            print(f"ElasticsearchWriter: Event is not a Pydantic model or dict, cannot process. Type: {type(event)}")
            return False

        try:
            target_index = self._generate_index_name(index_prefix, timestamp_for_index)
            resp = self.es_client.index(index=target_index, document=event_dict)

            if resp.get('result') in ['created', 'updated', 'noop']:
                return True
            else:
                print(f"ElasticsearchWriter: Failed to index event. Response: {resp}")
                return False
        except es_exceptions.ConnectionTimeout:
            print(
                f"ElasticsearchWriter: Connection Timeout while indexing event to {target_index if 'target_index' in locals() else index_prefix}.")
            return False
        except es_exceptions.TransportError as e:
            print(
                f"ElasticsearchWriter: Transport Error while indexing event: {e} (Status: {e.status_code if hasattr(e, 'status_code') else 'N/A'}, Info: {e.info if hasattr(e, 'info') else 'N/A'})")
            return False
        except Exception as e:
            print(f"ElasticsearchWriter: Unexpected error while indexing event: {e}")
            return False

    def close(self):
        if self.es_client:
            try:
                self.es_client.close()
                print("ElasticsearchWriter: Elasticsearch connection closed.")
            except Exception as e:
                print(f"ElasticsearchWriter: Error closing Elasticsearch connection: {e}")