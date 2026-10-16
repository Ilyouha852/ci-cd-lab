import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATABASE_PATH = Path(
    os.environ.get(
        "DATABASE_PATH",
        str(BASE_DIR / "database" / "cars.db")
    )
)

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "change-this-in-production"
)
