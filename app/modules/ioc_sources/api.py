# app/modules/ioc_sources/api.py
from typing import List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Body
from sqlalchemy.orm import Session

from app.core.config import settings  # Для ES налаштувань, якщо створюємо writer тут
from app.core.database import get_db
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter  # Потрібен для fetch
from . import schemas
from .services import IoCSourceService
from ...core.dependencies import get_es_writer


# --- Залежність для ElasticsearchWriter (якщо потрібна в цьому API) ---
# Краще, щоб сервіси самі отримували es_writer або es_client, якщо він їм потрібен постійно.
# Якщо es_writer потрібен лише для одного методу, його можна передавати.
def get_es_writer_dependency_ioc_source():  # Унікальне ім'я
    try:
        es_host_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT_API}"
        writer = ElasticsearchWriter(es_hosts=[es_host_url])
        yield writer
    except ConnectionError as e:
        raise HTTPException(status_code=503, detail=f"ES service unavailable (IoCSources API): {e}")
    except Exception as e_other:
        raise HTTPException(status_code=500, detail=f"Unexpected error with ES service (IoCSources API): {e_other}")


# Для взаємодії сервісів, ми будемо ін'єктувати їх у ендпоінти
from app.modules.apt_groups.services import APTGroupService
from app.modules.indicators.services import IndicatorService

router = APIRouter(
    prefix="/ioc-sources",
    tags=["IoC Sources"]
)


@router.post("/", response_model=schemas.IoCSourceResponse, status_code=201, operation_id="create_ioc_source")
def create_ioc_source_api(
        source_create: schemas.IoCSourceCreate,
        db: Session = Depends(get_db),
        service: IoCSourceService = Depends(IoCSourceService)
):
    try:
        return service.create_ioc_source(db=db, source_create=source_create)
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create IoC source: {str(e)}")


@router.get("/", response_model=List[schemas.IoCSourceResponse], operation_id="get_all_ioc_sources")
def read_ioc_sources_api(
        skip: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=200),
        db: Session = Depends(get_db), service: IoCSourceService = Depends(IoCSourceService)
):
    return service.get_all_ioc_sources(db=db, skip=skip, limit=limit)


@router.get("/{source_id}", response_model=schemas.IoCSourceResponse, operation_id="get_ioc_source")
def read_ioc_source_api(
        source_id: int = Path(..., ge=1), db: Session = Depends(get_db),
        service: IoCSourceService = Depends(IoCSourceService)
):
    db_source = service.get_ioc_source_by_id(db=db, source_id=source_id)
    if db_source is None: raise HTTPException(status_code=404, detail="IoC Source not found")
    return db_source


@router.put("/{source_id}", response_model=schemas.IoCSourceResponse, operation_id="update_ioc_source")
def update_ioc_source_api(
        source_id: int = Path(..., ge=1), source_update: schemas.IoCSourceUpdate = Body(...),
        db: Session = Depends(get_db), service: IoCSourceService = Depends(IoCSourceService)
):
    updated_source = service.update_ioc_source(db=db, source_id=source_id, source_update=source_update)
    if updated_source is None: raise HTTPException(status_code=404, detail="IoC Source not found for update")
    return updated_source


@router.delete("/{source_id}", status_code=204, operation_id="delete_ioc_source")
def delete_ioc_source_api(
        source_id: int = Path(..., ge=1), db: Session = Depends(get_db),
        service: IoCSourceService = Depends(IoCSourceService)
):
    if not service.delete_ioc_source(db=db, source_id=source_id):
        raise HTTPException(status_code=404, detail="IoC Source not found for deletion")
    return None


@router.post("/{source_id}/fetch-iocs", response_model=Dict[str, Any], operation_id="fetch_iocs_from_ioc_source")
def fetch_iocs_from_source_api(
        source_id: int = Path(..., ge=1),
        db: Session = Depends(get_db),
        es_writer: ElasticsearchWriter = Depends(get_es_writer),  # <--- ВИКОРИСТАННЯ
        ioc_source_service: IoCSourceService = Depends(IoCSourceService),
        apt_service: APTGroupService = Depends(APTGroupService),
        indicator_service: IndicatorService = Depends(IndicatorService)
):
    try:
        result = ioc_source_service.fetch_and_store_iocs_from_source(
            db=db,
            source_id=source_id,
            es_writer=es_writer,
            apt_service=apt_service,  # Передаємо
            indicator_service=indicator_service  # Передаємо
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=500, detail=result.get("message", "Failed to fetch IoCs."))
        return result
    # ... (обробка помилок)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching IoCs: {str(e)}")
