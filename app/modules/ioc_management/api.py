from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

from app.core.database import get_db
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from app.core.config import settings
from elasticsearch import exceptions as es_exceptions

from . import schemas
from .services import IoCManagementService

router = APIRouter(
    prefix="/ioc-management", # Змінив префікс для уникнення конфлікту з /ioc для окремих IoC
    tags=["IoC and APT Management"]
)

# --- Допоміжна функція для ElasticsearchWriter ---
# УВАГА: Це не найкращий підхід для продакшену. В ідеалі es_writer або es_client
# має бути залежністю, що ін'єктується на рівні всього додатку або сервісу.
# Це створює новий екземпляр на кожен запит, що може бути неефективно.
def get_es_writer_dependency():
    try:
        es_host_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT_API}"
        writer = ElasticsearchWriter(es_hosts=[es_host_url])
        yield writer # Надаємо writer
    except ConnectionError as e:
        # Логуємо помилку або обробляємо її відповідним чином
        print(f"API Layer: Failed to initialize ElasticsearchWriter for dependency: {e}")
        # Кидаємо HTTPException, щоб запит завершився з помилкою сервера
        raise HTTPException(status_code=503, detail=f"Elasticsearch service unavailable: {e}")
    except Exception as e_other:
        print(f"API Layer: Unexpected error initializing ElasticsearchWriter for dependency: {e_other}")
        raise HTTPException(status_code=500, detail=f"Unexpected error with Elasticsearch service: {e_other}")
    finally:
        # Тут не потрібно робити writer.close(), оскільки сесія Elasticsearch клієнта
        # зазвичай керується самим клієнтом або закривається при завершенні додатку.
        # Якщо writer має метод close, який потрібно викликати, це робиться після yield.
        # Але для об'єкта, що використовується як залежність, це не типово.
        pass

# === Ендпоїнти для Джерел IoC (IoCSource) ===

@router.post("/sources/", response_model=schemas.IoCSourceResponse, status_code=201, summary="Create new IoC Source")
def create_ioc_source_api(
    source_create: schemas.IoCSourceCreate,
    db: Session = Depends(get_db),
    service: IoCManagementService = Depends(IoCManagementService)
):
    try:
        return service.create_ioc_source(db=db, source_create=source_create)
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve)) # 409 Conflict, якщо ім'я вже існує
    except Exception as e:
        # TODO: Log error e
        raise HTTPException(status_code=500, detail=f"Failed to create IoC source: {str(e)}")

@router.get("/sources/", response_model=List[schemas.IoCSourceResponse], summary="Get all IoC Sources")
def read_ioc_sources_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    service: IoCManagementService = Depends(IoCManagementService)
):
    return service.get_all_ioc_sources(db=db, skip=skip, limit=limit)

@router.get("/sources/{source_id}", response_model=schemas.IoCSourceResponse, summary="Get IoC Source by ID")
def read_ioc_source_api(
    source_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    service: IoCManagementService = Depends(IoCManagementService)
):
    db_source = service.get_ioc_source_by_id(db=db, source_id=source_id)
    if db_source is None:
        raise HTTPException(status_code=404, detail="IoC Source not found")
    return db_source

@router.put("/sources/{source_id}", response_model=schemas.IoCSourceResponse, summary="Update IoC Source")
def update_ioc_source_api(
    source_id: int = Path(..., ge=1),
    source_update: schemas.IoCSourceUpdate = Body(...),
    db: Session = Depends(get_db),
    service: IoCManagementService = Depends(IoCManagementService)
):
    updated_source = service.update_ioc_source(db=db, source_id=source_id, source_update=source_update)
    if updated_source is None:
        raise HTTPException(status_code=404, detail="IoC Source not found for update")
    return updated_source

@router.delete("/sources/{source_id}", status_code=204, summary="Delete IoC Source")
def delete_ioc_source_api(
    source_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    service: IoCManagementService = Depends(IoCManagementService)
):
    success = service.delete_ioc_source(db=db, source_id=source_id)
    if not success:
        raise HTTPException(status_code=404, detail="IoC Source not found for deletion")
    return None # Відповідь 204 No Content

