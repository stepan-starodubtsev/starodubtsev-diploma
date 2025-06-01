from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.core.database import get_db  # Переконайся, що get_db імпортується звідси
from . import schemas  # Імпортуємо оновлені схеми
from .services import DeviceService
# Модель Device може не знадобитися тут напряму, якщо DeviceTypeEnum є в schemas
# from app.database.postgres_models.device_models import Device
from .connectors.base_connector import ConnectorConnectionError, ConnectorCommandError

router = APIRouter(
    prefix="/devices",
    tags=["Device Interaction"]
)


# --- CRUD Ендпоїнти для пристроїв (без змін) ---

@router.post("/", response_model=schemas.DeviceResponse, status_code=201,
             operation_id="device_interaction_create_device")
def create_device(
        device_create: schemas.DeviceCreate,
        db: Session = Depends(get_db),
        service: DeviceService = Depends(DeviceService)
):
    try:
        db_device = service.create_device(db=db, device_create=device_create)
        return db_device
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # TODO: Додати логування помилки e
        raise HTTPException(status_code=500, detail="An unexpected error occurred while creating the device.")


@router.get("/", response_model=List[schemas.DeviceResponse], operation_id="device_interaction_read_devices")
def read_devices(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db),
        service: DeviceService = Depends(DeviceService)
):
    devices = service.get_all_devices(db=db, skip=skip, limit=limit)
    return devices


@router.get("/{device_id}", response_model=schemas.DeviceResponse, operation_id="device_interaction_read_device")
def read_device(
        device_id: int = Path(..., title="The ID of the device to get", ge=1),
        db: Session = Depends(get_db),
        service: DeviceService = Depends(DeviceService)
):
    db_device = service.get_device_by_id(db=db, device_id=device_id)
    if db_device is None:
        raise HTTPException(status_code=404, detail="Device not found")
    return db_device


@router.put("/{device_id}", response_model=schemas.DeviceResponse, operation_id="device_interaction_update_device")
def update_device(
        device_id: int = Path(..., title="The ID of the device to update", ge=1),
        device_update: schemas.DeviceUpdate = Body(...),
        db: Session = Depends(get_db),
        service: DeviceService = Depends(DeviceService)
):
    try:
        updated_device = service.update_device(db=db, device_id=device_id, device_update=device_update)
        if updated_device is None:
            raise HTTPException(status_code=404, detail="Device not found for update")  # Хоча сервіс кидає ValueError
        return updated_device
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))  # Наприклад, "Device not found"
    except Exception as e:
        # TODO: Додати логування помилки e
        raise HTTPException(status_code=500, detail="An unexpected error occurred while updating the device.")


@router.delete("/{device_id}", status_code=204, operation_id="device_interaction_delete_device")
def delete_device(
        device_id: int = Path(..., title="The ID of the device to delete", ge=1),
        db: Session = Depends(get_db),
        service: DeviceService = Depends(DeviceService)
):
    success = service.delete_device(db=db, device_id=device_id)
    if not success:
        raise HTTPException(status_code=404, detail="Device not found")
    return None


# --- Ендпоїнти для операцій з пристроями ---

@router.get("/{device_id}/status", response_model=schemas.DeviceResponse,
            operation_id="device_interaction_get_device_status")
def get_device_status(  # Назва методу API залишається такою ж
        device_id: int = Path(..., title="The ID of the device", ge=1),
        db: Session = Depends(get_db),
        service: DeviceService = Depends(DeviceService)
):
    device_info = service.get_device_status_and_update_db(db=db, device_id=device_id)
    if device_info is None:
        raise HTTPException(status_code=404, detail=f"Device with ID {device_id} not found in database.")
    return device_info


@router.post("/{device_id}/configure-syslog", response_model=Dict[str, Any],
             operation_id="device_interaction_configure_device_syslog")
def configure_device_syslog(  # Назва методу API залишається такою ж
        device_id: int = Path(..., title="The ID of the device to configure syslog on", ge=1),
        syslog_config: schemas.SyslogConfigPayload = Body(...),
        db: Session = Depends(get_db),
        service: DeviceService = Depends(DeviceService)
):
    try:
        success = service.configure_syslog_on_device(db=db, device_id=device_id, syslog_config=syslog_config)
        if success:
            return {"message": "Syslog configuration command(s) executed successfully.", "success": True}
        else:
            raise HTTPException(status_code=502,
                                detail="Syslog configuration failed on the device. Check service logs and device status.")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except (ConnectorConnectionError, ConnectorCommandError) as ce:
        raise HTTPException(status_code=502, detail=f"Device communication error during syslog configuration: {ce}")
    except Exception as e:
        # TODO: Додати логування помилки e
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@router.post("/{device_id}/configure-netflow", response_model=Dict[str, Any],
             operation_id="device_interaction_configure_device_netflow")
