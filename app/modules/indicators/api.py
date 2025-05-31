# app/modules/indicators/api.py
from typing import List, Optional

from elasticsearch import exceptions as es_exceptions
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session  # Потрібен для передачі в сервіс для валідації APT ID

from app.core.database import get_db
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from . import schemas
from .services import IndicatorService
from ..apt_groups.services import APTGroupService
from ...core.dependencies import get_es_writer

router = APIRouter(
    prefix="/iocs",  # Окремий префікс для IoC
    tags=["Indicators (IoCs)"]
)


@router.post("/", response_model=Optional[schemas.IoCResponse], status_code=201, operation_id="add_manual_ioc")
def add_manual_ioc_api(
        ioc_create: schemas.IoCCreate,
        db: Session = Depends(get_db),
        es_writer: ElasticsearchWriter = Depends(get_es_writer),  # Використовуємо спільну залежність
        indicator_service: IndicatorService = Depends(IndicatorService),
        apt_service: APTGroupService = Depends(APTGroupService)  # <--- Ін'єкція
):
    try:
        created_ioc = indicator_service.add_manual_ioc(
            db=db, es_writer=es_writer, ioc_create_data=ioc_create,
            apt_service=apt_service  # <--- Передача
        )
        if created_ioc:
            return created_ioc
        else:
            raise HTTPException(status_code=500, detail="Failed to add IoC to ES.")
    # ... (обробка помилок)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add IoC: {str(e)}")


@router.post("/{ioc_elasticsearch_id}/link-apt/{apt_group_id}", response_model=Optional[schemas.IoCResponse],
             operation_id="link_ioc_to_apt")
def link_ioc_to_apt_api(
        ioc_elasticsearch_id: str = Path(..., description="ES ID of the IoC"),
        apt_group_id: int = Path(..., ge=1, description="DB ID of the APT Group"),
        db: Session = Depends(get_db),
        es_writer: ElasticsearchWriter = Depends(get_es_writer),
        indicator_service: IndicatorService = Depends(IndicatorService),
        apt_service: APTGroupService = Depends(APTGroupService)  # <--- Ін'єкція
):
    try:
        updated_ioc = indicator_service.link_ioc_to_apt(
            db=db, es_writer=es_writer, ioc_es_id=ioc_elasticsearch_id,
            apt_group_id=apt_group_id,
            apt_service=apt_service  # <--- Передача
        )
        if updated_ioc:
            return updated_ioc
        else:
            raise HTTPException(status_code=404, detail="Failed to link. IoC or APT not found, or ES error.")
    # ... (обробка помилок)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except es_exceptions.ElasticsearchWarning as es_exc:
        raise HTTPException(status_code=503, detail=f"ES error: {str(es_exc)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to link IoC to APT: {str(e)}")


@router.get("/list-all/", response_model=List[schemas.IoCResponse], summary="Get all IoCs (paginated)",
            operation_id="get_all_iocs_list")
def get_all_iocs_api(
        skip: int = Query(0, ge=0, description="Number of IoCs to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of IoCs to return"),
        es_writer: ElasticsearchWriter = Depends(get_es_writer),
        service: IndicatorService = Depends(IndicatorService)
):
    """
    Отримує список всіх індикаторів компрометації з Elasticsearch з пагінацією.
    """
    try:
        iocs = service.get_all_iocs(es_writer=es_writer, skip=skip, limit=limit)
        return iocs
    except es_exceptions.ElasticsearchWarning as es_exc:
        # TODO: Log error es_exc
        raise HTTPException(status_code=503, detail=f"Elasticsearch error retrieving all IoCs: {str(es_exc)}")
    except Exception as e:
        # TODO: Log error e
        raise HTTPException(status_code=500, detail=f"Failed to retrieve all IoCs: {str(e)}")


@router.get("/today/", response_model=List[schemas.IoCResponse], summary="Get IoCs created today (paginated)",
            operation_id="get_iocs_today_list")
def get_iocs_created_today_api(
        skip: int = Query(0, ge=0, description="Number of IoCs to skip"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of IoCs to return"),
        es_writer: ElasticsearchWriter = Depends(get_es_writer),
        service: IndicatorService = Depends(IndicatorService)
):
    """
    Отримує список індикаторів компрометації, доданих до системи сьогодні.
    Порівняння відбувається за полем 'created_at_siem'.
    """
    try:
        iocs = service.get_iocs_created_today(es_writer=es_writer, skip=skip, limit=limit)
        return iocs
    except es_exceptions.ElasticsearchWarning as es_exc:
        # TODO: Log error es_exc
        raise HTTPException(status_code=503, detail=f"Elasticsearch error retrieving today's IoCs: {str(es_exc)}")
    except Exception as e:
        # TODO: Log error e
        raise HTTPException(status_code=500, detail=f"Failed to retrieve today's IoCs: {str(e)}")
