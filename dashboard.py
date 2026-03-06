import streamlit as st
import pandas as pd
import altair as alt
from sqlalchemy import create_engine, text
from datetime import datetime
import parser
import os
import sys
import importlib

try:
    from config import DB_URL
except ModuleNotFoundError:
    # При запуске из собранного exe (PyInstaller) config может не попасть в бандл
    _base = os.path.dirname(os.path.abspath(sys.executable))
    _db = os.path.join(_base, "data", "budget.db")
    DB_URL = f"sqlite:///{_db}"

import analyze_telecom_payments as telecom_analyzer
import analyze_requests_vs_budget as requests_analyzer

# ПРИНУДИТЕЛЬНАЯ ПЕРЕЗАГРУЗКА ПАРСЕРА (чтобы видеть изменения в parser.py без перезапуска сервера)
importlib.reload(parser)

st.set_page_config(page_title="IT Бюджет 2026", layout="wide")

# --- 1. ПОДКЛЮЧЕНИЕ К БАЗЕ (ЭТА СТРОКА ДОЛЖНА БЫТЬ ТУТ) ---
engine = create_engine(DB_URL)

# --- 2. ФУНКЦИИ ---
def load_plan():
    # Читаем план из БД
    df = pd.read_sql("SELECT * FROM budget_plan", engine)
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def load_fact():
    # Читаем расходы из БД
    try:
        df = pd.read_sql("SELECT * FROM expenses", engine)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        return df
    except Exception:
        # Если таблицы еще нет
        return pd.DataFrame(columns=["id", "date", "category", "amount", "vendor", "comment"])


def load_telecom_history():
    """
    Справочный график по связи за предыдущие периоды (из выгрузок 2025–2026).
    """
    try:
        df_all = telecom_analyzer.load_payments()
        if df_all.empty:
            return pd.DataFrame()
        return telecom_analyzer.summarize_last_12_months(df_all)
    except Exception:
        return pd.DataFrame()


def load_telecom_recommendations():
    """
    Рекомендации по плану связи 2026 vs фактические траты 2025.
    """
    try:
        df_all = telecom_analyzer.load_payments()
        if df_all.empty:
            return pd.DataFrame()
        last12 = telecom_analyzer.summarize_last_12_months(df_all)
        plan_telecom = telecom_analyzer.load_plan_telecom()
        return telecom_analyzer.build_recommendations(last12, plan_telecom)
    except Exception:
        return pd.DataFrame()


def load_requests_vs_budget():
    """
    Сопоставление новых IT-заявок с бюджетом (по месяцу и категории).
    """
    try:
        df_plan = requests_analyzer.load_plan()
        df_req = requests_analyzer.load_requests()
        return requests_analyzer.compare_with_budget(df_plan, df_req)
    except Exception:
        return pd.DataFrame()


def prepare_requests_from_df(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Подготовка датафрейма заявок из загруженного CSV (как IT_Zayavki_дд.мм.гггг.csv).
    Повторяет правила из analyze_requests_vs_budget.load_requests.
    """
    if df_raw.empty:
        return df_raw

    df = df_raw.copy()
    df.columns = [c.strip() for c in df.columns]

    # Дата
    date_col = "Дата"
    if date_col not in df.columns:
        return pd.DataFrame()
    df[date_col] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")
    df = df.dropna(subset=[date_col])

    # Примерная стоимость
    amount_col = "Примерная стоимость (прогноз)"

    # Основной источник суммы — "Примерная стоимость (прогноз)"
    if amount_col in df.columns:
        base_amount_series = (
            df[amount_col]
            .astype(str)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        base_amount = pd.to_numeric(base_amount_series, errors="coerce")
    else:
        base_amount = pd.Series([0.0] * len(df))

    # Если в файле вместо нее заполнена "Итоговая сумма (₽)" — используем её
    total_col = "Итоговая сумма (₽)"
    if total_col in df.columns:
        total_series = (
            df[total_col]
            .astype(str)
            .str.replace(" ", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        total_amount = pd.to_numeric(total_series, errors="coerce")
        # там, где базовая оценка пустая/ноль, подставляем итоговую сумму
        base_amount = base_amount.fillna(0.0)
        mask = base_amount <= 0
        base_amount[mask] = total_amount[mask]

    df[amount_col] = base_amount.fillna(0.0)

    # Категория по тексту заявки
    def guess_category(text: str) -> str:
        t = str(text).lower()
        if any(x in t for x in ["сим", "sim", "телефон", "мобильный"]):
            return "Связь, интернет"
        return "P&ТО оргтехники"

    df["CategoryGuess"] = df["Запрос"].apply(guess_category)
    df["MonthStart"] = df[date_col].dt.to_period("M").dt.to_timestamp()
    return df

def save_expense(date, category, amount, vendor, comment):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO expenses (date, category, amount, vendor, comment)
            VALUES (:d, :c, :a, :v, :com)
        """), {'d': date, 'c': category, 'a': amount, 'v': vendor, 'com': comment})
        conn.commit()

