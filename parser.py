import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import re
from datetime import datetime

# Путь к Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# === БАЗА ЗНАНИЙ (ИНН -> Поставщик) ===
VENDOR_INNS = {
    '771442597': ('ООО "ИНИЦИАТИВА"', 'Расходные материалы'), # Ваш ИНН из лога
    '7707436531': ('ООО "ФИКС-КОМ"', 'P&ТО оргтехники'),      # Из актов FixCom
    '7718979307': ('ООО "Ситилинк"', 'Расходные материалы'),    # Из накладной Ситилинк
    '7702070139': ('МТС', 'Связь, интернет'),
    '7713076301': ('Билайн', 'Связь, интернет')
}

OCR_CORRECTIONS = {
    'chespana': 'февраля', 'espana': 'февраля', 'despana': 'февраля',
    'anpeia': 'апреля', 'mas': 'мая', 'niona': 'июня', 'aarycta': 'августа',
    'cenra6pa': 'сентября', 'okra6pa': 'октября', 'nos6pa': 'ноября', 'nekabps': 'декабря',
    'hulmatuba': 'инициатива', 'svnabtara': 'инициатива' # Ваши искажения
}

MONTHS_RU = {
    'января': '01', 'февраля': '02', 'марта': '03', 'апреля': '04',
    'мая': '05', 'июня': '06', 'июля': '07', 'августа': '08',
    'сентября': '09', 'октября': '10', 'ноября': '11', 'декабря': '12'
}

def clean_ocr_text(text):
    text = text.lower()
    for wrong, right in OCR_CORRECTIONS.items():
        text = text.replace(wrong, right)
    return text

def clean_number(num_str):
    if not num_str: return 0.0
    s = num_str.replace(' ', '').replace('\xa0', '').replace("'", "").replace('"', "")
    s = s.replace('o', '0').replace('O', '0').replace('б', '6')
    s = s.replace(',', '.')
    s = re.sub(r'[^\d\.]', '', s)
    if s.count('.') > 1:
        parts = s.split('.')
        s = "".join(parts[:-1]) + '.' + parts[-1]
    try:
        return float(s)
    except:
        return 0.0

def find_date(text):
    text = clean_ocr_text(text)
    # Поиск даты текстом (16 февраля 2026)
    for ru, en in MONTHS_RU.items():
        if ru in text:
            pattern = re.search(rf'(\d{{1,2}})[\s\._-]*{ru}[\s\._-]*(\d{{4}})', text)
            if pattern:
                try:
                    return datetime.strptime(f"{pattern.group(1)}.{en}.{pattern.group(2)}", '%d.%m.%Y')
                except: pass
    # Поиск даты цифрами (16.02.2026)
    pattern = re.search(r'(\d{2})[\.,](\d{2})[\.,](\d{4})', text)
    if pattern:
        try:
            return datetime.strptime(f"{pattern.group(1)}.{pattern.group(2)}.{pattern.group(3)}", '%d.%m.%Y')
        except: pass
    return datetime.now()

def find_amount(text):
    # Поиск суммы по ключевым словам
    lines = text.split('\n')
    triggers = ['всего', 'итого', 'onnare', 'onnate', 'cero', 'cyuua']
    candidates = []
    
    for line in lines:
        if any(t in line.lower() for t in triggers):
            nums = re.findall(r'(\d{1,3}(?:[\s\.]\d{3})*[.,]\d{2})', line)
            for n in nums:
                val = clean_number(n)
                if val > 100: candidates.append(val)
                
    if candidates: return max(candidates)
    
    # Резервный поиск в конце файла
    nums = re.findall(r'(\d{1,3}(?:[\s]\d{3})*[.,]\d{2})', text[-1500:])
    vals = [clean_number(n) for n in nums]
    return max(vals) if vals else 0.0

def find_vendor(text):
    text_low = text.lower()
    
    # 1. СТРАТЕГИЯ: ПОИСК ПО ИНН (Самая надежная)
    # Ищем последовательности из 10 или 12 цифр
    inn_matches = re.findall(r'\d{10}|\d{12}', text)
    for inn in inn_matches:
        # Ищем частичное совпадение (OCR может склеить ИНН с текстом, напр 7714425971102)
        for known_inn, (name, cat) in VENDOR_INNS.items():
            if known_inn in inn:
                return name, cat

    # 2. СТРАТЕГИЯ: ПОИСК ПО СЛОВАМ (С учетом искажений)
    if any(x in text_low for x in ['инициатива', 'hulmatuba', 'svnabtara', 'hnuuatuba']):
        return 'ООО "ИНИЦИАТИВА"', 'Расходные материалы'
    elif any(x in text_low for x in ['фикс-ком', 'fixcom', 'fix-com', 'pukc-kom']):
        return 'ООО "ФИКС-КОМ"', 'P&ТО оргтехники'
    elif 'ситилинк' in text_low:
        return 'ООО "Ситилинк"', 'Расходные материалы'
    elif 'мтс' in text_low:
        return 'МТС', 'Связь, интернет'
        
    return "Не определен", "Нераспределенное"

def extract_data_from_pdf(file_path):
    print(f"--- АНАЛИЗ: {file_path} ---")
    full_text = ""
    
    try:
        doc = fitz.open(file_path)
        for page in doc:
            t = page.get_text()
            if len(t) > 50:
                full_text += t + "\n"
            else:
                # OCR для сканов
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                full_text += pytesseract.image_to_string(image, lang='rus+eng') + "\n"
    except Exception as e:
        return {'error': str(e)}

    # Извлечение данных
    doc_date = find_date(full_text[:1500])
    amount = find_amount(full_text)
    vendor, category = find_vendor(full_text)
    
    return {
        'date': doc_date,
        'amount': amount,
        'vendor': vendor,
        'category': category,
        'text_snippet': full_text[:1000]
    }