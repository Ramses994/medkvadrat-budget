import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random
import re

# Маскируемся под обычный браузер
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15"
]

def clean_query(query):
    """Очищаем запрос от лишних слов (оставляем только суть)."""
    clean = str(query).split('/')[0].strip()
    if len(clean.split()) > 4 and '-' in clean:
        clean = clean.split('-')[0].strip()
    # Убираем лишние спецсимволы, которые ломают поиск
    clean = re.sub(r'[^\w\s-]', '', clean)
    return clean

def extract_price_from_text(text):
    """Чистит строку с ценой (например: '12 500 руб.' -> 12500.0)"""
    clean = text.replace(' ', '').replace('\xa0', '').replace('₽', '').replace('руб.', '').strip()
    try:
        return float(clean)
    except:
        return 0.0

def search_xcom_shop(session, query):
    """Парсинг B2B магазина XCOM-Shop"""
    print("   -> Опрашиваю XCOM-Shop...")
    encoded = urllib.parse.quote(query)
    url = f"https://www.xcom-shop.ru/search/?stext={encoded}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    
    prices = []
    try:
        resp = session.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # В XCOM-Shop цены обычно лежат в блоках, содержащих слово "цена" или класс price
            # Используем регулярку для поиска паттернов цен во всем тексте карточек товаров
            cards = soup.find_all('div', class_=re.compile(r'catalog-item|product|item'))
            if not cards:
                # Резервный поиск по всему HTML
                text_prices = re.findall(r'(\d{1,3}(?:[\s\xa0]?\d{3})*)\s*₽', resp.text)
                prices = [extract_price_from_text(p) for p in text_prices]
            else:
                for card in cards:
                    price_tag = card.find(string=re.compile(r'₽'))
                    if price_tag:
                        val = extract_price_from_text(price_tag)
                        if val > 10: prices.append(val)
    except Exception as e:
        print(f"      [Ошибка XCOM] {e}")
        
    prices = [p for p in prices if p > 50] # Убираем мусор
    if prices:
        print(f"      ✅ XCOM-Shop нашел {len(prices)} вариантов.")
    return prices

def search_kns(session, query):
    """Парсинг IT-дистрибьютора KNS.ru"""
    print("   -> Опрашиваю KNS.ru...")
    encoded = urllib.parse.quote(query)
    url = f"https://www.kns.ru/search/?q={encoded}"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    
    prices = []
    try:
        resp = session.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Ищем классы, отвечающие за цену (обычно price или catalog-price)
            price_tags = soup.find_all(class_=re.compile(r'price'))
            for tag in price_tags:
                val = extract_price_from_text(tag.get_text())
                if val > 50: prices.append(val)
    except Exception as e:
        print(f"      [Ошибка KNS] {e}")

    # Убираем дубликаты
    prices = list(set(prices))
    if prices:
        print(f"      ✅ KNS нашел {len(prices)} вариантов.")
    return prices

def get_average_price(session, query):
    print(f"\n🔍 Ищу: [{query}]")
    all_prices = []
    
    # 1. Поиск по XCOM
    xcom_prices = search_xcom_shop(session, query)
    all_prices.extend(xcom_prices)
    time.sleep(random.uniform(1.5, 3.0)) # Пауза между сайтами
    
    # 2. Поиск по KNS
    kns_prices = search_kns(session, query)
    all_prices.extend(kns_prices)
    
    if all_prices:
        # Убираем экстремумы (если нашли много)
        if len(all_prices) > 4:
            all_prices.sort()
            trim = len(all_prices) // 5
            all_prices = all_prices[trim:-trim]
            
        avg = sum(all_prices) / len(all_prices)
        print(f"   📊 ИТОГОВАЯ СРЕДНЯЯ ЦЕНА: {avg:.0f} ₽")
        return round(avg, 2)
        
    print("   ⚠️ Цены не найдены. Слишком специфичный запрос или нет в наличии.")
    return 0.0

def process_it_requests(input_file, output_file):
    print(f"📂 Читаем файл: {input_file}")
    
    try:
        df = pd.read_csv(input_file, sep=';', encoding='utf-8')
    except UnicodeDecodeError:
        df = pd.read_csv(input_file, sep=';', encoding='cp1251')
        
    if 'Запрос' not in df.columns:
        print("❌ Ошибка: В файле нет колонки 'Запрос'!")
        return

    df['Средняя цена (Парсинг)'] = 0.0

    with requests.Session() as session:
        for index, row in df.iterrows():
            search_query = clean_query(row['Запрос'])
            
            avg_price = get_average_price(session, search_query)
            df.at[index, 'Средняя цена (Парсинг)'] = avg_price
            
            # Обязательная пауза между разными товарами, чтобы не забанили
            sleep_time = random.uniform(3.0, 5.0)
            print(f"   [Пауза {sleep_time:.1f} сек...]")
            time.sleep(sleep_time)

    df['Количество'] = pd.to_numeric(df['Количество'], errors='coerce').fillna(1)
    df['Итоговая сумма (₽)'] = df['Средняя цена (Парсинг)'] * df['Количество']

    df.to_csv(output_file, sep=';', index=False, encoding='utf-8-sig')
    print(f"\n🎉 Готово! Сохранено в: {output_file}")
    
if __name__ == "__main__":
    INPUT_CSV = 'IT_Zayavki_06.02.2026.csv'
    OUTPUT_CSV = 'IT_Zayavki_Цены_IT_B2B.csv'
    
    process_it_requests(INPUT_CSV, OUTPUT_CSV)