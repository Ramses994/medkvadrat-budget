from pathlib import Path
import subprocess
import sys

from init_app import main as init_main


BASE_DIR = Path(__file__).resolve().parent
APP_PATH = BASE_DIR / "dashboard.py"


def main() -> None:
    # Первичная инициализация данных/БД
    init_main()
    # Запуск Streamlit-приложения
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(APP_PATH)])


if __name__ == "__main__":
    main()

