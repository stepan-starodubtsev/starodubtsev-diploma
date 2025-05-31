# app/modules/ioc_management/services.py
import enum
import json
import os
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union

from elasticsearch import exceptions as es_exceptions, Elasticsearch
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database.postgres_models.ioc_source_models import IoCSource
from app.database.postgres_models.threat_actor_models import APTGroup
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from . import schemas

# Шлях до JSON файлу з даними
# Визначаємо шлях відносно поточного файлу services.py
# services.py -> ioc_management -> modules -> app -> корінь_проєкту -> data/apt_iocs_data.json
# Поточний файл: E:\Progects\diploma\app\modules\ioc_management\services.py
# Корінь проєкту: E:\Progects\diploma\
# Потрібно: E:\Progects\diploma\data\apt_iocs_data.json
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# APP_MODULES_DIR = os.path.dirname(CURRENT_DIR) # /app/modules
# APP_DIR = os.path.dirname(APP_MODULES_DIR) # /app
# PROJECT_ROOT_DIR = os.path.dirname(APP_DIR) # /
PROJECT_ROOT_DIR = os.path.join(CURRENT_DIR, "..", "..", "..")  # Простіший спосіб вийти на 3 рівні вгору до кореня
MOCK_DATA_FILE_PATH = os.path.join(PROJECT_ROOT_DIR, "data", "apt_iocs_data.json")


