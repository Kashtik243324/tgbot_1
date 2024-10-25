import easyocr 
from docx import Document
import os
import logging
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import asyncio

# Настройка логгирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализируем EasyOCR
reader = easyocr.Reader(['ru', 'en'])

# Храним идентификаторы сообщений, отправленных ботом
bot_message_ids = []

# Функция для корректировки текста
def clean_text(text):
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        if cleaned_lines and not cleaned_lines[-1].endswith(('.', ',', '!', '?', ':', ';')):
            cleaned_lines[-1] += ' ' + line.strip()
        else:
            cleaned_lines.append(line.strip())
    return '\n'.join(cleaned_lines)

# Функция для обработки изображений
def extract_text_from_image(image_path):
    try:
        result = reader.readtext(image_path, detail=0)
        text = '\n'.join(result)
        return clean_text(text)
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения {image_path}: {e}")
        return ""

# Функция для создания Word-документа
def create_word_doc(text_list, output_path):
    doc = Document()
    for text in text_list:
        if text.strip():
            doc.add_paragraph(text)
    doc.save(output_path)

# Функция для удаления всех сообщений бота в чате
async def delete_all_bot_messages(update: Update, context) -> None:
    chat_id = update.effective_chat.id  # Получаем идентификатор чата
    for message_id in bot_message_ids:
        try:
            await context.bot.delete_message(chat_id, message_id)  # Удаляем сообщение
        except Exception as e:
            logger.error(f"Ошибка при удалении сообщения {message_id}: {e}")

# Обработчик команды /start
async def start(update: Update, context) -> None:
    keyboard = [[
        "Перезапустить бота",
        "Информация о боте"
    ]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    message = await update.message.reply_text('Привет! Отправь мне изображение, и я извлеку текст и создам документ Word.', reply_markup=reply_markup)

    # Сохраняем идентификатор отправленного сообщения
    bot_message_ids.append(message.message_id)

# Обработчик команды перезапуска
async def handle_restart(update: Update, context) -> None:
    await delete_all_bot_messages(update, context)  # Удаляем все сообщения
    bot_message_ids.clear()  # Очищаем список идентификаторов сообщений
    await start(update, context)  # Снова вызываем стартовую функцию

# Обработчик информации о боте
async def handle_info(update: Update, context) -> None:
    info_text = (
        "Я бот, который помогает извлекать текст из изображений!\n"
        "Просто отправь мне изображение, и я создам документ Word с извлечённым текстом.\n"
        "Кроме того, ты можешь перезапустить меня в любое время, нажав на соответствующую кнопку."
    )
    message = await update.message.reply_text(info_text)

    # Сохраняем идентификатор отправленного сообщения
    bot_message_ids.append(message.message_id)

# Список случайных ответов для текстовых сообщений
random_responses = [
    "Мне кажется, ты что-то хотел сказать? Может, пришлешь изображение?",
    "Я готов к работе! Жду твою картинку!",
    "Если у тебя есть изображение, я смогу извлечь из него текст.",
    "Скажи, что ты думаешь, или просто пришли мне фото!",
    "Я тут, чтобы помочь! Как насчет изображения?",
    "Не стесняйся, отправь мне фото, и я сделаю свою работу!"
]

# Обработчик текстовых сообщений
async def handle_text(update: Update, context) -> None:
    text = update.message.text
    # Проверяем, не является ли текст кнопкой
    if text == "Перезапустить бота":
        await handle_restart(update, context)
    elif text == "Информация о боте":
        await handle_info(update, context)
    else:
        response = random.choice(random_responses)  # Выбираем случайный ответ
        await update.message.reply_text(response)

# Обработчик изображений
async def handle_image(update: Update, context) -> None:
    photo = update.message.photo[-1]  # Выбираем изображение лучшего качества
    file = await photo.get_file()
    file_path = f"{photo.file_id}.jpg"

    try:
        # Скачиваем изображение на диск
        await file.download_to_drive(file_path)
        # Обработка изображения и извлечение текста
        extracted_text = extract_text_from_image(file_path)
        # Создание временного документа
        output_file = f"{photo.file_id}.docx"
        create_word_doc([extracted_text], output_file)
        # Отправка документа пользователю
        message = await update.message.reply_document(document=open(output_file, 'rb'))
        # Сохраняем идентификатор отправленного сообщения
        bot_message_ids.append(message.message_id)
        # Удаление временных файлов
        os.remove(file_path)
        os.remove(output_file)
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
        await update.message.reply_text("Произошла ошибка при обработке изображения. Попробуйте еще раз.")





# Обработчик документов
async def handle_document(update: Update, context) -> None:
    document = update.message.document
    file = await document.get_file()  # Используем get_file() для получения файла
    await file.download('path_to_save_file')  # Сохраняем файл в указанном пути

# Главная функция для запуска бота
async def main():
    TOKEN = "7325975392:AAFBLp0eLAixyCgD0I8du_UBnjGrq-jP2RQ"  # Вставьте ваш токен
    
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))  # Обрабатываем текстовые сообщения
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))  # Обрабатываем изображения
    app.add_handler(MessageHandler(filters.Document, handle_document))  # Обрабатываем документы

    # Запуск бота
    await app.initialize()  # Явная инициализация приложения
    await app.start()
    print("Бот запущен и готов к работе!")  # Вывод сообщения в консоль

    # Запускаем polling
    await app.updater.start_polling() 
    
    # Ожидание завершения работы
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
