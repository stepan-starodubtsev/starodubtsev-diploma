from cryptography.fernet import Fernet, InvalidToken
from .config import settings

try:
    cipher_suite = Fernet(settings.ENCRYPTION_KEY)
except ValueError as e:
    raise ValueError(f"Invalid Fernet key format in ENCRYPTION_KEY: {e}. Ensure it's a URL-safe base64-encoded 32-byte key.")


def encrypt_data(data: str) -> str:
    """Шифрує рядок і повертає зашифровані дані у вигляді рядка (base64)."""
    if not data:
        return ""
    encrypted_bytes = cipher_suite.encrypt(data.encode())
    return encrypted_bytes.decode() # Зберігаємо як рядок

def decrypt_data(encrypted_data_str: str) -> str:
    """Дешифрує рядок (base64) і повертає оригінальний рядок."""
    if not encrypted_data_str:
        return ""
    try:
        decrypted_bytes = cipher_suite.decrypt(encrypted_data_str.encode())
        return decrypted_bytes.decode()
    except InvalidToken:
        # Це може статися, якщо ключ змінився або дані пошкоджені/некоректні
        raise ValueError("Invalid token or decryption key.")
    except Exception as e:
        # Обробка інших можливих помилок дешифрування
        raise ValueError(f"Decryption failed: {e}")