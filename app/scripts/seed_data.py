# app/scripts/seed_data.py
import os
import sys
from typing import List

# Додаємо шлях до кореня проєкту (на два рівні вище від app/scripts/)
# __file__ -> app/scripts/seed_data.py
# os.path.dirname(__file__) -> app/scripts/
# os.path.join(os.path.dirname(__file__), '..') -> app/
# os.path.join(os.path.dirname(__file__), '..', '..') -> корінь проєкту
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT_DIR not in sys.path:  # Додаємо, тільки якщо ще немає
    sys.path.insert(0, PROJECT_ROOT_DIR)
    print(f"Added project root to sys.path: {PROJECT_ROOT_DIR}")

# Тепер імпорти з app мають працювати
from app.core.database import SessionLocal, engine, Base
from app.database.postgres_models import ioc_source_models
from app.modules.ioc_management.services import IoCManagementService
from app.modules.ioc_management import schemas as ioc_schemas
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from app.core.config import settings
from sqlalchemy.orm import Session  # Явний імпорт Session


# ... (решта коду seed_data.py без змін) ...

def seed_initial_data(db: Session):
    print("Starting data seeding...")
    ioc_service = IoCManagementService()

    try:
        print("Ensuring all database tables are created (via Base.metadata.create_all)...")
        Base.metadata.create_all(bind=engine)
        print("Database tables checked/created.")
    except Exception as e:
        print(f"Error during Base.metadata.create_all: {e}")
        # Вирішити, чи продовжувати, якщо таблиці не вдалося створити/перевірити
        # return # Можливо, варто зупинити, якщо таблиць немає

    # ... (решта логіки seed_initial_data) ...
    apt_data_from_file = ioc_service._load_mock_data_from_file()
    if apt_data_from_file:
        print(f"Loaded {len(apt_data_from_file)} APT entries from JSON file.")
        apt_id_map = ioc_service._ensure_apt_groups_exist(db, apt_data_from_file)
        print(f"Ensured APT groups exist in PostgreSQL. ID Map based on placeholder/name: {apt_id_map}")
    else:
        print("No APT data found in JSON file or file not found. Cannot seed IoCs linked to these APTs.")

    print("\nSeeding IoC Sources...")
    ioc_sources_to_seed = [
        ioc_schemas.IoCSourceCreate(
            name="Mocked MISP Feed (APT Report Data)",
            type=ioc_schemas.IoCSourceTypeEnum.MISP,
            description="Simulates a MISP feed using data from the local APT report JSON.",
            is_enabled=True,
            url=None
        ),
        # ioc_schemas.IoCSourceCreate(
        #     name="Mocked OpenCTI Feed (APT Report Data)",
        #     type=ioc_schemas.IoCSourceTypeEnum.OPENCTI,
        #     description="Simulates an OpenCTI feed using data from the local APT report JSON.",
        #     is_enabled=True
        # ),
        # ioc_schemas.IoCSourceCreate(
        #     name="Internal Manual IoCs",
        #     type=ioc_schemas.IoCSourceTypeEnum.INTERNAL,
        #     description="Source for IoCs added manually or from internal investigations.",
        #     is_enabled=True
        # )
    ]
    created_ioc_sources: List[ioc_source_models.IoCSource] = []
    for source_data in ioc_sources_to_seed:
        existing_source = ioc_service.get_ioc_source_by_name(db, name=source_data.name)
        if existing_source:
            print(f"IoC Source '{source_data.name}' already exists with ID {existing_source.id}. Using existing.")
            created_ioc_sources.append(existing_source)
        else:
            try:
                created_source = ioc_service.create_ioc_source(db, source_data)
                print(f"Created IoC Source: '{created_source.name}' with ID {created_source.id}")
                created_ioc_sources.append(created_source)
            except ValueError as ve:
                print(f"Could not create IoC Source '{source_data.name}': {ve}")
            except Exception as e:
                print(f"Unexpected error creating IoC Source '{source_data.name}': {e}")

    if not created_ioc_sources:
        print("No IoC sources available or created. Skipping IoC seeding into Elasticsearch.")
    else:
        try:
            es_host_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT_API}"
            es_writer = ElasticsearchWriter(es_hosts=[es_host_url])
            print(f"\nElasticsearchWriter initialized for IoC seeding.")

            for ioc_source_db_obj in created_ioc_sources:
                if ioc_source_db_obj.is_enabled and ioc_source_db_obj.type != ioc_schemas.IoCSourceTypeEnum.INTERNAL:
                    print(
                        f"\nAttempting to fetch/store IoCs for source ID {ioc_source_db_obj.id} ('{ioc_source_db_obj.name}')...")
                    fetch_result = ioc_service.fetch_and_store_iocs_from_source(db, ioc_source_db_obj.id, es_writer)
                    print(f"IoC fetching/storing result for source '{ioc_source_db_obj.name}': {fetch_result}")
                elif ioc_source_db_obj.type == ioc_schemas.IoCSourceTypeEnum.INTERNAL:
                    print(
                        f"Skipping auto-fetch for INTERNAL source '{ioc_source_db_obj.name}'. IoCs for this source should be added manually.")
                else:
                    print(f"Skipping fetch for disabled source '{ioc_source_db_obj.name}'.")
        except ConnectionError as e:
            print(f"Could not connect to Elasticsearch, IoCs will not be seeded into ES: {e}")
        except Exception as e_es:
            print(f"An error occurred while trying to seed IoCs into Elasticsearch: {e_es}")
            import traceback
            traceback.print_exc()
    print("\nData seeding finished.")


if __name__ == "__main__":
    print("Initializing database session for seeding...")
    # Переконуємося, що SQLAlchemy Base знає про всі моделі перед create_all
    # Імпорти моделей на початку файлу вже мають це забезпечити.
    db: Session = SessionLocal()
    try:
        seed_initial_data(db)
    except Exception as e:
        print(f"An error occurred during the seeding process: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("Closing database session.")
        db.close()
