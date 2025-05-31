# app/modules/apt_groups/api.py
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter, es_exceptions
from app.modules.indicators import schemas as indicator_schemas  # <--- ДОДАНО для response_model
from app.modules.indicators.services import IndicatorService  # <--- ДОДАНО
# Для взаємодії з іншими сервісами
from . import schemas
from .services import APTGroupService
from ...core.dependencies import get_es_writer

router = APIRouter(
    prefix="/apt-groups",
    tags=["APT Groups"]
)


@router.post("/", response_model=schemas.APTGroupResponse, status_code=201, operation_id="create_apt_group")
def create_apt_group_api(  # Перейменовано для уникнення конфлікту імен
        apt_create: schemas.APTGroupCreate, db: Session = Depends(get_db),
        service: APTGroupService = Depends(APTGroupService)
):
    try:
        return service.create_apt_group(db=db, apt_group_create=apt_create)
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create APT group: {str(e)}")


@router.get("/", response_model=List[schemas.APTGroupResponse], operation_id="get_all_apt_groups")
def read_apt_groups_api(  # Перейменовано
        skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200),
        db: Session = Depends(get_db), service: APTGroupService = Depends(APTGroupService)
):
    return service.get_all_apt_groups(db=db, skip=skip, limit=limit)


@router.get("/{group_id}", response_model=schemas.APTGroupResponse, operation_id="get_apt_group")
def read_apt_group_api(  # Перейменовано
        group_id: int = Path(..., ge=1), db: Session = Depends(get_db),
        service: APTGroupService = Depends(APTGroupService)
):
    db_group = service.get_apt_group_by_id(db=db, apt_group_id=group_id)
    if db_group is None: raise HTTPException(status_code=404, detail="APT Group not found")
    return db_group


@router.put("/{group_id}", response_model=schemas.APTGroupResponse, operation_id="update_apt_group")
def update_apt_group_api(  # Перейменовано
        group_id: int = Path(..., ge=1), apt_group_update: schemas.APTGroupUpdate = Body(...),
        db: Session = Depends(get_db), service: APTGroupService = Depends(APTGroupService)
):
    updated_group = service.update_apt_group(db=db, apt_group_id=group_id, apt_group_update=apt_group_update)
    if updated_group is None: raise HTTPException(status_code=404, detail="APT Group not found for update")
    return updated_group


@router.delete("/{group_id}", status_code=204, operation_id="delete_apt_group")
def delete_apt_group_api(
        group_id: int = Path(..., ge=1), db: Session = Depends(get_db),
        es_writer: ElasticsearchWriter = Depends(get_es_writer),  # <--- ВИКОРИСТАННЯ
        apt_service: APTGroupService = Depends(APTGroupService),
        indicator_service: IndicatorService = Depends(IndicatorService)
):
    try:
        success = apt_service.delete_apt_group(
            db=db, es_writer=es_writer, apt_group_id=group_id,
            indicator_service=indicator_service  # <--- Передача
        )
        if not success:
            raise HTTPException(status_code=404, detail="APT Group not found or failed to update linked IoCs.")
    # ... (обробка помилок)
    except es_exceptions.ElasticsearchWarning as es_exc:
        raise HTTPException(status_code=503, detail=f"ES error: {str(es_exc)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete APT group: {str(e)}")
    return None


@router.get("/{group_id}/iocs", response_model=List[indicator_schemas.IoCResponse],
            operation_id="get_iocs_for_apt_group")
def get_iocs_for_apt_group_api(
        group_id: int = Path(..., ge=1), skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=1000),
        db: Session = Depends(get_db), es_writer: ElasticsearchWriter = Depends(get_es_writer),  # <--- ВИКОРИСТАННЯ
        apt_service: APTGroupService = Depends(APTGroupService),
        indicator_service: IndicatorService = Depends(IndicatorService)
):
    apt_group = apt_service.get_apt_group_by_id(db, group_id)
    if not apt_group: raise HTTPException(status_code=404, detail=f"APT Group ID {group_id} not found.")
    try:
        return apt_service.get_iocs_for_apt_group(
            es_writer=es_writer, apt_group_id=group_id,
            indicator_service=indicator_service,  # <--- Передача
            skip=skip, limit=limit
        )
    # ... (обробка помилок)
    except es_exceptions.ElasticsearchWarning as es_exc:
        raise HTTPException(status_code=503, detail=f"ES error: {str(es_exc)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get IoCs for APT group: {str(e)}")
