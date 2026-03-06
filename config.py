import os
import sys
from pathlib import Path
from typing import Final

import yaml


# При запуске из exe (PyInstaller) используем папку установки, а не временную _MEI
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

DATA_DIR: Final[Path] = BASE_DIR / "data"
ASSETS_DIR: Final[Path] = BASE_DIR / "assets"

DATA_DIR.mkdir(exist_ok=True)

CONFIG_PATH: Final[Path] = BASE_DIR / "config.yaml"


def _load_config() -> dict:
    if CONFIG_PATH.exists():
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


_cfg = _load_config()


def _cfg_path(key: str, default: str) -> Path:
    rel = _cfg.get(key, default)
    return (BASE_DIR / rel).resolve()


BUDGET_DB_PATH: Final[Path] = _cfg_path("db_path", "data/budget.db")
BUDGET_CSV_PATH: Final[Path] = _cfg_path("budget_csv", "data/budget_2026_clean.csv")
REQUESTS_DEFAULT_CSV: Final[Path] = _cfg_path("requests_default_csv", "data/IT_Zayavki_06.02.2026.csv")
TELECOM_DIR: Final[Path] = _cfg_path("telecom_dir", "data/Payments_telecom_providers_2025&2026")

DB_URL: Final[str] = f"sqlite:///{BUDGET_DB_PATH}"

