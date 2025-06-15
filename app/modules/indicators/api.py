# app/modules/indicators/api.py
from typing import List, Optional, Dict

from elasticsearch import exceptions as es_exceptions
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
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


@router.post("/", response_model=Optional[schemas.IoCResponse], status_code=201, operation_id="add_manual_ioc")
def add_manual_ioc_api(
        ioc_create: schemas.IoCCreate,
        db: Session = Depends(get_db),
        es_writer: ElasticsearchWriter = Depends(get_es_writer),  # Використовуємо спільну залежність
        indicator_service: IndicatorService = Depends(IndicatorService),
        apt_service: APTGroupService = Depends(APTGroupService)  # <--- Ін'єкція
):
    try:
        created_ioc = indicator_service.add_ioc(
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


@router.put("/{ioc_elasticsearch_id}", response_model=Optional[schemas.IoCResponse],
            operation_id="indicator_update_ioc")
def update_ioc_api(
        ioc_elasticsearch_id: str = Path(..., description="Elasticsearch ID of the IoC to update"),
        ioc_update: schemas.IoCUpdate = Body(...),
        db: Session = Depends(get_db),  # Потрібен для валідації APT ID через apt_service
        es_writer: ElasticsearchWriter = Depends(get_es_writer),
        indicator_service: IndicatorService = Depends(IndicatorService),
        apt_service: APTGroupService = Depends(APTGroupService)  # Для валідації APT ID
):
    """
    Оновлює існуючий IoC в Elasticsearch.
    """
    try:
        updated_ioc = indicator_service.update_ioc(
            db=db,
            es_writer=es_writer,
            ioc_elasticsearch_id=ioc_elasticsearch_id,
            ioc_update_data=ioc_update,
            apt_service=apt_service
        )
        if updated_ioc:
            return updated_ioc
        else:
            # Якщо сервіс повернув None, це може бути 404 або 500
            raise HTTPException(status_code=404,
                                detail=f"IoC with ES ID '{ioc_elasticsearch_id}' not found or update failed.")
    except ValueError as ve:  # Наприклад, якщо APT ID не знайдено
        raise HTTPException(status_code=400, detail=str(ve))
    except es_exceptions.ElasticsearchWarning as es_exc:
        raise HTTPException(status_code=503, detail=f"Elasticsearch error during IoC update: {str(es_exc)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update IoC: {str(e)}")


@router.delete("/{ioc_elasticsearch_id}", status_code=204, operation_id="indicator_delete_ioc")
def delete_ioc_api(
        ioc_elasticsearch_id: str = Path(..., description="Elasticsearch ID of the IoC to delete"),
        es_writer: ElasticsearchWriter = Depends(get_es_writer),
        service: IndicatorService = Depends(IndicatorService)
):
    """
    Видаляє IoC з Elasticsearch.
    """
    try:
        success = service.delete_ioc(es_writer=es_writer, ioc_elasticsearch_id=ioc_elasticsearch_id)
        if not success:
            # Якщо сервіс повертає False, це може означати, що IoC не знайдено,
            # або сталася помилка ES (яка мала б бути залогована сервісом).
            # Для DELETE, якщо не знайдено, часто повертають 204 або 404.
            # Якщо наш сервіс повертає True, навіть якщо не знайдено (вважаючи "вже видалено"), то тут буде 204.
            # Якщо він повертає False, коли не знайдено, то 404 доречно.
            # Поточний delete_ioc повертає True, якщо 'not_found' від ES.
            pass  # 204 буде повернуто, якщо не було винятку
    except es_exceptions.ElasticsearchWarning as es_exc:
        raise HTTPException(status_code=503, detail=f"Elasticsearch error during IoC deletion: {str(es_exc)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete IoC: {str(e)}")
    return None  # Для 204 No Content


@router.get("/search/", response_model=List[schemas.IoCResponse], operation_id="indicator_search_iocs")
# ... (без змін)
def search_iocs_api(value: str = Query(..., description="Value of the IoC to search for"),
                    ioc_type: Optional[schemas.IoCTypeEnum] = Query(None, description="Optional IoC type to filter by"),
                    es_writer: ElasticsearchWriter = Depends(get_es_writer),
                    service: IndicatorService = Depends(IndicatorService)):
    try:
        return service.find_ioc_by_value(es_writer=es_writer, value=value, ioc_type=ioc_type)
    except es_exceptions.ElasticsearchWarning as es_exc:
        raise HTTPException(status_code=503, detail=f"Elasticsearch search error: {str(es_exc)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search IoCs: {str(e)}")


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


@router.get("/dashboard/summary_by_type",
            response_model=Dict[str, int],  # Повертає {"ipv4-addr": X, "domain-name": Y, ...}
            summary="Get active IoC counts grouped by type",
            operation_id="dashboard_get_ioc_summary_type")
def get_ioc_summary_by_type_api(
        es_writer: ElasticsearchWriter = Depends(get_es_writer),  # Використовуємо спільну залежність
        service: IndicatorService = Depends(IndicatorService)
):
    try:
        return service.get_active_ioc_summary_by_type(es_writer=es_writer)
    except es_exceptions.ElasticsearchWarning as es_exc:
        raise HTTPException(status_code=503, detail=f"Elasticsearch error getting IoC summary: {str(es_exc)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get IoC summary: {str(e)}")


@router.get("/tags/unique", response_model=List[str])
def get_unique_indicator_tags(
        es_writer: ElasticsearchWriter = Depends(get_es_writer),  # Отримуємо клієнт ES через залежність
        service: IndicatorService = Depends(IndicatorService)  # Отримуємо екземпляр сервісу
):
    """
    Ендпоінт для отримання списку всіх унікальних тегів,
    що використовуються в індикаторах компрометації.

    Використовується для заповнення випадаючих списків та автодоповнення на фронтенді.
    """
    try:
        # Уся логіка знаходиться в сервісі. Ендпоінт лише викликає потрібний метод.
        unique_tags = service.get_unique_tags(es_writer=es_writer)
        return unique_tags
    except Exception as e:
        # Базова обробка помилок на випадок, якщо щось піде не так
        raise HTTPException(
            status_code=500,
            detail=f"An internal error occurred while fetching tags: {e}"
        )
