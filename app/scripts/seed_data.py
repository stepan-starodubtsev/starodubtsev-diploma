# app/scripts/seed_data.py
import os
import sys
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import json

# --- Налаштування шляхів ---
CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT_DIR = os.path.abspath(os.path.join(CURRENT_SCRIPT_DIR, '..', '..'))
if PROJECT_ROOT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_DIR)
    print(f"Added project root to sys.path: {PROJECT_ROOT_DIR}")

# --- Імпорти з проєкту ---
from app.core.database import SessionLocal, engine, Base
from app.database.postgres_models import device_models, ioc_source_models, threat_actor_models, correlation_models, \
    response_models
from app.database.postgres_models.correlation_models import CorrelationRule

from app.modules.ioc_sources import schemas as ioc_source_schemas
from app.modules.ioc_sources.services import IoCSourceService

from app.modules.apt_groups import schemas as apt_schemas
from app.modules.apt_groups.services import APTGroupService

from app.modules.indicators import schemas as indicator_schemas
from app.modules.indicators.services import IndicatorService

from app.modules.correlation.services import CorrelationService
from app.modules.correlation.schemas import CorrelationRuleCreate, CorrelationRuleTypeEnum, EventFieldToMatchTypeEnum, \
    IoCTypeToMatchEnum, OffenceSeverityEnum

from app.modules.response import schemas as response_schemas
from app.modules.response.services import ResponseService

from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from app.core.config import settings
from pydantic import ValidationError

MOCK_DATA_FILE_PATH = os.path.join(PROJECT_ROOT_DIR, "data", "apt_iocs_data.json")


def load_mock_data_from_file() -> List[Dict[str, Any]]:
    try:
        if not os.path.exists(MOCK_DATA_FILE_PATH):
            print(f"ERROR: Mock data file not found at {MOCK_DATA_FILE_PATH}")
            return []
        with open(MOCK_DATA_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"ERROR loading mock data: {e}")
        return []


def seed_apt_groups(db: Session, apt_service: APTGroupService, apt_data_list: List[Dict[str, Any]]) -> Dict[str, int]:
    apt_id_map: Dict[str, int] = {}
    print("\n--- Seeding APT Groups ---")
    for apt_entry in apt_data_list:
        name = apt_entry.get("name")
        if not name:
            print(f"Skipping APT entry due to missing name: {apt_entry}")
            continue
        db_apt = apt_service.get_apt_group_by_name(db, name)
        if not db_apt:
            try:
                apt_create_schema = apt_schemas.APTGroupCreate.model_validate(apt_entry)
                db_apt = apt_service.create_apt_group(db, apt_create_schema)
                print(f"Created APT Group: '{db_apt.name}' with ID {db_apt.id}")
            except (ValidationError, ValueError) as e:
                print(f"Error creating/validating APT '{name}': {e}")
                db_apt = apt_service.get_apt_group_by_name(db, name)
                if not db_apt: continue
        if db_apt:
            apt_id_map[apt_entry.get("apt_id_placeholder", name)] = db_apt.id
    return apt_id_map


def seed_iocs_for_apts(db: Session, indicator_service: IndicatorService, apt_service: APTGroupService,
                       es_writer: ElasticsearchWriter, apt_data_list: List[Dict[str, Any]], apt_id_map: Dict[str, int],
                       source_name_for_iocs: str):
    print(f"\n--- Seeding IoCs for source '{source_name_for_iocs}' ---")
    iocs_created_count = 0
    iocs_failed_count = 0
    current_time = datetime.now(timezone.utc)
    for apt_entry in apt_data_list:
        apt_placeholder = apt_entry.get("apt_id_placeholder", apt_entry.get("name"))
        apt_db_id = apt_id_map.get(apt_placeholder)
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
                created_ioc_response = indicator_service.add_ioc(db=db, es_writer=es_writer, ioc_create_data=ioc_to_add,
                                                                 apt_service=apt_service)
                if created_ioc_response:
                    iocs_created_count += 1
                else:
                    iocs_failed_count += 1
            except (ValueError, ValidationError) as e:
                print(f"Skipping IoC due to error: {e}. IoC data: {ioc_json}")
                iocs_failed_count += 1
    print(f"IoCs for source '{source_name_for_iocs}': Added {iocs_created_count}, Failed {iocs_failed_count}")


