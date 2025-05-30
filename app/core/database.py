# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session  # Імпортуємо Session для type hinting в get_db

from .config import settings  # Імпортуємо налаштування, де є DATABASE_URL

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

print("Database connection established")

Base = declarative_base()


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db  # Надаємо сесію
    finally:
        db.close()  # Закриваємо сесію після використання
