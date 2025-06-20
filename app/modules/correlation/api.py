# app/modules/correlation/api.py
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional, Dict

from app.core.database import get_db
from . import schemas
from .schemas import OffenceResponse
from .services import CorrelationService
# Для запуску циклу кореляції може знадобитися доступ до інших сервісів
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from app.modules.indicators.services import IndicatorService
from app.core.dependencies import get_es_writer  # Використовуємо спільну залежність
from ..apt_groups.services import APTGroupService
from ..device_interaction.services import DeviceService
from ..response.services import ResponseService

router = APIRouter(
    prefix="/correlation",
    tags=["Correlation Engine & Offences"]
)


# --- CRUD для CorrelationRule ---
@router.post("/rules/", response_model=schemas.CorrelationRuleResponse, status_code=201)
def create_correlation_rule_api(
        rule_create: schemas.CorrelationRuleCreate,
        db: Session = Depends(get_db),
        service: CorrelationService = Depends(CorrelationService)
):
    try:
        return service.create_correlation_rule(db=db, rule_create=rule_create)
    except Exception as e:  # Обробка можливих помилок БД (наприклад, унікальність імені)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rules/", response_model=List[schemas.CorrelationRuleResponse])
def read_all_correlation_rules_api(
        skip: int = Query(0, ge=0), limit: int = Query(100, ge=1), only_enabled: bool = Query(False),
        db: Session = Depends(get_db), service: CorrelationService = Depends(CorrelationService)
):
    return service.get_all_correlation_rules(db=db, skip=skip, limit=limit, only_enabled=only_enabled)


@router.get("/rules/{rule_id}", response_model=schemas.CorrelationRuleResponse)
def read_correlation_rule_api(
        rule_id: int = Path(..., ge=1), db: Session = Depends(get_db),
        service: CorrelationService = Depends(CorrelationService)
):
    rule = service.get_correlation_rule_by_id(db=db, rule_id=rule_id)
    if not rule: raise HTTPException(status_code=404, detail="Correlation rule not found")
    return rule


@router.put("/rules/{rule_id}", response_model=schemas.CorrelationRuleResponse)
def update_correlation_rule_api(
        rule_id: int = Path(..., ge=1), rule_update: schemas.CorrelationRuleUpdate = Body(...),
        db: Session = Depends(get_db), service: CorrelationService = Depends(CorrelationService)
):
    rule = service.update_correlation_rule(db=db, rule_id=rule_id, rule_update=rule_update)
    if not rule: raise HTTPException(status_code=404, detail="Correlation rule not found for update")
    return rule


@router.delete("/rules/{rule_id}", status_code=204)
def delete_correlation_rule_api(
        rule_id: int = Path(..., ge=1), db: Session = Depends(get_db),
        service: CorrelationService = Depends(CorrelationService)
):
    if not service.delete_correlation_rule(db=db, rule_id=rule_id):
        raise HTTPException(status_code=404, detail="Correlation rule not found for deletion")
    return None


# --- CRUD для Offence ---
@router.get("/offences/", response_model=List[schemas.OffenceResponse])
def read_all_offences_api(
        skip: int = Query(0, ge=0), limit: int = Query(100, ge=1),
        db: Session = Depends(get_db), service: CorrelationService = Depends(CorrelationService)
):
    return service.get_all_offences(db=db, skip=skip, limit=limit)


@router.get("/offences/{offence_id}", response_model=schemas.OffenceResponse)
def read_offence_api(
        offence_id: int = Path(..., ge=1), db: Session = Depends(get_db),
        service: CorrelationService = Depends(CorrelationService)
):
    offence = service.get_offence_by_id(db=db, offence_id=offence_id)
    if not offence: raise HTTPException(status_code=404, detail="Offence not found")
    return offence


@router.put("/offences/{offence_id}/status", response_model=schemas.OffenceResponse)
def update_offence_status_api(  # Назва ендпоінту може бути більш загальною, якщо оновлюємо не тільки статус
        offence_id: int = Path(..., ge=1),
        # OffenceUpdate тепер містить і severity
        offence_data_update: schemas.OffenceUpdate = Body(..., example={"status": "in_progress", "severity": "high",
                                                                        "notes": "Analyst reviewed."}),
        db: Session = Depends(get_db),
        service: CorrelationService = Depends(CorrelationService)
):
    # Передаємо тільки ті поля, які дійсно є в схемі OffenceUpdate і які ми хочемо дозволити оновлювати тут.
    # Поточна OffenceUpdate дозволяє оновлювати title, description, severity, status, notes, assigned_to_user_id.
    # Метод сервісу update_offence_status був більш специфічним.
    # Давайте або зробимо метод сервісу більш загальним, або API ендпоінт буде викликати його з певними параметрами.

    # Варіант 1: Використовуємо існуючий сервісний метод, але передаємо тільки потрібні поля
    if offence_data_update.status is None:  # Статус обов'язковий для цього ендпоінту
        raise HTTPException(status_code=400, detail="Status must be provided for this endpoint.")

    updated_offence = service.update_offence_status(
        db=db,
        offence_id=offence_id,
        status=offence_data_update.status,
        notes=offence_data_update.notes,  # notes опціональний в схемі
        severity=offence_data_update.severity  # severity опціональний в схемі
    )
    if not updated_offence:
        raise HTTPException(status_code=404, detail="Offence not found for status update")
    return updated_offence


