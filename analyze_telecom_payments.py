import os
import sys
from datetime import datetime, timedelta

import pandas as pd
from sqlalchemy import create_engine

try:
    from config import TELECOM_DIR, BUDGET_DB_PATH
except ModuleNotFoundError:
    _base = os.path.dirname(os.path.abspath(sys.executable))
    TELECOM_DIR = os.path.join(_base, "data", "Payments_telecom_providers_2025&2026")
    BUDGET_DB_PATH = os.path.join(_base, "data", "budget.db")


def detect_date_column(df: pd.DataFrame) -> str:
    """
    Try to detect a date column:
    - Prefer column whose name contains 'дат'
    - Fallback: first column where most non-null values look like dates
    """
    lowered = {c: str(c).lower() for c in df.columns}
    for col, low in lowered.items():
        if "дат" in low:
            return col

    for col in df.columns:
        series = df[col].dropna().astype(str)
        if series.empty:
            continue
        sample = series.head(20)
        ok = 0
        for v in sample:
            try:
                # Russian-like dd.mm.yyyy or ISO
                if any(sep in v for sep in [".", "-", "/"]):
                    pd.to_datetime(v, dayfirst=True, errors="raise")
                    ok += 1
            except Exception:
                continue
        if ok >= max(3, len(sample) // 3):
            return col

    # Fallback to the second column if exists, else first
    return df.columns[1] if len(df.columns) > 1 else df.columns[0]


def detect_amount_column(df: pd.DataFrame) -> str:
    """
    Try to detect amount column:
    - Prefer columns whose name contains 'сумм', 'итог', 'к оплате'
    - Fallback: numeric column with the largest positive total
    """
    lowered = {c: str(c).lower() for c in df.columns}
    for col, low in lowered.items():
        if any(key in low for key in ("сумм", "итог", "оплат")):
            return col

    numeric = df.select_dtypes(include=["number", "float", "int"])
    if not numeric.empty:
        totals = numeric.clip(lower=0).sum()
        if not totals.empty:
            return totals.idxmax()

    # As a very last resort, try to coerce any column to numeric and pick best
    best_col = None
    best_total = 0
    for col in df.columns:
        s = pd.to_numeric(df[col], errors="coerce")
        total = s.clip(lower=0).sum()
        if total > best_total:
            best_total = total
            best_col = col
    if best_col is None:
        raise RuntimeError("Не удалось определить колонку суммы в выгрузке")
    return best_col


def load_payments() -> pd.DataFrame:
    rows = []

    for name in os.listdir(TELECOM_DIR):
        if not name.lower().endswith(".xlsx"):
            continue

        path = os.path.join(TELECOM_DIR, name)
        provider = os.path.splitext(name)[0]

        df = pd.read_excel(path)
        if df.empty:
            continue

        date_col = detect_date_column(df)
        amount_col = detect_amount_column(df)

        tmp = df[[date_col, amount_col]].copy()
        tmp.columns = ["date_raw", "amount_raw"]
        tmp["provider"] = provider

        tmp["date"] = pd.to_datetime(tmp["date_raw"], dayfirst=True, errors="coerce")
        tmp["amount"] = pd.to_numeric(tmp["amount_raw"], errors="coerce")

        tmp = tmp.dropna(subset=["date", "amount"])
        tmp = tmp[tmp["amount"] > 0]

        rows.append(tmp[["date", "amount", "provider"]])

    if not rows:
        return pd.DataFrame(columns=["date", "amount", "provider"])

    df_all = pd.concat(rows, ignore_index=True)
    return df_all


def summarize_last_12_months(df_all: pd.DataFrame) -> pd.DataFrame:
    if df_all.empty:
        return df_all

    today = datetime.today()
    start = (today - timedelta(days=365)).replace(hour=0, minute=0, second=0, microsecond=0)

    # Основной сценарий — последние 12 месяцев
    mask = (df_all["date"] >= start) & (df_all["date"] <= today)
    df = df_all.loc[mask].copy()

    # Запасной сценарий: если во временной рамке ничего нет (например, есть только 2025 год),
    # используем все доступные данные целиком, чтобы не показывать "пусто".
    if df.empty:
        df = df_all.copy()

    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    summary = (
        df.groupby("month")["amount"]
        .sum()
        .reset_index()
        .sort_values("month")
    )
    summary["avg_last_12m"] = summary["amount"].mean()
    return summary


def load_plan_telecom() -> pd.DataFrame:
    engine = create_engine(f"sqlite:///{BUDGET_DB_PATH}")
    df_plan = pd.read_sql("SELECT * FROM budget_plan", engine)
    df_plan["Date"] = pd.to_datetime(df_plan["Date"])
    telecom = df_plan[df_plan["Category"] == "Связь, интернет"].copy()
    telecom = telecom.sort_values("Date")
    return telecom[["Date", "Amount"]]


def build_recommendations(last12: pd.DataFrame, plan_telecom: pd.DataFrame) -> pd.DataFrame:
    if last12.empty or plan_telecom.empty:
        return pd.DataFrame()

    avg_fact = last12["amount"].mean()
    rec = plan_telecom.copy()
    rec["avg_fact_2025"] = avg_fact
    rec["delta_vs_avg"] = rec["Amount"] - avg_fact
    rec["delta_pct"] = (rec["delta_vs_avg"] / avg_fact * 100).round(1)

    def make_note(row):
        if abs(row["delta_pct"]) < 5:
            return "План близок к среднему факту 2025 (+/-5%) — можно оставить без изменений."
        if row["delta_pct"] < -5:
            return "План ниже среднего факта 2025 — риск недофинансирования, имеет смысл заложить резерв."
        return "План выше среднего факта 2025 — возможен резерв для экономии, при необходимости можно снизить план."

    rec["note"] = rec.apply(make_note, axis=1)
    return rec


def main():
    print("=== Анализ расходов на связь (выгрузки 2025–2026) ===")
    df_all = load_payments()
    if df_all.empty:
        print("Не удалось загрузить данные из Excel-файлов. Проверьте папку с выгрузками.")
        return

    last12 = summarize_last_12_months(df_all)
    if last12.empty:
        print("За последние 12 месяцев нет данных по оплатам.")
        return

    print("\nСводка по расходам за последние 12 месяцев (все операторы):")
    for _, row in last12.iterrows():
        month_str = row["month"].strftime("%Y-%m")
        print(f"{month_str}: {row['amount']:,.0f} руб.".replace(",", " "))

    avg_last12 = last12["amount"].mean()
    print(f"\nСредний ежемесячный расход за последние 12 месяцев: {avg_last12:,.0f} руб.".replace(",", " "))

    # Сохраняем сводку в CSV
    last12.to_csv(os.path.join(BASE_DIR, "telecom_last12m_summary.csv"), index=False, encoding="utf-8-sig")

    # Сопоставление с планом 2026 по категории "Связь, интернет"
    try:
        plan_telecom = load_plan_telecom()
    except Exception as e:
        print(f"\nНе удалось загрузить план из БД: {e}")
        return

    rec = build_recommendations(last12, plan_telecom)
    if rec.empty:
        print("\nНе удалось построить рекомендации по плану (нет данных плана или факта).")
        return

    out_path = os.path.join(BASE_DIR, "telecom_plan_2026_recommendations.csv")
    rec.to_csv(out_path, index=False, encoding="utf-8-sig")

    print("\nРекомендации по плану 2026 для категории 'Связь, интернет' сохранены в файле:")
    print(f"  {os.path.basename(out_path)}")
    print("\nПримеры интерпретации:")
    print("- Если план значительно ниже среднего факта 2025 — стоит обсудить увеличение бюджета или меры экономии.")
    print("- Если план заметно выше — можно использовать часть разницы как резерв или оптимизировать расходы.")


if __name__ == "__main__":
    main()