def delete_expense(expense_id):
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM expenses WHERE id = :id"), {'id': expense_id})
        conn.commit()

# --- 3. ЗАГРУЗКА ДАННЫХ ---
df_plan_all = load_plan()
df_fact = load_fact()
df_telecom_hist = load_telecom_history()
df_telecom_rec = load_telecom_recommendations()
df_requests_vs_budget = load_requests_vs_budget()

# --- 4. ИНТЕРФЕЙС ---
st.sidebar.title("Меню")

# Выбор сценария бюджета: Общий / Куркино / Каширка
if "Scope" in df_plan_all.columns:
    scopes_available = list(df_plan_all["Scope"].dropna().unique())
    # упорядочим: Общий, Куркино, Каширка, остальные по алфавиту
    priority = ["Общий", "Куркино", "Каширка"]
    scopes_sorted = [s for s in priority if s in scopes_available] + [
        s for s in scopes_available if s not in priority
    ]
    # если данных пока нет (пустая таблица), всё равно показываем стандартный набор
    if not scopes_sorted:
        scopes_sorted = priority

    current_scope = st.sidebar.selectbox("Локация бюджета", scopes_sorted)
    df_plan = df_plan_all[df_plan_all["Scope"] == current_scope].copy()
else:
    current_scope = "Общий"
    df_plan = df_plan_all.copy()

mode = st.sidebar.radio(
    "Выберите режим:",
    [
        "📊 Аналитика (Дашборд)",
        "📡 Связь: план vs факт (выгрузки)",
        "🧾 IT-заявки vs бюджет",
        "📥 Загрузка сканов (PDF)",
    ],
)

