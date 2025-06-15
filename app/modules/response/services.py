# app/modules/response/services.py
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from . import schemas as response_schemas
from ..indicators import schemas as indicator_schemas
from app.database.postgres_models.response_models import ResponseAction, ResponsePipeline
from app.database.postgres_models.correlation_models import Offence  # Для отримання даних офенса
from app.modules.device_interaction.services import DeviceService  # Для виконання дій
from app.modules.device_interaction import schemas as device_schemas  # Для параметрів дій


class ResponseService:
    # --- CRUD для ResponseAction ---
    def create_action(self, db: Session, action_create: response_schemas.ResponseActionCreate) -> ResponseAction:
        db_action = ResponseAction(**action_create.model_dump())
        db.add(db_action);
        db.commit();
        db.refresh(db_action)
        return db_action

    def get_action(self, db: Session, action_id: int) -> Optional[ResponseAction]:
        return db.query(ResponseAction).filter(ResponseAction.id == action_id).first()

    def get_all_actions(self, db: Session, skip: int = 0, limit: int = 100) -> List[ResponseAction]:
        return db.query(ResponseAction).offset(skip).limit(limit).all()

    def update_action(self, db: Session, action_id: int, action_update: response_schemas.ResponseActionUpdate) -> \
    Optional[ResponseAction]:
        db_action = self.get_action(db, action_id)
        if not db_action: return None
        update_data = action_update.model_dump(exclude_unset=True)
        for key, value in update_data.items(): setattr(db_action, key, value)
        db.add(db_action);
        db.commit();
        db.refresh(db_action)
        return db_action

    def delete_action(self, db: Session, action_id: int) -> bool:
        db_action = self.get_action(db, action_id)
        if db_action: db.delete(db_action); db.commit(); return True
        return False

    # --- CRUD для ResponsePipeline ---
    def create_pipeline(self, db: Session,
                        pipeline_create: response_schemas.ResponsePipelineCreate) -> ResponsePipeline:
        # Валідація action_id в actions_config (чи існують такі дії)
        for action_conf in pipeline_create.actions_config:
            if not self.get_action(db, action_conf.action_id):
                raise ValueError(f"Action with ID {action_conf.action_id} not found.")

        # Pydantic модель actions_config вже містить список PipelineActionConfig.
        # Ми зберігаємо його як JSON в БД.
        actions_config_json = [ac.model_dump() for ac in pipeline_create.actions_config]
        db_pipeline = ResponsePipeline(
            name=pipeline_create.name,
            description=pipeline_create.description,
            is_enabled=pipeline_create.is_enabled,
            trigger_correlation_rule_id=pipeline_create.trigger_correlation_rule_id,
            actions_config=actions_config_json  # Зберігаємо як JSON
        )
        db.add(db_pipeline);
        db.commit();
        db.refresh(db_pipeline)
        return db_pipeline

    def get_pipeline(self, db: Session, pipeline_id: int) -> Optional[ResponsePipeline]:
        return db.query(ResponsePipeline).filter(ResponsePipeline.id == pipeline_id).first()

    def get_all_pipelines(self, db: Session, skip: int = 0, limit: int = 100) -> List[ResponsePipeline]:
        return db.query(ResponsePipeline).offset(skip).limit(limit).all()

    def update_pipeline(self, db: Session, pipeline_id: int,
                        pipeline_update: response_schemas.ResponsePipelineUpdate) -> Optional[ResponsePipeline]:
        db_pipeline = self.get_pipeline(db, pipeline_id)
        if not db_pipeline: return None

        update_data = pipeline_update.model_dump(exclude_unset=True)
        if "actions_config" in update_data and update_data["actions_config"] is not None:
            # Валідація action_id в новому actions_config
            for action_conf_data in update_data["actions_config"]:
                # action_conf_data тут - це словник, не Pydantic модель
                if not self.get_action(db, action_conf_data['action_id']):
                    raise ValueError(f"Action with ID {action_conf_data['action_id']} not found.")
            # Зберігаємо як JSON
            # db_pipeline.actions_config = [ac.model_dump() for ac in update_data["actions_config"]] # Якщо update_data["actions_config"] - список Pydantic моделей
            db_pipeline.actions_config = update_data["actions_config"]  # Якщо це вже список словників
            del update_data["actions_config"]  # Видаляємо, щоб не намагатися встановити як звичайне поле

        for key, value in update_data.items():
            setattr(db_pipeline, key, value)

        db.add(db_pipeline);
        db.commit();
        db.refresh(db_pipeline)
        return db_pipeline

    def delete_pipeline(self, db: Session, pipeline_id: int) -> bool:
        db_pipeline = self.get_pipeline(db, pipeline_id)
        if db_pipeline: db.delete(db_pipeline); db.commit(); return True
        return False

    # --- Виконання Пайплайна Реагування ---
    def execute_response_for_offence(
            self,
            db: Session,
            offence: Offence,  # Об'єкт Offence з БД
            device_service: DeviceService  # Сервіс для взаємодії з пристроями
            # Тут можуть знадобитися інші сервіси для інших типів дій
    ):
        print(f"Executing response for Offence ID: {offence.id}, Title: '{offence.title}'")
        if not offence.correlation_rule_id:
            print(f"Offence {offence.id} has no associated correlation rule. Cannot determine pipeline.")
            return

        # Знайти пайплайн, пов'язаний з цим правилом кореляції
        pipeline = db.query(ResponsePipeline).filter(
            ResponsePipeline.trigger_correlation_rule_id == offence.correlation_rule_id,
            ResponsePipeline.is_enabled == True
        ).first()

        if not pipeline:
            print(f"No enabled response pipeline found for correlation rule ID {offence.correlation_rule_id}.")
            return

        print(f"Found pipeline: '{pipeline.name}' (ID: {pipeline.id})")

        # actions_config з БД - це список словників. Конвертуємо їх назад в Pydantic моделі для зручності
        actions_to_execute = [response_schemas.PipelineActionConfig(**action_conf) for action_conf in
                              pipeline.actions_config]
        # Сортуємо за полем order
        actions_to_execute.sort(key=lambda ac: ac.order)

        for action_config in actions_to_execute:
            action_db_obj = self.get_action(db, action_config.action_id)
            if not action_db_obj or not action_db_obj.is_enabled:
                print(f"Skipping action ID {action_config.action_id} (not found or disabled).")
                continue

            print(f"Executing action: '{action_db_obj.name}' (Type: {action_db_obj.type.value})")

            # --- Обробка параметрів дії ---
            # Параметри можуть бути з default_params дії та/або з action_params_template пайплайна,
            # а також можуть використовувати плейсхолдери з офенса.
            # Це спрощена логіка.
            final_action_params = (action_db_obj.default_params or {}).copy()
            if action_config.action_params_template:
                final_action_params.update(action_config.action_params_template)

            # Заміна плейсхолдерів (приклад для IP)
            # Потрібно буде розширити для інших плейсхолдерів
            # Наприклад, {offence.triggering_event_summary.source_ip}
            #             {offence.matched_ioc_details.value}

            # Припускаємо, що офенс містить потрібну інформацію, наприклад, IP для блокування.
            # Для блокування IP нам потрібен device_id та сам IP.
            # device_id може бути частиною default_params або action_params_template.
            # IP-адресу можемо взяти з triggering_event_summary або matched_ioc_details.

            if action_db_obj.type == response_schemas.ResponseActionTypeEnum.BLOCK_IP:
                # Приклад: отримуємо IP з matched_ioc_details, device_id з параметрів дії
                target_ip: Optional[str] = None
                if offence.matched_ioc_details and isinstance(offence.matched_ioc_details, dict):
                    # Якщо matched_ioc_details - це IoCResponse, розпарсений з JSONB
                    if offence.matched_ioc_details.get("type") in [indicator_schemas.IoCTypeEnum.IPV4_ADDR.value,
                                                                   indicator_schemas.IoCTypeEnum.IPV6_ADDR.value]:
                        target_ip = offence.matched_ioc_details.get("value")

                if not target_ip and offence.triggering_event_summary and isinstance(offence.triggering_event_summary,
                                                                                     dict):
                    # Спробуємо взяти з події (пріоритет source_ip, потім destination_ip)
                    target_ip = offence.triggering_event_summary.get(
                        "source_ip") or offence.triggering_event_summary.get("destination_ip")

                device_id_for_action = final_action_params.get("device_id")  # Наприклад, ID головного файрволу
                list_name_for_action = final_action_params.get("list_name",
                                                               "siem_blocked_ips")  # Назва списку за замовчуванням

                if target_ip and device_id_for_action is not None:
                    print(
                        f"  Action params: block IP {target_ip} on device ID {device_id_for_action} in list '{list_name_for_action}'")
                    try:
                        block_payload = device_schemas.BlockIpPayload(
                            list_name=list_name_for_action,
                            ip_address=target_ip,  # Pydantic перевірить валідність IP
                            comment=f"Blocked by SIEM Offence ID {offence.id}: {offence.title[:50]}"
                        )
                        # Викликаємо DeviceService
                        # DeviceService має бути переданий або ініціалізований тут
                        success = device_service.block_ip_on_device(db=db, device_id=device_id_for_action,
                                                                    payload=block_payload)
                        print(f"  Block IP action result: {'Success' if success else 'Failure'}")
                    except Exception as e_action:
                        print(f"  Error executing BLOCK_IP action: {e_action}")
                else:
                    print(
                        f"  Skipping BLOCK_IP action: target_ip ('{target_ip}') or device_id_for_action ('{device_id_for_action}') not found/specified in params.")

            elif action_db_obj.type == response_schemas.ResponseActionTypeEnum.SEND_EMAIL:
                recipient = final_action_params.get("recipient", "admin@example.com")
                subject = final_action_params.get("subject_template", "SIEM Alert: {offence.title}").format(
                    offence=offence)  # Проста заміна
                body = final_action_params.get("body_template",
                                               "Offence Details:\nID: {offence.id}\nSeverity: {offence.severity.value}\nDescription: {offence.description}\nTriggered by rule: {offence.correlation_rule_id}").format(
                    offence=offence)
                print(f"  SIMULATING SEND_EMAIL to {recipient}. Subject: '{subject}'. Body: '{body[:100]}...'")
                # Тут буде реальний код відправки email

            # TODO: Реалізувати інші типи дій
            else:
                print(f"  Action type '{action_db_obj.type.value}' not yet implemented.")