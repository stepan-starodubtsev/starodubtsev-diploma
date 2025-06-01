import os
import sys
from typing import List, Dict, Any

from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

# --- Налаштування шляхів для коректних імпортів ---
# Припускаємо, що цей скрипт знаходиться в app/scripts/
# Корінь проєкту - це каталог, що містить папку app/
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(CURRENT_SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_DIR)
    print(f"Added project root to sys.path: {PROJECT_ROOT_DIR}")

# --- Імпорти з твого проєкту ---
from app.core.database import SessionLocal, engine, Base
# Імпортуємо всі моделі, щоб Base.metadata.create_all знав про них,
# якщо ти використовуєш цей метод для створення таблиць тут.
from app.database.postgres_models import device_models, ioc_source_models, threat_actor_models

from app.modules.ioc_sources import schemas as ioc_source_schemas
from app.modules.ioc_sources.services import IoCSourceService

from app.modules.apt_groups import schemas as apt_schemas
from app.modules.apt_groups.services import APTGroupService

from app.modules.indicators import schemas as indicator_schemas
from app.modules.indicators.services import IndicatorService

from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from app.core.config import settings  # Для налаштувань ES
from pydantic import ValidationError

# Шлях до JSON файлу з даними (відносно кореня проєкту)
MOCK_DATA_FILE_PATH = os.path.join(PROJECT_ROOT_DIR, "data", "apt_iocs_data.json")


def load_mock_data_from_file() -> List[Dict[str, Any]]:
    """Завантажує дані APT та IoC з JSON файлу."""
    try:
        if not os.path.exists(MOCK_DATA_FILE_PATH):
            print(f"ERROR: Mock data file not found at {MOCK_DATA_FILE_PATH}")
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


def seed_apt_groups(db: Session, apt_service: APTGroupService, apt_data_list: List[Dict[str, Any]]) -> Dict[str, int]:
    """Створює або знаходить існуючі APT-угруповання в БД. Повертає мапінг placeholder_id -> db_id."""
    apt_id_map: Dict[str, int] = {}
    print("\n--- Seeding APT Groups ---")
    for apt_entry in apt_data_list:
        name = apt_entry.get("name")
        if not name:
            print(f"Skipping APT entry due to missing name: {apt_entry}")
            continue

        db_apt = apt_service.get_apt_group_by_name(db, name)  # Використовуємо метод сервісу
        if not db_apt:
            try:
                references_pydantic = [apt_schemas.HttpUrl(str(url)) for url in apt_entry.get("references", []) if url]
                apt_create_schema = apt_schemas.APTGroupCreate(
                    name=name,
                    aliases=apt_entry.get("aliases", []),
                    description=apt_entry.get("description"),
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
                    references=references_pydantic
                )
                db_apt = apt_service.create_apt_group(db, apt_create_schema)
                print(f"Created APT Group: '{db_apt.name}' with ID {db_apt.id}")
            except (ValidationError, ValueError) as e:
                print(f"Error creating/validating APT '{name}': {e}")
                db_apt = apt_service.get_apt_group_by_name(db,
                                                           name)  # Спробуємо отримати, якщо була помилка "вже існує"
                if not db_apt: continue

        if db_apt:
            apt_id_map[apt_entry.get("apt_id_placeholder", name)] = db_apt.id
    return apt_id_map


def seed_iocs_for_apts(
        db: Session,
        indicator_service: IndicatorService,
        es_writer: ElasticsearchWriter,
        apt_data_list: List[Dict[str, Any]],
        apt_id_map: Dict[str, int],
        source_name_for_iocs: str
):
    """Генерує та зберігає IoC з JSON, прив'язуючи їх до APT."""
    print(f"\n--- Seeding IoCs for source '{source_name_for_iocs}' ---")
    iocs_created_count = 0
    iocs_failed_count = 0
    current_time = datetime.now(timezone.utc)

    for apt_entry in apt_data_list:
        apt_name_from_file = apt_entry.get("name")
        apt_placeholder = apt_entry.get("apt_id_placeholder", apt_name_from_file)
        apt_db_id = apt_id_map.get(apt_placeholder)  # Реальний ID APT з БД

        for ioc_json in apt_entry.get("iocs", []):
            try:
                ioc_type_str = ioc_json.get("type", "").lower().replace("_", "-")
                ioc_type_enum = indicator_schemas.IoCTypeEnum(ioc_type_str)

                ioc_create_payload = {
                    "value": ioc_json.get("value"), "type": ioc_type_enum,
                    "description": ioc_json.get("description"), "source_name": source_name_for_iocs,
                    "is_active": ioc_json.get("is_active", True), "confidence": ioc_json.get("confidence"),
                    "tags": ioc_json.get("tags", []),
                    "first_seen": current_time, "last_seen": current_time,
                    "attributed_apt_group_ids": [apt_db_id] if apt_db_id else []
                }
                cleaned_payload = {k: v for k, v in ioc_create_payload.items() if v is not None}
                ioc_to_add = indicator_schemas.IoCCreate(**cleaned_payload)

                # Викликаємо метод з IndicatorService для додавання IoC
                # Йому потрібен db для валідації APT ID, якщо він це робить сам
                created_ioc_response = indicator_service.add_ioc(db=db, es_writer=es_writer,
                                                                 ioc_create_data=ioc_to_add)
                if created_ioc_response:
                    iocs_created_count += 1
                else:
                    iocs_failed_count += 1
            except (ValueError, ValidationError) as e:
                print(f"Skipping IoC due to error: {e}. IoC data: {ioc_json}")
                iocs_failed_count += 1

    print(f"IoCs for source '{source_name_for_iocs}': Added {iocs_created_count}, Failed {iocs_failed_count}")