# === РЕЖИМ 1: АНАЛИТИКА ===
if mode == "📊 Аналитика (Дашборд)":
    st.title("IT Бюджет Медквадрат: План/Факт 📊")

    # KPI
    total_plan = df_plan['Amount'].sum()
    total_fact = df_fact['amount'].sum() if not df_fact.empty else 0
    utilization = (total_fact / total_plan * 100) if total_plan > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("План", f"{total_plan:,.0f} ₽".replace(",", " "))
    c2.metric("Факт", f"{total_fact:,.0f} ₽".replace(",", " "), delta=f"{utilization:.1f}%")
    c3.metric("Остаток", f"{(total_plan - total_fact):,.0f} ₽".replace(",", " "))

    st.divider()

    col_main, col_details = st.columns([2, 1])
    
    with col_main:
        st.subheader("Динамика")
        if not df_plan.empty:
            plan_by_month = df_plan.groupby('Date')['Amount'].sum().reset_index()
            plan_by_month['Type'] = 'План'
            chart_data = plan_by_month
            
            if not df_fact.empty:
                df_fact['Month'] = df_fact['date'].dt.to_period('M').dt.to_timestamp()
                fact_by_month = df_fact.groupby('Month')['amount'].sum().reset_index()
                fact_by_month.rename(columns={'Month': 'Date', 'amount': 'Amount'}, inplace=True)
                fact_by_month['Type'] = 'Факт'
                chart_data = pd.concat([chart_data, fact_by_month])
                chart_data['Date'] = pd.to_datetime(chart_data['Date'])
                chart_data = chart_data.sort_values("Date")

            # Кастомный Altair-график: колонки + точки + подписи
            base = alt.Chart(chart_data).encode(
                x=alt.X('yearmonth(Date):T', title='Месяц'),
                y=alt.Y('Amount:Q', title='Сумма, ₽'),
                color=alt.Color('Type:N', title=''),
                tooltip=[
                    alt.Tooltip('yearmonth(Date):T', title='Месяц'),
                    alt.Tooltip('Type:N', title='Тип'),
                    alt.Tooltip('Amount:Q', title='Сумма, ₽', format=',.0f'),
                ],
            )

            bars = base.mark_bar(size=35)
            points = base.mark_circle(size=70)
            labels = base.mark_text(
                dy=-10,
                color='black'
            ).encode(
                text=alt.Text('Amount:Q', format=',.0f')
            )

            chart = (bars + points + labels).properties(
                height=380,
            )

            st.altair_chart(chart)

        # Справочный график: траты на связь за предыдущие периоды (меньший масштаб)
        if not df_telecom_hist.empty:
            st.markdown("##### Связь: траты за последние 12 месяцев (справочно)")
            telecom_chart = df_telecom_hist.copy()
            telecom_chart['month_str'] = telecom_chart['month'].dt.to_period('M').astype(str)
            st.bar_chart(telecom_chart, x='month_str', y='amount')

    with col_details:
        st.subheader("Последние расходы")
        if not df_fact.empty:
            st.dataframe(
                df_fact[['date', 'amount', 'vendor']].sort_values(by='date', ascending=False).head(10),
                hide_index=True,
                width='content'
            )
        
        with st.expander("🗑 Удалить запись"):
            if not df_fact.empty:
                options = {row['id']: f"{row['amount']}₽ | {row['vendor']}" for _, row in df_fact.sort_values(by='id', ascending=False).iterrows()}
                del_id = st.selectbox("Выбрать:", options.keys(), format_func=lambda x: options[x])
                if st.button("Удалить"):
                    delete_expense(del_id)
                    st.rerun()

# === РЕЖИМ 2: СПРАВОЧНЫЙ АНАЛИЗ СВЯЗИ (ВЫГРУЗКИ) ===
elif mode == "📡 Связь: план vs факт (выгрузки)":
    st.title("Связь: фактические траты и план 2026")

    st.subheader("Фактические расходы на связь за последние 12 месяцев (справочно)")
    if not df_telecom_hist.empty:
        chart_hist = df_telecom_hist.copy()
        chart_hist["month_str"] = chart_hist["month"].dt.to_period("M").astype(str)
        st.bar_chart(chart_hist, x="month_str", y="amount")
        avg_val = df_telecom_hist["amount"].mean()
        st.caption(
            f"Средний ежемесячный расход за последние 12 месяцев: {avg_val:,.0f} руб.".replace(",", " ")
        )
    else:
        st.info("Нет данных по выгрузкам связи за предыдущие периоды.")

    st.divider()

    st.subheader("План 2026 по связи vs средний факт 2025")
    if not df_telecom_rec.empty:
        show_cols = ["Date", "Amount", "avg_fact_2025", "delta_vs_avg", "delta_pct", "note"]
        st.dataframe(
            df_telecom_rec[show_cols],
            hide_index=True,
            width='stretch',
        )
    else:
        st.info(
            "Не удалось построить рекомендации по плану 2026. "
            "Проверьте, что есть выгрузки связи и заполнен план по категории 'Связь, интернет'."
        )


