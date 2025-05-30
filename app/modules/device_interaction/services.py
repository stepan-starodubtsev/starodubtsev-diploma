# app/modules/device_interaction/services.py
# ... (імпорти та DeviceService._get_device_or_fail, _get_connector, _update_device_status_and_info,
#      get_device_status_and_update_db, configure_syslog_on_device, configure_netflow_on_device,
#      get_firewall_rules_on_device, CRUD методи - без змін, окрім виправленої логіки os_version) ...
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional, Type
from datetime import datetime, timezone

from .connectors.base_connector import BaseConnector, ConnectorConnectionError, ConnectorCommandError
from .connectors.mikrotik_connector import MikrotikConnector

from app.database.postgres_models.device_models import Device, DeviceStatusEnum, DeviceTypeEnum
from . import schemas
from app.core.security import encrypt_data, decrypt_data

CONNECTOR_MAPPING: Dict[DeviceTypeEnum, Type[BaseConnector]] = {
    DeviceTypeEnum.MIKROTIK_ROUTEROS: MikrotikConnector,
}


class DeviceService:
    def _get_device_or_fail(self, db: Session, device_id: int) -> Device:
        device_db = db.query(Device).filter(Device.id == device_id, Device.is_enabled == True).first()
        if not device_db: raise ValueError(f"Enabled device with ID {device_id} not found.")
        return device_db

    def _get_connector(self, device_db: Device) -> BaseConnector:
        connector_class = CONNECTOR_MAPPING.get(device_db.device_type)
        if not connector_class: raise NotImplementedError(
            f"Connector for type '{device_db.device_type.value}' not implemented.")
        return connector_class(host=device_db.host, username=device_db.username,
                               password=decrypt_data(device_db.encrypted_password), port=device_db.port)

    def _update_device_status_and_info(self, db: Session, device_db: Device, status: DeviceStatusEnum,
                                       os_version: Optional[str] = None, commit: bool = True):
        device_db.status = status
        if os_version is not None: device_db.os_version = os_version
        if status == DeviceStatusEnum.REACHABLE: device_db.last_successful_connection = datetime.now(timezone.utc)
        device_db.last_status_update = datetime.now(timezone.utc)
        db.add(device_db)
        if commit:
            try:
                db.commit(); db.refresh(device_db)
            except Exception as e:
                db.rollback(); print(f"Error committing status update for {device_db.name}: {e}")

    # ... (get_device_status_and_update_db, configure_syslog_on_device, configure_netflow_on_device, get_firewall_rules_on_device - з виправленою логікою os_version)
    def get_device_status_and_update_db(self, db: Session, device_id: int) -> Optional[schemas.DeviceResponse]:
        device_db = db.query(Device).filter(Device.id == device_id).first()
        if not device_db: print(f"Device with ID {device_id} not found for status update."); return None
        initial_os_version = device_db.os_version;
        os_version_from_device: Optional[str] = None
        final_status = DeviceStatusEnum.UNKNOWN;
        os_to_update_in_db: Optional[str] = initial_os_version
        try:
            connector = self._get_connector(device_db)
            with connector:
                resources = connector.get_system_resource_info()
                if resources: os_version_from_device = resources.get('version')
                final_status = DeviceStatusEnum.REACHABLE
                if os_version_from_device is not None: os_to_update_in_db = os_version_from_device
                effective_os_for_log = os_version_from_device if os_version_from_device is not None else initial_os_version
                print(f"Successfully connected to device {device_db.name}. OS: {effective_os_for_log}")
        except (ConnectorConnectionError, ConnectorCommandError, NotImplementedError) as e:
            print(f"Could not connect or execute command for status update on device {device_db.name}: {e}")
            final_status = DeviceStatusEnum.UNREACHABLE
        except ValueError as ve:
            final_status = DeviceStatusEnum.ERROR;
            print(f"ValueError during status update for {device_db.name}: {ve}")
        self._update_device_status_and_info(db, device_db, final_status, os_version=os_to_update_in_db, commit=True)
        return schemas.DeviceResponse.from_orm(device_db)

    def configure_syslog_on_device(self, db: Session, device_id: int,
                                   syslog_config: schemas.SyslogConfigPayload) -> bool:
        device_db = self._get_device_or_fail(db, device_id)
        operation_successful = False;
        initial_os_version = device_db.os_version
        os_version_from_device: Optional[str] = None;
        final_status = DeviceStatusEnum.ERROR
        os_to_update_in_db: Optional[str] = initial_os_version
        self._update_device_status_and_info(db, device_db, DeviceStatusEnum.CONFIGURING, os_version=initial_os_version,
                                            commit=True)
        try:
            connector = self._get_connector(device_db)
            with connector:
                resource_info = connector.get_system_resource_info()
                if resource_info: os_version_from_device = resource_info.get('version')
                if os_version_from_device is not None: os_to_update_in_db = os_version_from_device
                effective_os_for_log = os_version_from_device if os_version_from_device is not None else initial_os_version
                print(f"Device {device_db.name} (OS: {effective_os_for_log}) - Configuring syslog...")
                safe_name_prefix = "".join(
                    c if c.isalnum() else "_" for c in device_db.name) if device_db.name else str(device_db.id)
                success = connector.configure_syslog(target_host=str(syslog_config.target_host),
                                                     target_port=syslog_config.target_port,
                                                     action_name_prefix=f"{syslog_config.action_name_prefix}_{safe_name_prefix}",
                                                     topics=syslog_config.topics)
                if success:
                    device_db.syslog_configured_by_siem = True; final_status = DeviceStatusEnum.REACHABLE; operation_successful = True; print(
                        f"Syslog configured successfully for {device_db.name}")
                else:
                    print(f"Syslog configuration reported failure by connector for {device_db.name}")
        except (ConnectorConnectionError, ConnectorCommandError, NotImplementedError) as e:
            print(f"Error during syslog configuration for {device_db.name}: {e}")
        except ValueError as ve:
            print(f"ValueError during syslog configuration for {device_db.name}: {ve}")
        self._update_device_status_and_info(db, device_db, final_status, os_version=os_to_update_in_db, commit=True)
        return operation_successful

    def configure_netflow_on_device(self, db: Session, device_id: int,
                                    netflow_config: schemas.NetflowConfigPayload) -> bool:
        device_db = self._get_device_or_fail(db, device_id)
        operation_successful = False;
        initial_os_version = device_db.os_version
        os_version_from_device: Optional[str] = None;
        final_status = DeviceStatusEnum.ERROR
        os_to_update_in_db: Optional[str] = initial_os_version
        self._update_device_status_and_info(db, device_db, DeviceStatusEnum.CONFIGURING, os_version=initial_os_version,
                                            commit=True)
        try:
            connector = self._get_connector(device_db)
            with connector:
                resource_info = connector.get_system_resource_info()
                if resource_info: os_version_from_device = resource_info.get('version')
                if os_version_from_device is not None: os_to_update_in_db = os_version_from_device
                effective_os_for_log = os_version_from_device if os_version_from_device is not None else initial_os_version
                print(f"Device {device_db.name} (OS: {effective_os_for_log}) - Configuring netflow...")
                success = connector.configure_netflow(target_host=str(netflow_config.target_host),
                                                      target_port=netflow_config.target_port,
                                                      interfaces=netflow_config.interfaces,
                                                      version=netflow_config.version)
                if success:
                    device_db.netflow_configured_by_siem = True; final_status = DeviceStatusEnum.REACHABLE; operation_successful = True; print(
                        f"Netflow configured successfully for {device_db.name}")
                else:
                    print(f"Netflow configuration reported failure by connector for {device_db.name}")
        except (ConnectorConnectionError, ConnectorCommandError, NotImplementedError) as e:
            print(f"Error during netflow configuration for {device_db.name}: {e}")
        except ValueError as ve:
            print(f"ValueError during netflow configuration for {device_db.name}: {ve}")
        self._update_device_status_and_info(db, device_db, final_status, os_version=os_to_update_in_db, commit=True)
        return operation_successful

    def get_firewall_rules_on_device(self, db: Session, device_id: int, chain: Optional[str] = None) -> List[
        Dict[str, Any]]:
        device_db = self._get_device_or_fail(db, device_id)
        rules: List[Dict[str, Any]] = [];
        initial_os_version = device_db.os_version
        os_version_from_device: Optional[str] = None;
        final_status = DeviceStatusEnum.ERROR
        os_to_update_in_db: Optional[str] = initial_os_version
        try:
            connector = self._get_connector(device_db)
            with connector:
                resource_info = connector.get_system_resource_info()
                if resource_info: os_version_from_device = resource_info.get('version')
                if os_version_from_device is not None: os_to_update_in_db = os_version_from_device
                effective_os_for_log = os_version_from_device if os_version_from_device is not None else initial_os_version
                print(
                    f"Device {device_db.name} (OS: {effective_os_for_log}) - Getting firewall rules (chain: {chain or 'all'})...")
                rules = connector.get_firewall_rules(chain=chain)
                final_status = DeviceStatusEnum.REACHABLE
                print(f"Successfully retrieved {len(rules)} firewall rules from {device_db.name}.")
        except (ConnectorConnectionError, ConnectorCommandError, NotImplementedError) as e:
            print(f"Error getting firewall rules for {device_db.name}: {e}")
        except ValueError as ve:
            print(f"ValueError during get firewall rules for {device_db.name}: {ve}")
        self._update_device_status_and_info(db, device_db, final_status, os_version=os_to_update_in_db, commit=True)
        return rules

    # --- Нові/перейменовані методи сервісу ---
    def block_ip_on_device(self, db: Session, device_id: int, payload: schemas.BlockIpPayload) -> bool:
        device_db = self._get_device_or_fail(db, device_id)
        operation_successful = False
        initial_os_version = device_db.os_version
        os_version_from_device: Optional[str] = None
        final_status = DeviceStatusEnum.ERROR  # Починаємо з помилки, якщо щось піде не так
        os_to_update_in_db: Optional[str] = initial_os_version

        # Можна встановити CONFIGURING, якщо операція тривала, але для блокування IP це зазвичай швидко
        # self._update_device_status_and_info(db, device_db, DeviceStatusEnum.CONFIGURING, os_version=initial_os_version, commit=True)
        try:
            connector = self._get_connector(device_db)
            with connector:
                resource_info = connector.get_system_resource_info()
                if resource_info: os_version_from_device = resource_info.get('version')
                if os_version_from_device is not None: os_to_update_in_db = os_version_from_device
                effective_os_for_log = os_version_from_device if os_version_from_device is not None else initial_os_version
                print(
                    f"Device {device_db.name} (OS: {effective_os_for_log}) - Blocking IP {payload.ip_address} in list '{payload.list_name}'...")

                # Параметри для правила файрволу (можна зробити їх частиною payload, якщо потрібна гнучкість)
                firewall_chain = "forward"  # Або "input", залежно від політики
                firewall_action = "drop"
                rule_comment_prefix = f"SIEM_block_{device_db.id}_"

                success = connector.block_ip(
                    list_name=payload.list_name,
                    ip_address=str(payload.ip_address),
                    comment=payload.comment,
                    firewall_chain=firewall_chain,
                    firewall_action=firewall_action,
                    rule_comment_prefix=rule_comment_prefix
                )
                if success:
                    final_status = DeviceStatusEnum.REACHABLE
                    operation_successful = True
                    print(
                        f"IP {payload.ip_address} blocking for list '{payload.list_name}' on {device_db.name} reported success.")
                else:
                    # final_status залишається ERROR
                    print(
                        f"IP {payload.ip_address} blocking for list '{payload.list_name}' on {device_db.name} reported failure by connector.")
        except (ConnectorConnectionError, ConnectorCommandError, NotImplementedError) as e:
            # os_to_update_in_db залишається initial_os_version
            print(f"Error blocking IP for {device_db.name}: {e}")
        except ValueError as ve:  # Помилка розшифрування або інша
            # os_to_update_in_db залишається initial_os_version
            print(f"ValueError during block IP for {device_db.name}: {ve}")

        self._update_device_status_and_info(db, device_db, final_status, os_version=os_to_update_in_db, commit=True)
        return operation_successful

    def unblock_ip_on_device(self, db: Session, device_id: int, payload: schemas.UnblockIpPayload) -> bool:
        device_db = self._get_device_or_fail(db, device_id)
        operation_successful = False
        initial_os_version = device_db.os_version
        os_version_from_device: Optional[str] = None
        final_status = DeviceStatusEnum.ERROR
        os_to_update_in_db: Optional[str] = initial_os_version

        try:
            connector = self._get_connector(device_db)
            with connector:
                resource_info = connector.get_system_resource_info()
                if resource_info: os_version_from_device = resource_info.get('version')
                if os_version_from_device is not None: os_to_update_in_db = os_version_from_device
                effective_os_for_log = os_version_from_device if os_version_from_device is not None else initial_os_version
                print(
                    f"Device {device_db.name} (OS: {effective_os_for_log}) - Unblocking IP {payload.ip_address} from list '{payload.list_name}'...")

                success = connector.unblock_ip(
                    list_name=payload.list_name,
                    ip_address=str(payload.ip_address)
                )
                if success:
                    final_status = DeviceStatusEnum.REACHABLE
                    operation_successful = True
                    print(
                        f"IP {payload.ip_address} unblocking for list '{payload.list_name}' on {device_db.name} reported success.")
                else:
                    print(
                        f"IP {payload.ip_address} unblocking for list '{payload.list_name}' on {device_db.name} reported failure by connector.")
        except (ConnectorConnectionError, ConnectorCommandError, NotImplementedError) as e:
            os_to_update_in_db = initial_os_version
            print(f"Error unblocking IP for {device_db.name}: {e}")
        except ValueError as ve:
            os_to_update_in_db = initial_os_version
            print(f"ValueError during unblock IP for {device_db.name}: {ve}")

        self._update_device_status_and_info(db, device_db, final_status, os_version=os_to_update_in_db, commit=True)
        return operation_successful

    # --- CRUD методи для пристроїв (залишаються без змін, крім виправлення DeviceResponse.from_orm) ---
    def create_device(self, db: Session, device_create: schemas.DeviceCreate) -> Device:
        existing_device = db.query(Device).filter(Device.host == device_create.host).first()
        if existing_device: raise ValueError(
            f"Device with host {device_create.host} already exists with ID {existing_device.id}.")
        encrypted_pass = encrypt_data(device_create.password)
        db_device = Device(name=device_create.name, host=device_create.host, port=device_create.port,
                           username=device_create.username, encrypted_password=encrypted_pass,
                           device_type=device_create.device_type, is_enabled=device_create.is_enabled,
                           status=DeviceStatusEnum.UNKNOWN)
        db.add(db_device);
        db.commit();
        db.refresh(db_device)
        return db_device

    def get_all_devices(self, db: Session, skip: int = 0, limit: int = 100) -> List[schemas.DeviceResponse]:
        devices_db = db.query(Device).offset(skip).limit(limit).all()
        return [schemas.DeviceResponse.from_orm(dev) for dev in devices_db]

    def get_device_by_id(self, db: Session, device_id: int) -> Optional[schemas.DeviceResponse]:
        device_db = db.query(Device).filter(Device.id == device_id).first()
        return schemas.DeviceResponse.from_orm(device_db) if device_db else None

    def update_device(self, db: Session, device_id: int, device_update: schemas.DeviceUpdate) -> Optional[
        schemas.DeviceResponse]:
        device_db = db.query(Device).filter(Device.id == device_id).first()
        if not device_db: raise ValueError(f"Device with ID {device_id} not found for update.")
        update_data = device_update.model_dump(exclude_unset=True)
        if "password" in update_data and update_data["password"] is not None:
            device_db.encrypted_password = encrypt_data(update_data["password"]);
            del update_data["password"]
        for key, value in update_data.items(): setattr(device_db, key, value)
        if "is_enabled" in update_data and not update_data["is_enabled"]: device_db.status = DeviceStatusEnum.UNKNOWN
        db.add(device_db);
        db.commit();
        db.refresh(device_db)
        return schemas.DeviceResponse.from_orm(device_db)

    def delete_device(self, db: Session, device_id: int) -> bool:
        device_db = db.query(Device).filter(Device.id == device_id).first()
        if device_db: db.delete(device_db); db.commit(); return True
        return False
