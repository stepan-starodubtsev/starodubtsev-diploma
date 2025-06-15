# app/modules/users/services.py
from sqlalchemy.orm import Session
from typing import Optional, List
from fastapi import HTTPException, status
from app.database.postgres_models.user_models import User
from app.modules.users import schemas
from app.core.security import get_password_hash, verify_password


class UserService:
    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    def get_user(self, db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def get_all_users(self, db: Session, skip: int = 0, limit: int = 100) -> List[User]:
        return db.query(User).offset(skip).limit(limit).all()

    def create_user(self, db: Session, user: schemas.UserCreate) -> User:
        if self.get_user_by_username(db, user.username):
            raise ValueError(f"User with username '{user.username}' already exists.")

        hashed_password = get_password_hash(user.password)
        db_user = User(
            username=user.username,
            full_name=user.full_name,
            hashed_password=hashed_password,
            role=user.role
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    def update_user(self, db: Session, user_id: int, user_update: schemas.UserUpdate) -> Optional[User]:
        db_user = self.get_user(db, user_id)
        if not db_user:
            return None

        update_data = user_update.model_dump(exclude_unset=True)

        if "password" in update_data and update_data["password"]:
            hashed_password = get_password_hash(update_data["password"])
            db_user.hashed_password = hashed_password

        # Оновлюємо інші поля
        if "full_name" in update_data:
            db_user.full_name = update_data["full_name"]
        if "role" in update_data:
            db_user.role = update_data["role"]
        if "is_active" in update_data:
            db_user.is_active = update_data["is_active"]

        db.commit()
        db.refresh(db_user)
        return db_user

    def delete_user(self, db: Session, user_id: int) -> Optional[User]:
        db_user = self.get_user(db, user_id)
        if not db_user:
            return None

        db.delete(db_user)
        db.commit()
        return db_user