# app/modules/correlation/services.py
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from elasticsearch import Elasticsearch, exceptions as es_exceptions
from sqlalchemy.orm import Session

from app.database.postgres_models.correlation_models import CorrelationRule, Offence
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter  # Або просто es_client
from app.modules.indicators import schemas as indicator_schemas
# Для взаємодії з іншими сервісами та Elasticsearch
from app.modules.indicators.services import IndicatorService
from . import schemas as correlation_schemas
from .schemas import OffenceSeverityEnum  # Імпортуємо новий Enum


class CorrelationService:
    # --- CRUD для CorrelationRule ---
    def create_correlation_rule(self, db: Session,
                                rule_create: correlation_schemas.CorrelationRuleCreate) -> CorrelationRule:
        # rule_create.generated_offence_severity вже буде типу OffenceSeverityEnum завдяки Pydantic
        db_rule = CorrelationRule(**rule_create.model_dump())
        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)
        return db_rule

    # ... (get_correlation_rule_by_id, get_all_correlation_rules - без змін) ...
    def get_correlation_rule_by_id(self, db: Session, rule_id: int) -> Optional[CorrelationRule]:  # ...
        return db.query(CorrelationRule).filter(CorrelationRule.id == rule_id).first()

    def get_all_correlation_rules(self, db: Session, skip: int = 0, limit: int = 100, only_enabled: bool = True) -> \
            List[CorrelationRule]:  # ...
        query = db.query(CorrelationRule)
        if only_enabled: query = query.filter(CorrelationRule.is_enabled == True)
        return query.order_by(CorrelationRule.id).offset(skip).limit(limit).all()

    def update_correlation_rule(self, db: Session, rule_id: int,
                                rule_update: correlation_schemas.CorrelationRuleUpdate) -> Optional[CorrelationRule]:
        db_rule = self.get_correlation_rule_by_id(db, rule_id)
        if not db_rule: return None
        update_data = rule_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            # generated_offence_severity вже буде правильного типу Enum завдяки Pydantic
            setattr(db_rule, key, value)
        db.add(db_rule);
        db.commit();
        db.refresh(db_rule)
        return db_rule

    # ... (delete_correlation_rule - без змін) ...
    def delete_correlation_rule(self, db: Session, rule_id: int) -> bool:  # ...
        db_rule = self.get_correlation_rule_by_id(db, rule_id)
        if db_rule: db.delete(db_rule); db.commit(); return True
        return False

    # --- CRUD для Offence ---
    def create_offence(self, db: Session, offence_create: correlation_schemas.OffenceCreate) -> Offence:
        # offence_create.severity вже буде типу OffenceSeverityEnum
        db_offence = Offence(**offence_create.model_dump())
        db.add(db_offence);
        db.commit();
        db.refresh(db_offence)
        print(
            f"CREATED OFFENCE: ID={db_offence.id}, Title='{db_offence.title}', Severity='{db_offence.severity.value}'")
        return db_offence

    # ... (get_offence_by_id, get_all_offences - без змін) ...
    def get_offence_by_id(self, db: Session, offence_id: int) -> Optional[Offence]:  # ...
        return db.query(Offence).filter(Offence.id == offence_id).first()

    def get_all_offences(self, db: Session, skip: int = 0, limit: int = 100) -> List[Offence]:  # ...
        return db.query(Offence).order_by(Offence.detected_at.desc()).offset(skip).limit(limit).all()

    def update_offence_status(self, db: Session, offence_id: int, status: correlation_schemas.OffenceStatusEnum,
                              notes: Optional[str] = None,
                              severity: Optional[OffenceSeverityEnum] = None
                              # <--- Додано можливість оновлювати severity
                              ) -> Optional[Offence]:
        db_offence = self.get_offence_by_id(db, offence_id)
        if not db_offence: return None

        db_offence.status = status
        if notes is not None: db_offence.notes = notes
        if severity is not None:  # Оновлюємо серйозність, якщо передано
            db_offence.severity = severity

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
        # ... (початок методу без змін) ...
        print(f"\n--- Running Correlation Cycle at {datetime.now(timezone.utc)} ---")
        if not es_writer or not es_writer.es_client: print("CorrelationEngine: ES client not available."); return
        es_client: Elasticsearch = es_writer.es_client
        active_rules = self.get_all_correlation_rules(db, only_enabled=True, limit=1000)
        if not active_rules: print("CorrelationEngine: No active rules."); return
        print(f"CorrelationEngine: Loaded {len(active_rules)} active rules.")
        all_active_iocs: List[indicator_schemas.IoCResponse] = indicator_service.get_all_iocs(es_writer, limit=10000)
        if not all_active_iocs: print("CorrelationEngine: No active IoCs found.")
        iocs_map: Dict[str, Dict[str, indicator_schemas.IoCResponse]] = {}
        for ioc in all_active_iocs:
            if ioc.type not in iocs_map: iocs_map[ioc.type] = {}
            iocs_map[ioc.type][ioc.value] = ioc
        print(f"CorrelationEngine: Loaded {len(all_active_iocs)} IoCs into map.")
        events_to_correlate: List[Dict[str, Any]] = []
        try:
            syslog_resp = es_client.search(index="siem-syslog-events-*", body={"query": {"match_all": {}}, "size": 100,
                                                                               "sort": [{"timestamp": "desc"}]})
            for hit in syslog_resp.get('hits', {}).get('hits', []): events_to_correlate.append(hit['_source'])
            netflow_resp = es_client.search(index="siem-netflow-events-*",
                                            body={"query": {"match_all": {}}, "size": 100,
                                                  "sort": [{"timestamp": "desc"}]})
            for hit in netflow_resp.get('hits', {}).get('hits', []): events_to_correlate.append(hit['_source'])
            print(f"CorrelationEngine: Fetched {len(events_to_correlate)} recent events.")
        except es_exceptions.ElasticsearchWarning as e:
            print(f"CorrelationEngine: Error fetching events: {e}")
            return

        for event_doc in events_to_correlate:
            for rule in active_rules:
                if rule.event_source_type:
                    event_category_or_type = event_doc.get('event_category') or event_doc.get('event_type')
                    if not event_category_or_type or event_category_or_type not in rule.event_source_type:
                        continue
                field_value_in_event = event_doc.get(rule.event_field_to_match.value)
                if not field_value_in_event: continue
                matched_ioc = iocs_map.get(rule.ioc_type_to_match.value, {}).get(str(field_value_in_event))
                if matched_ioc:
                    if rule.ioc_min_confidence and (
                            matched_ioc.confidence is None or matched_ioc.confidence < rule.ioc_min_confidence): continue
                    if rule.ioc_tags_match:
                        if not all(tag in (matched_ioc.tags or []) for tag in rule.ioc_tags_match): continue

                    offence_title = rule.generated_offence_title_template.format(
                        ioc_value=matched_ioc.value, ioc_type=matched_ioc.type,
                        event_source_ip=event_doc.get('source_ip', 'N/A'),
                        event_destination_ip=event_doc.get('destination_ip', 'N/A'),
                        event_hostname=event_doc.get('hostname', 'N/A'))

                    trigger_event_summary_dict = {k: str(v)[:250] for k, v in event_doc.items() if
                                                  k in ['timestamp', 'reporter_ip', 'hostname', 'message', 'source_ip',
                                                        'destination_ip', 'event_category',
                                                        'event_type']}  # Більш вибіркові поля для summary

                    matched_ioc_details_dict = matched_ioc.model_dump(mode='json') if matched_ioc else None

                    offence_create_data = correlation_schemas.OffenceCreate(
                        title=offence_title,
                        description=f"Rule '{rule.name}' (ID: {rule.id}) triggered. Event (reporter: {event_doc.get('reporter_ip')}) matched IoC '{matched_ioc.value}'.",
                        severity=rule.generated_offence_severity,  # Це вже буде OffenceSeverityEnum
                        status=correlation_schemas.OffenceStatusEnum.NEW,
                        correlation_rule_id=rule.id,
                        triggering_event_summary=trigger_event_summary_dict,
                        matched_ioc_details=matched_ioc_details_dict,
                        attributed_apt_group_ids=matched_ioc.attributed_apt_group_ids or [])
                    self.create_offence(db, offence_create_data)
        print(f"--- Correlation Cycle Finished at {datetime.now(timezone.utc)} ---")
