# app/modules/response/api.py
from typing import List, Optional  # Додано Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.database.postgres_models.correlation_models import Offence as OffenceModel  # Для отримання з БД
# Для тестового запуску execute_response_for_offence
from app.modules.correlation.services import CorrelationService
from app.modules.device_interaction.services import DeviceService
from . import schemas as response_schemas  # Перейменовуємо для уникнення конфлікту
from .services import ResponseService

router = APIRouter(
    prefix="/response-management",  # Змінено префікс для унікальності
    tags=["Response Management (Actions & Pipelines)"]
)


# === Ендпоїнти для Дій Реагування (ResponseAction) ===

@router.post("/actions/", response_model=response_schemas.ResponseActionResponse, status_code=201,
             operation_id="response_create_action")
def create_response_action_api(
        action_create: response_schemas.ResponseActionCreate,
        db: Session = Depends(get_db),
        service: ResponseService = Depends(ResponseService)
):
    try:
        return service.create_action(db, action_create)
    except Exception as e:  # Більш загальна обробка помилок, якщо є обмеження унікальності тощо
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/actions/", response_model=List[response_schemas.ResponseActionResponse],
            operation_id="response_get_all_actions")
def get_all_response_actions_api(
        skip: int = 0, limit: int = 100,
        db: Session = Depends(get_db),
        service: ResponseService = Depends(ResponseService)
):
    return service.get_all_actions(db, skip=skip, limit=limit)


@router.get("/actions/{action_id}", response_model=response_schemas.ResponseActionResponse,
            operation_id="response_get_action_by_id")
def get_response_action_by_id_api(
        action_id: int = Path(..., ge=1),
        db: Session = Depends(get_db),
        service: ResponseService = Depends(ResponseService)
):
    action = service.get_action(db, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Response Action not found")
    return action


@router.put("/actions/{action_id}", response_model=response_schemas.ResponseActionResponse,
            operation_id="response_update_action")
def update_response_action_api(
        action_id: int = Path(..., ge=1),
        action_update: response_schemas.ResponseActionUpdate = Body(...),
        db: Session = Depends(get_db),
        service: ResponseService = Depends(ResponseService)
):
    updated_action = service.update_action(db, action_id, action_update)
    if not updated_action:
        raise HTTPException(status_code=404, detail="Response Action not found for update")
    return updated_action


@router.delete("/actions/{action_id}", status_code=204,
               operation_id="response_delete_action")
def delete_response_action_api(
        action_id: int = Path(..., ge=1),
        db: Session = Depends(get_db),
        service: ResponseService = Depends(ResponseService)
):
    if not service.delete_action(db, action_id):
        raise HTTPException(status_code=404, detail="Response Action not found for deletion")
    return None


# === Ендпоїнти для Пайплайнів Реагування (ResponsePipeline) ===

@router.post("/pipelines/", response_model=response_schemas.ResponsePipelineResponse, status_code=201,
             operation_id="response_create_pipeline")
def create_response_pipeline_api(
        pipeline_create: response_schemas.ResponsePipelineCreate,
        db: Session = Depends(get_db),
        service: ResponseService = Depends(ResponseService)
):
    try:
        return service.create_pipeline(db, pipeline_create)
    except ValueError as ve:  # Наприклад, якщо action_id в actions_config не знайдено
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create response pipeline: {str(e)}")


@router.get("/pipelines/", response_model=List[response_schemas.ResponsePipelineResponse],
            operation_id="response_get_all_pipelines")
def get_all_response_pipelines_api(
        skip: int = 0, limit: int = 100,
        db: Session = Depends(get_db),
        service: ResponseService = Depends(ResponseService)
):
    return service.get_all_pipelines(db, skip=skip, limit=limit)


@router.get("/pipelines/{pipeline_id}", response_model=response_schemas.ResponsePipelineResponse,
            operation_id="response_get_pipeline_by_id")
def get_response_pipeline_by_id_api(
        pipeline_id: int = Path(..., ge=1),
        db: Session = Depends(get_db),
        service: ResponseService = Depends(ResponseService)
):
    pipeline = service.get_pipeline(db, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Response Pipeline not found")
    return pipeline


@router.put("/pipelines/{pipeline_id}", response_model=response_schemas.ResponsePipelineResponse,
            operation_id="response_update_pipeline")
def update_response_pipeline_api(
        pipeline_id: int = Path(..., ge=1),
        pipeline_update: response_schemas.ResponsePipelineUpdate = Body(...),
        db: Session = Depends(get_db),
        service: ResponseService = Depends(ResponseService)
):
    try:
        updated_pipeline = service.update_pipeline(db, pipeline_id, pipeline_update)
        if not updated_pipeline:
            raise HTTPException(status_code=404, detail="Response Pipeline not found for update")
        return updated_pipeline
    except ValueError as ve:  # Наприклад, якщо action_id в новому actions_config не знайдено
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update response pipeline: {str(e)}")


@router.delete("/pipelines/{pipeline_id}", status_code=204,
               operation_id="response_delete_pipeline")
def delete_response_pipeline_api(
        pipeline_id: int = Path(..., ge=1),
        db: Session = Depends(get_db),
        service: ResponseService = Depends(ResponseService)
):
    if not service.delete_pipeline(db, pipeline_id):
        raise HTTPException(status_code=404, detail="Response Pipeline not found for deletion")
    return None


# --- Тестовий ендпоїнт для запуску реагування на офенс (опціонально) ---
# Цей ендпоїнт може бути корисним для відладки, але в реальній системі
# execute_response_for_offence викликається з CorrelationService.

class ExecuteResponsePayload(BaseModel):  # Pydantic схема для тіла запиту
    offence_id: int


@router.post("/execute-for-offence/",
             summary="Manually trigger response execution for a given offence ID (for testing)",
             operation_id="response_execute_for_offence")
def execute_response_for_offence_api(
        payload: ExecuteResponsePayload = Body(...),
        db: Session = Depends(get_db),
        response_service: ResponseService = Depends(ResponseService),
        device_service: DeviceService = Depends(DeviceService),  # Потрібен для виконання дій
        correlation_service: CorrelationService = Depends(CorrelationService)  # Потрібен для отримання офенса
):
    offence_db_obj: Optional[OffenceModel] = correlation_service.get_offence_by_id(db, offence_id=payload.offence_id)
    if not offence_db_obj:
        raise HTTPException(status_code=404, detail=f"Offence with ID {payload.offence_id} not found.")

    try:
        response_service.execute_response_for_offence(
            db=db,
            offence=offence_db_obj,
            device_service=device_service
        )
        return {"message": f"Response execution triggered for offence ID {payload.offence_id}."}
    except Exception as e:
        # TODO: Log error
        raise HTTPException(status_code=500, detail=f"Error during response execution: {str(e)}")