@router.post("/sources/{source_id}/fetch-iocs", response_model=Dict[str, Any], summary="Fetch IoCs from a source (mocked)")
def fetch_iocs_from_source_api(
    source_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    es_writer: ElasticsearchWriter = Depends(get_es_writer_dependency),
    service: IoCManagementService = Depends(IoCManagementService)
):
    try:
        result = service.fetch_and_store_iocs_from_source(db=db, source_id=source_id, es_writer=es_writer)
        if result.get("status") == "error": # Перевірка статусу з відповіді сервісу
            # Сервіс міг повернути помилку, якщо джерело не знайдено або es_writer недоступний
            raise HTTPException(status_code=404 if "not found" in result.get("message", "").lower() else 500,
                                detail=result.get("message", "Failed to fetch IoCs from source."))
        return result
    except ValueError as ve:
         raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        # TODO: Log error e
        raise HTTPException(status_code=500, detail=f"Unexpected error fetching IoCs: {str(e)}")

# === Ендпоїнти для Індикаторів Компрометації (IoC) ===

@router.post("/iocs/", response_model=Optional[schemas.IoCResponse], status_code=201, summary="Manually add a new IoC")
def add_manual_ioc_api(
    ioc_create: schemas.IoCCreate,
    db: Session = Depends(get_db), # Потрібен для валідації APT ID
    es_writer: ElasticsearchWriter = Depends(get_es_writer_dependency),
    service: IoCManagementService = Depends(IoCManagementService)
):
    try:
        created_ioc = service.add_manual_ioc(db=db, es_writer=es_writer, ioc_create_data=ioc_create)
        if created_ioc:
            return created_ioc
        else:
            # Сервіс мав би залогувати причину, якщо повертає None
            raise HTTPException(status_code=500, detail="Failed to add IoC to Elasticsearch. Check service logs.")
    except ValueError as ve: # Наприклад, якщо APT ID не знайдено
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # TODO: Log error e
        raise HTTPException(status_code=500, detail=f"Failed to manually add IoC: {str(e)}")

@router.get("/iocs/search/", response_model=List[schemas.IoCResponse], summary="Search IoCs by value and type")
def search_iocs_api(
    value: str = Query(..., description="Value of the IoC to search for"),
    ioc_type: Optional[schemas.IoCTypeEnum] = Query(None, description="Optional IoC type to filter by"),
    es_writer: ElasticsearchWriter = Depends(get_es_writer_dependency),
    service: IoCManagementService = Depends(IoCManagementService)
):
    try:
        # Метод сервісу тепер синхронний
        results = service.find_ioc_by_value(es_writer=es_writer, value=value, ioc_type=ioc_type)
        return results
    except es_exceptions.ElasticsearchWarning as es_exc:
        # TODO: Log error es_exc
        raise HTTPException(status_code=503, detail=f"Elasticsearch search error: {str(es_exc)}")
    except Exception as e:
        # TODO: Log error e
        raise HTTPException(status_code=500, detail=f"Failed to search IoCs: {str(e)}")

# === Ендпоїнти для APT-угруповань (APTGroup) ===

@router.post("/apt-groups/", response_model=schemas.APTGroupResponse, status_code=201, summary="Create new APT Group")
def create_apt_group_api(
    apt_create: schemas.APTGroupCreate,
    db: Session = Depends(get_db),
    service: IoCManagementService = Depends(IoCManagementService)
):
    try:
        return service.create_apt_group(db=db, apt_group_create=apt_create)
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve)) # 409 Conflict for existing name
    except Exception as e:
        # TODO: Log error e
        raise HTTPException(status_code=500, detail=f"Failed to create APT group: {str(e)}")

@router.get("/apt-groups/", response_model=List[schemas.APTGroupResponse], summary="Get all APT Groups")
def read_apt_groups_api(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    service: IoCManagementService = Depends(IoCManagementService)
):
    return service.get_all_apt_groups(db=db, skip=skip, limit=limit)

@router.get("/apt-groups/{group_id}", response_model=schemas.APTGroupResponse, summary="Get APT Group by ID")
def read_apt_group_api(
    group_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    service: IoCManagementService = Depends(IoCManagementService)
):
    db_group = service.get_apt_group_by_id(db=db, apt_group_id=group_id)
    if db_group is None:
        raise HTTPException(status_code=404, detail="APT Group not found")
    # Важливо: service.get_apt_group_by_id повертає модель SQLAlchemy.
    # FastAPI автоматично конвертує її в schemas.APTGroupResponse завдяки response_model.
    return db_group

