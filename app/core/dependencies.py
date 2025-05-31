# app/core/dependencies.py
from fastapi import HTTPException
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from app.core.config import settings  # Для ES налаштувань


def get_es_writer():  # Уніфікована назва
    """FastAPI Dependency to get an ElasticsearchWriter instance."""
    try:
        # Припускаємо, що ELASTICSEARCH_HOST та ELASTICSEARCH_PORT_API визначені в settings
        es_host_url = f"http://{settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT_API}"
        writer = ElasticsearchWriter(es_hosts=[es_host_url])
        # `yield writer` не потрібен, якщо writer не керує ресурсами, що потребують `finally`
        # Якщо ElasticsearchWriter.close() важливий, тоді так:
        # try:
        #     yield writer
        # finally:
        #     writer.close() # Але це закриє з'єднання після кожного запиту, що може бути неефективно.
        # Краще керувати життєвим циклом es_client на рівні додатку або не закривати його так часто.
        # Поки що, для простоти, просто повертаємо екземпляр.
        return writer
    except ConnectionError as e:
        print(f"Dependency: Failed to initialize ElasticsearchWriter: {e}")
        raise HTTPException(status_code=503, detail=f"Elasticsearch service unavailable: {e}")
    except Exception as e_other:
        print(f"Dependency: Unexpected error initializing ElasticsearchWriter: {e_other}")
        raise HTTPException(status_code=500, detail=f"Unexpected error with Elasticsearch service: {e_other}")
