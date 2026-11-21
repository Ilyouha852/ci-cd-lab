import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# У owners-service своя БД: другие сервисы получают данные только через REST API.
DATABASE_PATH = Path(
    os.environ.get(
        "DATABASE_PATH",
        str(BASE_DIR / "database" / "owners_service.db")
    )
)

SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production")

# Адрес cars-service (в Compose и Kubernetes: http://cars-service:5000).
CARS_SERVICE_URL = os.environ.get("CARS_SERVICE_URL", "http://localhost:5000").rstrip("/")
CARS_TIMEOUT = float(os.environ.get("CARS_TIMEOUT", "2"))
