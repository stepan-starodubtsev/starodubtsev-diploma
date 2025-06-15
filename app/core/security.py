# app/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from .config import settings

# --- Існуючий код для шифрування ---
try:
    cipher_suite = Fernet(settings.ENCRYPTION_KEY)
except ValueError as e:
    raise ValueError(f"Invalid Fernet key format in ENCRYPTION_KEY: {e}. Ensure it's a URL-safe base64-encoded 32-byte key.")

def encrypt_data(data: str) -> str:
    # ... (код без змін)
    if not data:
        return ""
    encrypted_bytes = cipher_suite.encrypt(data.encode())
    return encrypted_bytes.decode()

def decrypt_data(encrypted_data_str: str) -> str:
    # ... (код без змін)
    if not encrypted_data_str:
        return ""
    try:
        decrypted_bytes = cipher_suite.decrypt(encrypted_data_str.encode())
        return decrypted_bytes.decode()
    except InvalidToken:
        raise ValueError("Invalid token or decryption key.")
    except Exception as e:
        raise ValueError(f"Decryption failed: {e}")

# --- НОВИЙ КОД для паролів та JWT ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

JWT_SECRET_KEY = settings.JWT_SECRET_KEY # Додайте в .env!
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 години

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Перевіряє, чи збігається пароль з хешем."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Створює хеш пароля."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Створює JWT-токен."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# --- Схема для даних в токені ---
class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None