def seed_default_correlation_rules(db: Session, correlation_service: CorrelationService,
                                   apt_data_list: List[Dict[str, Any]]):
    print("\n--- Loading Default IoC-Match Correlation Rules (based on APTs from JSON) ---")
    stats_ioc_rules = correlation_service.load_default_rules_from_apt_data(db, apt_data_list)
    print(
        f"Default IoC-match correlation rules processed. Created: {stats_ioc_rules.get('created')}, Skipped: {stats_ioc_rules.get('skipped')}")
    print("\n--- Loading Default Threshold Correlation Rules ---")
    threshold_rules_data = [
        # ... (як було раніше)
        {"name": "Default: High Number of Failed Logins (by Username+Host)",
         "description": "Detects 5+ failed logins for same user on same host in 10m.", "is_enabled": True,
         "rule_type": CorrelationRuleTypeEnum.THRESHOLD_LOGIN_FAILURES,
         "event_source_type": ["syslog_auth", "authentication"], "threshold_count": 5,
         "threshold_time_window_minutes": 10,
         "aggregation_fields": [EventFieldToMatchTypeEnum.USERNAME, EventFieldToMatchTypeEnum.HOSTNAME],
         "generated_offence_title_template": "Brute-force (User+Host): {actual_count} failed logins for '{aggregation_key_info}' in {time_window_minutes}m",
         "generated_offence_severity": OffenceSeverityEnum.MEDIUM},
        {"name": "Default: Potential Data Exfiltration (Source IP to Dest IP)",
         "description": "Detects if an internal host sends >100MB to an external IP in 15m.", "is_enabled": True,
         "rule_type": CorrelationRuleTypeEnum.THRESHOLD_DATA_EXFILTRATION, "event_source_type": ["netflow", "flow"],
         "threshold_count": 100 * 1024 * 1024, "threshold_time_window_minutes": 15,
         "aggregation_fields": [EventFieldToMatchTypeEnum.SOURCE_IP, EventFieldToMatchTypeEnum.DESTINATION_IP],
         "generated_offence_title_template": "Data Exfil Alert: {aggregation_key_info} sent {actual_sum_bytes} bytes in {time_window_minutes}m",
         "generated_offence_severity": OffenceSeverityEnum.HIGH}
    ]
    created_thresh_count, skipped_thresh_count = 0, 0
    for rule_data in threshold_rules_data:
        if not db.query(CorrelationRule).filter(CorrelationRule.name == rule_data["name"]).first():
            try:
                correlation_service.create_correlation_rule(db, CorrelationRuleCreate(**rule_data))
                print(f"CREATED default threshold rule: {rule_data['name']}")
                created_thresh_count += 1
            except Exception as e:
                print(f"Error creating default threshold rule '{rule_data['name']}': {e}")
                skipped_thresh_count += 1
        else:
            skipped_thresh_count += 1
    print(f"Default threshold rules processed. Created: {created_thresh_count}, Skipped: {skipped_thresh_count}")


def seed_default_response_actions_and_pipelines(db: Session, response_service: ResponseService,
                                                correlation_service: CorrelationService):
    print("\n--- Seeding Default Response Actions and Pipelines ---")
    # ... (код без змін)
    block_ip_action_name = "Block IP on Main Firewall (Mikrotik)"
    block_ip_action = db.query(response_models.ResponseAction).filter(
        response_models.ResponseAction.name == block_ip_action_name).first()
    if not block_ip_action:
        action_create_schema = response_schemas.ResponseActionCreate(name=block_ip_action_name,
                                                                     type=response_schemas.ResponseActionTypeEnum.BLOCK_IP,
                                                                     description="Blocks the offending IP address on the main Mikrotik firewall by adding it to 'siem_auto_blocked_ips' list.",
                                                                     is_enabled=True, default_params={"device_id": 1,
                                                                                                      "list_name": "siem_auto_blocked_ips"})
        try:
            block_ip_action = response_service.create_action(db, action_create_schema)
            print(f"Created Response Action: '{block_ip_action.name}' with ID {block_ip_action.id}")
        except Exception as e:
            print(f"Error creating response action '{block_ip_action_name}': {e}"); return
    else:
        print(f"Response Action '{block_ip_action_name}' already exists with ID {block_ip_action.id}.")
    if not block_ip_action: return
    target_correlation_rule_name = "Default: Traffic TO APT28 IP IoCs"
    correlation_rule_for_pipeline = db.query(correlation_models.CorrelationRule).filter(
        correlation_models.CorrelationRule.name == target_correlation_rule_name).first()
    if not correlation_rule_for_pipeline:
        print(f"WARNING: Correlation rule '{target_correlation_rule_name}' not found. Cannot create pipeline for it.")
        all_rules = correlation_service.get_all_correlation_rules(db, limit=1)
        if all_rules:
            correlation_rule_for_pipeline = all_rules[0]
            print(
                f"Using first available rule for pipeline demo: '{correlation_rule_for_pipeline.name}' (ID: {correlation_rule_for_pipeline.id})")
        else:
            print("No correlation rules found to attach a pipeline to."); return
    pipeline_name = f"Pipeline for Rule: {correlation_rule_for_pipeline.name}"
    existing_pipeline = db.query(response_models.ResponsePipeline).filter(
        response_models.ResponsePipeline.name == pipeline_name).first()
    if not existing_pipeline:
        pipeline_action_config = response_schemas.PipelineActionConfig(action_id=block_ip_action.id, order=1,
                                                                       action_params_template={})
        pipeline_create_schema = response_schemas.ResponsePipelineCreate(name=pipeline_name,
                                                                         description=f"Automatically blocks IP based on offence from rule '{correlation_rule_for_pipeline.name}'.",
                                                                         is_enabled=True,
                                                                         trigger_correlation_rule_id=correlation_rule_for_pipeline.id,
                                                                         actions_config=[pipeline_action_config])
        try:
            created_pipeline = response_service.create_pipeline(db, pipeline_create_schema)
            print(f"Created Response Pipeline: '{created_pipeline.name}' with ID {created_pipeline.id}")
        except Exception as e:
            print(f"Error creating response pipeline '{pipeline_name}': {e}")
    else:
        print(f"Response Pipeline '{pipeline_name}' already exists.")