def seed_initial_data(db: Session):
    print("Starting data seeding...")
    ioc_source_service = IoCSourceService()
    apt_service = APTGroupService()
    indicator_service = IndicatorService()  # Створюємо екземпляр IndicatorService

    # 1. Створення таблиць (якщо потрібно, але краще через Alembic)
    try:
        print("Ensuring all database tables are created (via Base.metadata.create_all)...")
        Base.metadata.create_all(bind=engine)
        print("Database tables checked/created.")
    except Exception as e:
        print(f"Warning: Error during Base.metadata.create_all: {e}. Assuming tables exist or managed by Alembic.")

    # 2. Завантаження даних APT з JSON та створення/оновлення їх в PostgreSQL
    all_apt_data_from_file = load_mock_data_from_file()  # Використовуємо нову функцію
    apt_id_map = {}
    if all_apt_data_from_file:
        print(f"Loaded {len(all_apt_data_from_file)} APT entries from JSON file.")
        apt_id_map = seed_apt_groups(db, apt_service, all_apt_data_from_file)  # Використовуємо нову функцію
        print(f"Ensured APT groups exist in PostgreSQL. DB ID Map: {apt_id_map}")
    else:
        print("No APT data found in JSON file. APTs and their IoCs will not be seeded.")

    # 3. Створення тестових Джерел IoC в PostgreSQL
    print("\n--- Seeding IoC Sources ---")
    ioc_sources_to_seed_data = [
        {"name": "APT Report Feed (MISP-like)", "type": ioc_source_schemas.IoCSourceTypeEnum.MISP,
         "description": "Simulates IoCs from the APT report for MISP-like source."},
        {"name": "APT Report Feed (OpenCTI-like)", "type": ioc_source_schemas.IoCSourceTypeEnum.OPENCTI,
         "description": "Simulates IoCs from the APT report for OpenCTI-like source."},
        {"name": "Internal Manual Additions", "type": ioc_source_schemas.IoCSourceTypeEnum.INTERNAL,
         "description": "Source for manually added IoCs."}
    ]

    created_ioc_sources_for_seeding: List[ioc_source_models.IoCSource] = []
    for source_def in ioc_sources_to_seed_data:
        existing_source = ioc_source_service.get_ioc_source_by_name(db, name=source_def["name"])
        if existing_source:
            print(f"IoC Source '{source_def['name']}' already exists (ID: {existing_source.id}). Using existing.")
            created_ioc_sources_for_seeding.append(existing_source)
        else:
            try:
                source_create_schema = ioc_source_schemas.IoCSourceCreate(**source_def)
                created = ioc_source_service.create_ioc_source(db, source_create_schema)
                print(f"Created IoC Source: '{created.name}' (ID: {created.id})")
                created_ioc_sources_for_seeding.append(created)
            except Exception as e:
                print(f"Error creating IoC Source '{source_def['name']}': {e}")

    # 4. Завантаження IoC в Elasticsearch для певних джерел
    if all_apt_data_from_file and created_ioc_sources_for_seeding:
        try:
            es_host_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT_API}"
            es_writer = ElasticsearchWriter(es_hosts=[es_host_url])
            print(f"\nElasticsearchWriter initialized for IoC seeding to {es_host_url}.")

            # Завантажуємо IoC, використовуючи наш JSON, але для конкретних джерел
            # Наприклад, для джерела "APT Report Feed (MISP-like)"
            misp_like_source = next(
                (s for s in created_ioc_sources_for_seeding if s.name == "APT Report Feed (MISP-like)"), None)
            if misp_like_source and misp_like_source.is_enabled:
                # Логіка _generate_iocs_from_mock_data тепер не потрібна в IoCSourceService,
                # оскільки ми завантажуємо дані з файлу тут і передаємо їх для створення IoC.
                # Метод fetch_and_store_iocs_from_source тепер має просто приймати список IoCCreate.
                # Або ми можемо залишити його, але він буде використовувати ці функції.
                # Поки що, для простоти, зробимо завантаження IoC тут.
                seed_iocs_for_apts(db, indicator_service, es_writer, all_apt_data_from_file, apt_id_map,
                                   misp_like_source.name)
            else:
                print("MISP-like source not found or not enabled, skipping IoC seeding for it.")

            # Можна додати аналогічно для інших типів джерел, якщо потрібно різний набір IoC

        except ConnectionError as e:
            print(f"Could not connect to Elasticsearch. IoCs from file will not be seeded into ES: {e}")
        except Exception as e_es:
            print(f"An error occurred while trying to seed IoCs into Elasticsearch: {e_es}")
            import traceback
            traceback.print_exc()
    else:
        print("Skipping IoC seeding into Elasticsearch as APT data or IoC sources are not available.")

    print("\nData seeding finished.")


if __name__ == "__main__":
    print("Initializing database session for seeding...")
    db: Session = SessionLocal()
    try:
        seed_initial_data(db)
    except Exception as e:
        print(f"An critical error occurred during the seeding process: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("Closing database session.")
        db.close()