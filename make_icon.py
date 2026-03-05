import os
from PIL import Image, ImageDraw, ImageFont

# 1. Создаем папку assets, если её нет
os.makedirs(r"C:\medkvadrat-budget\assets", exist_ok=True)

# 2. Создаем изображение 256x256 с прозрачным фоном
size = 256
img = Image.new('RGBA', (size, size), color=(0, 0, 0, 0)) 
draw = ImageDraw.Draw(img)

# Рисуем красивый квадрат со скругленными углами (цвет синий, под IT/Медицину)
margin = 15
draw.rounded_rectangle([margin, margin, size-margin, size-margin], radius=50, fill=(41, 128, 185))

# Добавляем текст (знак рубля)
text = "₽"
try:
    # Используем стандартный шрифт Windows
    font = ImageFont.truetype("arialbd.ttf", 160)
except IOError:
    font = ImageFont.load_default()

# Выравниваем текст по центру
bbox = draw.textbbox((0, 0), text, font=font)
text_x = (size - (bbox[2] - bbox[0])) / 2
text_y = (size - (bbox[3] - bbox[1])) / 2 - 45

draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)

# 3. Сохраняем как НАСТОЯЩИЙ .ico файл (Inno Setup требует именно этот формат)
ico_path = r"C:\medkvadrat-budget\assets\icon.ico"
img.save(ico_path, format="ICO", sizes=[(256, 256), (64, 64), (32, 32)])

print(f"✅ Готово! Папка создана, иконка сохранена по пути: {ico_path}")