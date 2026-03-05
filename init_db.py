import pandas as pd
from sqlalchemy import create_engine, text

from config import DB_URL, BUDGET_CSV_PATH

# Подключаемся
engine = create_engine(DB_URL)

def init_database():
    print("--- Инициализация БД ---")
    
    # 1. Загружаем ПЛАН (теперь с поддержкой Scope и служебных колонок типа "ИТОГО")
    df = pd.read_csv(BUDGET_CSV_PATH)

    id_vars = ['Category']
    if 'Scope' in df.columns:
        id_vars.insert(0, 'Scope')

    # оставляем в значениях только те колонки, которые выглядят как даты (YYYY-MM-DD)
    value_cols = [c for c in df.columns if c not in id_vars]
    date_cols = []
    for col in value_cols:
        try:
            parsed = pd.to_datetime(col, format="%Y-%m-%d", errors="raise")
            date_cols.append(col)
        except Exception:
            # пропускаем служебные колонки типа "ИТОГО"
            continue

    if not date_cols:
        print("⚠ В budget_2026_clean.csv не найдено колонок с датами плана. План не загружен.")
        df_melted = pd.DataFrame(columns=id_vars + ['Date', 'Amount'])
    else:
        df_melted = df.melt(id_vars=id_vars, value_vars=date_cols, var_name='Date', value_name='Amount')
        df_melted['Date'] = pd.to_datetime(df_melted['Date'])
    df_melted['Amount'] = pd.to_numeric(df_melted['Amount'])
    df_melted.to_sql('budget_plan', con=engine, index=False, if_exists='replace')
    print(f"✅ План загружен: {len(df_melted)} строк.")

    # 2. Создаем таблицу для ФАКТА (расходов), если её нет
    # Мы используем сырой SQL для создания структуры, чтобы она была четкой
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TIMESTAMP,
                category TEXT,
                amount REAL,
                vendor TEXT,
                comment TEXT,
                receipt_url TEXT
            )
        """))
        print("✅ Таблица расходов (expenses) проверена/создана.")

if __name__ == "__main__":
    init_database()