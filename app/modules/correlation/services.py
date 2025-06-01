# app/modules/correlation/services.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from . import schemas as correlation_schemas
from app.database.postgres_models.correlation_models import CorrelationRule, Offence
# Переконайся, що всі Enum типи імпортовані для використання
from app.modules.correlation.schemas import (
    CorrelationRuleTypeEnum,
    EventFieldToMatchTypeEnum,
    IoCTypeToMatchEnum,
    OffenceSeverityEnum,
    OffenceStatusEnum
)

from app.modules.indicators.services import IndicatorService
from app.modules.indicators import schemas as indicator_schemas
# from app.modules.apt_groups.services import APTGroupService # Для деталей APT в офенсі, якщо потрібно
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from pydantic import ValidationError


class CorrelationService:
    def load_default_rules_from_apt_data(self, db: Session, apt_data_list: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Завантажує дефолтні правила кореляції на основі даних про APT та їх IoC.
        Створює правила для виявлення трафіку до/з IP-адрес, пов'язаних з APT.

        Args:
            db: Сесія бази даних SQLAlchemy.
            apt_data_list: Список словників, де кожен словник представляє APT-групу та її IoC
                           (структура аналогічна apt_iocs_data.json).

        Returns:
            Словник зі статистикою: {"created": count, "skipped": count}.
        """
        created_count = 0
        skipped_count = 0

        print("Attempting to load default correlation rules based on APT IoC data...")

        for apt_entry in apt_data_list:
            apt_name = apt_entry.get("name")
            iocs = apt_entry.get("iocs", [])

            if not apt_name:
                print(f"Skipping entry due to missing APT name: {apt_entry.get('apt_id_placeholder')}")
                skipped_count += 2  # Припускаємо, що для кожного APT мало б бути 2 правила
                continue

            # Генеруємо безпечне ім'я APT для тегу (як в IndicatorService)
            safe_apt_name_tag = "apt:" + "".join(c if c.isalnum() else '_' for c in apt_name).lower()

            # Перевіряємо, чи є у цієї APT хоча б один IPv4 IoC у наданих даних.
            # Це лише для того, щоб вирішити, чи створювати правила для цього APT.
            # Самі правила будуть покладатися на теги, а не на конкретні IoC з цього файлу.
            has_ipv4_ioc = any(ioc.get("type") == "ipv4-addr" for ioc in iocs)

            if not has_ipv4_ioc:
                # print(f"No IPv4 IoCs found for APT '{apt_name}' in the provided data. Skipping default rule creation for it.")
                # Ми все одно можемо створити правила, що покладаються на тег,
                # навіть якщо в цьому конкретному JSON немає IPv4. Індикатори можуть бути додані з інших джерел.
                # Тому, давайте створювати правила для всіх APT з файлу.
                pass

            # --- Правило 1: Вихідний трафік на IP-адреси APT ---
            rule_name_out = f"Default: Traffic TO {apt_name} IP IoCs"
            # Перевірка, чи правило з такою назвою вже існує
            existing_rule_out = db.query(CorrelationRule).filter(CorrelationRule.name == rule_name_out).first()

            if not existing_rule_out:
                rule_desc_out = (
                    f"Detects outbound network traffic (e.g., NetFlow, Firewall logs) "
                    f"to IP addresses known to be associated with {apt_name} ({safe_apt_name_tag})."
                )
                rule_create_out_schema = correlation_schemas.CorrelationRuleCreate(
                    name=rule_name_out,
                    description=rule_desc_out,
                    is_enabled=True,
                    rule_type=CorrelationRuleTypeEnum.IOC_MATCH_IP,
                    event_source_type=["flow", "firewall"],  # Приклад джерел
                    event_field_to_match=EventFieldToMatchTypeEnum.DESTINATION_IP,
                    ioc_type_to_match=IoCTypeToMatchEnum.IPV4_ADDR,  # Фокусуємося на IPv4
                    ioc_tags_match=[safe_apt_name_tag],  # Основний фільтр!
                    ioc_min_confidence=50,  # Можна налаштувати
                    generated_offence_title_template=f"Outbound Traffic to {apt_name} IoC: {{event.source_ip}} -> {{ioc_value}}",
                    generated_offence_severity=OffenceSeverityEnum.HIGH  # Можна налаштувати
                )
                try:
                    self.create_correlation_rule(db, rule_create_out_schema)
                    print(f"CREATED default rule: {rule_name_out}")
                    created_count += 1
                except Exception as e:
                    print(f"Error creating default rule '{rule_name_out}': {e}")
                    skipped_count += 1
            else:
                # print(f"SKIPPED (already exists): {rule_name_out}")
                skipped_count += 1

            # --- Правило 2: Вхідний трафік З IP-адрес APT ---
            rule_name_in = f"Default: Traffic FROM {apt_name} IP IoCs"
            existing_rule_in = db.query(CorrelationRule).filter(CorrelationRule.name == rule_name_in).first()

            if not existing_rule_in:
                rule_desc_in = (
                    f"Detects inbound network traffic (e.g., NetFlow, Firewall logs) "
                    f"from IP addresses known to be associated with {apt_name} ({safe_apt_name_tag})."
                )
                rule_create_in_schema = correlation_schemas.CorrelationRuleCreate(
                    name=rule_name_in,
                    description=rule_desc_in,
                    is_enabled=True,
                    rule_type=CorrelationRuleTypeEnum.IOC_MATCH_IP,
                    event_source_type=["flow", "firewall"],
                    event_field_to_match=EventFieldToMatchTypeEnum.SOURCE_IP,
                    ioc_type_to_match=IoCTypeToMatchEnum.IPV4_ADDR,
                    ioc_tags_match=[safe_apt_name_tag],
                    ioc_min_confidence=50,
                    generated_offence_title_template=f"Inbound Traffic from {apt_name} IoC: {{ioc_value}} -> {{event.destination_ip}}",
                    generated_offence_severity=OffenceSeverityEnum.MEDIUM
                )
                try:
                    self.create_correlation_rule(db, rule_create_in_schema)
                    print(f"CREATED default rule: {rule_name_in}")
                    created_count += 1
                except Exception as e:
                    print(f"Error creating default rule '{rule_name_in}': {e}")
                    skipped_count += 1
            else:
                # print(f"SKIPPED (already exists): {rule_name_in}")
                skipped_count += 1

        print(
            f"Default rule loading complete. Created: {created_count}, Skipped (or already existing): {skipped_count}")
        return {"created": created_count, "skipped": skipped_count}

    # --- CRUD для CorrelationRule ---
    def create_correlation_rule(self, db: Session,
                                rule_create: correlation_schemas.CorrelationRuleCreate) -> CorrelationRule:
        # Валідація на основі rule_type (приклад)
        if rule_create.rule_type == CorrelationRuleTypeEnum.IOC_MATCH_IP:
            if not rule_create.event_field_to_match or not rule_create.ioc_type_to_match:
                raise ValueError("For IOC_MATCH_IP rules, 'event_field_to_match' and 'ioc_type_to_match' are required.")
        elif rule_create.rule_type in [CorrelationRuleTypeEnum.THRESHOLD_LOGIN_FAILURES,
                                       CorrelationRuleTypeEnum.THRESHOLD_DATA_EXFILTRATION]:
            if not rule_create.threshold_count or not rule_create.threshold_time_window_minutes or not rule_create.aggregation_fields:
                raise ValueError(
                    "For threshold rules, 'threshold_count', 'threshold_time_window_minutes', and 'aggregation_fields' are required.")

        db_rule = CorrelationRule(**rule_create.model_dump())
        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)
        return db_rule

    def get_correlation_rule_by_id(self, db: Session, rule_id: int) -> Optional[CorrelationRule]:
        return db.query(CorrelationRule).filter(CorrelationRule.id == rule_id).first()

    def get_all_correlation_rules(self, db: Session, skip: int = 0, limit: int = 100, only_enabled: bool = True) -> \
            List[CorrelationRule]:
        query = db.query(CorrelationRule)
        if only_enabled:
            query = query.filter(CorrelationRule.is_enabled == True)
        return query.order_by(CorrelationRule.id).offset(skip).limit(limit).all()

    def update_correlation_rule(self, db: Session, rule_id: int,
                                rule_update: correlation_schemas.CorrelationRuleUpdate) -> Optional[CorrelationRule]:
        db_rule = self.get_correlation_rule_by_id(db, rule_id)
        if not db_rule:
            return None
        update_data = rule_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_rule, key, value)
        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)
        return db_rule

    def delete_correlation_rule(self, db: Session, rule_id: int) -> bool:
        db_rule = self.get_correlation_rule_by_id(db, rule_id)
        if db_rule:
            db.delete(db_rule)
            db.commit()
            return True
        return False

    # --- CRUD для Offence ---
    def create_offence(self, db: Session, offence_create: correlation_schemas.OffenceCreate) -> Offence:
        db_offence = Offence(**offence_create.model_dump())
        db.add(db_offence)
        db.commit()
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
        db.refresh(db_offence)
        return db_offence

    # --- Логіка Correlation Engine ---
    def run_correlation_cycle(self,
                              db: Session,
                              es_writer: ElasticsearchWriter,
                              indicator_service: IndicatorService
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

            # --- Часове вікно для запитів до ES ---
            # Використовуємо правило, якщо воно для порогового значення, або дефолтне (напр., 1 година)
            time_window_minutes = rule.threshold_time_window_minutes or 60
            time_from = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)

            # --------------------------------------------------------------------
            # Rule Type: IOC_MATCH_IP
            # --------------------------------------------------------------------
            if rule.rule_type == CorrelationRuleTypeEnum.IOC_MATCH_IP:
                if not rule.event_field_to_match or not rule.ioc_type_to_match:
                    print(f"CorrelationEngine: Rule '{rule.name}' (IOC_MATCH_IP) missing critical fields. Skipping.")
                    continue
                # ... (Код для IOC_MATCH_IP з попередньої відповіді, але з коректним використанням Enum)
                ioc_query_filters = [{"term": {"is_active": True}}]
                if rule.ioc_type_to_match:  # Переконуємося, що це Enum
                    ioc_query_filters.append({"term": {"type.keyword": rule.ioc_type_to_match.value}})
                if rule.ioc_tags_match:
                    for tag in rule.ioc_tags_match: ioc_query_filters.append({"term": {"tags.keyword": tag}})
                if rule.ioc_min_confidence is not None:
                    ioc_query_filters.append({"range": {"confidence": {"gte": rule.ioc_min_confidence}}})

                ioc_query_body = {"query": {"bool": {"filter": ioc_query_filters}}, "size": 10000}
                try:
                    relevant_iocs_resp = es_client.search(index="siem-iocs-*", body=ioc_query_body)
                    active_iocs_for_rule_map: Dict[str, indicator_schemas.IoCResponse] = {}  # value -> IoC_object
                    for hit in relevant_iocs_resp.get('hits', {}).get('hits', []):
                        ioc_data = hit.get('_source', {});
                        ioc_data['ioc_id'] = hit.get('_id')
                        try:
                            ioc_obj = indicator_schemas.IoCResponse(**ioc_data)
                            active_iocs_for_rule_map[ioc_obj.value] = ioc_obj
                        except ValidationError:
                            pass
                except es_exceptions.ElasticsearchWarning as e_ioc:
                    print(f"CorrelationEngine: Error fetching IoCs for rule '{rule.name}': {e_ioc}");
                    continue
                if not active_iocs_for_rule_map: continue

                event_field_to_check = rule.event_field_to_match.value  # Отримуємо рядок з Enum
                event_query_body = {"query": {"bool": {"must": [{"exists": {"field": event_field_to_check}}, {
                    "terms": {f"{event_field_to_check}.keyword": list(active_iocs_for_rule_map.keys())}}], "filter": [
                    {"range": {"@timestamp": {"gte": time_from.isoformat()}}}]}}, "size": 200,
                                    "sort": [{"@timestamp": "desc"}]}  # Використовуємо @timestamp
                if rule.event_source_type:
                    event_source_terms = [{"term": {"event_category.keyword": est}} for est in rule.event_source_type]
                    if event_source_terms: event_query_body["query"]["bool"]["filter"].append(
                        {"bool": {"should": event_source_terms, "minimum_should_match": 1}})
                try:
                    events_resp = es_client.search(index=["siem-syslog-events-*", "siem-netflow-events-*"],
                                                   body=event_query_body)
                    events_to_process = [hit['_source'] for hit in events_resp.get('hits', {}).get('hits', [])]
                except es_exceptions.ElasticsearchWarning as e_evt:
                    print(f"CorrelationEngine: Error fetching events for rule '{rule.name}': {e_evt}");
                    continue

                for event_doc in events_to_process:
                    field_value_in_event = event_doc.get(event_field_to_check)
                    if str(field_value_in_event) in active_iocs_for_rule_map:
                        matched_ioc_obj = active_iocs_for_rule_map[str(field_value_in_event)]
                        # ... (Генерація та збереження офенса як раніше) ...
                        offence_title = rule.generated_offence_title_template.format(ioc_value=matched_ioc_obj.value,
                                                                                     ioc_type=str(matched_ioc_obj.type),
                                                                                     event_source_ip=event_doc.get(
                                                                                         'source_ip', 'N/A'),
                                                                                     event_destination_ip=event_doc.get(
                                                                                         'destination_ip', 'N/A'),
                                                                                     event_hostname=event_doc.get(
                                                                                         'hostname', 'N/A'))
                        trigger_event_summary_dict = {k: str(v)[:250] for k, v in event_doc.items() if
                                                      k in ['timestamp', '@timestamp', 'reporter_ip', 'hostname',
                                                            'message', 'source_ip', 'destination_ip', 'event_category',
                                                            'event_type']}
                        matched_ioc_details_dict = matched_ioc_obj.model_dump(mode='json')
                        offence_create_data = correlation_schemas.OffenceCreate(title=offence_title,
                                                                                description=f"Rule '{rule.name}' matched IoC '{matched_ioc_obj.value}'. Event (reporter: {event_doc.get('reporter_ip')}, @timestamp: {event_doc.get('@timestamp')})",
                                                                                severity=rule.generated_offence_severity,
                                                                                correlation_rule_id=rule.id,
                                                                                triggering_event_summary=trigger_event_summary_dict,
                                                                                matched_ioc_details=matched_ioc_details_dict,
                                                                                attributed_apt_group_ids=matched_ioc_obj.attributed_apt_group_ids or [])
                        self.create_offence(db, offence_create_data)
                        print(
                            f"CorrelationEngine: Offence generated by rule '{rule.name}' for IoC '{matched_ioc_obj.value}'")

            # --------------------------------------------------------------------
            # Rule Type: THRESHOLD_LOGIN_FAILURES
            # --------------------------------------------------------------------
            elif rule.rule_type == CorrelationRuleTypeEnum.THRESHOLD_LOGIN_FAILURES:
                if not rule.threshold_count or not rule.aggregation_fields or not rule.threshold_time_window_minutes:
                    print(
                        f"CorrelationEngine: Rule '{rule.name}' (THRESHOLD_LOGIN_FAILURES) missing required threshold fields. Skipping.")
                    continue

                # Визначаємо поля для агрегації (напр., username, source_ip)
                # Важливо, щоб ці поля існували в CommonEventSchema і були замаплені в ES як .keyword для точної агрегації
                es_agg_fields = [f"{field.value}.keyword" for field in rule.aggregation_fields]
                if not es_agg_fields:
                    print(f"CorrelationEngine: No valid aggregation fields for rule '{rule.name}'. Skipping.");
                    continue

                # Формуємо запит для агрегації
                # Ми хочемо групувати за КОМБІНАЦІЄЮ полів з rule.aggregation_fields.
                # Для цього найкраще підходить "composite" aggregation.
                sources_for_composite = [{"agg_field_" + str(i): {"terms": {"field": field_keyword}}}
                                         for i, field_keyword in enumerate(es_agg_fields)]

                threshold_query_body = {
                    "query": {
                        "bool": {
                            "filter": [
                                {"range": {"@timestamp": {"gte": time_from.isoformat()}}},  # Використовуємо @timestamp
                                {"term": {"event_category.keyword": "authentication"}},
                                {"term": {"event_outcome.keyword": "failure"}}
                                # Можна додати фільтр за rule.event_source_type, якщо потрібно
                            ]
                        }
                    },
                    "aggs": {
                        "failed_logins_by_combination": {
                            "composite": {
                                "sources": sources_for_composite,
                                "size": 1000  # Кількість комбінацій для повернення за раз
                            }
                            # Ми не можемо напряму підрахувати doc_count всередині composite для умови,
                            # doc_count буде для кожного bucket.
                            # Ми будемо перевіряти bucket.doc_count
                        }
                    },
                    "size": 0
                }

                # Додавання фільтра за event_source_type (наприклад, типи логів з певних систем)
                if rule.event_source_type:
                    source_type_filters = []
                    for est in rule.event_source_type:
                        # Припускаємо, що event_source_type може бути або event_category, або event_type
                        source_type_filters.append({"term": {"event_category.keyword": est}})
                        source_type_filters.append({"term": {"event_type.keyword": est}})
                    if source_type_filters:
                        threshold_query_body["query"]["bool"]["filter"].append(
                            {"bool": {"should": source_type_filters, "minimum_should_match": 1}})

                try:
                    # Припускаємо, що логи автентифікації зберігаються в індексах, що відповідають syslog
                    current_response = es_client.search(index="siem-syslog-events-*", body=threshold_query_body)

                    while True:  # Цикл для обробки пагінації composite aggregation
                        buckets = current_response.get('aggregations', {}).get('failed_logins_by_combination', {}).get(
                            'buckets', [])
                        if not buckets: break

                        for bucket in buckets:
                            failed_count = bucket.get('doc_count')
                            if failed_count >= rule.threshold_count:
                                aggregation_key_dict = bucket.get('key', {})
                                aggregation_key_str = ", ".join(
                                    [f"{k.split('_')[-1]}='{v}'" for k, v in aggregation_key_dict.items()])

                                offence_title = rule.generated_offence_title_template.format(
                                    aggregation_key_info=aggregation_key_str,
                                    actual_count=failed_count,
                                    time_window_minutes=rule.threshold_time_window_minutes
                                )
                                offence_create_data = correlation_schemas.OffenceCreate(
                                    title=offence_title,
                                    description=f"Rule '{rule.name}' triggered for {aggregation_key_str} with {failed_count} failed logins in {rule.threshold_time_window_minutes}m.",
                                    severity=rule.generated_offence_severity,
                                    correlation_rule_id=rule.id,
                                    triggering_event_summary={"aggregation_key": aggregation_key_dict,
                                                              "count": failed_count}
                                )
                                self.create_offence(db, offence_create_data)
                                print(
                                    f"CorrelationEngine: Offence generated by login threshold rule '{rule.name}' for {aggregation_key_str}")

                        after_key = current_response.get('aggregations', {}).get('failed_logins_by_combination',
                                                                                 {}).get('after_key')
                        if not after_key: break  # Немає більше сторінок
                        threshold_query_body['aggs']['failed_logins_by_combination']['composite']['after'] = after_key
                        current_response = es_client.search(index="siem-syslog-events-*", body=threshold_query_body)

                except es_exceptions.ElasticsearchWarning as e_agg_login:
                    print(
                        f"CorrelationEngine: Error during aggregation for login failures rule '{rule.name}': {e_agg_login}")
                    continue

            # --------------------------------------------------------------------
            # Rule Type: THRESHOLD_DATA_EXFILTRATION
            # --------------------------------------------------------------------
            elif rule.rule_type == CorrelationRuleTypeEnum.THRESHOLD_DATA_EXFILTRATION:
                if not rule.threshold_count or not rule.aggregation_fields or not rule.threshold_time_window_minutes:
                    print(
                        f"CorrelationEngine: Rule '{rule.name}' (THRESHOLD_DATA_EXFILTRATION) missing required fields. Skipping.")
                    continue

                # Припускаємо, що aggregation_fields = ["source_ip", "destination_ip"] або подібні
                # І ми сумуємо 'network_bytes_total'
                sources_for_composite = [{"term_agg_" + str(i): {"terms": {"field": f"{field.value}.keyword"}}}
                                         for i, field in enumerate(rule.aggregation_fields)]

                exfil_query_body = {
                    "query": {
                        "bool": {
                            "filter": [
                                {"range": {"@timestamp": {"gte": time_from.isoformat()}}},
                                # Можна додати фільтр на напрямок трафіку, якщо є такі дані
                                # Наприклад, source_ip - внутрішній, destination_ip - зовнішній.
                                # Або поле network_direction в CommonEventSchema
                            ]
                        }
                    },
                    "aggs": {
                        "exfiltration_agg": {
                            "composite": {
                                "sources": sources_for_composite,
                                "size": 100
                            },
                            "aggs": {
                                "total_bytes_sum": {  # Змінено ім'я агрегації
                                    "sum": {"field": EventFieldToMatchTypeEnum.NETWORK_BYTES_TOTAL.value}
                                }
                            }
                        }
                    },
                    "size": 0
                }
                # Додавання фільтра за event_source_type (має бути "netflow" або "flow")
                if rule.event_source_type:
                    if not any(est in ["netflow", "flow"] for est in rule.event_source_type):
                        print(
                            f"CorrelationEngine: Rule '{rule.name}' type DATA_EXFILTRATION typically uses 'netflow' or 'flow' as event_source_type, found {rule.event_source_type}. May yield no results if not applied to netflow indices.")
                    # Фільтрація за індексом вже обробляє це: index="siem-netflow-events-*"

                try:
                    current_response = es_client.search(index="siem-netflow-events-*", body=exfil_query_body)

                    while True:
                        buckets = current_response.get('aggregations', {}).get('exfiltration_agg', {}).get('buckets',
                                                                                                           [])
                        if not buckets: break

                        for bucket in buckets:
                            aggregation_key_dict = bucket.get('key', {})
                            total_bytes = bucket.get('total_bytes_sum', {}).get('value', 0)  # Використовуємо нове ім'я

                            if total_bytes >= rule.threshold_count:  # rule.threshold_count тут - це поріг у байтах
                                aggregation_key_str = ", ".join(
                                    [f"{k.replace('term_agg_', '').split('.')[0]}='{v}'" for k, v in
                                     aggregation_key_dict.items()])  # Покращене формування ключа

                                offence_title = rule.generated_offence_title_template.format(
                                    aggregation_key_info=aggregation_key_str,
                                    actual_sum_bytes=total_bytes,
                                    time_window_minutes=rule.threshold_time_window_minutes
                                )
                                offence_create_data = correlation_schemas.OffenceCreate(
                                    title=offence_title,
                                    description=f"Rule '{rule.name}' triggered for {aggregation_key_str} with {total_bytes} bytes in {rule.threshold_time_window_minutes}m.",
                                    severity=rule.generated_offence_severity,
                                    correlation_rule_id=rule.id,
                                    triggering_event_summary={"aggregation_key": aggregation_key_dict,
                                                              "sum_bytes": total_bytes}
                                )
                                self.create_offence(db, offence_create_data)
                                print(
                                    f"CorrelationEngine: Offence generated by exfiltration rule '{rule.name}' for {aggregation_key_str}")

                        after_key = current_response.get('aggregations', {}).get('exfiltration_agg', {}).get(
                            'after_key')
                        if not after_key: break
                        exfil_query_body['aggs']['exfiltration_agg']['composite']['after'] = after_key
                        current_response = es_client.search(index="siem-netflow-events-*", body=exfil_query_body)

                except es_exceptions.ElasticsearchWarning as e_agg_exfil:
                    print(
                        f"CorrelationEngine: Error during aggregation query for exfiltration rule '{rule.name}': {e_agg_exfil}")
                    continue
            else:
                print(
                    f"CorrelationEngine: Rule type '{rule.rule_type.value}' not yet implemented for rule '{rule.name}'. Skipping.")

        print(f"--- Correlation Cycle Finished at {datetime.now(timezone.utc)} ---")