class IoCManagementService:
    # --- CRUD для IoCSource (без змін) ---
    # ... (методи create_ioc_source, get_ioc_source_by_id, get_all_ioc_sources, update_ioc_source, delete_ioc_source)
    def create_ioc_source(self, db: Session, source_create: schemas.IoCSourceCreate) -> IoCSource:  # ...
        existing_source = db.query(IoCSource).filter(IoCSource.name == source_create.name).first()
        if existing_source: raise ValueError(f"IoC Source with name '{source_create.name}' already exists.")
        db_source = IoCSource(name=source_create.name, type=source_create.type,
                              url=str(source_create.url) if source_create.url else None,
                              description=source_create.description, is_enabled=source_create.is_enabled)
        db.add(db_source)
        db.commit()
        db.refresh(db_source)
        return db_source

    def get_ioc_source_by_id(self, db: Session, source_id: int) -> Optional[IoCSource]:  # ...
        return db.query(IoCSource).filter(IoCSource.id == source_id).first()

    def get_all_ioc_sources(self, db: Session, skip: int = 0, limit: int = 100) -> List[IoCSource]:  # ...
        return db.query(IoCSource).order_by(IoCSource.id).offset(skip).limit(limit).all()

    def update_ioc_source(self, db: Session, source_id: int, source_update: schemas.IoCSourceUpdate) -> Optional[
        IoCSource]:  # ...
        db_source = self.get_ioc_source_by_id(db, source_id)
        if not db_source: return None
        update_data = source_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "url" and value is not None:
                setattr(db_source, key, str(value))
            elif key == "type" and value is not None:
                setattr(db_source, key, schemas.IoCSourceTypeEnum(value))
            else:
                setattr(db_source, key, value)
        db.add(db_source)
        db.commit()
        db.refresh(db_source)
        return db_source

    def delete_ioc_source(self, db: Session, source_id: int) -> bool:  # ...
        db_source = self.get_ioc_source_by_id(db, source_id)
        if db_source: db.delete(db_source); db.commit(); return True
        return False

    # --- CRUD для APTGroup (без змін) ---
    # ... (методи create_apt_group, get_apt_group_by_id, get_all_apt_groups, update_apt_group)
    def create_apt_group(self, db: Session, apt_group_create: schemas.APTGroupCreate) -> APTGroup:  # ...
        existing_group = db.query(APTGroup).filter(APTGroup.name == apt_group_create.name).first()
        if existing_group: raise ValueError(f"APT Group with name '{apt_group_create.name}' already exists.")
        references_str = [str(url) for url in apt_group_create.references] if apt_group_create.references else []
        db_apt_group = APTGroup(name=apt_group_create.name, aliases=apt_group_create.aliases or [],
                                description=apt_group_create.description,
                                sophistication=apt_group_create.sophistication,
                                primary_motivation=apt_group_create.primary_motivation,
                                target_sectors=apt_group_create.target_sectors or [],
                                country_of_origin=apt_group_create.country_of_origin,
                                first_observed=apt_group_create.first_observed,
                                last_observed=apt_group_create.last_observed, references=references_str)
        db.add(db_apt_group)
        db.commit()
        db.refresh(db_apt_group)
        return db_apt_group

    def get_apt_group_by_id(self, db: Session, apt_group_id: int) -> Optional[APTGroup]:  # ...
        return db.query(APTGroup).filter(APTGroup.id == apt_group_id).first()

    def get_all_apt_groups(self, db: Session, skip: int = 0, limit: int = 100) -> List[APTGroup]:  # ...
        return db.query(APTGroup).order_by(APTGroup.name).offset(skip).limit(limit).all()

    def update_apt_group(self, db: Session, apt_group_id: int, apt_group_update: schemas.APTGroupUpdate) -> Optional[
        APTGroup]:  # ...
        db_apt_group = self.get_apt_group_by_id(db, apt_group_id)
        if not db_apt_group: return None
        update_data = apt_group_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "references" and value is not None:
                setattr(db_apt_group, key, [str(url) for url in value])
            elif (key == "aliases" or key == "target_sectors") and value is None:
                setattr(db_apt_group, key, [])
            else:
                setattr(db_apt_group, key, value)
        db.add(db_apt_group)
        db.commit()
        db.refresh(db_apt_group)
        return db_apt_group

    def _load_mock_data_from_file(self) -> List[Dict[str, Any]]:
        # ... (без змін) ...
        try:
            if not os.path.exists(MOCK_DATA_FILE_PATH):
                print(f"ERROR: Mock data file not found at {MOCK_DATA_FILE_PATH}")
                print(f"DEBUG: Current working directory: {os.getcwd()}")
                # Для перевірки, чи правильно розраховано шлях до кореня:
                # script_dir = os.path.dirname(os.path.abspath(__file__))
                # project_root_check = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
                # print(f"DEBUG: Calculated project root for MOCK_DATA_FILE_PATH: {project_root_check}")
                return []
            with open(MOCK_DATA_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except FileNotFoundError:
            print(f"ERROR: Mock data file not found at {MOCK_DATA_FILE_PATH}")
            return []
        except json.JSONDecodeError as e:
            print(f"ERROR: Could not decode JSON from {MOCK_DATA_FILE_PATH}: {e}")
            return []
        except Exception as e:
            print(f"ERROR: An unexpected error occurred while loading mock data: {e}")
            return []

    def get_ioc_source_by_name(self, db: Session, name: str) -> Optional[IoCSource]:  # Переконайся, що цей метод є
        return db.query(IoCSource).filter(IoCSource.name == name).first()

    def get_apt_group_by_name(self, db: Session, name: str) -> Optional[APTGroup]:
        """
        Отримує APT-угруповання з бази даних за його точною назвою.
        """
        return db.query(APTGroup).filter(APTGroup.name == name).first()

    def _ensure_apt_groups_exist(self, db: Session, apt_data_list: List[Dict[str, Any]]) -> Dict[str, int]:
        # ... (без змін, але переконайся, що HttpUrl обробляються коректно) ...
        apt_id_map: Dict[str, int] = {}
        for apt_entry in apt_data_list:
            name = apt_entry.get("name")
            if not name: continue
            db_apt = self.get_apt_group_by_name(db, name)
            if not db_apt:
                try:
                    references_pydantic = [schemas.HttpUrl(str(url)) for url in apt_entry.get("references", []) if url]
                    apt_create_schema = schemas.APTGroupCreate(
                        name=name, aliases=apt_entry.get("aliases", []), description=apt_entry.get("description"),
                        sophistication=schemas.APTGroupSophisticationEnum(
                            apt_entry.get("sophistication", "unknown").lower()) if apt_entry.get(
                            "sophistication") else schemas.APTGroupSophisticationEnum.UNKNOWN,
                        primary_motivation=schemas.APTGroupMotivationsEnum(
                            apt_entry.get("primary_motivation", "unknown").lower()) if apt_entry.get(
                            "primary_motivation") else schemas.APTGroupMotivationsEnum.UNKNOWN,
                        target_sectors=apt_entry.get("target_sectors", []),
                        country_of_origin=apt_entry.get("country_of_origin"),
                        first_observed=datetime.fromisoformat(apt_entry["first_observed"]) if apt_entry.get(
                            "first_observed") else None,
                        last_observed=datetime.fromisoformat(apt_entry["last_observed"]) if apt_entry.get(
                            "last_observed") else None,
                        references=references_pydantic)
                    db_apt = self.create_apt_group(db, apt_create_schema)
                    print(f"Created APT Group: '{db_apt.name}' with ID {db_apt.id}")
                except (ValidationError, ValueError) as e:
                    print(f"Error creating/validating APT '{name}': {e}")
                    continue
            if db_apt: apt_id_map[apt_entry.get("apt_id_placeholder", name)] = db_apt.id
        return apt_id_map

    def _generate_iocs_from_mock_data(self, db: Session, ioc_source: IoCSource) -> List[schemas.IoCCreate]:
        """
        Завантажує дані з JSON, створює/перевіряє APT, та генерує IoC,
        фільтруючи або адаптуючи їх на основі типу джерела `ioc_source`.
        """
        all_apt_data = self._load_mock_data_from_file()
        if not all_apt_data: return []

        apt_id_map = self._ensure_apt_groups_exist(db, all_apt_data)
        generated_iocs: List[schemas.IoCCreate] = []
        current_time = datetime.now(timezone.utc)

        # Фільтруємо APT дані або IoC на основі типу джерела (ioc_source.type)
        # Це дуже спрощена логіка мокінгу.
        # Наприклад, "MISP" джерело може "бачити" тільки APT28 та Gamaredon,
        # "OPENCTI" - Sandworm та Turla, а "INTERNAL" - свої специфічні.

        source_specific_apt_names_map = {
            schemas.IoCSourceTypeEnum.MISP: ["APT28", "Gamaredon"],
            schemas.IoCSourceTypeEnum.OPENCTI: ["Sandworm", "Turla"],
            schemas.IoCSourceTypeEnum.INTERNAL: [],  # Для INTERNAL IoC можуть додаватися вручну або мати іншу логіку
            schemas.IoCSourceTypeEnum.STIX_FEED: ["UAC-0056"],  # Приклад
            schemas.IoCSourceTypeEnum.CSV_URL: ["APT28"]  # Приклад
        }

        relevant_apt_names = source_specific_apt_names_map.get(ioc_source.type,
                                                               [apt.get("name") for apt in all_apt_data])
        if ioc_source.type == schemas.IoCSourceTypeEnum.INTERNAL:  # Для INTERNAL не генеруємо з файлу автоматично
            print(f"Source '{ioc_source.name}' is INTERNAL, no IoCs will be auto-generated from mock file.")
            return []

        for apt_entry in all_apt_data:
            apt_name_from_file = apt_entry.get("name")
            if apt_name_from_file not in relevant_apt_names:
                continue  # Пропускаємо APT, якщо воно не релевантне для цього типу джерела

            apt_placeholder = apt_entry.get("apt_id_placeholder", apt_name_from_file)
            apt_db_id = apt_id_map.get(apt_placeholder)  # Реальний ID APT з БД

            for ioc_json in apt_entry.get("iocs", []):
                try:
                    # Конвертуємо рядковий тип IoC з JSON в наш Enum
                    # Додаємо .lower().replace("_", "-") для більшої гнучкості з форматом типів у JSON
                    ioc_type_str = ioc_json.get("type", "").lower().replace("_", "-")
                    ioc_type_enum = schemas.IoCTypeEnum(ioc_type_str)

                    ioc_create_data = {
                        "value": ioc_json.get("value"), "type": ioc_type_enum,
                        "description": ioc_json.get("description"), "source_name": ioc_source.name,
                        "is_active": ioc_json.get("is_active", True), "confidence": ioc_json.get("confidence"),
                        "tags": ioc_json.get("tags", []),
                        "first_seen": current_time, "last_seen": current_time,
                        "attributed_apt_group_ids": [apt_db_id] if apt_db_id else []
                    }
                    ioc_create_data_cleaned = {k: v for k, v in ioc_create_data.items() if v is not None}
                    generated_iocs.append(schemas.IoCCreate(**ioc_create_data_cleaned))
                except ValueError as e:
                    print(
                        f"Skipping IoC due to ValueError (e.g. invalid IoCType '{ioc_json.get('type')}'): {e}. IoC data: {ioc_json}")
                except ValidationError as e_pydantic:
                    print(f"Skipping IoC due to Pydantic ValidationError: {e_pydantic}. IoC data: {ioc_json}")

        print(
            f"Generated {len(generated_iocs)} IoCs from mock data file for source '{ioc_source.name}' (type: {ioc_source.type.value}).")
        return generated_iocs

    # --- fetch_and_store_iocs_from_source, add_manual_ioc, find_ioc_by_value, 
    #     link_ioc_to_apt, delete_apt_group, get_iocs_for_apt_group -
    #     використовують _ensure_apt_groups_exist та _prepare_ioc_document_for_es
    #     і залишаються функціонально такими ж, як у попередньому повному прикладі,
    #     але тепер _generate_iocs_from_mock_data викликається з db та ioc_source.

    def fetch_and_store_iocs_from_source(self, db: Session, source_id: int, es_writer: ElasticsearchWriter) -> Dict[
        str, Any]:
        # ... (Код з попереднього прикладу, але _generate_mock_iocs тепер _generate_iocs_from_mock_data(db, ioc_source)) ...
        ioc_source = self.get_ioc_source_by_id(db, source_id)
        if not ioc_source or not ioc_source.is_enabled:
            message = f"IoC Source with ID {source_id} not found or not enabled."
            return {"status": "error", "message": message, "added_iocs": 0, "failed_iocs": 0}

        print(f"Fetching IoCs for source: {ioc_source.name} (Type: {ioc_source.type.value}) using mock data file...")
        iocs_to_create: List[schemas.IoCCreate] = self._generate_iocs_from_mock_data(db, ioc_source)  # <--- Змінено тут

        if not iocs_to_create:
            print(f"No IoCs generated for source '{ioc_source.name}' from mock data file.")
            ioc_source.last_fetched = datetime.now(timezone.utc)
            db.add(ioc_source)
            db.commit()
            return {"status": "success", "message": "No new IoCs found/generated.", "added_iocs": 0, "failed_iocs": 0}

        added_count = 0
        failed_count = 0
        if not es_writer:
            return {"status": "error", "message": "Elasticsearch writer not configured.", "added_iocs": 0,
                    "failed_iocs": len(iocs_to_create)}

        for ioc_data_create_schema in iocs_to_create:
            ioc_doc_to_index = self._prepare_ioc_document_for_es(
                ioc_data_create_schema)  # _prepare_ioc_document_for_es з попереднього прикладу
            if es_writer.write_event(ioc_doc_to_index, index_prefix="siem-iocs"):
                added_count += 1
            else:
                failed_count += 1

        if ioc_source:
            ioc_source.last_fetched = datetime.now(timezone.utc)
            db.add(ioc_source)
            db.commit()
        message = f"Fetched from '{ioc_source.name}'. Added IoCs: {added_count}. Failed: {failed_count}."
        return {"status": "success", "message": message, "added_iocs": added_count, "failed_iocs": failed_count}

    def _prepare_ioc_document_for_es(self, ioc_data: Union[schemas.IoCCreate, schemas.IoCUpdate, Dict[str, Any]],
                                     existing_doc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # ... (Код з попереднього прикладу) ...
        current_time = datetime.now(timezone.utc)
        if isinstance(ioc_data, (schemas.IoCCreate, schemas.IoCUpdate)):
            doc_to_index = ioc_data.model_dump(exclude_unset=True, mode='json')
        elif isinstance(ioc_data, dict):
            doc_to_index = ioc_data.copy()
        else:
            raise TypeError("ioc_data must be an IoC schema instance or a dict")
        if existing_doc and 'created_at_siem' in existing_doc:
            doc_to_index["created_at_siem"] = existing_doc['created_at_siem']
        else:
            doc_to_index["created_at_siem"] = current_time.isoformat()
        doc_to_index["updated_at_siem"] = current_time.isoformat()
        ts_val_dt: Optional[datetime] = None
        val_last_seen = doc_to_index.get('last_seen')
        val_first_seen = doc_to_index.get('first_seen')
        if val_last_seen:
            ts_val_dt = datetime.fromisoformat(val_last_seen) if isinstance(val_last_seen, str) else val_last_seen
        elif val_first_seen:
            ts_val_dt = datetime.fromisoformat(val_first_seen) if isinstance(val_first_seen, str) else val_first_seen
        else:
            ts_val_dt = current_time
        doc_to_index["@timestamp"] = ts_val_dt.isoformat() if isinstance(ts_val_dt,
                                                                         datetime) else current_time.isoformat()
        doc_to_index['timestamp'] = ts_val_dt  # datetime об'єкт
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
        if 'type' in doc_to_index and isinstance(doc_to_index['type'], enum.Enum): doc_to_index['type'] = doc_to_index[
            'type'].value
        return doc_to_index

    def add_manual_ioc(self, db: Session, es_writer: ElasticsearchWriter, ioc_create_data: schemas.IoCCreate) -> \
            Optional[schemas.IoCResponse]:
        # ... (Код з попереднього прикладу, з валідацією APT ID та _prepare_ioc_document_for_es) ...
        if not es_writer or not es_writer.es_client: return None
        valid_apt_ids = []
        if ioc_create_data.attributed_apt_group_ids:
            for apt_id in ioc_create_data.attributed_apt_group_ids:
                if not self.get_apt_group_by_id(db, apt_id):
                    print(f"Warning: APT ID {apt_id} for IoC '{ioc_create_data.value}' not found. Skipping.")
                else:
                    valid_apt_ids.append(apt_id)
        ioc_create_data.attributed_apt_group_ids = valid_apt_ids
        ioc_doc_prepared = self._prepare_ioc_document_for_es(ioc_create_data)
        try:
            target_index = es_writer._generate_index_name("siem-iocs",
                                                          ioc_doc_prepared['timestamp'])  # timestamp має бути datetime
            doc_payload_for_es = {
                k: v.isoformat() if isinstance(v, datetime) else (v.value if isinstance(v, enum.Enum) else v) for k, v
                in ioc_doc_prepared.items() if k != 'timestamp'}
            doc_payload_for_es['@timestamp'] = ioc_doc_prepared['timestamp'].isoformat()
            resp = es_writer.es_client.index(index=target_index, document=doc_payload_for_es)
            if resp.get('result') in ['created', 'updated']:
                ioc_es_id = resp.get('_id')
                # Створюємо відповідь, конвертуючи рядкові дати з ioc_doc_prepared (де вони вже можуть бути рядками)
                response_data = ioc_create_data.model_dump()
                response_data['ioc_id'] = ioc_es_id
                response_data['created_at'] = datetime.fromisoformat(ioc_doc_prepared["created_at_siem"])
                response_data['updated_at'] = datetime.fromisoformat(ioc_doc_prepared["updated_at_siem"])
                return schemas.IoCResponse(**response_data)
            else:
                print(f"Failed to index manual IoC (direct call). Response: {resp}")
                return None
        except Exception as e:
            print(f"Error adding manual IoC: {e}")
            return None

    def find_ioc_by_value(self, es_writer: ElasticsearchWriter, value: str,
                          ioc_type: Optional[schemas.IoCTypeEnum] = None) -> List[schemas.IoCResponse]:
        # ... (Код з попереднього прикладу) ...
        if not es_writer or not es_writer.es_client: return []
        query_body: Dict[str, Any] = {"query": {"bool": {"must": [{"term": {"value.keyword": value}}]}}}
        if ioc_type: query_body["query"]["bool"]["must"].append({"term": {"type": ioc_type.value}})
        try:
            resp = es_writer.es_client.search(index="siem-iocs-*", body=query_body, size=100)
            iocs_found = []
            for hit in resp.get('hits', {}).get('hits', []):
                source_data = hit.get('_source', {})
                source_data['ioc_id'] = hit.get('_id')
                for dt_field_name in ['created_at_siem', 'updated_at_siem', 'first_seen', 'last_seen', '@timestamp',
                                      'timestamp']:
                    if dt_field_name in source_data and isinstance(source_data[dt_field_name], str):
                        try:
                            dt_val_str = source_data[dt_field_name].replace('Z', '+00:00')
                            if 'T' not in dt_val_str and len(dt_val_str) == 10:
                                parsed_dt = datetime.strptime(dt_val_str, '%Y-%m-%d')
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
                    iocs_found.append(schemas.IoCResponse(**ioc_response_data))
                except ValidationError as e:
                    print(f"Error validating IoC from ES (find_ioc_by_value): {e}. Data: {ioc_response_data}")
            return iocs_found
        except es_exceptions.NotFoundError:
            print(f"Index pattern siem-iocs-* not found.")
            return []
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error searching IoCs in ES: {e}")
            return []
        except Exception as e_generic:
            print(f"Generic error searching IoCs: {e_generic}")
            return []

    def link_ioc_to_apt(self, db: Session, es_writer: ElasticsearchWriter, ioc_es_id: str, apt_group_id: int) -> \
            Optional[schemas.IoCResponse]:
        # ... (Код з попереднього прикладу) ...
        apt_group = self.get_apt_group_by_id(db, apt_group_id)
        if not apt_group: raise ValueError(f"APT Group with ID {apt_group_id} not found.")
        if not es_writer or not es_writer.es_client: print("ES client not available."); return None
        es_client: Elasticsearch = es_writer.es_client
        try:
            search_query = {"query": {"ids": {"values": [ioc_es_id]}}}
            search_res = es_client.search(index="siem-iocs-*", body=search_query)
            if not search_res['hits']['hits']: print(f"IoC ES_ID '{ioc_es_id}' not found."); return None
            hit = search_res['hits']['hits'][0]
            target_index = hit['_index']
            update_script = {"script": {
                "source": "if (ctx._source.attributed_apt_group_ids == null) { ctx._source.attributed_apt_group_ids = new ArrayList() } if (!ctx._source.attributed_apt_group_ids.contains(params.apt_id)) { ctx._source.attributed_apt_group_ids.add(params.apt_id) ctx._source.updated_at_siem = params.now } else { ctx.op = 'noop' }",
                "lang": "painless", "params": {"apt_id": apt_group_id, "now": datetime.now(timezone.utc).isoformat()}}}
            es_client.update(index=target_index, id=ioc_es_id, body=update_script, refresh=True)
            print(f"Successfully linked APT ID {apt_group_id} to IoC ES_ID {ioc_es_id}")
            updated_doc_source = es_client.get(index=target_index, id=ioc_es_id)['_source']
            updated_doc_source['ioc_id'] = ioc_es_id
            for dt_field_name in ['created_at_siem', 'updated_at_siem', 'first_seen', 'last_seen', '@timestamp',
                                  'timestamp']:
                if dt_field_name in updated_doc_source and isinstance(updated_doc_source[dt_field_name], str):
                    try:
                        dt_val_str = updated_doc_source[dt_field_name].replace('Z', '+00:00')
                        if 'T' not in dt_val_str and len(dt_val_str) == 10:
                            parsed_dt = datetime.strptime(dt_val_str, '%Y-%m-%d')
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
            return schemas.IoCResponse(**updated_doc_source)
        except es_exceptions.NotFoundError:
            print(f"IoC ES_ID '{ioc_es_id}' not found (NotFoundError).")
            return None
        except es_exceptions.ElasticsearchWarning as e:
            print(f"ES error linking IoC {ioc_es_id} to APT {apt_group_id}: {e}")
            return None
        except Exception as e_gen:
            print(f"Generic error linking IoC {ioc_es_id} to APT {apt_group_id}: {e_gen}")
            return None

    def delete_apt_group(self, db: Session, es_writer: ElasticsearchWriter, apt_group_id: int) -> bool:
        # ... (Код з попереднього прикладу) ...
        db_apt_group = self.get_apt_group_by_id(db, apt_group_id)
        if not db_apt_group: print(f"APT Group ID {apt_group_id} not found in PG."); return False
        if not es_writer or not es_writer.es_client: print("ES client not available. Cannot update IoCs."); return False
        es_client: Elasticsearch = es_writer.es_client
        update_by_query_body = {"script": {
            "source": "if (ctx._source.attributed_apt_group_ids != null && ctx._source.attributed_apt_group_ids.contains(params.apt_id_to_remove)) { ArrayList new_ids = new ArrayList() for (int id : ctx._source.attributed_apt_group_ids) { if (id != params.apt_id_to_remove) { new_ids.add(id) } } ctx._source.attributed_apt_group_ids = new_ids ctx._source.updated_at_siem = params.now } else { ctx.op = 'noop' }",
            "lang": "painless",
            "params": {"apt_id_to_remove": apt_group_id, "now": datetime.now(timezone.utc).isoformat()}},
            "query": {"term": {"attributed_apt_group_ids": apt_group_id}}}
        try:
            print(f"Attempting to remove APT ID {apt_group_id} from linked IoCs in ES...")
            response = es_client.update_by_query(index="siem-iocs-*", body=update_by_query_body, refresh=True,
                                                 wait_for_completion=True, conflicts='proceed')
            print(f"ES update_by_query response for APT ID {apt_group_id}: {response}")
            if response.get('failures') and len(response['failures']) > 0: print(
                f"WARNING: ES failures during update_by_query for APT ID {apt_group_id}: {response['failures']}")
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error updating IoCs in ES during APT group deletion (ID: {apt_group_id}): {e}")
        db.delete(db_apt_group)
        db.commit()
        print(f"APT Group '{db_apt_group.name}' (ID: {apt_group_id}) deleted from PostgreSQL.")
        return True

    def get_iocs_for_apt_group(self, es_writer: ElasticsearchWriter, apt_group_id: int, skip: int = 0,
                               limit: int = 100) -> List[schemas.IoCResponse]:
        # ... (Код з попереднього прикладу) ...
        if not es_writer or not es_writer.es_client: print("ES client not available."); return []
        es_client: Elasticsearch = es_writer.es_client
        query_body = {"query": {"term": {"attributed_apt_group_ids": apt_group_id}}, "from": skip, "size": limit,
                      "sort": [{"updated_at_siem": {"order": "desc", "unmapped_type": "date"}},
                               {"created_at_siem": {"order": "desc", "unmapped_type": "date"}}]}
        try:
            resp = es_client.search(index="siem-iocs-*", body=query_body)
            iocs_found = []
            for hit in resp.get('hits', {}).get('hits', []):
                source_data = hit.get('_source', {})
                source_data['ioc_id'] = hit.get('_id')
                for dt_field_name in ['created_at_siem', 'updated_at_siem', 'first_seen', 'last_seen', '@timestamp',
                                      'timestamp']:
                    if dt_field_name in source_data and isinstance(source_data[dt_field_name], str):
                        try:
                            dt_val_str = source_data[dt_field_name].replace('Z', '+00:00')
                            if 'T' not in dt_val_str and len(dt_val_str) == 10:
                                parsed_dt = datetime.strptime(dt_val_str, '%Y-%m-%d')
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
                    iocs_found.append(schemas.IoCResponse(**ioc_response_data))
                except ValidationError as e:
                    print(f"Error validating IoC for APT group: {e}. Data: {ioc_response_data}")
            return iocs_found
        except es_exceptions.ElasticsearchWarning as e:
            print(f"Error getting IoCs for APT group {apt_group_id}: {e}")
            return []
