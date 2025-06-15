# app/modules/correlation/services.py
import json
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any

from elasticsearch import Elasticsearch, exceptions as es_exceptions
from pydantic import ValidationError
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.postgres_models.correlation_models import CorrelationRule, Offence
from app.modules.correlation.schemas import (
    CorrelationRuleTypeEnum,
    EventFieldToMatchTypeEnum,
    IoCTypeToMatchEnum,
    OffenceSeverityEnum
)
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from app.modules.device_interaction.services import DeviceService
from app.modules.indicators import schemas as indicator_schemas
from app.modules.indicators.services import IndicatorService
# --- ДОДАНО: Імпорти для сервісів реагування та взаємодії з пристроями ---
from app.modules.response.services import ResponseService
from . import schemas as correlation_schemas
from ..apt_groups.services import APTGroupService


class CorrelationService:
    # --- CRUD для CorrelationRule (без змін) ---
    def create_correlation_rule(self, db: Session,
                                rule_create: correlation_schemas.CorrelationRuleCreate) -> CorrelationRule:
        if rule_create.rule_type == CorrelationRuleTypeEnum.IOC_MATCH_IP:
            if not rule_create.event_field_to_match or not rule_create.ioc_type_to_match:
                raise ValueError("For IOC_MATCH_IP rules, 'event_field_to_match' and 'ioc_type_to_match' are required.")
        elif rule_create.rule_type in [CorrelationRuleTypeEnum.THRESHOLD_LOGIN_FAILURES,
                                       CorrelationRuleTypeEnum.THRESHOLD_DATA_EXFILTRATION]:
            if not rule_create.threshold_count or not rule_create.threshold_time_window_minutes or not rule_create.aggregation_fields:
                raise ValueError(
                    "For threshold rules, 'threshold_count', 'threshold_time_window_minutes', and 'aggregation_fields' are required.")
        db_rule = CorrelationRule(**rule_create.model_dump());
        db.add(db_rule);
        db.commit();
        db.refresh(db_rule);
        return db_rule

    def get_correlation_rule_by_id(self, db: Session, rule_id: int) -> Optional[CorrelationRule]:
        return db.query(CorrelationRule).filter(CorrelationRule.id == rule_id).first()

    def get_all_correlation_rules(self, db: Session, skip: int = 0, limit: int = 100, only_enabled: bool = False) -> \
            List[CorrelationRule]:
        query = db.query(CorrelationRule)
        if only_enabled: query = query.filter(CorrelationRule.is_enabled == True)
        return query.order_by(CorrelationRule.id).offset(skip).limit(limit).all()

    def update_correlation_rule(self, db: Session, rule_id: int,
                                rule_update: correlation_schemas.CorrelationRuleUpdate) -> Optional[CorrelationRule]:
        db_rule = self.get_correlation_rule_by_id(db, rule_id)
        if not db_rule: return None
        update_data = rule_update.model_dump(exclude_unset=True)
        for key, value in update_data.items(): setattr(db_rule, key, value)
        db.add(db_rule);
        db.commit();
        db.refresh(db_rule);
        return db_rule

    def delete_correlation_rule(self, db: Session, rule_id: int) -> bool:
        db_rule = self.get_correlation_rule_by_id(db, rule_id)
        if db_rule: db.delete(db_rule); db.commit(); return True
        return False

    # --- CRUD для Offence (без змін) ---
    def create_offence(self, db: Session, offence_create: correlation_schemas.OffenceCreate) -> Offence:
        db_offence = Offence(**offence_create.model_dump());
        db.add(db_offence);
        db.commit();
        db.refresh(db_offence)
        print(
            f"CREATED OFFENCE: ID={db_offence.id}, Title='{db_offence.title}', Severity='{db_offence.severity.value}'")
        return db_offence

    def get_offence_by_id(self, db: Session, offence_id: int) -> Optional[Offence]:
        return db.query(Offence).filter(Offence.id == offence_id).first()

    def get_all_offences(self, db: Session, skip: int = 0, limit: int = 100) -> List[Offence]:
        return db.query(Offence).order_by(Offence.detected_at.desc()).offset(skip).limit(limit).all()

    def update_offence_status(self, db: Session, offence_id: int, status: correlation_schemas.OffenceStatusEnum,
                              notes: Optional[str] = None,
                              severity: Optional[OffenceSeverityEnum] = None
                              ) -> Optional[Offence]:
        db_offence = self.get_offence_by_id(db, offence_id)
        if not db_offence: return None
        db_offence.status = status
        if notes is not None: db_offence.notes = notes
        if severity is not None: db_offence.severity = severity
        db_offence.updated_at = datetime.now(timezone.utc)
        db.add(db_offence);
        db.commit();
        db.refresh(db_offence);
        return db_offence

    # --- Метод для завантаження дефолтних правил (якщо він тут) ---
    def load_default_rules_from_apt_data(self, db: Session, apt_data_list: List[Dict[str, Any]]) -> Dict[str, int]:
        # ... (код з попередньої відповіді) ...
        created_count = 0;
        skipped_count = 0
        print("Attempting to load default correlation rules based on APT IoC data...")
        for apt_entry in apt_data_list:
            apt_name = apt_entry.get("name")
            if not apt_name: skipped_count += 2; continue
            safe_apt_name_tag = "apt:" + "".join(c if c.isalnum() else '_' for c in apt_name).lower()

            rules_to_check_create = [
                {"name_suffix": "IP IoCs (Outbound)", "event_field": EventFieldToMatchTypeEnum.DESTINATION_IP,
                 "title_template": f"Outbound Traffic to {apt_name} IoC: {{event[source_ip]}} -> {{ioc_value}}"},
                {"name_suffix": "IP IoCs (Inbound)", "event_field": EventFieldToMatchTypeEnum.SOURCE_IP,
                 "title_template": f"Inbound Traffic from {apt_name} IoC: {{ioc_value}} -> {{event[destination_ip]}}"}
            ]
            for r_data in rules_to_check_create:
                rule_name = f"Default: Traffic {r_data['name_suffix'].split(' ')[0]} {apt_name} {r_data['name_suffix'].split(' ')[1]}"  # Формуємо назву
                existing_rule = db.query(CorrelationRule).filter(CorrelationRule.name == rule_name).first()
                if not existing_rule:
                    rule_create_schema = correlation_schemas.CorrelationRuleCreate(
                        name=rule_name,
                        description=f"Detects network traffic to/from IP addresses associated with {apt_name} ({safe_apt_name_tag}). Field: {r_data['event_field'].value}",
                        is_enabled=True, rule_type=CorrelationRuleTypeEnum.IOC_MATCH_IP,
                        event_source_type=["netflow", "syslog_firewall"],
                        event_field_to_match=r_data['event_field'],
                        ioc_type_to_match=IoCTypeToMatchEnum.IPV4_ADDR,
                        ioc_tags_match=[safe_apt_name_tag], ioc_min_confidence=50,
                        generated_offence_title_template=r_data['title_template'],
                        generated_offence_severity=OffenceSeverityEnum.HIGH)
                    try:
                        self.create_correlation_rule(db, rule_create_schema);
                        created_count += 1;
                        print(
                            f"CREATED default rule: {rule_name}")
                    except Exception as e:
                        print(f"Error creating default rule '{rule_name}': {e}");
                        skipped_count += 1
                else:
                    skipped_count += 1
        print(f"Default IoC-match rule loading. Created: {created_count}, Skipped: {skipped_count}")
        return {"created": created_count, "skipped": skipped_count}

    def get_offences_summary_by_severity(self, db: Session, days_back: int) -> Dict[str, int]:
        """
        Повертає кількість офенсів за вказаний період, згрупованих за серйозністю.
        """
        time_from = datetime.now(timezone.utc) - timedelta(days=days_back)

        # Використовуємо SQLAlchemy агрегацію
        # Offence.severity - це SAEnum(OffenceSeverityEnum)
        query_result = db.query(
            Offence.severity,
            func.count(Offence.id)
        ).filter(
            Offence.detected_at >= time_from
        ).group_by(
            Offence.severity
        ).all()

        summary = {sev.value: 0 for sev in OffenceSeverityEnum}  # Ініціалізуємо всіма можливими серйозностями
        for severity_enum, count in query_result:
            if severity_enum:  # Перевірка, що severity_enum не None
                summary[severity_enum.value] = count
        return summary

    def get_recent_offences(self, db: Session, limit: int = 10) -> List[Offence]:
        """Повертає список останніх N офенсів."""
        return db.query(Offence).order_by(Offence.detected_at.desc()).limit(limit).all()

    def get_top_triggered_iocs_from_offences(self, db: Session, limit: int = 10, days_back: int = 7) -> List[
        Dict[str, Any]]:
        """
        Повертає топ-N IoC, на які найчастіше спрацьовували правила, на основі даних з офенсів.
        Повертає список словників: [{"ioc_value": "1.2.3.4", "ioc_type": "ipv4-addr", "trigger_count": 5}, ...]
        """
        time_from = datetime.now(timezone.utc) - timedelta(days=days_back)

        # Це складний запит, оскільки matched_ioc_details - це JSONB.
        # Ми можемо або витягнути всі офенси і агрегувати в Python, або написати складний SQL.
        # Для MVP, агрегація в Python може бути простішою.

        offences_in_period = db.query(Offence.matched_ioc_details).filter(
            Offence.detected_at >= time_from,
            Offence.matched_ioc_details.isnot(None)  # Переконуємося, що поле не NULL
        ).all()

        ioc_counts: Dict[tuple, int] = {}  # (value, type) -> count
        for offence_details_tuple in offences_in_period:
            ioc_detail = offence_details_tuple[0]  # matched_ioc_details - це перший елемент кортежу
            if isinstance(ioc_detail, dict):  # Перевірка, чи це словник
                ioc_value = ioc_detail.get("value")
                ioc_type = ioc_detail.get("type")  # Це вже буде рядок, бо Pydantic схема так зберігає
                if ioc_value and ioc_type:
                    key = (str(ioc_value), str(ioc_type))
                    ioc_counts[key] = ioc_counts.get(key, 0) + 1

        # Сортуємо та беремо топ-N
        sorted_iocs = sorted(ioc_counts.items(), key=lambda item: item[1], reverse=True)

        top_iocs = [{"ioc_value": val_type[0], "ioc_type": val_type[1], "trigger_count": count}
                    for (val_type, count) in sorted_iocs[:limit]]
        return top_iocs

    def get_offences_by_apt_from_iocs(self, db: Session, apt_service: APTGroupService, days_back: int = 7) -> List[
        Dict[str, Any]]:
        """
        Повертає кількість офенсів, згрупованих за APT.
        Використовує attributed_apt_group_ids з matched_ioc_details в офенсах.
        """
        time_from = datetime.now(timezone.utc) - timedelta(days=days_back)

        offences_in_period = db.query(Offence.matched_ioc_details, Offence.attributed_apt_group_ids).filter(
            Offence.detected_at >= time_from
        ).all()  # Завантажуємо поле attributed_apt_group_ids з офенса

        apt_offence_counts: Dict[int, Dict[str, Any]] = {}  # apt_id -> {"name": "APT Name", "count": X}

        for offence_tuple in offences_in_period:
            # attributed_apt_ids_in_offence - це список ID APT, напряму збережений в офенсі
            attributed_apt_ids_in_offence = offence_tuple.attributed_apt_group_ids or []

            # Якщо attributed_apt_group_ids не зберігається в офенсі, а тільки в matched_ioc_details:
            # ioc_detail = offence_tuple.matched_ioc_details
            # if isinstance(ioc_detail, dict):
            #     apt_ids_from_ioc = ioc_detail.get("attributed_apt_group_ids", [])
            #     if isinstance(apt_ids_from_ioc, list):
            #         for apt_id in apt_ids_from_ioc:
            #             # ... (логіка підрахунку)

            for apt_id in attributed_apt_ids_in_offence:
                if apt_id not in apt_offence_counts:
                    apt_group_db = apt_service.get_apt_group_by_id(db, apt_id)
                    apt_name = apt_group_db.name if apt_group_db else f"Unknown APT ID {apt_id}"
                    apt_offence_counts[apt_id] = {"apt_id": apt_id, "apt_name": apt_name, "offence_count": 0}
                apt_offence_counts[apt_id]["offence_count"] += 1

        return list(apt_offence_counts.values())

    # --- Логіка Correlation Engine (оновлена з викликом ResponseService) ---
    def run_correlation_cycle(self,
                              db: Session,
                              es_writer: ElasticsearchWriter,
                              indicator_service: IndicatorService,
                              device_service: DeviceService,  # <--- Додано для ResponseService
                              response_service: ResponseService  # <--- Додано екземпляр ResponseService
                              ):
        print(f"\n--- Running Correlation Cycle at {datetime.now(timezone.utc)} ---")
        if not es_writer or not es_writer.es_client:
            print("CorrelationEngine: Elasticsearch client not available. Skipping cycle.")
            return

        es_client: Elasticsearch = es_writer.es_client  # type: ignore
        active_rules = self.get_all_correlation_rules(db, only_enabled=True, limit=1000)
        if not active_rules:
            print("CorrelationEngine: No active correlation rules found. Skipping cycle.")
            return
        print(f"CorrelationEngine: Loaded {len(active_rules)} active rules.")

        for rule in active_rules:
            print(f"\nCorrelationEngine: Processing rule '{rule.name}' (ID: {rule.id}, Type: {rule.rule_type.value})")
            time_window_minutes = rule.threshold_time_window_minutes or 60
            time_from = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)

            # --- Обробка IOC_MATCH_IP ---
            if rule.rule_type == CorrelationRuleTypeEnum.IOC_MATCH_IP:
                if not rule.event_field_to_match or not rule.ioc_type_to_match: print(
                    f"Rule '{rule.name}' IOC_MATCH_IP missing fields."); continue
                ioc_query_filters = [{"term": {"is_active": True}}]  # is_active - boolean, term працює

                # Для поля 'type', оскільки воно вже типу 'keyword', .keyword не потрібен
                if rule.ioc_type_to_match:
                    ioc_query_filters.append(
                        {"term": {"type": rule.ioc_type_to_match.value}}
                    )

                # Для поля 'tags', оскільки воно теж 'keyword', .keyword не потрібен
                if rule.ioc_tags_match:
                    # 'terms' query ефективніший для пошуку по кількох значеннях, але 'term' для кожного тегу теж працює
                    ioc_query_filters.append({"terms": {"tags": rule.ioc_tags_match}})

                if rule.ioc_min_confidence is not None:
                    ioc_query_filters.append(
                        {"range": {"confidence": {"gte": rule.ioc_min_confidence}}}
                    )
                ioc_query_body = {"query": {"bool": {"filter": ioc_query_filters}}, "size": 10000}
                try:
                    relevant_iocs_resp = es_client.search(index="siem-iocs-*", body=ioc_query_body)
                    active_iocs_for_rule_map: Dict[str, indicator_schemas.IoCResponse] = {}
                    for hit in relevant_iocs_resp.get('hits', {}).get('hits', []):
                        ioc_data = hit.get('_source', {})
                        ioc_data['ioc_id'] = hit.get('_id')
                        try:
                            ioc_obj = indicator_schemas.IoCResponse(**ioc_data)
                            active_iocs_for_rule_map[
                                ioc_obj.value] = ioc_obj
                        except ValidationError as e:
                            print(e)
                            pass
                except es_exceptions.ElasticsearchWarning as e_ioc:
                    print(f"Error fetching IoCs for rule '{rule.name}': {e_ioc}")
                    continue
                if not active_iocs_for_rule_map: continue
                event_field_to_check = rule.event_field_to_match.value
                ioc_values_list = list(active_iocs_for_rule_map.keys())

                # --- Зміни в логіці формування запиту ---

                # 1. Список фільтрів тепер значно простіший.
                all_event_filters = [
                    # 1.1. Жорсткий фільтр за часом по полю `timestamp` з використанням date math.
                    {
                        "range": {
                            "timestamp": {
                                "gte": "now-1h",
                                "lte": "now"
                            }
                        }
                    },
                    # 1.2. Фільтр наявності поля, яке перевіряється.
                    {"exists": {"field": event_field_to_check}},
                    # 1.3. Фільтр, що перевіряє збіг значення поля з одним з IoC.
                    {"terms": {event_field_to_check: ioc_values_list}}
                ]

                # 2. Блок фільтрації за event_category/event_type ПОВНІСТЮ ВИДАЛЕНО,
                #    оскільки його немає у вашому бажаному запиті.

                # 3. Фінальний запит до Elasticsearch згідно вашого зразка.
                event_query_body = {
                    "query": {
                        "bool": {
                            "filter": all_event_filters
                        }
                    },
                    "size": 10,  # Змінено з 200 на 10
                    "sort": [{"timestamp": "desc"}]  # Змінено з @timestamp на timestamp
                }

                # Відлагоджувальний вивід
                # print(f"DEBUG: Executing event search query for rule '{rule.name}':")
                # print(json.dumps(event_query_body, indent=2))

                # --- КРОК 3: Виконання запиту та обробка результатів (з мінімальними змінами) ---
                try:
                    events_resp = es_client.search(
                        index=["siem-syslog-events-*", "siem-netflow-events-*"],
                        body=event_query_body
                    )
                    events_to_process = [hit['_source'] for hit in events_resp.get('hits', {}).get('hits', [])]

                    if not events_to_process:
                        print("CorrelationEngine: No matching events found for this cycle.")

                    for event_doc in events_to_process:
                        field_value_in_event = event_doc.get(event_field_to_check)
                        if str(field_value_in_event) in active_iocs_for_rule_map:
                            matched_ioc_obj = active_iocs_for_rule_map[str(field_value_in_event)]
                            if matched_ioc_obj:
                                # Спрощено отримання часу, оскільки ми шукаємо тільки по 'timestamp'
                                event_time = event_doc.get('timestamp', 'N/A')

                                offence_title = rule.generated_offence_title_template.format(
                                    ioc_value=matched_ioc_obj.value,
                                    ioc_type=str(matched_ioc_obj.type),
                                    event_source_ip=event_doc.get('source_ip', 'N/A'),
                                    event_destination_ip=event_doc.get('destination_ip', 'N/A'),
                                    event_hostname=event_doc.get('hostname', 'N/A'),
                                    event=event_doc
                                )

                                # Спрощено словник, оскільки @timestamp більше не релевантний для запиту
                                trigger_event_summary_dict = {k: str(v)[:250] for k, v in event_doc.items() if
                                                              k in ['timestamp', 'reporter_ip', 'hostname',
                                                                    'message', 'source_ip', 'destination_ip',
                                                                    'event_category', 'event_type']}

                                matched_ioc_details_dict = matched_ioc_obj.model_dump(mode='json')

                                offence_create_data = correlation_schemas.OffenceCreate(title=offence_title,
                                                                                        description=f"Rule '{rule.name}' matched IoC '{matched_ioc_obj.value}'. Event (reporter: {event_doc.get('reporter_ip')}, timestamp: {event_time})",
                                                                                        severity=rule.generated_offence_severity,
                                                                                        correlation_rule_id=rule.id,
                                                                                        triggering_event_summary=trigger_event_summary_dict,
                                                                                        matched_ioc_details=matched_ioc_details_dict,
                                                                                        attributed_apt_group_ids=matched_ioc_obj.attributed_apt_group_ids or [])
                                db_offence = self.create_offence(db, offence_create_data)
                                if db_offence:
                                    try:
                                        response_service.execute_response_for_offence(db, db_offence, device_service)
                                    except Exception as e_resp:
                                        print(
                                            f"CorrelationEngine: Error during response execution for offence ID {db_offence.id}: {e_resp}")

                except es_exceptions.ElasticsearchWarning as e_evt:
                    print(f"CorrelationEngine: Error fetching events for rule '{rule.name}': {e_evt}")
                    # continue

            # --- Обробка THRESHOLD_LOGIN_FAILURES ---
            elif rule.rule_type == CorrelationRuleTypeEnum.THRESHOLD_LOGIN_FAILURES:
                if not all([rule.threshold_count, rule.aggregation_fields, rule.threshold_time_window_minutes]):
                    print(f"Rule '{rule.name}' THRESHOLD_LOGIN_FAILURES missing required fields.")
                    # continue

                # --- 1. Формування тіла запиту (виправлено) ---

                # Універсальний фільтр часу, що працює з полями @timestamp та timestamp
                threshold_query_body = {
                    "size": 0,
                    "query": {
                        "bool": {
                            "filter": [
                                {
                                    "bool": {
                                        "should": [
                                            {"range": {"@timestamp": {"gte": "now-1h"}}},
                                            {"range": {"timestamp": {"gte": "now-1h"}}}
                                        ],
                                        "minimum_should_match": 1
                                    }
                                },
                                {
                                    "term": {
                                        "event_category": "authentication"
                                    }
                                },
                                {
                                    "term": {
                                        "event_outcome.keyword": "failure"
                                    }
                                }
                            ]
                        }
                    },
                    "aggs": {
                        "failed_logins_by_combination": {
                            "composite": {
                                "size": 1000,
                                "sources": [
                                    {"target_host": {"terms": {"field": "hostname.keyword"}}},
                                    {"reporter_device": {"terms": {"field": "reporter_ip"}}}
                                ]
                            }
                        }
                    }
                }

                # print("DEBUG: Executing aggregation query:", json.dumps(threshold_query_body, indent=2))

                # --- 3. Виконання запиту та обробка результатів (обробка ключів виправлена) ---
                try:
                    current_response = es_client.search(index=["siem-syslog-events-*", "siem-netflow-events-*"],
                                                        body=threshold_query_body)

                    # Цикл для обробки всіх сторінок результатів агрегації (пагінація)
                    while True:
                        aggregation_results = current_response.get('aggregations', {}).get(
                            'failed_logins_by_combination', {})
                        buckets = aggregation_results.get('buckets', [])

                        if not buckets:
                            break

                        for bucket in buckets:
                            failed_count = bucket.get('doc_count', 0)

                            if failed_count >= rule.threshold_count:
                                aggregation_key_dict = bucket.get('key', {})

                                # Формуємо рядок з ключів агрегації (виправлено)
                                # Тепер він буде виглядати як "hostname='host-1', reporter_ip='1.2.3.4'"
                                aggregation_key_str = ", ".join([f"{k}='{v}'" for k, v in aggregation_key_dict.items()])

                                offence_title = rule.generated_offence_title_template.format(
                                    aggregation_key_info=aggregation_key_str,
                                    actual_count=failed_count,
                                    time_window_minutes=rule.threshold_time_window_minutes
                                )

                                offence_create_data = correlation_schemas.OffenceCreate(
                                    title=offence_title,
                                    description=f"Rule '{rule.name}' triggered. Details: {aggregation_key_str}. Count: {failed_count} failures in {rule.threshold_time_window_minutes} min.",
                                    severity=rule.generated_offence_severity,
                                    correlation_rule_id=rule.id,
                                    triggering_event_summary={
                                        "aggregation_key": aggregation_key_dict,
                                        "count": failed_count
                                    }
                                )

                                db_offence = self.create_offence(db, offence_create_data)
                                # ... (логіка реагування на offence)

                        # Перевіряємо, чи є наступна сторінка результатів
                        after_key = aggregation_results.get('after_key')
                        if not after_key:
                            break  # Немає наступної сторінки, виходимо з циклу

                        # Готуємо запит для отримання наступної сторінки
                        threshold_query_body['aggs']['failed_logins_by_combination']['composite']['after'] = after_key
                        current_response = es_client.search(index=["siem-syslog-events-*", "siem-netflow-events-*"],
                                                            body=threshold_query_body)

                except es_exceptions.ElasticsearchWarning as e_agg_login:
                    print(f"CorrelationEngine: Error during aggregation for rule '{rule.name}': {e_agg_login}")
                    # continue

            # --- Обробка THRESHOLD_DATA_EXFILTRATION ---
            elif rule.rule_type == CorrelationRuleTypeEnum.THRESHOLD_DATA_EXFILTRATION:
                # ... (код для THRESHOLD_DATA_EXFILTRATION з попередньої відповіді, включаючи створення offence_create_data)
                if not rule.threshold_count or not rule.aggregation_fields or not rule.threshold_time_window_minutes: print(
                    f"Rule '{rule.name}' THRESHOLD_DATA_EXFILTRATION missing fields."); continue
                sources_for_composite = [{"term_agg_" + str(i): {"terms": {"field": f"{field.value}.keyword"}}} for
                                         i, field in enumerate(rule.aggregation_fields)]
                exfil_query_body = {
                    "query": {"bool": {"filter": [{"range": {"@timestamp": {"gte": time_from.isoformat()}}}]}},
                    "aggs": {"exfiltration_agg": {"composite": {"sources": sources_for_composite, "size": 100},
                                                  "aggs": {"total_bytes_sum": {"sum": {
                                                      "field": EventFieldToMatchTypeEnum.NETWORK_BYTES_TOTAL.value}}}}},
                    "size": 0}
                if rule.event_source_type and not any(
                        est in ["netflow", "flow"] for est in rule.event_source_type): print(
                    f"Rule '{rule.name}' exfil usually uses 'netflow', found {rule.event_source_type}.")
                try:
                    current_response = es_client.search(index="siem-netflow-events-*", body=exfil_query_body)
                    while True:
                        buckets = current_response.get('aggregations', {}).get('exfiltration_agg', {}).get('buckets',
                                                                                                           [])
                        if not buckets: break
                        for bucket in buckets:
                            aggregation_key_dict = bucket.get('key', {});
                            total_bytes = bucket.get('total_bytes_sum', {}).get('value', 0)
                            if total_bytes >= rule.threshold_count:
                                aggregation_key_str = ", ".join(
                                    [f"{k.replace('term_agg_', '').split('.')[0]}='{v}'" for k, v in
                                     aggregation_key_dict.items()])
                                offence_title = rule.generated_offence_title_template.format(
                                    aggregation_key_info=aggregation_key_str, actual_sum_bytes=total_bytes,
                                    time_window_minutes=rule.threshold_time_window_minutes)
                                offence_create_data = correlation_schemas.OffenceCreate(title=offence_title,
                                                                                        description=f"Rule '{rule.name}' triggered: {aggregation_key_str} with {total_bytes} bytes in {rule.threshold_time_window_minutes}m.",
                                                                                        severity=rule.generated_offence_severity,
                                                                                        correlation_rule_id=rule.id,
                                                                                        triggering_event_summary={
                                                                                            "aggregation_key": aggregation_key_dict,
                                                                                            "sum_bytes": total_bytes})
                                db_offence = self.create_offence(db, offence_create_data)
                                if db_offence:
                                    try:
                                        response_service.execute_response_for_offence(db, db_offence, device_service)
                                    except Exception as e_resp:
                                        print(
                                            f"CorrelationEngine: Error response for offence ID {db_offence.id}: {e_resp}")
                        after_key = current_response.get('aggregations', {}).get('exfiltration_agg', {}).get(
                            'after_key')
                        if not after_key: break
                        exfil_query_body['aggs']['exfiltration_agg']['composite']['after'] = after_key
                        current_response = es_client.search(index="siem-netflow-events-*", body=exfil_query_body)
                except es_exceptions.ElasticsearchWarning as e_agg_exfil:
                    print(f"CorrelationEngine: Error aggregation for exfil rule '{rule.name}': {e_agg_exfil}");
                    continue

            else:
                print(f"CorrelationEngine: Rule type '{rule.rule_type.value}' not implemented for rule '{rule.name}'.")

        print(f"--- Correlation Cycle Finished at {datetime.now(timezone.utc)} ---")