@router.put("/apt-groups/{group_id}", response_model=schemas.APTGroupResponse, summary="Update APT Group")
def update_apt_group_api(
    group_id: int = Path(..., ge=1),
    apt_update: schemas.APTGroupUpdate = Body(...),
    db: Session = Depends(get_db),
    service: IoCManagementService = Depends(IoCManagementService)
):
    updated_group = service.update_apt_group(db=db, apt_group_id=group_id, apt_group_update=apt_update)
    if updated_group is None:
        raise HTTPException(status_code=404, detail="APT Group not found for update")
    return updated_group

@router.delete("/apt-groups/{group_id}", status_code=204, summary="Delete APT Group and unlink from IoCs")
def delete_apt_group_api(
    group_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    es_writer: ElasticsearchWriter = Depends(get_es_writer_dependency), # Потрібен для оновлення IoC
    service: IoCManagementService = Depends(IoCManagementService)
):
    try:
        # Передаємо es_writer в сервісний метод
        success = service.delete_apt_group(db=db, es_writer=es_writer, apt_group_id=group_id)
        if not success:
            # Причина може бути або "APT Group not found" або помилка ES
            # Сервіс має логувати деталі.
            raise HTTPException(status_code=404, detail="APT Group not found or failed to update linked IoCs.")
    except es_exceptions.ElasticsearchWarning as es_exc:
        raise HTTPException(status_code=503, detail=f"Elasticsearch error during APT group deletion: {str(es_exc)}")
    except Exception as e:
        # TODO: Log error e
        raise HTTPException(status_code=500, detail=f"Failed to delete APT group: {str(e)}")
    return None # Відповідь 204 No Content

# --- Ендпоїнти для зв'язків IoC та APT ---

@router.post("/iocs/{ioc_elasticsearch_id}/link-apt/{apt_group_id}", response_model=Optional[schemas.IoCResponse], summary="Link an IoC to an APT Group")
def link_ioc_to_apt_api(
    ioc_elasticsearch_id: str = Path(..., description="Elasticsearch ID of the IoC"),
    apt_group_id: int = Path(..., ge=1, description="Database ID of the APT Group"),
    db: Session = Depends(get_db),
    es_writer: ElasticsearchWriter = Depends(get_es_writer_dependency),
    service: IoCManagementService = Depends(IoCManagementService)
):
    """
    Прив'язує існуючий IoC (за його Elasticsearch ID) до APT-угруповання.
    """
    try:
        updated_ioc = service.link_ioc_to_apt(db=db, es_writer=es_writer, ioc_es_id=ioc_elasticsearch_id, apt_group_id=apt_group_id)
        if updated_ioc:
            return updated_ioc
        else:
            # Якщо IoC або APT не знайдено, або сталася помилка ES
            raise HTTPException(status_code=404, detail="Failed to link IoC to APT group. IoC or APT Group not found, or Elasticsearch error.")
    except ValueError as ve: # Наприклад, APT група не знайдена
        raise HTTPException(status_code=404, detail=str(ve))
    except es_exceptions.ElasticsearchWarning as es_exc:
        raise HTTPException(status_code=503, detail=f"Elasticsearch error during IoC-APT linking: {str(es_exc)}")
    except Exception as e:
        # TODO: Log error e
        raise HTTPException(status_code=500, detail=f"Failed to link IoC to APT group: {str(e)}")


@router.get("/apt-groups/{group_id}/iocs", response_model=List[schemas.IoCResponse], summary="Get IoCs linked to an APT Group")
def get_iocs_for_apt_group_api(
    group_id: int = Path(..., ge=1, description="Database ID of the APT Group"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000), # Можна дозволити більший ліміт для IoC
    db: Session = Depends(get_db), # Потрібен, щоб перевірити, чи існує сама APT група
    es_writer: ElasticsearchWriter = Depends(get_es_writer_dependency),
    service: IoCManagementService = Depends(IoCManagementService)
):
    # Перевірка, чи існує APT група
    apt_group = service.get_apt_group_by_id(db, group_id)
    if not apt_group:
        raise HTTPException(status_code=404, detail=f"APT Group with ID {group_id} not found.")
    try:
        return service.get_iocs_for_apt_group(es_writer=es_writer, apt_group_id=group_id, skip=skip, limit=limit)
    except es_exceptions.ElasticsearchWarning as es_exc:
        raise HTTPException(status_code=503, detail=f"Elasticsearch error retrieving IoCs for APT group: {str(es_exc)}")
    except Exception as e:
        # TODO: Log error e
        raise HTTPException(status_code=500, detail=f"Failed to retrieve IoCs for APT group: {str(e)}")