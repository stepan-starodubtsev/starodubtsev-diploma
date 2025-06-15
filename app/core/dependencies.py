# app/core/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from jose import jwt
from sqlalchemy.orm import Session

from app.core.config import settings  # Для ES налаштувань
from app.core.security import ALGORITHM, JWT_SECRET_KEY, TokenData
from app.database.postgres_models.user_models import User, UserRoleEnum
from app.modules.data_ingestion.writers.elasticsearch_writer import ElasticsearchWriter
from app.modules.users.services import UserService
from .database import get_db


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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    user_service = UserService()
    user = user_service.get_user_by_username(db, username=token_data.username)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="The user doesn't have enough privileges")
    return current_user