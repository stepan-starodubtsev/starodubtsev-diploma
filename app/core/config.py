import os

from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    print(f"Warning: .env file not found at {dotenv_path}. Ensure environment variables are set.")


class Settings:
    ENCRYPTION_KEY_STR: str = os.getenv("ENCRYPTION_KEY")
    if not ENCRYPTION_KEY_STR:
        raise ValueError("ENCRYPTION_KEY environment variable not set!")
    try:
        ENCRYPTION_KEY: bytes = ENCRYPTION_KEY_STR.encode()
    except Exception as e:
        raise ValueError(f"Could not encode ENCRYPTION_KEY to bytes: {e}")

    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/default_db")

    ELASTICSEARCH_HOST: str = os.getenv("ELASTICSEARCH_HOST", "localhost")  # Для запуску Python поза Docker
    ELASTICSEARCH_PORT_API: int = int(os.getenv("ELASTICSEARCH_PORT_API", "9200"))  # Для запуску Python поза Docker

settings = Settings()

print(f"Loaded Encryption Key (first 5 bytes): {settings.ENCRYPTION_KEY[:5]}...")