# --- Ендпоінт для запуску циклу кореляції (для тестування) ---
@router.post("/run-cycle/",
             summary="Manually trigger a correlation cycle",
             operation_id="correlation_trigger_run_cycle")  # Змінено operation_id для унікальності
def run_correlation_cycle_api(
        db: Session = Depends(get_db),
        es_writer: ElasticsearchWriter = Depends(get_es_writer),
        indicator_service: IndicatorService = Depends(IndicatorService),
        correlation_service: CorrelationService = Depends(CorrelationService),
        device_service: DeviceService = Depends(DeviceService),  # <--- ІН'ЄКЦІЯ DeviceService
        response_service: ResponseService = Depends(ResponseService)  # <--- ІН'ЄКЦІЯ ResponseService
):
    try:
        correlation_service.run_correlation_cycle(
            db=db,
            es_writer=es_writer,
            indicator_service=indicator_service,
            device_service=device_service,  # <--- Передаємо device_service
            response_service=response_service  # <--- Передаємо response_service
        )
        return {"message": "Correlation cycle triggered successfully and ran."}  # Змінено повідомлення
    except Exception as e:
        # TODO: Log error
        # import traceback # Для детального логування під час розробки
        # traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error during correlation cycle: {str(e)}")


@router.get("/dashboard/offences/summary_by_severity",
            response_model=Dict[str, int],  # Повертаємо словник {"low": X, "medium": Y ...}
            summary="Get offence counts grouped by severity for a given period",
            operation_id="dashboard_get_offence_summary_severity")
def get_offence_summary_by_severity_api(
        days_back: int = Query(7, ge=1, le=365, description="Number of past days to include (e.g., 7 for last week)"),
        db: Session = Depends(get_db),
        service: CorrelationService = Depends(CorrelationService)
):
    # Сервіс повертає Dict[str, int], де ключ - це рядок Enum.value
    raw_summary = service.get_offences_summary_by_severity(db=db, days_back=days_back)
    return raw_summary


@router.get("/dashboard/offences/recent",
            response_model=List[OffenceResponse],  # Використовуємо існуючу схему
            summary="Get a list of recent offences",
            operation_id="dashboard_get_recent_offences")
def get_recent_offences_api(
        limit: int = Query(10, ge=1, le=50, description="Number of recent offences to return"),
        db: Session = Depends(get_db),
        service: CorrelationService = Depends(CorrelationService)
):
    return service.get_recent_offences(db=db, limit=limit)


class TopIoCTrigger(BaseModel):
    ioc_value: str
    ioc_type: str  # Або indicator_schemas.IoCTypeEnum, але рядок простіше для JSON
    trigger_count: int


@router.get("/dashboard/offences/top_triggered_iocs",
            response_model=List[TopIoCTrigger],
            summary="Get top IoCs that triggered correlation rules",
            operation_id="dashboard_get_top_triggered_iocs")
def get_top_triggered_iocs_api(
        limit: int = Query(10, ge=1, le=50),
        days_back: int = Query(7, ge=1, le=365),
        db: Session = Depends(get_db),
        service: CorrelationService = Depends(CorrelationService)
):
    return service.get_top_triggered_iocs_from_offences(db=db, limit=limit, days_back=days_back)


class AptOffenceSummary(BaseModel):
    apt_id: int
    apt_name: str
    offence_count: int


@router.get("/dashboard/offences/by_apt",
            response_model=List[AptOffenceSummary],
            summary="Get offence counts grouped by attributed APT",
            operation_id="dashboard_get_offences_by_apt")
def get_offences_by_apt_api(
        days_back: int = Query(7, ge=1, le=365),
        db: Session = Depends(get_db),
        correlation_service: CorrelationService = Depends(CorrelationService),
        apt_service: APTGroupService = Depends(APTGroupService)  # Потрібен для отримання імен APT
):
    return correlation_service.get_offences_by_apt_from_iocs(db=db, apt_service=apt_service, days_back=days_back)