# --- ОНОВЛЕНА ФУНКЦІЯ ---
def seed_initial_data(db: Session):
    print("Starting data seeding...")
    ioc_source_service = IoCSourceService()
    apt_service = APTGroupService()
    indicator_service = IndicatorService()
    correlation_service = CorrelationService()
    response_service = ResponseService()

    try:
        print("Ensuring all database tables are created (via Base.metadata.create_all)...")
        Base.metadata.create_all(bind=engine)
        print("Database tables checked/created.")
    except Exception as e:
        print(f"Warning: Error during Base.metadata.create_all: {e}.")

    all_apt_data_from_file = load_mock_data_from_file()
    apt_id_map = {}
    if all_apt_data_from_file:
        print(f"Loaded {len(all_apt_data_from_file)} APT entries from JSON file.")
        apt_id_map = seed_apt_groups(db, apt_service, all_apt_data_from_file)
        print(f"Ensured APT groups exist in PostgreSQL. DB ID Map: {apt_id_map}")
    else:
        print("No APT data found in JSON file. Some seeding steps might be skipped.")

    print("\n--- Seeding IoC Sources ---")
    ioc_sources_to_seed = [
        {"name": "APT Report Feed (MISP-like)", "type": ioc_source_schemas.IoCSourceTypeEnum.MOCK_APT_REPORT,
         "description": "Simulates IoCs from the APT report."},
        {"name": "Internal Manual Additions", "type": ioc_source_schemas.IoCSourceTypeEnum.INTERNAL,
         "description": "Source for manually added IoCs."}
    ]
    created_ioc_sources = []
    for source_def in ioc_sources_to_seed:
        existing = ioc_source_service.get_ioc_source_by_name(db, name=source_def["name"])
        if existing:
            created_ioc_sources.append(existing)
        else:
            try:
                created = ioc_source_service.create_ioc_source(db, ioc_source_schemas.IoCSourceCreate(**source_def))
                created_ioc_sources.append(created)
            except Exception as e:
                print(f"Error creating IoC Source '{source_def['name']}': {e}")
    if created_ioc_sources:
        print(f"IoC Sources seeded/verified: {len(created_ioc_sources)}")

    # ---> ПОЧАТОК ВИПРАВЛЕННЯ <---
    if all_apt_data_from_file and created_ioc_sources:
        try:
            es_host_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT_API}"
            es_writer = ElasticsearchWriter(es_hosts=[es_host_url])
            print(f"\nElasticsearchWriter initialized for IoC seeding to {es_host_url}.")

            # Знаходимо джерело, яке ми хочемо використати для завантаження IoC з файлу
            source_for_seeding = next(
                (s for s in created_ioc_sources if s.type == ioc_source_schemas.IoCSourceTypeEnum.MOCK_APT_REPORT),
                None)

            if source_for_seeding and source_for_seeding.is_enabled:
                # Викликаємо метод seed_iocs_for_apts
                seed_iocs_for_apts(
                    db=db,
                    indicator_service=indicator_service,
                    apt_service=apt_service,
                    es_writer=es_writer,
                    apt_data_list=all_apt_data_from_file,
                    apt_id_map=apt_id_map,
                    source_name_for_iocs=source_for_seeding.name
                )
            else:
                print("Source for mock APT report data not found or not enabled, skipping IoC seeding for it.")

        except ConnectionError as e:
            print(f"Could not connect to Elasticsearch. IoCs from file will not be seeded into ES: {e}")
        except Exception as e_es:
            print(f"An error occurred while trying to seed IoCs into Elasticsearch: {e_es}")
            import traceback
            traceback.print_exc()
    else:
        print("Skipping IoC seeding into Elasticsearch as APT data or IoC sources are not available.")
    # ---> КІНЕЦЬ ВИПРАВЛЕННЯ <---

    if all_apt_data_from_file:
        seed_default_correlation_rules(db, correlation_service, all_apt_data_from_file)

    seed_default_response_actions_and_pipelines(db, response_service, correlation_service)

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