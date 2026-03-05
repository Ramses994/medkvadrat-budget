import os
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ContentType
from aiogram.filters import Command
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from datetime import datetime
import parser # Наш общий парсер

# Загрузка токена
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

# Настройка бота и БД
bot = Bot(token=TOKEN)
dp = Dispatcher()

from config import DB_URL
engine = create_engine(DB_URL)

def save_to_db(date, category, amount, vendor, comment):
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO expenses (date, category, amount, vendor, comment)
            VALUES (:d, :c, :a, :v, :com)
        """), {'d': date, 'c': category, 'a': amount, 'v': vendor, 'com': comment})
        conn.commit()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Я финансовый бот 🏥.\nПришли мне PDF файл (УПД, Акт), и я занесу его в бюджет.")

# Обработка документов (PDF)
@dp.message(F.document)
async def handle_document(message: Message):
    if message.document.mime_type == 'application/pdf':
        file_id = message.document.file_id
        file_name = message.document.file_name
        
        # Скачиваем файл
        file = await bot.get_file(file_id)
        file_path = f"temp_{file_name}"
        await bot.download_file(file.file_path, file_path)
        
        await message.answer("🔍 Анализирую документ...")
        
        try:
            # Используем ту же логику, что и в Dashboard!
            data = parser.extract_data_from_pdf(file_path)
            
            # Сохраняем в БД
            # Примечание: тут пока сохраняем автоматически, в идеале лучше спросить подтверждение кнопками
            save_to_db(data['date'], data['category'], data['amount'], data['vendor'], f"Telegram: {file_name}")
            
            response = (
                f"✅ **Расход сохранен!**\n"
                f"📅 Дата: {data['date'].strftime('%d.%m.%Y')}\n"
                f"💰 Сумма: {data['amount']} ₽\n"
                f"🏢 Поставщик: {data['vendor']}\n"
                f"📂 Категория: {data['category']}"
            )
            await message.answer(response, parse_mode="Markdown")
            
        except Exception as e:
            await message.answer(f"Ошибка при чтении: {e}")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
    else:
        await message.answer("Я понимаю только PDF файлы.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())