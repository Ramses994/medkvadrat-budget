from pathlib import Path
import shutil

from config import DATA_DIR, BUDGET_DB_PATH, BUDGET_CSV_PATH, TELECOM_DIR, REQUESTS_DEFAULT_CSV
from init_db import init_database


def main() -> None:
    print("--- Первичная инициализация приложения ---")
    DATA_DIR.mkdir(exist_ok=True)
    TELECOM_DIR.mkdir(parents=True, exist_ok=True)

    # Авто-миграция старых файлов из корня в data/
    root = Path(__file__).resolve().parent

    def move_if_exists(src_name: str, dst_path: Path) -> None:
        src = root / src_name
        if src.exists() and not dst_path.exists():
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            print(f"Перемещаю {src.name} → {dst_path}")
            shutil.move(str(src), str(dst_path))

    move_if_exists("budget_2026_clean.csv", BUDGET_CSV_PATH)
    move_if_exists("budget.db", BUDGET_DB_PATH)
    move_if_exists("IT_Zayavki_06.02.2026.csv", REQUESTS_DEFAULT_CSV)
    old_telecom = root / "Payments_telecom_providers_2025&2026"
    if old_telecom.exists() and not any(TELECOM_DIR.iterdir()):
        print(f"Перемещаю {old_telecom} → {TELECOM_DIR}")
        shutil.move(str(old_telecom), str(TELECOM_DIR))

    # Если базы нет, но есть CSV с планом — создаем БД
    if not BUDGET_DB_PATH.exists() and BUDGET_CSV_PATH.exists():
        print("База не найдена, создаю новую из CSV плана...")
        init_database()
    else:
        print("База уже существует, инициализация плана пропущена.")

    print("Инициализация завершена.")


if __name__ == "__main__":
    main()

