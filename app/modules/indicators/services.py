# app/modules/indicators/services.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING
from datetime import datetime, timezone, date as date_type, timedelta
import json
import enum

from . import schemas as indicator_schemas
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from pydantic import ValidationError

# Для type hinting та доступу до APTGroupService для отримання імен/валідації APT
if TYPE_CHECKING:
    from app.modules.apt_groups.services import APTGroupService
    from app.database.postgres_models.threat_actor_models import APTGroup


class IndicatorService:
    def _prepare_ioc_document_for_es(
            self,
            db: Session,
            apt_service: 'APTGroupService',
            ioc_data: Union[indicator_schemas.IoCCreate, indicator_schemas.IoCUpdate, Dict[str, Any]],
            existing_doc: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        current_time = datetime.now(timezone.utc)

        if isinstance(ioc_data, (indicator_schemas.IoCCreate, indicator_schemas.IoCUpdate)):
            is_update_operation = isinstance(ioc_data, indicator_schemas.IoCUpdate)
            doc_to_index = ioc_data.model_dump(exclude_unset=is_update_operation)
        elif isinstance(ioc_data, dict):
            doc_to_index = ioc_data.copy()
        else:
            raise TypeError("ioc_data must be an IoC schema instance or a dict")

        if 'type' in doc_to_index and isinstance(doc_to_index['type'], enum.Enum):
            doc_to_index['type'] = doc_to_index['type'].value

        # Часові мітки SIEM (datetime об'єкти)
        created_at_val = doc_to_index.get("created_at_siem")
        if existing_doc and 'created_at_siem' in existing_doc:
            created_at_val = existing_doc['created_at_siem']

        if isinstance(created_at_val, str):
            try:
                doc_to_index["created_at_siem"] = datetime.fromisoformat(created_at_val.replace('Z', '+00:00'))
            except ValueError:
                doc_to_index["created_at_siem"] = current_time
        elif isinstance(created_at_val, datetime):
            doc_to_index["created_at_siem"] = created_at_val
        else:  # Для нового документа або якщо не передано/некоректно
            doc_to_index["created_at_siem"] = current_time

        doc_to_index["updated_at_siem"] = current_time

        ts_val_dt: Optional[datetime] = None
        for date_field_key_ioc in ['last_seen', 'first_seen']:
            val_ioc = doc_to_index.get(date_field_key_ioc)
            if isinstance(val_ioc, str):
                try:
                    doc_to_index[date_field_key_ioc] = datetime.fromisoformat(val_ioc.replace('Z', '+00:00'))
                except ValueError:
                    doc_to_index[date_field_key_ioc] = None

        val_last_seen = doc_to_index.get('last_seen');
        val_first_seen = doc_to_index.get('first_seen')
        if val_last_seen and isinstance(val_last_seen, datetime):
            ts_val_dt = val_last_seen
        elif val_first_seen and isinstance(val_first_seen, datetime):
            ts_val_dt = val_first_seen
        else:
            ts_val_dt = current_time

        doc_to_index["@timestamp"] = ts_val_dt
        doc_to_index['timestamp'] = ts_val_dt

        apt_ids_to_process: List[int] = []
        raw_apt_ids = doc_to_index.get("attributed_apt_group_ids")
        if raw_apt_ids is not None:
            try:
                apt_ids_to_process = sorted(list(set(map(int, raw_apt_ids))))
            except (ValueError, TypeError):
                apt_ids_to_process = []
        elif existing_doc and "attributed_apt_group_ids" in existing_doc:
            apt_ids_to_process = existing_doc.get("attributed_apt_group_ids", [])
        doc_to_index["attributed_apt_group_ids"] = apt_ids_to_process

        current_tags_set = set()
        # Ініціалізуємо теги з існуючого документа або з ioc_data
        initial_tags = doc_to_index.get("tags", [])
        if isinstance(initial_tags, list) and all(isinstance(t, str) for t in initial_tags):
            current_tags_set.update(initial_tags)
        elif existing_doc and isinstance(existing_doc.get("tags"), list):
            current_tags_set.update(str(t) for t in existing_doc.get("tags", []))

        if apt_ids_to_process:
            for apt_id_val in apt_ids_to_process:
                apt_group_db_obj: Optional['APTGroup'] = apt_service.get_apt_group_by_id(db, apt_id_val)
                if apt_group_db_obj:
                    safe_apt_name = "".join(c if c.isalnum() else '_' for c in apt_group_db_obj.name).lower()
                    current_tags_set.add(f"apt:{safe_apt_name}")
        doc_to_index["tags"] = sorted(list(current_tags_set))

        return doc_to_index

    def _parse_ioc_hit_to_response(self, hit: Dict[str, Any]) -> Optional[indicator_schemas.IoCResponse]:
        # ... (код без змін з попереднього повного файлу services.py) ...
        source_data = hit.get('_source', {});
        source_data['ioc_id'] = hit.get('_id')
        for dt_field_name in ['created_at_siem', 'updated_at_siem', 'first_seen', 'last_seen', '@timestamp',
                              'timestamp']:
            if dt_field_name in source_data and isinstance(source_data[dt_field_name], str):
                try:
                    dt_val_str = source_data[dt_field_name].replace('Z', '+00:00')
                    if 'T' not in dt_val_str and len(dt_val_str) == 10:
                        parsed_dt = datetime.strptime(dt_val_str, '%Y-%m-%d');
                        source_data[dt_field_name] = datetime(
                            parsed_dt.year, parsed_dt.month, parsed_dt.day, tzinfo=timezone.utc)
                    else:
                        source_data[dt_field_name] = datetime.fromisoformat(dt_val_str)
                    if source_data[dt_field_name] and source_data[dt_field_name].tzinfo is None: source_data[
                        dt_field_name] = source_data[dt_field_name].replace(tzinfo=timezone.utc)
                except ValueError:
                    source_data[dt_field_name] = None
        ioc_response_payload = {"ioc_id": source_data.get('ioc_id'), "value": source_data.get('value'),
                                "type": source_data.get('type'), "description": source_data.get('description'),
                                "source_name": source_data.get('source_name'),
                                "is_active": source_data.get('is_active', True),
                                "confidence": source_data.get('confidence'), "tags": source_data.get('tags', []),
                                "first_seen": source_data.get('first_seen'), "last_seen": source_data.get('last_seen'),
                                "created_at_siem": source_data.get('created_at_siem'),
                                "updated_at_siem": source_data.get('updated_at_siem'),
                                "attributed_apt_group_ids": source_data.get('attributed_apt_group_ids', [])}
        try:
            return indicator_schemas.IoCResponse(**ioc_response_payload)
        except ValidationError as e:
            print(f"Error validating IoC from ES: {e}. Data: {ioc_response_payload}");
            return None

    def add_ioc(self, db: Session, es_writer: ElasticsearchWriter, ioc_create_data: indicator_schemas.IoCCreate,
                apt_service: 'APTGroupService') -> Optional[indicator_schemas.IoCResponse]:
        if not es_writer or not es_writer.es_client: return None
        valid_apt_ids = []
        if ioc_create_data.attributed_apt_group_ids:
            for apt_id in ioc_create_data.attributed_apt_group_ids:
                if not apt_service.get_apt_group_by_id(db, apt_id):
                    print(f"Warning: APT ID {apt_id} for IoC '{ioc_create_data.value}' not found. Skipping.")
                else:
                    valid_apt_ids.append(apt_id)
        ioc_create_data.attributed_apt_group_ids = valid_apt_ids

        ioc_doc_internal = self._prepare_ioc_document_for_es(db, apt_service, ioc_create_data)
        timestamp_for_index_name = ioc_doc_internal.get('timestamp', datetime.now(timezone.utc))
        if not isinstance(timestamp_for_index_name, datetime):
            timestamp_for_index_name = datetime.now(timezone.utc)

        doc_payload_for_es = {}
        for k, v in ioc_doc_internal.items():
            if isinstance(v, datetime):
                doc_payload_for_es[k] = v.isoformat()
            elif isinstance(v, enum.Enum):
                doc_payload_for_es[k] = v.value
            elif k == 'timestamp':
                continue
            else:
                doc_payload_for_es[k] = v
        if '@timestamp' not in doc_payload_for_es and 'timestamp' in ioc_doc_internal:
            doc_payload_for_es['@timestamp'] = ioc_doc_internal['timestamp'].isoformat()

        try:
            target_index = es_writer._generate_index_name("siem-iocs", timestamp_for_index_name)
            resp = es_writer.es_client.index(index=target_index, document=doc_payload_for_es)
            if resp.get('result') in ['created', 'updated']:
                ioc_es_id = resp.get('_id')
                # Створюємо відповідь на основі ioc_doc_internal (де дати ще datetime)
                response_data_dict = ioc_doc_internal.copy()
                response_data_dict['ioc_id'] = ioc_es_id
                response_data_dict['created_at_siem'] = ioc_doc_internal["created_at_siem"]  # Вже datetime
                response_data_dict['updated_at_siem'] = ioc_doc_internal["updated_at_siem"]  # Вже datetime
                # Тип IoC для відповіді має бути Enum, якщо він був таким у ioc_create_data
                response_data_dict['type'] = ioc_create_data.type
                # tags та attributed_apt_group_ids вже оновлені в ioc_doc_internal

                # Поля, які можуть бути відсутні в ioc_doc_internal, але є в IoCBase
                for base_field in indicator_schemas.IoCBase.model_fields.keys():
                    if base_field not in response_data_dict:
                        response_data_dict[base_field] = getattr(ioc_create_data, base_field)

                return indicator_schemas.IoCResponse(**response_data_dict)
            else:
                print(f"Failed to index IoC. Response: {resp}");
                return None
        except Exception as e:
            print(f"Error adding IoC: {e}");
            import traceback;
            traceback.print_exc();
            return None

    def get_ioc_by_es_id(self, es_writer: ElasticsearchWriter, ioc_elasticsearch_id: str) -> Optional[
        indicator_schemas.IoCResponse]:
        # ... (код без змін)
        if not es_writer or not es_writer.es_client: return None
        es_client: Elasticsearch = es_writer.es_client
        try:
            search_query = {"query": {"ids": {"values": [ioc_elasticsearch_id]}}}
            res = es_client.search(index="siem-iocs-*", body=search_query, size=1)
            if res['hits']['hits']: return self._parse_ioc_hit_to_response(res['hits']['hits'][0])
            return None
        except es_exceptions.NotFoundError:
            return None
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error getting IoC by ES ID '{ioc_elasticsearch_id}': {e}");
            return None

    def update_ioc(self, db: Session, es_writer: ElasticsearchWriter, ioc_elasticsearch_id: str,
                   ioc_update_data: indicator_schemas.IoCUpdate, apt_service: 'APTGroupService') -> Optional[
        indicator_schemas.IoCResponse]:
        # ... (код потребує уважної реалізації з _prepare_ioc_document_for_es та отриманням existing_doc)
        if not es_writer or not es_writer.es_client: return None
        es_client: Elasticsearch = es_writer.es_client
        current_ioc_hit = None
        try:
            search_query = {"query": {"ids": {"values": [ioc_elasticsearch_id]}}}
            res = es_client.search(index="siem-iocs-*", body=search_query, size=1)
            if res['hits']['hits']:
                current_ioc_hit = res['hits']['hits'][0]
            else:
                print(f"IoC ES_ID '{ioc_elasticsearch_id}' not found for update.");
                return None
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error fetching current IoC for update: {e}");
            return None
        target_index = current_ioc_hit['_index'];
        existing_doc_source = current_ioc_hit['_source']

        # Валідація APT IDs
        if ioc_update_data.attributed_apt_group_ids is not None:
            valid_apt_ids = []
            for apt_id in ioc_update_data.attributed_apt_group_ids:
                if not apt_service.get_apt_group_by_id(db, apt_id):
                    print(f"Warning: APT ID {apt_id} for IoC update not found. Skipping.")
                else:
                    valid_apt_ids.append(apt_id)
            ioc_update_data.attributed_apt_group_ids = valid_apt_ids

        ioc_doc_prepared = self._prepare_ioc_document_for_es(db, apt_service, ioc_update_data,
                                                             existing_doc=existing_doc_source)
        timestamp_for_index_name = ioc_doc_prepared.get('timestamp', datetime.now(timezone.utc))
        if not isinstance(timestamp_for_index_name, datetime): timestamp_for_index_name = datetime.now(timezone.utc)

        doc_payload_for_es = {};
        for k, v in ioc_doc_prepared.items():
            if isinstance(v, datetime):
                doc_payload_for_es[k] = v.isoformat()
            elif isinstance(v, enum.Enum):
                doc_payload_for_es[k] = v.value
            elif k == 'timestamp':
                continue
            else:
                doc_payload_for_es[k] = v
        if '@timestamp' not in doc_payload_for_es and 'timestamp' in ioc_doc_prepared:
            doc_payload_for_es['@timestamp'] = ioc_doc_prepared['timestamp'].isoformat()
        try:
            resp = es_client.index(index=target_index, id=ioc_elasticsearch_id,
                                   document=doc_payload_for_es)  # index перезапише
            if resp.get('result') == 'updated':
                updated_hit = es_client.get(index=target_index, id=ioc_elasticsearch_id)
                return self._parse_ioc_hit_to_response(updated_hit)
            else:
                print(f"Failed to update IoC {ioc_elasticsearch_id}. Response: {resp}");
                return None
        except es_exceptions.NotFoundError:
            print(
                f"IoC {ioc_elasticsearch_id} not found in index {target_index} for update (during index call).");
            return None
        except Exception as e:
            print(f"Error updating IoC {ioc_elasticsearch_id}: {e}");
            return None

    def delete_ioc(self, es_writer: ElasticsearchWriter, ioc_elasticsearch_id: str) -> bool:
        # ... (код без змін) ...
        if not es_writer or not es_writer.es_client: return False
        es_client: Elasticsearch = es_writer.es_client
        try:
            search_query = {"query": {"ids": {"values": [ioc_elasticsearch_id]}}}
            res = es_client.search(index="siem-iocs-*", body=search_query, size=1)
            if not res['hits']['hits']: print(
                f"IoC ES_ID '{ioc_elasticsearch_id}' not found for deletion."); return True
            target_index = res['hits']['hits'][0]['_index']
            resp = es_client.delete(index=target_index, id=ioc_elasticsearch_id)
            if resp.get('result') == 'deleted':
                print(f"IoC {ioc_elasticsearch_id} deleted from {target_index}.");
                return True
            elif resp.get('result') == 'not_found':
                print(f"IoC {ioc_elasticsearch_id} already not found in {target_index}.");
                return True
            else:
                print(f"Failed to delete IoC {ioc_elasticsearch_id}. Response: {resp}");
                return False
        except es_exceptions.NotFoundError:
            print(f"IoC {ioc_elasticsearch_id} not found for deletion (NotFoundError).");
            return True
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error deleting IoC {ioc_elasticsearch_id}: {e}");
            return False

    def get_all_iocs(self, es_writer: ElasticsearchWriter, skip: int = 0, limit: int = 100) -> List[
        indicator_schemas.IoCResponse]:
        # ... (код без змін, використовує _parse_ioc_hit_to_response) ...
        if not es_writer or not es_writer.es_client: return []
        es_client: Elasticsearch = es_writer.es_client
        query_body = {"query": {"match_all": {}}, "from": skip, "size": limit,
                      "sort": [{"updated_at_siem": {"order": "desc", "unmapped_type": "date"}},
                               {"created_at_siem": {"order": "desc", "unmapped_type": "date"}}]}
        try:
            resp = es_client.search(index="siem-iocs-*", body=query_body)
            iocs_found = []
            for hit in resp.get('hits', {}).get('hits', []):
                ioc_resp = self._parse_ioc_hit_to_response(hit)
                if ioc_resp: iocs_found.append(ioc_resp)
            return iocs_found
        except es_exceptions.NotFoundError:
            print(f"Index pattern siem-iocs-* not found.");
            return []
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error getting all IoCs: {e}");
            return []

    def get_iocs_created_today(self, es_writer: ElasticsearchWriter, skip: int = 0, limit: int = 100) -> List[
        indicator_schemas.IoCResponse]:
        # ... (код без змін, використовує _parse_ioc_hit_to_response) ...
        if not es_writer or not es_writer.es_client: return []
        es_client: Elasticsearch = es_writer.es_client
        today_utc = datetime.now(timezone.utc);
        start_of_day_utc = datetime(today_utc.year, today_utc.month, today_utc.day, 0, 0, 0, 0, tzinfo=timezone.utc)
        end_of_day_utc = start_of_day_utc + timedelta(days=1)
        query_body = {"query": {
            "range": {"created_at_siem": {"gte": start_of_day_utc.isoformat(), "lt": end_of_day_utc.isoformat()}}},
            "from": skip, "size": limit, "sort": [{"created_at_siem": {"order": "desc"}}]}
        try:
            resp = es_client.search(index="siem-iocs-*", body=query_body)
            iocs_found = []
            for hit in resp.get('hits', {}).get('hits', []):
                ioc_resp = self._parse_ioc_hit_to_response(hit)
                if ioc_resp: iocs_found.append(ioc_resp)
            return iocs_found
        except es_exceptions.NotFoundError:
            print(f"Index pattern siem-iocs-* not found for today's IoCs.");
            return []
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error getting today's IoCs: {e}");
            return []

    def link_ioc_to_apt(self, db: Session, es_writer: ElasticsearchWriter, ioc_es_id: str, apt_group_id: int,
                        apt_service: 'APTGroupService') -> Optional[indicator_schemas.IoCResponse]:
        # ... (код без змін, використовує _parse_ioc_hit_to_response) ...
        apt_group = apt_service.get_apt_group_by_id(db, apt_group_id)
        if not apt_group: raise ValueError(f"APT Group with ID {apt_group_id} not found.")
        if not es_writer or not es_writer.es_client: print("ES client not available."); return None
        es_client: Elasticsearch = es_writer.es_client
        try:
            search_query = {"query": {"ids": {"values": [ioc_es_id]}}}
            search_res = es_client.search(index="siem-iocs-*", body=search_query)
            if not search_res['hits']['hits']: print(f"IoC ES_ID '{ioc_es_id}' not found."); return None
            hit_for_update = search_res['hits']['hits'][0];
            target_index = hit_for_update['_index']
            update_script = {
                "script": {
                    "source": """
                        ctx._source.attributed_apt_group_ids = [params.apt_id];
                        ctx._source.updated_at_siem = params.now;
                    """,
                    "lang": "painless",
                    "params": {
                        "apt_id": apt_group_id,
                        "now": datetime.now(timezone.utc).isoformat()
                    }
                }
            }
            es_client.update(index=target_index, id=ioc_es_id, body=update_script, refresh=True)
            print(f"Successfully linked APT ID {apt_group_id} to IoC ES_ID {ioc_es_id}")
            updated_hit = es_client.get(index=target_index, id=ioc_es_id)
            return self._parse_ioc_hit_to_response(updated_hit)
        except es_exceptions.NotFoundError:
            print(f"IoC ES_ID '{ioc_es_id}' not found (NotFoundError).");
            return None
        except es_exceptions.ElasticsearchWarning as e:
            print(f"ES error linking IoC {ioc_es_id} to APT {apt_group_id}: {e}");
            return None

    def remove_apt_id_from_all_iocs(self, es_writer: ElasticsearchWriter, apt_group_id_to_remove: int) -> bool:
        # ... (код без змін) ...
        if not es_writer or not es_writer.es_client: print("ES client not available."); return False
        es_client: Elasticsearch = es_writer.es_client
        update_by_query_body = {"script": {
            "source": "if (ctx._source.attributed_apt_group_ids != null && ctx._source.attributed_apt_group_ids.contains(params.apt_id_to_remove)) { ArrayList new_ids = new ArrayList(); for (int id : ctx._source.attributed_apt_group_ids) { if (id != params.apt_id_to_remove) { new_ids.add(id); } } ctx._source.attributed_apt_group_ids = new_ids; ctx._source.updated_at_siem = params.now; } else { ctx.op = 'noop'; }",
            "lang": "painless",
            "params": {"apt_id_to_remove": apt_group_id_to_remove, "now": datetime.now(timezone.utc).isoformat()}},
            "query": {"term": {"attributed_apt_group_ids": apt_group_id_to_remove}}}
        try:
            print(f"Attempting to remove APT ID {apt_group_id_to_remove} from linked IoCs in Elasticsearch...")
            response = es_client.update_by_query(index="siem-iocs-*", body=update_by_query_body, refresh=True,
                                                 wait_for_completion=True, conflicts='proceed')
            print(f"ES update_by_query response for removing APT ID {apt_group_id_to_remove} from IoCs: {response}")
            if response.get('failures') and len(response['failures']) > 0: print(
                f"WARNING: ES failures during update_by_query for APT ID {apt_group_id_to_remove}: {response['failures']}"); return False
            return True
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error updating IoCs in ES to remove APT ID {apt_group_id_to_remove}: {e}");
            return False

    def get_iocs_by_apt_group_id(self, es_writer: ElasticsearchWriter, apt_group_id: int, skip: int = 0,
                                 limit: int = 100) -> List[indicator_schemas.IoCResponse]:
        # ... (код без змін, використовує _parse_ioc_hit_to_response) ...
        if not es_writer or not es_writer.es_client: print("ES client not available."); return []
        es_client: Elasticsearch = es_writer.es_client
        query_body = {"query": {"term": {"attributed_apt_group_ids": apt_group_id}}, "from": skip, "size": limit,
                      "sort": [{"updated_at_siem": {"order": "desc"}}, {"created_at_siem": {"order": "desc"}}]}
        try:
            resp = es_client.search(index="siem-iocs-*", body=query_body)
            iocs_found = []
            for hit in resp.get('hits', {}).get('hits', []):
                ioc_resp = self._parse_ioc_hit_to_response(hit)
                if ioc_resp: iocs_found.append(ioc_resp)
            return iocs_found
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error getting IoCs for APT group {apt_group_id}: {e}");
            return []

    def get_active_ioc_summary_by_type(self, es_writer: ElasticsearchWriter) -> Dict[str, int]:
        """
        Повертає загальну кількість активних IoC, згрупованих за типом.
        """
        if not es_writer or not es_writer.es_client:
            print("Elasticsearch client not available in get_active_ioc_summary_by_type.")
            return {}

        es_client: Elasticsearch = es_writer.es_client

        # Запит агрегації до Elasticsearch
        aggregation_query_body = {
            "query": {
                "term": {
                    "is_active": True  # Тільки активні IoC
                }
            },
            "aggs": {
                "iocs_by_type": {
                    "terms": {"field": "type.keyword", "size": 20}  # Групуємо за типом, .keyword для точного збігу
                }
            },
            "size": 0  # Нам не потрібні самі документи, тільки агрегація
        }

        summary: Dict[str, int] = {}
        try:
            response = es_client.search(index="siem-iocs-*", body=aggregation_query_body)
            buckets = response.get('aggregations', {}).get('iocs_by_type', {}).get('buckets', [])
            for bucket in buckets:
                ioc_type = bucket.get('key')
                count = bucket.get('doc_count')
                if ioc_type:
                    summary[ioc_type] = count
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error getting IoC summary by type from Elasticsearch: {e}")

        return summary

    def get_unique_tags(self, es_writer: ElasticsearchWriter) -> List[str]:
        """
        Отримує список унікальних тегів з усіх індикаторів компрометації.

        Для цього використовується 'terms' агрегація в Elasticsearch, яка є
        дуже ефективним способом для таких завдань.

        :param es_writer: Активний клієнт Elasticsearch.
        :return: Відсортований список унікальних тегів.
        """

        es_client: Elasticsearch = es_writer.es_client
        # Запит до Elasticsearch для агрегації
        query_body = {
            "size": 0,  # Нам не потрібні самі документи, лише результати агрегації
            "aggs": {
                "unique_tags": {
                    "terms": {
                        "field": "tags",  # Поле, по якому групуємо. .keyword не потрібен, бо поле вже keyword.
                        "size": 1000  # Максимальна кількість унікальних тегів для повернення
                    }
                }
            }
        }

        try:
            response = es_client.search(
                index="siem-iocs-*",  # Шукаємо по всіх індексах з IoC
                body=query_body
            )

            # Обробляємо відповідь: витягуємо ключі з "бакетів" агрегації
            buckets = response.get('aggregations', {}).get('unique_tags', {}).get('buckets', [])

            # Створюємо список з імен тегів
            tags = [bucket['key'] for bucket in buckets]

            return sorted(tags)

        except Exception as e:
            print(f"Error fetching unique tags from Elasticsearch: {e}")
            # В реальному додатку тут варто використовувати логер
            return []
