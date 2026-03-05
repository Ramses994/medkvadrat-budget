import os

import pandas as pd

from config import BUDGET_CSV_PATH


def create_real_budget_csv(excel_path: str = "Budget_IT_2026.xlsx") -> None:
    """
    Формирует единый budget_2026_clean.csv с вариантами:
    - Общий
    - Куркино
    - Каширка

    Ожидается, что в книге есть листы с этими именами.
    На каждом листе:
      * первый столбец — категория (P&ТО оргтехники, Связь, интернет, IT техподдержка);
      * остальные столбцы — месяцы 2026 года (названия колонок с датами/месяцами).

    На выходе CSV имеет вид:
    Scope, Category, 2026-01-01, 2026-02-01, ..., 2026-12-01
    """
    if not os.path.exists(excel_path):
        print(
            f"⚠ Excel-файл '{excel_path}' не найден. "
            "Оставляю текущий budget_2026_clean.csv без изменений."
        )
        return

    xls = pd.ExcelFile(excel_path)
    scopes_frames = []

    for scope_name in ["Общий", "Куркино", "Каширка"]:
        if scope_name not in xls.sheet_names:
            continue

        df_raw = pd.read_excel(xls, sheet_name=scope_name)
        if df_raw.empty:
            continue

        # удаляем полностью пустые строки/колонки
        df_raw = df_raw.dropna(how="all")
        df_raw = df_raw.dropna(axis=1, how="all")
        if df_raw.shape[1] < 2:
            continue

        category_col = df_raw.columns[0]
        month_cols = list(df_raw.columns[1:])

        df = df_raw[[category_col] + month_cols].copy()
        df.rename(columns={category_col: "Category"}, inplace=True)

        # переименуем заголовки месяцев в формат YYYY-MM-01, когда это возможно
        new_columns = ["Category"]
        for col in month_cols:
            parsed = pd.to_datetime(str(col), dayfirst=True, errors="coerce")
            if pd.isna(parsed):
                new_columns.append(str(col))
            else:
                new_columns.append(parsed.strftime("%Y-%m-01"))
        df.columns = new_columns
        # удаляем возможные дубликаты колонок (если в листе повторяются месяцы)
        df = df.loc[:, ~df.columns.duplicated()]

        df.insert(0, "Scope", scope_name)
        scopes_frames.append(df)

    if not scopes_frames:
        print(
            "⚠ Не удалось найти листы 'Общий', 'Куркино' или 'Каширка' в книге. "
            "budget_2026_clean.csv не изменён."
        )
        return

    df_all = pd.concat(scopes_frames, ignore_index=True)

    # На всякий случай сгруппируем по Scope + Category
    group_cols = ["Scope", "Category"]
    value_cols = [c for c in df_all.columns if c not in group_cols]
    df_final = df_all.groupby(group_cols, as_index=False)[value_cols].sum(numeric_only=True)

    filename = str(BUDGET_CSV_PATH)
    df_final.to_csv(filename, index=False)
    print(f"✅ Файл {filename} перезаписан с вариантами: {df_final['Scope'].unique().tolist()}.")


if __name__ == "__main__":
    create_real_budget_csv()