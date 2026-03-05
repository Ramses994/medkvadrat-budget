## IT Бюджет Медквадрат

Десктопное приложение для планирования и контроля IT‑бюджета по филиалам (Общий, Куркино, Каширка), анализа счетов, заявок и расходов по связи.


### Установка (через Python)

1. Установите **Python 3.11+** с сайта `python.org` (при установке включите опцию «Add Python to PATH»).

2. Откройте PowerShell в папке проекта (где лежит этот `README.md`) и выполните:

   ```powershell
   python -m venv venv
   venv\Scripts\pip install -r requirements.txt
   ```

3. Один раз выполните первичную инициализацию:

   ```powershell
   venv\Scripts\python init_app.py
   ```

   Скрипт создаст папку `data`, перенесёт в неё файлы бюджета/заявок/выгрузок (если они лежали рядом с программой) и при необходимости создаст базу `data\budget.db`.

4. Запустите приложение:

   ```powershell
   venv\Scripts\python -m streamlit run dashboard.py
   ```

   Откроется браузер со страницей `http://localhost:8501`.


### Структура данных

- `data\budget_2026_clean.csv` — план IT‑бюджета (Общий/Куркино/Каширка)
- `data\budget.db` — база данных (создаётся автоматически)
- `data\IT_Zayavki_*.csv` — файлы IT‑заявок
- `data\Payments_telecom_providers_2025&2026\` — выгрузки по связи


### Сборка exe (PyInstaller)

1. В активном виртуальном окружении выполните:

   ```powershell
   venv\Scripts\pip install pyinstaller
   venv\Scripts\pyinstaller --onefile --icon assets\icon.ico --name ITBudgetMedkvadrat run_app.py
   ```

2. После сборки исполняемый файл будет лежать в:

   ```text
   dist\ITBudgetMedkvadrat.exe
   ```

Этот exe можно запускать напрямую — он сначала выполнит `init_app.py`, затем откроет веб‑приложение в браузере.


### Подмена на свои данные

Все рабочие файлы находятся в папке `data`.  
Чтобы заменить план/заявки/выгрузки на свои:

1. Подготовьте файлы в том же формате, что и демо‑файлы.
2. Замените файлы в `data`.
3. Для обновления плана (при замене `budget_2026_clean.csv`) выполните:

   ```powershell
   venv\Scripts\python init_db.py
   ```