# === РЕЖИМ 3: IT-ЗАЯВКИ VS БЮДЖЕТ ===
elif mode == "🧾 IT-заявки vs бюджет":
    st.title("IT-заявки vs бюджет 2026 по месяцам")

    uploaded_reqs = st.file_uploader(
        "Загрузить файл заявок (IT_Zayavki_дд.мм.гггг.csv)", type=["csv"]
    )

    df_compare = pd.DataFrame()

    if uploaded_reqs is not None:
        try:
            df_raw = pd.read_csv(uploaded_reqs, sep=";", encoding="utf-8")
            df_prepared = prepare_requests_from_df(df_raw)
            if not df_prepared.empty:
                df_compare = requests_analyzer.compare_with_budget(df_plan, df_prepared)
        except Exception as e:
            st.error(f"Ошибка при чтении загруженного файла: {e}")

    # Если файл не загружен или не удалось обработать — fallback к стандартному файлу
    if df_compare.empty and not df_requests_vs_budget.empty:
        df_compare = df_requests_vs_budget.copy()

    if df_compare.empty:
        st.info(
            "Нет данных для анализа. Загрузите файл заявок IT_Zayavki_дд.мм.гггг.csv "
            "и заполните колонку 'Примерная стоимость (прогноз)'."
        )
    else:
        view = df_compare.copy()
        view["Month"] = view["MonthStart"].dt.to_period("M").astype(str)
        view = view.rename(
            columns={
                "CategoryGuess": "Категория",
                "PlanAmount": "План 2026, руб.",
                "RequestsAmount": "Заявки, руб.",
                "Delta": "Остаток (план - заявки)",
                "Status": "Статус",
            }
        )

        st.subheader("Сводка по месяцам и категориям")
        st.dataframe(
            view[
                [
                    "Month",
                    "Категория",
                    "План 2026, руб.",
                    "Заявки, руб.",
                    "Остаток (план - заявки)",
                    "Статус",
                ]
            ],
            hide_index=True,
            width='stretch',
        )

        st.markdown(
            "**Интерпретация:** 'УКЛАДЫВАЕМСЯ В БЮДЖЕТ' — сумма заявок не превышает план по месяцу и категории; "
            "'НЕ УКЛАДЫВАЕМСЯ В БЮДЖЕТ' — заявки выше плана, требуется решение (перенос, доп. бюджет, оптимизация)."
        )


# === РЕЖИМ 4: ЗАГРУЗКА ДОКУМЕНТОВ ===
elif mode == "📥 Загрузка сканов (PDF)":
    st.title("📥 Распознавание документов")
    st.markdown("Загрузите **УПД, Счет или Акт (PDF)**. Система найдет дату, поставщика и сумму.")

    uploaded_file = st.file_uploader("Перетащите файл сюда", type=['pdf'])

    if uploaded_file is not None:
        temp_filename = f"temp_{uploaded_file.name}"
        with open(temp_filename, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.info("Анализирую файл...")

        try:
            # Вызываем парсер
            data = parser.extract_data_from_pdf(temp_filename)
            
            st.success("Данные найдены!")

            with st.form("confirm_scan"):
                c1, c2 = st.columns(2)
                scan_date = c1.date_input("Дата", data['date'])
                scan_vendor = c2.text_input("Поставщик", data['vendor'])
                scan_amount = c1.number_input("Сумма (₽)", value=float(data['amount']), step=100.0)
                
                # Категория
                all_cats = list(df_plan['Category'].unique())
                cat_index = 0
                if data['category'] in all_cats:
                    cat_index = all_cats.index(data['category'])
                
                scan_cat = c2.selectbox("Категория", all_cats, index=cat_index)
                scan_comment = st.text_input("Комментарий", f"Скан: {uploaded_file.name}")

                if st.form_submit_button("💾 Сохранить в бюджет"):
                    save_expense(scan_date, scan_cat, scan_amount, scan_vendor, scan_comment)
                    st.toast("Документ добавлен!")
                    os.remove(temp_filename)

            with st.expander("Сырой текст (Debug)"):
                st.text(data.get('text_snippet', ''))

        except Exception as e:
            st.error(f"Ошибка: {e}")