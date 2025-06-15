# app/scripts/create_admin.py
import os
import sys
import asyncio
from sqlalchemy.orm import Session

# Це необхідно, щоб скрипт "бачив" модулі вашого додатку
# Додаємо кореневу директорію проєкту до шляхів пошуку модулів
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.core.database import get_db
from app.modules.users.services import UserService
from app.modules.users.schemas import UserCreate
from app.database.postgres_models.user_models import UserRoleEnum


def create_initial_admin(db: Session, username: str, password: str, full_name: str = "Admin"):
    """
    Функція для створення першого адміністратора.
    """
    print("Attempting to create an admin user...")
    user_service = UserService()

    # Перевіряємо, чи існує користувач з таким іменем
    existing_user = user_service.get_user_by_username(db, username=username)
    if existing_user:
        print(f"User with username '{username}' already exists. No action taken.")
        return

    # Створюємо нового користувача з роллю адміна
    admin_user_schema = UserCreate(
        username=username,
        password=password,
        full_name=full_name,
        role=UserRoleEnum.ADMIN  # Явно вказуємо роль
    )

    try:
        new_admin = user_service.create_user(db, user=admin_user_schema)
        print(f"Successfully created admin user: {new_admin.username} with ID: {new_admin.id}")
    except ValueError as e:
        print(f"An error occurred: {e}")
    except Exception as e:
        print(f"A critical error occurred: {e}")


if __name__ == "__main__":
    # Отримуємо сесію бази даних
    db_session = next(get_db())
    try:
        # ЗАМІНІТЬ ЦІ ЗНАЧЕННЯ НА ВАШІ!
        # В ідеалі, їх потрібно передавати через аргументи командного рядка або змінні середовища
        ADMIN_USERNAME = "admin"
        ADMIN_PASSWORD = "admin123"

        print("-" * 50)
        print(f"Running admin creation script for username: {ADMIN_USERNAME}")

        create_initial_admin(
            db=db_session,
            username=ADMIN_USERNAME,
            password=ADMIN_PASSWORD
        )

        print("Script finished.")
        print("-" * 50)
    finally:
        db_session.close()