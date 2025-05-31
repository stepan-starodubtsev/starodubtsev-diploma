# app/modules/ioc_sources/services.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import os
import json

from app.database.postgres_models.ioc_source_models import IoCSource
from . import schemas as ioc_source_schemas
from app.modules.apt_groups.services import APTGroupService  # Для взаємодії з APT
from app.modules.apt_groups import schemas as apt_schemas  # Потрібно для type hint APTGroupService
from app.modules.indicators.services import IndicatorService  # Для взаємодії з IoC
from app.modules.indicators import schemas as indicator_schemas  # Потрібно для type hint IndicatorService
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from pydantic import ValidationError

# Шлях до JSON файлу (якщо використовується)
CURRENT_DIR_IOC_SOURCES = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR_IOC_SOURCES = os.path.join(CURRENT_DIR_IOC_SOURCES, "..", "..", "..")
MOCK_DATA_FILE_PATH_IOC_SOURCES = os.path.join(PROJECT_ROOT_DIR_IOC_SOURCES, "data", "apt_iocs_data.json")


class IoCSourceService:
    def create_ioc_source(self, db: Session, source_create: ioc_source_schemas.IoCSourceCreate) -> IoCSource:
        existing_source = db.query(IoCSource).filter(IoCSource.name == source_create.name).first()
        if existing_source:
            raise ValueError(f"IoC Source with name '{source_create.name}' already exists.")
        db_source = IoCSource(
            name=source_create.name, type=source_create.type,
            url=str(source_create.url) if source_create.url else None,
            description=source_create.description, is_enabled=source_create.is_enabled
        )
        db.add(db_source);
        db.commit();
        db.refresh(db_source)
        return db_source

    def get_ioc_source_by_id(self, db: Session, source_id: int) -> Optional[IoCSource]:
        return db.query(IoCSource).filter(IoCSource.id == source_id).first()

    def get_ioc_source_by_name(self, db: Session, name: str) -> Optional[IoCSource]:  # Цей метод потрібен
        return db.query(IoCSource).filter(IoCSource.name == name).first()

    def get_all_ioc_sources(self, db: Session, skip: int = 0, limit: int = 100) -> List[IoCSource]:
        return db.query(IoCSource).order_by(IoCSource.id).offset(skip).limit(limit).all()

    def update_ioc_source(self, db: Session, source_id: int, source_update: ioc_source_schemas.IoCSourceUpdate) -> \
    Optional[IoCSource]:
        db_source = self.get_ioc_source_by_id(db, source_id)
        if not db_source: return None
        update_data = source_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if key == "url" and value is not None:
                setattr(db_source, key, str(value))
            elif key == "type" and value is not None:
                setattr(db_source, key, ioc_source_schemas.IoCSourceTypeEnum(value))
            else:
                setattr(db_source, key, value)
        db.add(db_source);
        db.commit();
        db.refresh(db_source)
        return db_source

    def delete_ioc_source(self, db: Session, source_id: int) -> bool:
        db_source = self.get_ioc_source_by_id(db, source_id)
        if db_source: db.delete(db_source); db.commit(); return True
        return False

    def _load_mock_data_from_file(self) -> List[Dict[str, Any]]:
        try:
            if not os.path.exists(MOCK_DATA_FILE_PATH_IOC_SOURCES):
                print(f"ERROR: Mock data file not found at {MOCK_DATA_FILE_PATH_IOC_SOURCES}")
                return []
            with open(MOCK_DATA_FILE_PATH_IOC_SOURCES, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            print(f"ERROR loading mock data: {e}"); return []

    def fetch_and_store_iocs_from_source(
            self,
            db: Session,
            source_id: int,
            es_writer: ElasticsearchWriter,
            apt_service: APTGroupService,  # Тепер це екземпляр APTGroupService
            indicator_service: IndicatorService  # Тепер це екземпляр IndicatorService
    ) -> Dict[str, Any]:
        ioc_source = self.get_ioc_source_by_id(db, source_id)
        if not ioc_source or not ioc_source.is_enabled:
            return {"status": "error", "message": f"IoC Source ID {source_id} not found or disabled.", "added_iocs": 0,
                    "failed_iocs": 0}

        print(f"Fetching IoCs for source: {ioc_source.name} (Type: {ioc_source.type.value})...")

        all_apt_data_from_file = self._load_mock_data_from_file()
        if not all_apt_data_from_file:
            return {"status": "success", "message": "Mock data file empty or not found.", "added_iocs": 0,
                    "failed_iocs": 0}

        apt_name_to_id_map: Dict[str, int] = {}
        try:
            # Використовуємо метод з apt_service для створення/перевірки APT-угруповань
            apt_name_to_id_map = apt_service._ensure_apt_groups_exist_from_data(db, all_apt_data_from_file)
        except Exception as e:
            print(f"Error ensuring APT groups exist via apt_service: {e}")

        iocs_to_create: List[indicator_schemas.IoCCreate] = []
        current_time = datetime.now(timezone.utc)

        source_type_filter_map = {
            ioc_source_schemas.IoCSourceTypeEnum.MISP: ["APT28", "Gamaredon"],
            ioc_source_schemas.IoCSourceTypeEnum.OPENCTI: ["Sandworm", "Turla"],
            ioc_source_schemas.IoCSourceTypeEnum.MOCK_APT_REPORT: [apt.get("name") for apt in all_apt_data_from_file]
        }
        relevant_apt_names_for_source = source_type_filter_map.get(ioc_source.type)
        if relevant_apt_names_for_source is None and ioc_source.type != ioc_source_schemas.IoCSourceTypeEnum.INTERNAL:
            relevant_apt_names_for_source = [apt.get("name") for apt in all_apt_data_from_file]
        if ioc_source.type == ioc_source_schemas.IoCSourceTypeEnum.INTERNAL:
            print(f"Source '{ioc_source.name}' is INTERNAL, no IoCs auto-generated from mock file for it.")
            ioc_source.last_fetched = datetime.now(timezone.utc);
            db.add(ioc_source);
            db.commit()
            return {"status": "success", "message": "Internal source, no auto-fetch.", "added_iocs": 0,
                    "failed_iocs": 0}

        for apt_entry in all_apt_data_from_file:
            apt_name_from_file = apt_entry.get("name")
            if relevant_apt_names_for_source is not None and apt_name_from_file not in relevant_apt_names_for_source:
                continue
            apt_db_id = apt_name_to_id_map.get(apt_name_from_file)

            for ioc_json in apt_entry.get("iocs", []):
                try:
                    ioc_type_str = ioc_json.get("type", "").lower().replace("_", "-")
                    ioc_type_enum = indicator_schemas.IoCTypeEnum(ioc_type_str)
                    ioc_create_payload = {
                        "value": ioc_json.get("value"), "type": ioc_type_enum,
                        "description": ioc_json.get("description"), "source_name": ioc_source.name,
                        "is_active": ioc_json.get("is_active", True), "confidence": ioc_json.get("confidence"),
                        "tags": ioc_json.get("tags", []),
                        "first_seen": current_time, "last_seen": current_time,
                        "attributed_apt_group_ids": [apt_db_id] if apt_db_id else []
                    }
                    cleaned_payload = {k: v for k, v in ioc_create_payload.items() if v is not None}
                    iocs_to_create.append(indicator_schemas.IoCCreate(**cleaned_payload))
                except (ValueError, ValidationError) as e:
                    print(f"Skipping IoC due to error: {e}. Data: {ioc_json}")

        if not iocs_to_create:
            ioc_source.last_fetched = datetime.now(timezone.utc);
            db.add(ioc_source);
            db.commit()
            return {"status": "success", "message": "No new relevant IoCs to create for this source.", "added_iocs": 0,
                    "failed_iocs": 0}

        added_count = 0;
        failed_count = 0
        if not es_writer:
            return {"status": "error", "message": "ES writer not configured.", "added_iocs": 0,
                    "failed_iocs": len(iocs_to_create)}

        for ioc_to_add_schema in iocs_to_create:
            # Викликаємо метод з IndicatorService для додавання одного IoC
            created_ioc_response = indicator_service.add_manual_ioc(
                db=db,  # db потрібен для IndicatorService для валідації APT ID
                es_writer=es_writer,
                ioc_create_data=ioc_to_add_schema,
                apt_service=apt_service  # Передаємо екземпляр APTGroupService
            )
            if created_ioc_response:
                added_count += 1
            else:
                failed_count += 1

        if ioc_source:  # Перевірка, що ioc_source не None
            ioc_source.last_fetched = datetime.now(timezone.utc);
            db.add(ioc_source);
            db.commit()
        message = f"Fetched from '{ioc_source.name if ioc_source else 'N/A'}'. Added IoCs: {added_count}. Failed: {failed_count}."
        return {"status": "success", "message": message, "added_iocs": added_count, "failed_iocs": failed_count}