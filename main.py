# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager  # Для lifespan в нових версіях FastAPI/Starlette

from app.core.database import engine, Base  # Для створення таблиць (якщо ще не через Alembic)
from app.modules.device_interaction import api as device_interaction_api
from app.modules.data_ingestion.service import DataIngestionService  # <--- Імпортуй твій сервіс

from app.modules.ioc_sources import api as ioc_sources_api  # <--- НОВИЙ
from app.modules.apt_groups import api as apt_groups_api  # <--- НОВИЙ
from app.modules.indicators import api as indicators_api  # <--- НОВИЙ
from app.modules.correlation import api as correlation_api

# ... інші імпорти ...

# --- Створення екземпляра сервісу прийому даних ---
# Ти можеш налаштувати хост/порт тут або завантажити з конфігурації
# Для прикладу, використаємо порт 514, як у твоєму тестовому блоці.
# Переконайся, що цей порт не конфліктує з іншими сервісами і відкритий у файрволі.
# УВАГА: Якщо ти запускаєш додаток з sudo для використання порту 514, будь обережний.
# Краще налаштувати перенаправлення портів або використовувати непривілейований порт для розробки.
SYSLOG_LISTEN_HOST = "0.0.0.0"
SYSLOG_LISTEN_PORT = 514  # Або 514, якщо є права і потреба

data_ingestion_service = DataIngestionService(
    syslog_host=SYSLOG_LISTEN_HOST,
    syslog_port=SYSLOG_LISTEN_PORT
)


# --- Обробники подій життєвого циклу (lifespan) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Код, що виконується перед запуском додатку (startup)
    print("Application startup...")

    # Створення таблиць (якщо ще використовуєш цей метод, а не тільки Alembic)
    # try:
    #     print("Checking/creating database tables...")
    #     Base.metadata.create_all(bind=engine)
    #     print("Database tables checked/created successfully.")
    # except Exception as e:
    #     print(f"Error creating database tables: {e}")

    # Запуск слухачів сервісу прийому даних
    try:
        print(f"Starting data ingestion listeners (Syslog on {SYSLOG_LISTEN_HOST}:{SYSLOG_LISTEN_PORT})...")
        data_ingestion_service.start_listeners()
    except Exception as e:
        print(f"Error starting data ingestion listeners: {e}")
        # Тут можна вирішити, чи критична ця помилка для запуску всього додатку

    yield  # Додаток працює тут

    # Код, що виконується після зупинки додатку (shutdown)
    print("Application shutdown...")
    try:
        print("Stopping data ingestion listeners...")
        data_ingestion_service.stop_listeners()
    except Exception as e:
        print(f"Error stopping data ingestion listeners: {e}")


# --- Створення екземпляра FastAPI з lifespan ---
app = FastAPI(
    title="Програмний модуль агрегації та обробки індикаторів безпеки",
    description="API для управління пристроями та іншими компонентами системи безпеки ЗСУ.",
    version="0.1.0",
    lifespan=lifespan  # <--- Підключення обробників життєвого циклу
)

# Підключаємо роутер для модуля взаємодії з пристроями
app.include_router(device_interaction_api.router)  # Префікс вже визначений в самому роутері
app.include_router(device_interaction_api.router)
app.include_router(ioc_sources_api.router)  # <--- ДОДАНО
app.include_router(apt_groups_api.router)  # <--- ДОДАНО
app.include_router(indicators_api.router)  # <--- ДОДАНО

app.include_router(correlation_api.router)


@app.get("/")
async def root():
    return {"message": "Ласкаво просимо до API модуля безпеки!"}

# ... інші роутери та логіка ...
