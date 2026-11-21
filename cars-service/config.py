import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# У cars-service своя БД: ни owners-service, ни кто-либо ещё в неё не ходит.
DATABASE_PATH = Path(
    os.environ.get(
        "DATABASE_PATH",
        str(BASE_DIR / "database" / "cars_service.db")
    )
)

SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-in-production")

# Адрес соседнего сервиса. В Compose и Kubernetes это имя сервиса в сети:
# http://owners-service:5000. Локально owners-service запускается на порту 5001.
OWNERS_SERVICE_URL = os.environ.get("OWNERS_SERVICE_URL", "http://localhost:5001").rstrip("/")
OWNERS_TIMEOUT = float(os.environ.get("OWNERS_TIMEOUT", "2"))
