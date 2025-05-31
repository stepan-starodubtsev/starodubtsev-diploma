# app/modules/indicators/services.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING  # Додано TYPE_CHECKING
from datetime import datetime, timezone, timedelta
import json
import enum

from . import schemas as indicator_schemas
# НЕ РОБИМО: from app.modules.apt_groups.services import APTGroupService
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from pydantic import ValidationError

# Для type hinting без реального імпорту під час виконання, щоб уникнути циклу
if TYPE_CHECKING:
    from app.modules.apt_groups.services import APTGroupService


class IndicatorService:
    def _prepare_ioc_document_for_es(self, ioc_data: Union[
        indicator_schemas.IoCCreate, indicator_schemas.IoCUpdate, Dict[str, Any]],
                                     existing_doc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # ... (код методу без змін)
        current_time = datetime.now(timezone.utc)
        if isinstance(ioc_data, (indicator_schemas.IoCCreate, indicator_schemas.IoCUpdate)):
            doc_to_index = ioc_data.model_dump(exclude_unset=True, mode='json')
        elif isinstance(ioc_data, dict):
            doc_to_index = ioc_data.copy()
            if 'type' in doc_to_index and isinstance(doc_to_index['type'], enum.Enum):
                doc_to_index['type'] = doc_to_index['type'].value
        else:
            raise TypeError("ioc_data must be an IoC schema instance or a dict")
        if existing_doc and 'created_at_siem' in existing_doc:
            doc_to_index["created_at_siem"] = existing_doc['created_at_siem']
        else:
            doc_to_index["created_at_siem"] = current_time.isoformat()
        doc_to_index["updated_at_siem"] = current_time.isoformat()
        ts_val_dt: Optional[datetime] = None
        val_last_seen = doc_to_index.get('last_seen');
        val_first_seen = doc_to_index.get('first_seen')
        if isinstance(val_last_seen, str): val_last_seen = datetime.fromisoformat(val_last_seen.replace('Z', '+00:00'))
        if isinstance(val_first_seen, str): val_first_seen = datetime.fromisoformat(
            val_first_seen.replace('Z', '+00:00'))
        if val_last_seen:
            ts_val_dt = val_last_seen
        elif val_first_seen:
            ts_val_dt = val_first_seen
        else:
            ts_val_dt = current_time
        doc_to_index["@timestamp"] = ts_val_dt.isoformat() if isinstance(ts_val_dt,
                                                                         datetime) else current_time.isoformat()
        doc_to_index['timestamp'] = ts_val_dt
        if "attributed_apt_group_ids" in doc_to_index and doc_to_index["attributed_apt_group_ids"] is not None:
            try:
                doc_to_index["attributed_apt_group_ids"] = sorted(
                    list(set(map(int, doc_to_index["attributed_apt_group_ids"]))))
            except (ValueError, TypeError):
                doc_to_index["attributed_apt_group_ids"] = []
        elif "attributed_apt_group_ids" not in doc_to_index and existing_doc:
            doc_to_index["attributed_apt_group_ids"] = existing_doc.get("attributed_apt_group_ids", [])
        else:
            doc_to_index["attributed_apt_group_ids"] = []
        return doc_to_index

    def add_manual_ioc(self,
                       db: Session,
                       es_writer: ElasticsearchWriter,
                       ioc_create_data: indicator_schemas.IoCCreate,
                       apt_service: 'APTGroupService'  # <--- ІН'ЄКЦІЯ СЕРВІСУ
                       ) -> Optional[indicator_schemas.IoCResponse]:
        if not es_writer or not es_writer.es_client:
            print("ERROR: ElasticsearchWriter not provided to add_manual_ioc.")
            return None

        valid_apt_ids = []
        if ioc_create_data.attributed_apt_group_ids:
            for apt_id in ioc_create_data.attributed_apt_group_ids:
                if not apt_service.get_apt_group_by_id(db, apt_id):  # Використовуємо переданий apt_service
                    print(f"Warning: APT ID {apt_id} for IoC '{ioc_create_data.value}' not found. Skipping.")
                else:
                    valid_apt_ids.append(apt_id)
        ioc_create_data.attributed_apt_group_ids = valid_apt_ids

        ioc_doc_prepared = self._prepare_ioc_document_for_es(ioc_create_data)

        try:
            target_index = es_writer._generate_index_name("siem-iocs", ioc_doc_prepared['timestamp'])
            doc_payload_for_es = {
                k: v.isoformat() if isinstance(v, datetime) else (v.value if isinstance(v, enum.Enum) else v)
                for k, v in ioc_doc_prepared.items() if k != 'timestamp'}
            doc_payload_for_es['@timestamp'] = ioc_doc_prepared['timestamp'].isoformat()

            resp = es_writer.es_client.index(index=target_index, document=doc_payload_for_es)
            if resp.get('result') in ['created', 'updated']:
                ioc_es_id = resp.get('_id')
                response_data = ioc_create_data.model_dump()
                response_data['ioc_id'] = ioc_es_id
                response_data['created_at'] = datetime.fromisoformat(ioc_doc_prepared["created_at_siem"])
                response_data['updated_at'] = datetime.fromisoformat(ioc_doc_prepared["updated_at_siem"])
                return indicator_schemas.IoCResponse(**response_data)
            else:
                print(f"Failed to index manual IoC (direct call). Response: {resp}")
                return None
        except Exception as e:
            print(f"Error adding manual IoC: {e}")
            return None

    def find_ioc_by_value(self, es_writer: ElasticsearchWriter, value: str,
                          ioc_type: Optional[indicator_schemas.IoCTypeEnum] = None) -> List[
        indicator_schemas.IoCResponse]:
        # ... (код без змін з попереднього повного файлу services.py) ...
        if not es_writer or not es_writer.es_client: return []
        query_body: Dict[str, Any] = {"query": {"bool": {"must": [{"term": {"value.keyword": value}}]}}}
        if ioc_type: query_body["query"]["bool"]["must"].append({"term": {"type": ioc_type.value}})
        try:
            resp = es_writer.es_client.search(index="siem-iocs-*", body=query_body, size=100)
            iocs_found = []
            for hit in resp.get('hits', {}).get('hits', []):
                source_data = hit.get('_source', {});
                source_data['ioc_id'] = hit.get('_id')
                for dt_field_name in ['created_at_siem', 'updated_at_siem', 'first_seen', 'last_seen', '@timestamp',
                                      'timestamp']:
                    if dt_field_name in source_data and isinstance(source_data[dt_field_name], str):
                        try:
                            dt_val_str = source_data[dt_field_name].replace('Z', '+00:00')
                            if 'T' not in dt_val_str and len(dt_val_str) == 10:
                                parsed_dt = datetime.strptime(dt_val_str, '%Y-%m-%d');
                                source_data[
                                    dt_field_name] = datetime(parsed_dt.year, parsed_dt.month, parsed_dt.day,
                                                              tzinfo=timezone.utc)
                            else:
                                source_data[dt_field_name] = datetime.fromisoformat(dt_val_str)
                            if source_data[dt_field_name] and source_data[dt_field_name].tzinfo is None: source_data[
                                dt_field_name] = source_data[dt_field_name].replace(tzinfo=timezone.utc)
                        except ValueError:
                            source_data[dt_field_name] = None

                ioc_response_data = {"ioc_id": source_data.get('ioc_id'), "value": source_data.get('value'),
                                     "type": source_data.get('type'), "description": source_data.get('description'),
                                     "source_name": source_data.get('source_name'),
                                     "is_active": source_data.get('is_active', True),
                                     "confidence": source_data.get('confidence'), "tags": source_data.get('tags', []),
                                     "first_seen": source_data.get('first_seen'),
                                     "last_seen": source_data.get('last_seen'),
                                     "created_at": source_data.get('created_at_siem'),
                                     "updated_at": source_data.get('updated_at_siem'),
                                     "attributed_apt_group_ids": source_data.get('attributed_apt_group_ids', [])}
                try:
                    iocs_found.append(indicator_schemas.IoCResponse(**ioc_response_data))
                except ValidationError as e:
                    print(f"Error validating IoC from ES (find_ioc_by_value): {e}. Data: {ioc_response_data}")
            return iocs_found
        except es_exceptions.NotFoundError:
            print(f"Index pattern siem-iocs-* not found.");
            return []
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error searching IoCs in ES: {e}");
            return []
        except Exception as e_generic:
            print(f"Generic error searching IoCs: {e_generic}");
            return []

    def link_ioc_to_apt(self,
                        db: Session,
                        es_writer: ElasticsearchWriter,
                        ioc_es_id: str,
                        apt_group_id: int,
                        apt_service: 'APTGroupService'  # <--- ІН'ЄКЦІЯ СЕРВІСУ
                        ) -> Optional[indicator_schemas.IoCResponse]:
        apt_group = apt_service.get_apt_group_by_id(db, apt_group_id)  # Використовуємо переданий apt_service
        if not apt_group: raise ValueError(f"APT Group with ID {apt_group_id} not found.")

        if not es_writer or not es_writer.es_client: print("ES client not available."); return None
        es_client: Elasticsearch = es_writer.es_client
        try:
            # ... (логіка пошуку IoC та оновлення attributed_apt_group_ids з попереднього прикладу)
            search_query = {"query": {"ids": {"values": [ioc_es_id]}}}
            search_res = es_client.search(index="siem-iocs-*", body=search_query)
            if not search_res['hits']['hits']: print(f"IoC ES_ID '{ioc_es_id}' not found."); return None
            hit = search_res['hits']['hits'][0];
            target_index = hit['_index'];
            ioc_doc = hit['_source']

            update_script = {"script": {
                "source": "if (ctx._source.attributed_apt_group_ids == null) { ctx._source.attributed_apt_group_ids = new ArrayList(); } if (!ctx._source.attributed_apt_group_ids.contains(params.apt_id)) { ctx._source.attributed_apt_group_ids.add(params.apt_id); ctx._source.updated_at_siem = params.now; } else { ctx.op = 'noop'; }",
                "lang": "painless", "params": {"apt_id": apt_group_id, "now": datetime.now(timezone.utc).isoformat()}}}
            es_client.update(index=target_index, id=ioc_es_id, body=update_script, refresh=True)
            print(f"Successfully linked APT ID {apt_group_id} to IoC ES_ID {ioc_es_id}")

            updated_doc_source = es_client.get(index=target_index, id=ioc_es_id)['_source']
            updated_doc_source['ioc_id'] = ioc_es_id
            # ... (конвертація дат та створення IoCResponse) ...
            for dt_field_name in ['created_at_siem', 'updated_at_siem', 'first_seen', 'last_seen', '@timestamp',
                                  'timestamp']:
                if dt_field_name in updated_doc_source and isinstance(updated_doc_source[dt_field_name], str):
                    try:
                        dt_val_str = updated_doc_source[dt_field_name].replace('Z', '+00:00')
                        if 'T' not in dt_val_str and len(dt_val_str) == 10:
                            parsed_dt = datetime.strptime(dt_val_str, '%Y-%m-%d');
                            updated_doc_source[
                                dt_field_name] = datetime(parsed_dt.year, parsed_dt.month, parsed_dt.day,
                                                          tzinfo=timezone.utc)
                        else:
                            updated_doc_source[dt_field_name] = datetime.fromisoformat(dt_val_str)
                        if updated_doc_source[dt_field_name] and updated_doc_source[dt_field_name].tzinfo is None:
                            updated_doc_source[dt_field_name] = updated_doc_source[dt_field_name].replace(
                                tzinfo=timezone.utc)
                    except ValueError:
                        updated_doc_source[dt_field_name] = None
            if 'created_at_siem' in updated_doc_source: updated_doc_source['created_at'] = updated_doc_source.pop(
                'created_at_siem')
            if 'updated_at_siem' in updated_doc_source: updated_doc_source['updated_at'] = updated_doc_source.pop(
                'updated_at_siem')
            return indicator_schemas.IoCResponse(**updated_doc_source)
        except es_exceptions.NotFoundError:
            print(f"IoC ES_ID '{ioc_es_id}' not found (NotFoundError).");
            return None
        except es_exceptions.ElasticsearchWarning as e:
            print(f"ES error linking IoC {ioc_es_id} to APT {apt_group_id}: {e}");
            return None
        except Exception as e_gen:
            print(f"Generic error linking IoC {ioc_es_id} to APT {apt_group_id}: {e_gen}");
            return None

    def remove_apt_id_from_all_iocs(self, es_writer: ElasticsearchWriter, apt_group_id_to_remove: int) -> bool:
        # ... (код методу без змін, він не залежить від інших сервісів напряму) ...
        if not es_writer or not es_writer.es_client:
            print("Elasticsearch client not available. Cannot update IoCs.")
            return False
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
            if response.get('failures') and len(response['failures']) > 0:
                print(
                    f"WARNING: ES failures during update_by_query for APT ID {apt_group_id_to_remove}: {response['failures']}")
                return False
            return True
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error updating IoCs in ES to remove APT ID {apt_group_id_to_remove}: {e}")
            return False

    def get_iocs_by_apt_group_id(self, es_writer: ElasticsearchWriter, apt_group_id: int, skip: int = 0,
                                 limit: int = 100) -> List[indicator_schemas.IoCResponse]:
        # ... (код методу без змін, він не залежить від інших сервісів напряму) ...
        if not es_writer or not es_writer.es_client: print("ES client not available."); return []
        es_client: Elasticsearch = es_writer.es_client
        query_body = {"query": {"term": {"attributed_apt_group_ids": apt_group_id}}, "from": skip, "size": limit,
                      "sort": [{"updated_at_siem": {"order": "desc"}}, {"created_at_siem": {"order": "desc"}}]}
        try:
            resp = es_client.search(index="siem-iocs-*", body=query_body)
            iocs_found = []
            for hit in resp.get('hits', {}).get('hits', []):
                source_data = hit.get('_source', {});
                source_data['ioc_id'] = hit.get('_id')
                for dt_field_name in ['created_at_siem', 'updated_at_siem', 'first_seen', 'last_seen', '@timestamp',
                                      'timestamp']:
                    if dt_field_name in source_data and isinstance(source_data[dt_field_name], str):
                        try:
                            dt_val_str = source_data[dt_field_name].replace('Z', '+00:00')
                            if 'T' not in dt_val_str and len(dt_val_str) == 10:
                                parsed_dt = datetime.strptime(dt_val_str, '%Y-%m-%d');
                                source_data[
                                    dt_field_name] = datetime(parsed_dt.year, parsed_dt.month, parsed_dt.day,
                                                              tzinfo=timezone.utc)
                            else:
                                source_data[dt_field_name] = datetime.fromisoformat(dt_val_str)
                            if source_data[dt_field_name] and source_data[dt_field_name].tzinfo is None: source_data[
                                dt_field_name] = source_data[dt_field_name].replace(tzinfo=timezone.utc)
                        except ValueError:
                            source_data[dt_field_name] = None
                ioc_response_data = {"ioc_id": source_data.get('ioc_id'), "value": source_data.get('value'),
                                     "type": source_data.get('type'), "description": source_data.get('description'),
                                     "source_name": source_data.get('source_name'),
                                     "is_active": source_data.get('is_active', True),
                                     "confidence": source_data.get('confidence'), "tags": source_data.get('tags', []),
                                     "first_seen": source_data.get('first_seen'),
                                     "last_seen": source_data.get('last_seen'),
                                     "created_at": source_data.get('created_at_siem'),
                                     "updated_at": source_data.get('updated_at_siem'),
                                     "attributed_apt_group_ids": source_data.get('attributed_apt_group_ids', [])}
                try:
                    iocs_found.append(indicator_schemas.IoCResponse(**ioc_response_data))
                except ValidationError as e:
                    print(f"Error validating IoC for APT group (get_iocs_by_apt_id): {e}. Data: {ioc_response_data}")
            return iocs_found
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error getting IoCs for APT group {apt_group_id}: {e}");
            return []

    def _parse_ioc_hit_to_response(self, hit: Dict[str, Any]) -> Optional[indicator_schemas.IoCResponse]:
        """Допоміжна функція для конвертації 'hit' з Elasticsearch у IoCResponse."""
        source_data = hit.get('_source', {})
        source_data['ioc_id'] = hit.get('_id')

        for dt_field_name in ['created_at_siem', 'updated_at_siem', 'first_seen', 'last_seen', '@timestamp',
                              'timestamp']:
            if dt_field_name in source_data and isinstance(source_data[dt_field_name], str):
                try:
                    dt_val_str = source_data[dt_field_name].replace('Z', '+00:00')
                    if 'T' not in dt_val_str and len(dt_val_str) == 10:  # Тільки дата
                        parsed_dt = datetime.strptime(dt_val_str, '%Y-%m-%d')
                        source_data[dt_field_name] = datetime(parsed_dt.year, parsed_dt.month, parsed_dt.day,
                                                              tzinfo=timezone.utc)
                    else:  # Дата і час
                        source_data[dt_field_name] = datetime.fromisoformat(dt_val_str)

                    # Переконуємося, що є часова зона (встановлюємо UTC, якщо naive)
                    if source_data[dt_field_name] and source_data[dt_field_name].tzinfo is None:
                        source_data[dt_field_name] = source_data[dt_field_name].replace(tzinfo=timezone.utc)
                except ValueError:
                    print(
                        f"Warning: Could not parse datetime string '{source_data[dt_field_name]}' for field '{dt_field_name}' in IoC {source_data['ioc_id']}")
                    source_data[dt_field_name] = None

                    # Мапінг для IoCResponse
        ioc_response_data = {
            "ioc_id": source_data.get('ioc_id'), "value": source_data.get('value'),
            "type": source_data.get('type'), "description": source_data.get('description'),
            "source_name": source_data.get('source_name'), "is_active": source_data.get('is_active', True),
            "confidence": source_data.get('confidence'), "tags": source_data.get('tags', []),
            "first_seen": source_data.get('first_seen'), "last_seen": source_data.get('last_seen'),
            "created_at": source_data.get('created_at_siem'),  # Вже datetime після обробки вище
            "updated_at": source_data.get('updated_at_siem'),  # Вже datetime
            "attributed_apt_group_ids": source_data.get('attributed_apt_group_ids', [])
        }
        try:
            return indicator_schemas.IoCResponse(**ioc_response_data)
        except ValidationError as e:
            print(f"Error validating IoC from ES: {e}. Data: {ioc_response_data}")
            return None

    def get_all_iocs(self, es_writer: ElasticsearchWriter, skip: int = 0, limit: int = 100) -> List[
        indicator_schemas.IoCResponse]:
        """Отримує всі IoC з Elasticsearch з пагінацією."""
        if not es_writer or not es_writer.es_client:
            print("Elasticsearch client not available in get_all_iocs.")
            return []

        es_client: Elasticsearch = es_writer.es_client
        query_body = {
            "query": {"match_all": {}},
            "from": skip,
            "size": limit,
            "sort": [
                {"updated_at_siem": {"order": "desc", "unmapped_type": "date"}},
                {"created_at_siem": {"order": "desc", "unmapped_type": "date"}}
            ]
        }
        try:
            resp = es_client.search(index="siem-iocs-*", body=query_body)
            iocs_found = []
            for hit in resp.get('hits', {}).get('hits', []):
                ioc_resp = self._parse_ioc_hit_to_response(hit)
                if ioc_resp:
                    iocs_found.append(ioc_resp)
            return iocs_found
        except es_exceptions.NotFoundError:
            print(f"Index pattern siem-iocs-* not found when trying to get all IoCs.")
            return []
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error getting all IoCs from Elasticsearch: {e}")
            return []
        except Exception as e_generic:
            print(f"Generic error getting all IoCs: {e_generic}")
            return []

    def get_iocs_created_today(self, es_writer: ElasticsearchWriter, skip: int = 0, limit: int = 100) -> List[
        indicator_schemas.IoCResponse]:
        """Отримує IoC, створені (додані в SIEM) сьогодні, з Elasticsearch."""
        if not es_writer or not es_writer.es_client:
            print("Elasticsearch client not available in get_iocs_created_today.")
            return []

        es_client: Elasticsearch = es_writer.es_client

        today_utc = datetime.now(timezone.utc)
        start_of_day_utc = datetime(today_utc.year, today_utc.month, today_utc.day, 0, 0, 0, 0, tzinfo=timezone.utc)
        # Кінець дня - це початок наступного дня
        end_of_day_utc = start_of_day_utc + timedelta(days=1)

        query_body = {
            "query": {
                "range": {
                    "created_at_siem": {  # Поле, яке ми записуємо при створенні IoC в ES
                        "gte": start_of_day_utc.isoformat(),
                        "lt": end_of_day_utc.isoformat()  # lt (less than) початок наступного дня
                    }
                }
            },
            "from": skip,
            "size": limit,
            "sort": [{"created_at_siem": {"order": "desc"}}]
        }
        try:
            resp = es_client.search(index="siem-iocs-*", body=query_body)
            iocs_found = []
            for hit in resp.get('hits', {}).get('hits', []):
                ioc_resp = self._parse_ioc_hit_to_response(hit)
                if ioc_resp:
                    iocs_found.append(ioc_resp)
            return iocs_found
        except es_exceptions.NotFoundError:
            print(f"Index pattern siem-iocs-* not found when trying to get today's IoCs.")
            return []
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error getting today's IoCs from Elasticsearch: {e}")
            return []
        except Exception as e_generic:
            print(f"Generic error getting today's IoCs: {e_generic}")
            return []