def configure_device_netflow(  # Назва методу API залишається такою ж
        device_id: int = Path(..., title="The ID of the device to configure netflow on", ge=1),
        netflow_config: schemas.NetflowConfigPayload = Body(...),
        db: Session = Depends(get_db),
        service: DeviceService = Depends(DeviceService)
):
    try:
        success = service.configure_netflow_on_device(db=db, device_id=device_id, netflow_config=netflow_config)
        if success:
            return {"message": "Netflow configuration command(s) executed successfully.", "success": True}
        else:
            raise HTTPException(status_code=502,
                                detail="Netflow configuration failed on the device. Check service logs and device status.")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except (ConnectorConnectionError, ConnectorCommandError) as ce:
        raise HTTPException(status_code=502, detail=f"Device communication error during netflow configuration: {ce}")
    except Exception as e:
        # TODO: Додати логування помилки e
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@router.get("/{device_id}/firewall-rules", response_model=List[Dict[str, Any]],
            operation_id="device_interaction_get_device_firewall_rules")
def get_device_firewall_rules(  # Назва методу API залишається такою ж
        device_id: int = Path(..., title="The ID of the device", ge=1),
        chain: Optional[str] = Query(None,
                                     description="Optional firewall chain to filter by (e.g., 'forward', 'input')"),
        db: Session = Depends(get_db),
        service: DeviceService = Depends(DeviceService)
):
    try:
        rules = service.get_firewall_rules_on_device(db=db, device_id=device_id, chain=chain)
        return rules
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except (ConnectorConnectionError, ConnectorCommandError) as ce:
        raise HTTPException(status_code=502,
                            detail=f"Could not retrieve firewall rules due to device communication error: {ce}")
    except Exception as e:
        # TODO: Додати логування помилки e
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


# --- ОНОВЛЕНІ ЕНДПОЇНТИ для блокування/розблокування IP ---

@router.post("/{device_id}/block-ip", response_model=Dict[str, Any],
             operation_id="device_interaction_block_ip_on_device")
def block_ip_on_device_endpoint(  # Нова назва функції ендпоінту
        device_id: int = Path(..., title="The ID of the device", ge=1),
        payload: schemas.BlockIpPayload = Body(...),  # Використовуємо нову схему
        db: Session = Depends(get_db),
        service: DeviceService = Depends(DeviceService)
):
    """
    Блокує IP-адресу: додає її до списку адрес на пристрої
    та переконується, що існує відповідне правило у файрволі.
    """
    try:
        # Викликаємо оновлений метод сервісу
        success = service.block_ip_on_device(db=db, device_id=device_id, payload=payload)
        if success:
            return {
                "message": f"IP {payload.ip_address} blocking process for list '{payload.list_name}' reported success.",
                "success": True}
        else:
            # Сервіс мав би оновити статус пристрою на ERROR
            raise HTTPException(status_code=502,
                                detail=f"Action to block IP {payload.ip_address} in list '{payload.list_name}' failed on the device or rule creation failed.")
    except ValueError as ve:  # Наприклад, пристрій не знайдено
        raise HTTPException(status_code=404, detail=str(ve))
    except (ConnectorConnectionError, ConnectorCommandError) as ce:  # Помилки зв'язку з пристроєм
        raise HTTPException(status_code=502, detail=f"Device communication error during IP blocking: {ce}")
    except NotImplementedError as nie:  # Якщо конектор для типу пристрою не реалізовано
        raise HTTPException(status_code=501, detail=str(nie))
    except Exception as e:
        # TODO: Додати логування помилки e
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during IP blocking: {e}")


@router.post("/{device_id}/unblock-ip", response_model=Dict[str, Any],
             operation_id="device_interaction_unblock_ip_on_device")
def unblock_ip_on_device_endpoint(  # Нова назва функції ендпоінту
        device_id: int = Path(..., title="The ID of the device", ge=1),
        payload: schemas.UnblockIpPayload = Body(...),  # Використовуємо нову схему
        db: Session = Depends(get_db),
        service: DeviceService = Depends(DeviceService)
):
    """
    Розблоковує IP-адресу: видаляє її з вказаного списку адрес на пристрої.
    """
    try:
        # Викликаємо оновлений метод сервісу
        success = service.unblock_ip_on_device(db=db, device_id=device_id, payload=payload)
        if success:
            return {
                "message": f"IP {payload.ip_address} unblocking process for list '{payload.list_name}' reported success.",
                "success": True}
        else:
            raise HTTPException(status_code=502,
                                detail=f"Action to unblock IP {payload.ip_address} from list '{payload.list_name}' failed on the device.")
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except (ConnectorConnectionError, ConnectorCommandError) as ce:
        raise HTTPException(status_code=502, detail=f"Device communication error during IP unblocking: {ce}")
    except NotImplementedError as nie:
        raise HTTPException(status_code=501, detail=str(nie))
    except Exception as e:
        # TODO: Додати логування помилки e
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during IP unblocking: {e}")
