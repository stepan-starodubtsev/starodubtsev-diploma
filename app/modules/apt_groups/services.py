# app/modules/apt_groups/services.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any, TYPE_CHECKING  # Додано TYPE_CHECKING

from app.database.postgres_models.threat_actor_models import APTGroup
from . import schemas as apt_schemas
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter  # Потрібен для delete_apt_group
from elasticsearch import Elasticsearch, exceptions as es_exceptions  # Потрібен для delete_apt_group
from datetime import datetime, timezone  # Для painless скрипта в delete_apt_group
from pydantic import ValidationError

# Для type hinting без реального імпорту під час виконання
if TYPE_CHECKING:
    from app.modules.indicators.services import IndicatorService
    from app.modules.indicators import schemas as indicator_schemas


class APTGroupService:
    # ... (create_apt_group, get_apt_group_by_id, get_apt_group_by_name,
    #      get_all_apt_groups, update_apt_group - без змін, вони не викликають інші сервіси) ...
    def create_apt_group(self, db: Session, apt_group_create: apt_schemas.APTGroupCreate) -> APTGroup:
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
        db.add(db_apt_group);
        db.commit();
        db.refresh(db_apt_group);
        return db_apt_group

    def get_apt_group_by_id(self, db: Session, apt_group_id: int) -> Optional[APTGroup]:
        return db.query(APTGroup).filter(APTGroup.id == apt_group_id).first()

    def get_apt_group_by_name(self, db: Session, name: str) -> Optional[APTGroup]:
        return db.query(APTGroup).filter(APTGroup.name == name).first()

    def get_all_apt_groups(self, db: Session, skip: int = 0, limit: int = 100) -> List[APTGroup]:
        return db.query(APTGroup).order_by(APTGroup.name).offset(skip).limit(limit).all()

    def update_apt_group(self, db: Session, apt_group_id: int, apt_group_update: apt_schemas.APTGroupUpdate) -> \
    Optional[APTGroup]:
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
        db.add(db_apt_group);
        db.commit();
        db.refresh(db_apt_group);
        return db_apt_group

    def _ensure_apt_groups_exist_from_data(self, db: Session, apt_data_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """Використовується IoCSourceService. Перевіряє/створює APT з даних JSON."""
        # ... (код цього методу без змін з попереднього повного файлу IoCManagementService) ...
        apt_id_map: Dict[str, int] = {}
        for apt_entry in apt_data_list:
            name = apt_entry.get("name")
            if not name: continue
            db_apt = self.get_apt_group_by_name(db, name)
            if not db_apt:
                try:
                    references_pydantic = [apt_schemas.HttpUrl(str(url)) for url in apt_entry.get("references", []) if
                                           url]
                    apt_create_schema = apt_schemas.APTGroupCreate(
                        name=name, aliases=apt_entry.get("aliases", []), description=apt_entry.get("description"),
                        sophistication=apt_schemas.APTGroupSophisticationEnum(
                            apt_entry.get("sophistication", "unknown").lower()) if apt_entry.get(
                            "sophistication") else apt_schemas.APTGroupSophisticationEnum.UNKNOWN,
                        primary_motivation=apt_schemas.APTGroupMotivationsEnum(
                            apt_entry.get("primary_motivation", "unknown").lower()) if apt_entry.get(
                            "primary_motivation") else apt_schemas.APTGroupMotivationsEnum.UNKNOWN,
                        target_sectors=apt_entry.get("target_sectors", []),
                        country_of_origin=apt_entry.get("country_of_origin"),
                        first_observed=datetime.fromisoformat(apt_entry["first_observed"]) if apt_entry.get(
                            "first_observed") else None,
                        last_observed=datetime.fromisoformat(apt_entry["last_observed"]) if apt_entry.get(
                            "last_observed") else None,
                        references=references_pydantic)
                    db_apt = self.create_apt_group(db, apt_create_schema)
                    print(f"APTService: Created APT Group: '{db_apt.name}' with ID {db_apt.id}")
                except (ValidationError, ValueError) as e:
                    print(f"APTService: Error creating/validating APT '{name}': {e}"); continue
            if db_apt: apt_id_map[apt_entry.get("apt_id_placeholder", name)] = db_apt.id
        return apt_id_map

    def delete_apt_group(self,
                         db: Session,
                         es_writer: ElasticsearchWriter,
                         apt_group_id: int,
                         indicator_service: 'IndicatorService'  # <--- ІН'ЄКЦІЯ СЕРВІСУ
                         ) -> bool:
        db_apt_group = self.get_apt_group_by_id(db, apt_group_id)
        if not db_apt_group:
            print(f"APT Group ID {apt_group_id} not found in PostgreSQL.")
            return False

        # 1. Використовуємо IndicatorService для оновлення IoC в Elasticsearch
        try:
            print(f"Attempting to remove APT ID {apt_group_id} from linked IoCs in Elasticsearch...")
            # Викликаємо метод з IndicatorService
            success_es_update = indicator_service.remove_apt_id_from_all_iocs(es_writer, apt_group_id)
            if not success_es_update:
                print(
                    f"Warning: Failed to fully remove APT ID {apt_group_id} from all linked IoCs in Elasticsearch. Proceeding with PG delete.")
        except Exception as e:
            print(f"Error updating IoCs in ES during APT group {apt_group_id} deletion: {e}")
            # Вирішити, чи продовжувати видалення з PostgreSQL
            # return False # Можна зупинити тут, якщо оновлення ES критичне

        # 2. Видалити саме APT-угруповання з PostgreSQL
        db.delete(db_apt_group)
        db.commit()
        print(f"APT Group '{db_apt_group.name}' (ID: {apt_group_id}) deleted from PostgreSQL.")
        return True

    def get_iocs_for_apt_group(self,
                               es_writer: ElasticsearchWriter,
                               apt_group_id: int,
                               indicator_service: 'IndicatorService',  # <--- ІН'ЄКЦІЯ СЕРВІСУ
                               skip: int = 0,
                               limit: int = 100
                               ) -> List[
        'indicator_schemas.IoCResponse']:  # Використовуємо type hint з indicator_schemas
        # Цей метод тепер просто викликає відповідний метод з IndicatorService
        return indicator_service.get_iocs_by_apt_group_id(es_writer, apt_group_id, skip, limit)
