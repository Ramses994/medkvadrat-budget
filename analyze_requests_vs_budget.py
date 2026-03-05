import os
from datetime import datetime

import pandas as pd
from sqlalchemy import create_engine

from config import BUDGET_DB_PATH, REQUESTS_DEFAULT_CSV


def load_plan() -> pd.DataFrame:
    engine = create_engine(f"sqlite:///{BUDGET_DB_PATH}")
    df_plan = pd.read_sql("SELECT * FROM budget_plan", engine)
    df_plan["Date"] = pd.to_datetime(df_plan["Date"])
    return df_plan


def load_requests() -> pd.DataFrame:
    df = pd.read_csv(REQUESTS_DEFAULT_CSV, sep=";", encoding="utf-8")
    if df.empty:
        return df

    # Нормализуем названия колонок
    df.columns = [c.strip() for c in df.columns]

    # Дата
    date_col = "Дата"
    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")
    df = df.dropna(subset=[date_col])

    # Сумма (может быть пока пустой в файле)
    amount_col = "Примерная стоимость (прогноз)"
    if amount_col not in df.columns:
        df[amount_col] = 0.0
    df[amount_col] = (
        df[amount_col]
        .astype(str)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df[amount_col] = pd.to_numeric(df[amount_col], errors="coerce").fillna(0.0)

    # Грубое отнесение к категориям бюджета по тексту заявки
    def guess_category(request_text: str) -> str:
        text = str(request_text).lower()
        if any(x in text for x in ["сим", "sim", "телефон", "мобильный"]):
            return "Связь, интернет"
        return "P&ТО оргтехники"

    df["CategoryGuess"] = df["Запрос"].apply(guess_category)

    # Месяц для сопоставления с планом (берем первый день месяца)
    df["MonthStart"] = df[date_col].dt.to_period("M").dt.to_timestamp()

    return df


def compare_with_budget(df_plan: pd.DataFrame, df_req: pd.DataFrame) -> pd.DataFrame:
    if df_req.empty:
        return pd.DataFrame()

    # План по двум ключевым категориям (оргтехника и связь)
    plan_subset = df_plan[df_plan["Category"].isin(["P&ТО оргтехники", "Связь, интернет"])].copy()
    plan_subset = plan_subset.rename(columns={"Date": "MonthStart", "Amount": "PlanAmount"})

    # Сумма заявок по месяцу и категории
    req_grouped = (
        df_req.groupby(["MonthStart", "CategoryGuess"])["Примерная стоимость (прогноз)"]
        .sum()
        .reset_index()
        .rename(columns={"Примерная стоимость (прогноз)": "RequestsAmount"})
    )

    # Объединяем с планом
    merged = req_grouped.merge(
        plan_subset,
        left_on=["MonthStart", "CategoryGuess"],
        right_on=["MonthStart", "Category"],
        how="left",
    )
    merged.drop(columns=["Category"], inplace=True, errors="ignore")

    # Если плана нет (на всякий случай) — считаем 0
    merged["PlanAmount"] = merged["PlanAmount"].fillna(0.0)

    # Отклонение и статус
    merged["Delta"] = merged["PlanAmount"] - merged["RequestsAmount"]
    merged["Status"] = merged["Delta"].apply(
        lambda x: "УКЛАДЫВАЕМСЯ В БЮДЖЕТ" if x >= 0 else "НЕ УКЛАДЫВАЕМСЯ В БЮДЖЕТ"
    )

    return merged.sort_values(["MonthStart", "CategoryGuess"])


def main():
    print("=== Сопоставление нового заказа IT с бюджетом 2026 ===")

    try:
        df_plan = load_plan()
    except Exception as e:
        print(f"Не удалось загрузить план из БД: {e}")
        return

    if not os.path.exists(REQUESTS_DEFAULT_CSV):
        print(f"Файл с заявками не найден: {REQUESTS_DEFAULT_CSV}")
        return

    df_req = load_requests()
    if df_req.empty:
        print("Файл заявок пуст или не содержит корректных строк.")
        return

    compare = compare_with_budget(df_plan, df_req)
    if compare.empty:
        print("Не удалось сопоставить заявки с бюджетом.")
        return

    out_path = os.path.join(os.path.dirname(REQUESTS_DEFAULT_CSV), "IT_Zayavki_vs_budget_2026.csv")
    compare.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("\nИтог по месяцам и категориям:")
    for _, row in compare.iterrows():
        m = row["MonthStart"].strftime("%Y-%m")
        cat = row["CategoryGuess"]
        plan = row["PlanAmount"]
        reqs = row["RequestsAmount"]
        status = row["Status"]
        print(
            f"{m} | {cat}: план {plan:,.0f} руб., заявки {reqs:,.0f} руб. -> {status}".replace(",", " ")
        )

    print(f"\nДетальный файл сохранен: {os.path.basename(out_path)}")
    print(
        "Как пользоваться: заполните в исходном CSV колонку "
        "'Примерная стоимость (прогноз)' по каждой заявке, "
        "запустите этот скрипт и посмотрите сводный результат в файле IT_Zayavki_vs_budget_2026.csv."
    )


if __name__ == "__main__":
    main()

