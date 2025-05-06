import random
import json
import requests
import os
from io import BytesIO
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Ключи и настройки
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
FOLDER_ID = os.getenv('FOLDER_ID')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Загрузка колоды карт
with open('ivent_taro_full_deck.json', 'r', encoding='utf-8') as f:
    deck = json.load(f)

# Позиции расклада
positions = [
    ("🥂 Атмосфера и гости", "Кубки"),
    ("🎤 Как пройдут шоу на сцене", "Жезлы"),
    ("⚙️ Техника и организация", "Мечи"),
    ("💰 Финансы и подрядчики", "Пентакли")
]

# Окончания мастей
suit_endings = {
    "Жезлы": "Жезлов",
    "Кубки": "Кубков",
    "Мечи": "Мечей",
    "Пентакли": "Пентаклей"
}

# Поиск файла на Google Drive
def find_file_on_drive(file_name):
    search_url = (
        f"https://www.googleapis.com/drive/v3/files?q="
        f"name='{file_name}' and '{FOLDER_ID}' in parents and trashed=false"
        f"&key={GOOGLE_API_KEY}&fields=files(id,name)"
    )
    response = requests.get(search_url)
    if response.status_code == 200:
        files = response.json().get('files', [])
        if files:
            return files[0]['id']
    return None

# Получение прямой ссылки на файл
def get_drive_download_link(file_id):
    return f"https://drive.google.com/uc?id={file_id}"

# Загрузка и поворот изображения
def download_and_rotate_image(image_url, rotate=False):
    response = requests.get(image_url)
    if response.status_code == 200:
        img = Image.open(BytesIO(response.content))
        if rotate:
            img = img.rotate(180, expand=True)
        bio = BytesIO()
        bio.name = 'card.png'
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio
    return None

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🍏 Добро пожаловать в Ивент Таро — волшебный расклад для вашего будущего мероприятия!\n\n"
        "Здесь карты расскажут:\n"
        "• Какой будет атмосфера среди гостей 🥂\n"
        "• Как пройдут шоу на сцене 🎤\n"
        "• Всё ли будет в порядке с техникой ⚙️\n"
        "• И порадуют ли вас финансы 💰\n\n"
        "Введите команду /rasclad, чтобы узнать предсказание!"
    )

# Команда /rasclad
async def rasclad(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔮✨ Перемешиваем карты, вращаем колесо судьбы... Ваше предсказание почти готово!")

    for position_text, suit in positions:
        available_cards = [card for card in deck if card['suit'] == suit or card['suit'] == 'Старший Аркан']
        card = random.choice(available_cards)

        is_reversed = random.choice([True, False])

        if card['suit'] == "Старший Аркан":
            card_name = card['name'].title().replace(' ', '_')
            file_name = f"{card['number']}_{card_name}.png"
        elif "number" in card:
            suit_name = suit_endings.get(card['suit'], card['suit'])
            file_name = f"{card['number']}_{suit_name}.png"
        else:
            file_name = f"{card['name']}.png"

        file_id = find_file_on_drive(file_name)

        if file_id:
            image_url = get_drive_download_link(file_id)
            rotated_image = download_and_rotate_image(image_url, rotate=is_reversed)
            if rotated_image:
                caption = f"{position_text}:\n{card['name']} ({'Перевёрнутая' if is_reversed else 'Прямая'})\n➡️ {card['reversed' if is_reversed else 'upright']}"
                await update.message.reply_photo(photo=rotated_image, caption=caption)
            else:
                await update.message.reply_text(f"⚠️ Ошибка загрузки изображения карты {card['name']} (ожидали файл: {file_name}).")
        else:
            await update.message.reply_text(f"⚠️ Карта {card['name']} не найдена на Google Drive (ожидали файл: {file_name}).")

    keyboard = [[InlineKeyboardButton("🎯 Сделать новый расклад", callback_data='new_rasclad')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🔮 Если хотите узнать предсказание для другого события, нажмите кнопку ниже.\n"
        "💬 Помните: изменить Судьбу в силах только опытные ивентеры!",
        reply_markup=reply_markup
    )

# Обработчик кнопок
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'new_rasclad':
        await rasclad(query, context)

# Запуск приложения
if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rasclad", rasclad))
    app.add_handler(CallbackQueryHandler(button))

    app.run_polling()
