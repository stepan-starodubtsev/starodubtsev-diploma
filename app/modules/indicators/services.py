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

# Для type hinting та доступу до APTGroupService для отримання імен APT
if TYPE_CHECKING:
    from app.modules.apt_groups.services import APTGroupService
    from app.database.postgres_models.threat_actor_models import APTGroup  # Потрібен для type hint


class IndicatorService:
    def _prepare_ioc_document_for_es(
            self,
            db: Session,  # Додаємо db для доступу до APT імен через apt_service
            apt_service: 'APTGroupService',  # Додаємо apt_service
            ioc_data: Union[indicator_schemas.IoCCreate, indicator_schemas.IoCUpdate, Dict[str, Any]],
            existing_doc: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        current_time = datetime.now(timezone.utc)

        if isinstance(ioc_data, (indicator_schemas.IoCCreate, indicator_schemas.IoCUpdate)):
            # Використовуємо exclude_unset=True при оновленні, щоб не перезаписувати всі поля
            # Для IoCCreate exclude_unset не має великого значення, бо всі поля з IoCBase зазвичай присутні
            is_update = isinstance(ioc_data, indicator_schemas.IoCUpdate)
            doc_to_index = ioc_data.model_dump(exclude_unset=is_update)
        elif isinstance(ioc_data, dict):
            doc_to_index = ioc_data.copy()
        else:
            raise TypeError("ioc_data must be an IoC schema instance or a dict")

        # Перетворення Enum в рядок, якщо це ще не зроблено Pydantic (наприклад, якщо дані прийшли як dict з Enum об'єктами)
        if 'type' in doc_to_index and isinstance(doc_to_index['type'], enum.Enum):
            doc_to_index['type'] = doc_to_index['type'].value

        # Часові мітки SIEM
        if existing_doc and 'created_at_siem' in existing_doc:
            doc_to_index["created_at_siem"] = existing_doc['created_at_siem']
        elif 'created_at_siem' not in doc_to_index:
            doc_to_index["created_at_siem"] = current_time
        doc_to_index["updated_at_siem"] = current_time

        # @timestamp та 'timestamp' для ElasticsearchWriter
        ts_val_dt: Optional[datetime] = None
        # Пріоритет для last_seen, потім first_seen, потім поточний час
        for field_name_candidate in ['last_seen', 'first_seen']:
            val = doc_to_index.get(field_name_candidate)
            if isinstance(val, str):
                try:
                    val = datetime.fromisoformat(val.replace('Z', '+00:00'))
                except ValueError:
                    val = None  # Не вдалося розпарсити, ігноруємо
            if isinstance(val, datetime):
                ts_val_dt = val
                break
        if not ts_val_dt:
            ts_val_dt = current_time  # Фолбек на поточний час

        doc_to_index["@timestamp"] = ts_val_dt
        doc_to_index['timestamp'] = ts_val_dt  # datetime об'єкт для _generate_index_name

        # Обробка attributed_apt_group_ids та автоматичне додавання тегів APT
        apt_ids_to_process: List[int] = []
        raw_apt_ids = doc_to_index.get("attributed_apt_group_ids")

        if raw_apt_ids is not None:  # Якщо поле передано (навіть як порожній список)
            try:
                apt_ids_to_process = sorted(list(set(map(int, raw_apt_ids))))
            except (ValueError, TypeError):
                print(f"Warning: Could not parse attributed_apt_group_ids: {raw_apt_ids}. Setting to empty list.")
                apt_ids_to_process = []
        elif existing_doc and "attributed_apt_group_ids" in existing_doc:  # Для оновлення, якщо поле не передано
            apt_ids_to_process = existing_doc.get("attributed_apt_group_ids", [])
        # Для створення, якщо поле не передано, воно буде default_factory=list зі схеми IoCBase

        doc_to_index["attributed_apt_group_ids"] = apt_ids_to_process

        # Додавання тегів на основі APT
        # Починаємо з тегів, які вже є в ioc_data або existing_doc
        current_tags_set = set(doc_to_index.get("tags", []))
        if not isinstance(current_tags_set, set) or not all(isinstance(t, str) for t in current_tags_set):
            # Якщо 'tags' прийшли не як список рядків, ініціалізуємо порожнім set
            current_tags_set = set()
            if isinstance(doc_to_index.get("tags"), list):  # Якщо це список, спробуємо його використати
                current_tags_set.update(str(t) for t in doc_to_index.get("tags", []))

        if apt_ids_to_process:
            for apt_id in apt_ids_to_process:
                apt_group_db_obj: Optional['APTGroup'] = apt_service.get_apt_group_by_id(db,
                                                                                         apt_id)  # Використовуємо переданий сервіс
                if apt_group_db_obj:
                    # Формуємо тег. Робимо ім'я безпечним для тегу (заміна не-alphanum на "_").
                    safe_apt_name = "".join(c if c.isalnum() else '_' for c in apt_group_db_obj.name)
                    current_tags_set.add(f"apt:{safe_apt_name.lower()}")  # Додаємо тег у нижньому регістрі
                    current_tags_set.add(f"apt_id:{apt_group_db_obj.id}")  # Додаємо тег з ID

        doc_to_index["tags"] = sorted(list(current_tags_set))

        # Конвертуємо всі datetime в ISO рядки для фінального документа ES
        # і Enum в їх значення
        final_doc_for_es = {}
        for k, v in doc_to_index.items():
            if isinstance(v, datetime):
                final_doc_for_es[k] = v.isoformat()
            elif isinstance(v, enum.Enum):
                final_doc_for_es[k] = v.value
            elif k == 'timestamp':  # Пропускаємо наш внутрішній datetime 'timestamp'
                continue
            else:
                final_doc_for_es[k] = v

        # Переконуємося, що @timestamp є і в правильному форматі (вже має бути ISO з doc_to_index)
        if '@timestamp' in final_doc_for_es and isinstance(doc_to_index['@timestamp'], datetime):
            final_doc_for_es['@timestamp'] = doc_to_index['@timestamp'].isoformat()

        # Додаємо 'timestamp_dt' для ElasticsearchWriter, якщо він очікує datetime об'єкт
        # Це поле буде використано в _generate_index_name і не буде індексовано в ES, якщо не вказано в мапінгу.
        # Наш ElasticsearchWriter.write_event тепер достатньо розумний.
        # Він використовує event.timestamp або event.get('timestamp') або event.get('@timestamp')
        # і очікує, що це буде datetime.
        # У doc_to_index['timestamp'] у нас вже є потрібний datetime.
        # Ми передаємо весь doc_to_index (де дати ще datetime) в write_event,
        # а write_event робить model_dump(mode='json') або обробляє словник.
        # Давайте повернемо doc_to_index, де дати є datetime об'єктами,
        # а _prepare_ioc_document_for_es буде викликатися перед model_dump в add_ioc.

        # Повертаємо словник, де datetime ще є об'єктами, а Enum вже значеннями.
        # model_dump(mode='json') далі подбає про серіалізацію datetime.
        return doc_to_index

    def add_ioc(self, db: Session, es_writer: ElasticsearchWriter, ioc_create_data: indicator_schemas.IoCCreate,
                apt_service: 'APTGroupService') -> Optional[indicator_schemas.IoCResponse]:
        if not es_writer or not es_writer.es_client:
            print("ERROR: ElasticsearchWriter not available in add_ioc.")
            return None

        # Валідація APT IDs (можна залишити тут або перенести повністю в _prepare_ioc_document_for_es)
        valid_apt_ids = []
        if ioc_create_data.attributed_apt_group_ids:
            for apt_id in ioc_create_data.attributed_apt_group_ids:
                if not apt_service.get_apt_group_by_id(db, apt_id):
                    print(f"Warning: APT ID {apt_id} for IoC '{ioc_create_data.value}' not found. Skipping.")
                else:
                    valid_apt_ids.append(apt_id)
        ioc_create_data.attributed_apt_group_ids = valid_apt_ids

        # Готуємо документ, _prepare_ioc_document_for_es тепер також додає APT теги
        # Він повертає словник, де дати ще datetime
        ioc_doc_internal = self._prepare_ioc_document_for_es(db, apt_service, ioc_create_data)

        # Створюємо Pydantic модель з цього словника, щоб потім ElasticsearchWriter
        # міг викликати model_dump(mode='json') для правильної серіалізації,
        # включаючи datetime в ISO рядки та Enum в їх значення.
        # Нам потрібна тимчасова модель, яка включає всі поля, що йдуть в ES.
        # Або ми можемо передати ioc_doc_internal напряму в es_writer.write_event,
        # якщо він може обробити словник з datetime об'єктами.
        # Поточний ElasticsearchWriter.write_event приймає event: Any.
        # Якщо event - Pydantic модель, він робить model_dump(mode='json').
        # Якщо event - словник, він його використовує як є.
        # Тому нам потрібно, щоб ioc_doc_internal мав дати вже як рядки для прямої передачі в es_client.index.
        # Або ми створюємо "повний" Pydantic об'єкт для запису.

        # Давайте змінимо _prepare_ioc_document_for_es, щоб він повертав словник,
        # повністю готовий для es_client.index (дати як ISO рядки).
        # А timestamp для індексу буде передаватися окремо.

        # Повернемося до логіки, де _prepare_ioc_document_for_es повертає словник з рядковими датами,
        # а також зберігає datetime 'timestamp' під тимчасовим ключем.

        ioc_doc_prepared_for_es_payload = self._prepare_ioc_document_for_es(db, apt_service, ioc_create_data)
        timestamp_for_index_name = ioc_doc_prepared_for_es_payload.pop('_internal_dt_timestamp_for_index', datetime.now(
            timezone.utc))  # Витягуємо та видаляємо
        # Якщо раптом ключа немає, використовуємо поточний час (малоймовірно, якщо _prepare... працює)

        try:
            target_index = es_writer._generate_index_name("siem-iocs", timestamp_for_index_name)
            resp = es_writer.es_client.index(index=target_index, document=ioc_doc_prepared_for_es_payload)

            if resp.get('result') in ['created', 'updated']:
                ioc_es_id = resp.get('_id')
                # Для IoCResponse нам потрібні datetime об'єкти для created_at, updated_at.
                # ioc_doc_prepared_for_es_payload містить їх як рядки.
                # А ioc_create_data містить їх як datetime (якщо вони були).

                # Створюємо відповідь на основі ioc_create_data та даних з ES
                response_data_dict = ioc_create_data.model_dump()
                response_data_dict['ioc_id'] = ioc_es_id
                # created_at_siem та updated_at_siem є рядками в ioc_doc_prepared_for_es_payload
                response_data_dict['created_at'] = datetime.fromisoformat(
                    ioc_doc_prepared_for_es_payload["created_at_siem"])
                response_data_dict['updated_at'] = datetime.fromisoformat(
                    ioc_doc_prepared_for_es_payload["updated_at_siem"])
                # Теги в ioc_doc_prepared_for_es_payload вже оновлені
                response_data_dict['tags'] = ioc_doc_prepared_for_es_payload.get('tags', [])
                # attributed_apt_group_ids теж оновлені
                response_data_dict['attributed_apt_group_ids'] = ioc_doc_prepared_for_es_payload.get(
                    'attributed_apt_group_ids', [])

                return indicator_schemas.IoCResponse(**response_data_dict)
            else:
                print(f"Failed to index IoC (after prepare). Response: {resp}")
                return None
        except Exception as e:
            print(f"Error adding IoC (after prepare): {e}");
            import traceback;
            traceback.print_exc();
            return None

    def _convert_es_hit_to_ioc_response(self, hit: Dict[str, Any]) -> Optional[indicator_schemas.IoCResponse]:
        """Допоміжна функція для конвертації 'hit' з Elasticsearch у IoCResponse."""
        source_data = hit.get('_source', {})
        source_data['ioc_id'] = hit.get('_id')

        for dt_field_name in ['created_at_siem', 'updated_at_siem', 'first_seen', 'last_seen', '@timestamp',
                              'timestamp']:
            if dt_field_name in source_data and isinstance(source_data[dt_field_name], str):
                try:
                    dt_val_str = source_data[dt_field_name].replace('Z', '+00:00')
                    if 'T' not in dt_val_str and len(dt_val_str) == 10:
                        parsed_dt = datetime.strptime(dt_val_str, '%Y-%m-%d')
                        source_data[dt_field_name] = datetime(parsed_dt.year, parsed_dt.month, parsed_dt.day,
                                                              tzinfo=timezone.utc)
                    else:
                        source_data[dt_field_name] = datetime.fromisoformat(dt_val_str)
                    if source_data[dt_field_name] and source_data[dt_field_name].tzinfo is None:
                        source_data[dt_field_name] = source_data[dt_field_name].replace(tzinfo=timezone.utc)
                except ValueError:
                    source_data[dt_field_name] = None

        ioc_response_data = {
            "ioc_id": source_data.get('ioc_id'), "value": source_data.get('value'),
            "type": source_data.get('type'), "description": source_data.get('description'),
            "source_name": source_data.get('source_name'), "is_active": source_data.get('is_active', True),
            "confidence": source_data.get('confidence'), "tags": source_data.get('tags', []),
            "first_seen": source_data.get('first_seen'), "last_seen": source_data.get('last_seen'),
            "created_at": source_data.get('created_at_siem'),
            "updated_at": source_data.get('updated_at_siem'),
            "attributed_apt_group_ids": source_data.get('attributed_apt_group_ids', [])
        }
        try:
            return indicator_schemas.IoCResponse(**ioc_response_data)
        except ValidationError as e:
            print(f"Error validating IoC from ES for IoCResponse: {e}. Data: {ioc_response_data}")
            return None

    def add_ioc(self, db: Session, es_writer: ElasticsearchWriter, ioc_create_data: indicator_schemas.IoCCreate,
                apt_service: 'APTGroupService') -> Optional[indicator_schemas.IoCResponse]:
        """Додає новий IoC в Elasticsearch. Раніше називався add_manual_ioc."""
        if not es_writer or not es_writer.es_client:
            print("ERROR: ElasticsearchWriter not available in add_ioc.")
            return None

        valid_apt_ids = []
        if ioc_create_data.attributed_apt_group_ids:
            for apt_id in ioc_create_data.attributed_apt_group_ids:
                if not apt_service.get_apt_group_by_id(db, apt_id):
                    print(f"Warning: APT ID {apt_id} for IoC '{ioc_create_data.value}' not found. Skipping.")
                else:
                    valid_apt_ids.append(apt_id)
        ioc_create_data.attributed_apt_group_ids = valid_apt_ids  # Оновлюємо тільки валідними

        ioc_doc_prepared = self._prepare_ioc_document_for_es(ioc_create_data)

        try:
            # timestamp для _generate_index_name має бути datetime
            timestamp_for_index_name = ioc_doc_prepared.get('timestamp')
            if not isinstance(timestamp_for_index_name, datetime):  # Перевірка, якщо раптом не datetime
                timestamp_for_index_name = datetime.fromisoformat(str(timestamp_for_index_name)) if isinstance(
                    timestamp_for_index_name, str) else datetime.now(timezone.utc)

            target_index = es_writer._generate_index_name("siem-iocs",
                                                          timestamp_for_index_name)  # Використовуємо datetime

            # Готуємо документ для ES: всі datetime мають бути ISO рядками, Enum - значеннями
            doc_payload_for_es = {}
            for k, v in ioc_doc_prepared.items():
                if isinstance(v, datetime):
                    doc_payload_for_es[k] = v.isoformat()
                elif isinstance(v, enum.Enum):
                    doc_payload_for_es[k] = v.value
                elif k == 'timestamp' and isinstance(v, datetime):  # Пропускаємо наш тимчасовий datetime 'timestamp'
                    continue  # Він вже використаний для @timestamp та імені індексу
                else:
                    doc_payload_for_es[k] = v
            # Переконуємося, що @timestamp є і в правильному форматі
            if '@timestamp' not in doc_payload_for_es or not isinstance(doc_payload_for_es.get('@timestamp'), str):
                doc_payload_for_es['@timestamp'] = timestamp_for_index_name.isoformat()

            resp = es_writer.es_client.index(index=target_index, document=doc_payload_for_es)
            if resp.get('result') in ['created', 'updated']:
                ioc_es_id = resp.get('_id')
                # Створюємо відповідь, використовуючи дані, які ми підготували для ES, та ID
                # Конвертуємо рядкові дати назад в datetime для Pydantic схеми IoCResponse
                response_data_dict = ioc_doc_prepared.copy()  # Починаємо з підготовлених даних
                response_data_dict['ioc_id'] = ioc_es_id
                response_data_dict['created_at'] = datetime.fromisoformat(ioc_doc_prepared["created_at_siem"])
                response_data_dict['updated_at'] = datetime.fromisoformat(ioc_doc_prepared["updated_at_siem"])
                # first_seen, last_seen в ioc_create_data вже datetime
                response_data_dict['first_seen'] = ioc_create_data.first_seen
                response_data_dict['last_seen'] = ioc_create_data.last_seen
                response_data_dict['type'] = ioc_create_data.type  # Повертаємо Enum об'єкт

                return indicator_schemas.IoCResponse(**response_data_dict)
            else:
                print(f"Failed to index IoC. Response: {resp}")
                return None
        except Exception as e:
            print(f"Error adding IoC: {e}");
            import traceback;
            traceback.print_exc();
            return None

    def get_ioc_by_es_id(self, es_writer: ElasticsearchWriter, ioc_elasticsearch_id: str) -> Optional[
        indicator_schemas.IoCResponse]:
        """Отримує IoC з Elasticsearch за його _id."""
        if not es_writer or not es_writer.es_client: return None
        es_client: Elasticsearch = es_writer.es_client
        try:
            # Потрібно знати індекс, або шукати по всіх siem-iocs-*
            # Для GET /index/_doc/id потрібен точний індекс.
            # Якщо індекс невідомий, краще використовувати search.
            search_query = {"query": {"ids": {"values": [ioc_elasticsearch_id]}}}
            res = es_client.search(index="siem-iocs-*", body=search_query)
            if res['hits']['total']['value'] > 0:
                hit = res['hits']['hits'][0]
                return self._parse_ioc_hit_to_response(hit)
            return None
        except es_exceptions.NotFoundError:
            return None
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error getting IoC by ES ID '{ioc_elasticsearch_id}': {e}")
            return None

    def update_ioc(self, db: Session, es_writer: ElasticsearchWriter, ioc_elasticsearch_id: str,
                   ioc_update_data: indicator_schemas.IoCUpdate, apt_service: 'APTGroupService') -> Optional[
        indicator_schemas.IoCResponse]:
        """Оновлює існуючий IoC в Elasticsearch."""
        if not es_writer or not es_writer.es_client: return None
        es_client: Elasticsearch = es_writer.es_client

        # 1. Отримати поточний документ, щоб знати індекс та для часткового оновлення
        current_ioc_response = self.get_ioc_by_es_id(es_writer, ioc_elasticsearch_id)
        if not current_ioc_response:
            return None  # IoC не знайдено

        # Знаходимо індекс документа (потрібно, щоб update був націлений на правильний індекс)
        # Це може бути не найнадійніший спосіб, якщо ioc_id не глобально унікальний поза індексом.
        # Але для _id з ES він унікальний в межах індексу.
        # Якщо індекси щоденні, то 'timestamp' з поточного документа визначить індекс.
        target_index = es_writer._generate_index_name("siem-iocs",
                                                      current_ioc_response.created_at)  # Або updated_at, або timestamp
        # Краще використовувати той timestamp, що визначав індекс при створенні

        # Валідація APT IDs, якщо вони передані
        if ioc_update_data.attributed_apt_group_ids is not None:  # Якщо поле є в запиті (навіть якщо порожній список)
            valid_apt_ids = []
            for apt_id in ioc_update_data.attributed_apt_group_ids:
                if not apt_service.get_apt_group_by_id(db, apt_id):
                    print(f"Warning: APT ID {apt_id} for IoC update not found. Skipping.")
                else:
                    valid_apt_ids.append(apt_id)
            ioc_update_data.attributed_apt_group_ids = valid_apt_ids

        # Готуємо документ для оновлення, беручи до уваги існуючі дані
        # _prepare_ioc_document_for_es може бути використаний, але йому потрібен 'existing_doc' у вигляді dict
        current_doc_dict = current_ioc_response.model_dump()  # Pydantic V2
        ioc_doc_prepared = self._prepare_ioc_document_for_es(ioc_update_data, existing_doc=current_doc_dict)

        try:
            doc_payload_for_es = {  # Готуємо фінальний словник для ES
                k: v.isoformat() if isinstance(v, datetime) else (v.value if isinstance(v, enum.Enum) else v)
                for k, v in ioc_doc_prepared.items()
                if k != 'timestamp'  # Виключаємо тимчасовий datetime timestamp
            }
            if '@timestamp' not in doc_payload_for_es and 'timestamp' in ioc_doc_prepared:  # Переконуємося, що @timestamp є
                doc_payload_for_es['@timestamp'] = ioc_doc_prepared['timestamp'].isoformat()

            # Використовуємо 'update' API Elasticsearch для часткового оновлення
            # або 'index' API для повного перезапису документа
            # 'index' простіше, якщо ми передаємо весь оновлений документ
            resp = es_client.index(index=target_index, id=ioc_elasticsearch_id, document=doc_payload_for_es)

            if resp.get('result') == 'updated' or resp.get('result') == 'created':  # index може створити, якщо ID немає
                # Повертаємо оновлений документ, знову його завантаживши або збудувавши з ioc_doc_prepared
                updated_ioc = self.get_ioc_by_es_id(es_writer, ioc_elasticsearch_id)
                return updated_ioc
            else:
                print(f"Failed to update IoC {ioc_elasticsearch_id}. Response: {resp}")
                return None
        except es_exceptions.NotFoundError:
            print(f"IoC {ioc_elasticsearch_id} not found in index {target_index} for update.")
            return None
        except Exception as e:
            print(f"Error updating IoC {ioc_elasticsearch_id}: {e}")
            return None

    def delete_ioc(self, es_writer: ElasticsearchWriter, ioc_elasticsearch_id: str) -> bool:
        """Видаляє IoC з Elasticsearch за його _id."""
        if not es_writer or not es_writer.es_client: return False
        es_client: Elasticsearch = es_writer.es_client
        try:
            # Потрібно знайти індекс, де знаходиться документ, перед видаленням
            search_query = {"query": {"ids": {"values": [ioc_elasticsearch_id]}}}
            res = es_client.search(index="siem-iocs-*", body=search_query, size=1)
            if not res['hits']['hits']:
                print(f"IoC with Elasticsearch ID '{ioc_elasticsearch_id}' not found for deletion.")
                return False  # Або True, якщо "вже видалено" вважається успіхом

            target_index = res['hits']['hits'][0]['_index']

            resp = es_client.delete(index=target_index, id=ioc_elasticsearch_id)
            if resp.get('result') == 'deleted':
                print(f"IoC {ioc_elasticsearch_id} successfully deleted from index {target_index}.")
                return True
            elif resp.get('result') == 'not_found':  # Якщо раптом видалили між search та delete
                print(
                    f"IoC {ioc_elasticsearch_id} was already not found in index {target_index} during delete attempt.")
                return True  # Вважаємо успіхом
            else:
                print(f"Failed to delete IoC {ioc_elasticsearch_id}. Response: {resp}")
                return False
        except es_exceptions.NotFoundError:  # Може бути кинуто delete, якщо ID не знайдено в конкретному індексі
            print(f"IoC {ioc_elasticsearch_id} not found for deletion (NotFoundError).")
            return True  # Якщо не знайдено, мета (видалити) досягнута
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error deleting IoC {ioc_elasticsearch_id}: {e}")
            return False

    def add_ioc(self,
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
