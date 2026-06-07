import logging
import json
import random
import os
from datetime import datetime, time
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загрузка токена
TOKEN = os.getenv('TELEGRAM_TOKEN')
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN не найден в переменных окружения!")

# Глобальные переменные для статистики
user_stats = {
    'total_users': 0,
    'facts_sent': 0,
    'admin_users': [int(x.strip()) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
}

# Загрузка фактов из JSON
def load_facts():
    try:
        with open('facts.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Файл facts.json не найден!")
        return {"all": []}

# Сохранение фактов в JSON
def save_facts(facts):
    with open('facts.json', 'w', encoding='utf-8') as f:
        json.dump(facts, f, ensure_ascii=False, indent=2)

# Сохранение ID пользователя
def save_user_id(user_id):
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
    except FileNotFoundError:
        users = []
    
    if user_id not in users:
        users.append(user_id)
        with open('users.json', 'w', encoding='utf-8') as f:
            json.dump(users, f)
        return True
    return False

# Получение всех пользователей
def get_all_users():
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Главное меню
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start - приветствие и главное меню"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # Сохраняем ID пользователя
    is_new = save_user_id(user_id)
    if is_new:
        user_stats['total_users'] += 1
        logger.info(f"Новый пользователь: {user_id} (@{update.effective_user.username})")
    
    # Создаём клавиатуру с кнопками
    keyboard = [
        ["🐾 Получить факт"],
        ["🐱 Выбрать животное"],
        ["📊 Статистика"],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    welcome_text = (
        f"👋 Привет, {user_name}!\n\n"
        "🐾 Я бот с интересными фактами о животных.\n\n"
        "Нажми кнопку ниже, чтобы получить случайный факт! 🎲\n\n"
        "_Каждый факт - новое открытие!_"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

# Получение факта
async def get_fact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправка случайного факта"""
    facts = load_facts()
    category = context.user_data.get('selected_category', 'all')
    
    if category not in facts or not facts[category]:
        await update.message.reply_text("❌ К сожалению, фактов в этой категории нет.")
        return
    
    fact = random.choice(facts[category])
    user_stats['facts_sent'] += 1
    
    # Добавляем эмодзи в зависимости от категории
    emoji_map = {
        'cats': '🐱',
        'dogs': '🐶',
        'wild': '🦁',
        'birds': '🦅',
        'reptiles': '🐍',
        'insects': '🦋',
        'marine': '🐠',
        'all': '🐾'
    }
    emoji = emoji_map.get(category, '🐾')
    
    # Формируем сообщение
    fact_text = f"{emoji} *Факт о животных:*\n\n{fact['text']}"
    if 'source' in fact:
        fact_text += f"\n\n_Источник: {fact['source']}_"
    
    # Кнопки для получения нового факта
    keyboard = [
        [InlineKeyboardButton("➕ Ещё факт", callback_data=f"fact_{category}")],
        [InlineKeyboardButton("🐱 Выбрать категорию", callback_data="categories")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(fact_text, reply_markup=reply_markup, parse_mode='Markdown')
    logger.info(f"Отправлен факт пользователю {update.effective_user.id}")

# Выбор категории
async def select_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Меню выбора категорий"""
    facts = load_facts()
    categories = [cat for cat in facts.keys() if cat != 'all' and facts[cat]]
    
    keyboard = [
        [InlineKeyboardButton(f"🐱 Кошки", callback_data="cat_cats")],
        [InlineKeyboardButton(f"🐶 Собаки", callback_data="cat_dogs")],
        [InlineKeyboardButton(f"🦁 Дикие животные", callback_data="cat_wild")],
        [InlineKeyboardButton(f"🦅 Птицы", callback_data="cat_birds")],
        [InlineKeyboardButton(f"🐍 Рептилии", callback_data="cat_reptiles")],
        [InlineKeyboardButton(f"🦋 Насекомые", callback_data="cat_insects")],
        [InlineKeyboardButton(f"🐠 Морские животные", callback_data="cat_marine")],
        [InlineKeyboardButton(f"🐾 Все факты", callback_data="cat_all")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("🐾 Выбери категорию животных:", reply_markup=reply_markup)

# Обработка кнопок категорий
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("cat_"):
        category = query.data.replace("cat_", "")
        context.user_data['selected_category'] = category
        
        facts = load_facts()
        if category not in facts or not facts[category]:
            await query.edit_message_text("❌ Фактов в этой категории пока нет.")
            return
        
        fact = random.choice(facts[category])
        user_stats['facts_sent'] += 1
        
        emoji_map = {
            'cats': '🐱', 'dogs': '🐶', 'wild': '🦁', 'birds': '🦅',
            'reptiles': '🐍', 'insects': '🦋', 'marine': '🐠', 'all': '🐾'
        }
        emoji = emoji_map.get(category, '🐾')
        
        fact_text = f"{emoji} *Факт о животных:*\n\n{fact['text']}"
        if 'source' in fact:
            fact_text += f"\n\n_Источник: {fact['source']}_"
        
        keyboard = [
            [InlineKeyboardButton("➕ Ещё факт", callback_data=f"fact_{category}")],
            [InlineKeyboardButton("🐱 Выбрать категорию", callback_data="categories")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(fact_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data.startswith("fact_"):
        category = query.data.replace("fact_", "")
        facts = load_facts()
        if facts.get(category):
            fact = random.choice(facts[category])
            user_stats['facts_sent'] += 1
            
            emoji_map = {
                'cats': '🐱', 'dogs': '🐶', 'wild': '🦁', 'birds': '🦅',
                'reptiles': '🐍', 'insects': '🦋', 'marine': '🐠', 'all': '🐾'
            }
            emoji = emoji_map.get(category, '🐾')
            
            fact_text = f"{emoji} *Факт о животных:*\n\n{fact['text']}"
            if 'source' in fact:
                fact_text += f"\n\n_Источник: {fact['source']}_"
            
            keyboard = [
                [InlineKeyboardButton("➕ Ещё факт", callback_data=f"fact_{category}")],
                [InlineKeyboardButton("🐱 Выбрать категорию", callback_data="categories")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(fact_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif query.data == "categories":
        await select_category_inline(update, context)

# Выбор категории из инлайн кнопок
async def select_category_inline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Меню выбора категорий в инлайн режиме"""
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton(f"🐱 Кошки", callback_data="cat_cats")],
        [InlineKeyboardButton(f"🐶 Собаки", callback_data="cat_dogs")],
        [InlineKeyboardButton(f"🦁 Дикие животные", callback_data="cat_wild")],
        [InlineKeyboardButton(f"🦅 Птицы", callback_data="cat_birds")],
        [InlineKeyboardButton(f"🐍 Рептилии", callback_data="cat_reptiles")],
        [InlineKeyboardButton(f"🦋 Насекомые", callback_data="cat_insects")],
        [InlineKeyboardButton(f"🐠 Морские животные", callback_data="cat_marine")],
        [InlineKeyboardButton(f"🐾 Все факты", callback_data="cat_all")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("🐾 Выбери категорию животных:", reply_markup=reply_markup)

# Обработка текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    
    if text == "🐾 Получить факт":
        await get_fact(update, context)
    elif text == "🐱 Выбрать животное":
        await select_category(update, context)
    elif text == "📊 Статистика":
        await show_stats(update, context)
    else:
        # Подсказка при других сообщениях
        keyboard = [
            ["🐾 Получить факт"],
            ["🐱 Выбрать животное"],
            ["📊 Статистика"],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text(
            "🤔 Я не понимаю эту команду.\n\n"
            "Используй кнопки меню или команды:\n"
            "/start - главное меню\n"
            "/fact - получить факт\n"
            "/help - справка",
            reply_markup=reply_markup
        )

# Статистика (для всех)
async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показать статистику"""
    users = get_all_users()
    stats_text = (
        "📊 *Статистика бота:*\n\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"📚 Отправлено фактов: {user_stats['facts_sent']}\n"
        f"⏰ Время работы: 24/7"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')

# Админ команды
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /stats - статистика (только для админов)"""
    user_id = update.effective_user.id
    
    if user_id not in user_stats['admin_users']:
        await update.message.reply_text("❌ Доступ запрещён. Эта команда только для администраторов.")
        return
    
    users = get_all_users()
    stats_text = (
        "📊 *Статистика бота (АДМИН):*\n\n"
        f"👥 Всего пользователей: {len(users)}\n"
        f"📚 Отправлено фактов: {user_stats['facts_sent']}\n"
        f"⏰ Время работы: 24/7\n\n"
        f"IDs пользователей (первые 10): {users[:10]}"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')

# Добавление факта (админ)
async def add_fact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /add_fact - добавить факт (только для админов)"""
    user_id = update.effective_user.id
    
    if user_id not in user_stats['admin_users']:
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    
    await update.message.reply_text(
        "📝 Пожалуйста, отправь факт в формате:\n"
        "категория|текст факта|источник\n\n"
        "Категории: cats, dogs, wild, birds, reptiles, insects, marine"
    )
    context.user_data['waiting_for_fact'] = True

# Рассылка (админ)
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /new - рассылка сообщения всем (только для админов)"""
    user_id = update.effective_user.id
    
    if user_id not in user_stats['admin_users']:
        await update.message.reply_text("❌ Доступ запрещён.")
        return
    
    await update.message.reply_text(
        "📢 Отправь сообщение для рассылки всем пользователям:"
    )
    context.user_data['waiting_for_broadcast'] = True

# Справка
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /help"""
    help_text = (
        "*📖 Справка по командам:*\n\n"
        "/start - главное меню\n"
        "/fact - получить случайный факт\n"
        "/help - эта справка\n\n"
        "*🔒 Админ команды:*\n"
        "/stats - статистика бота\n"
        "/add_fact - добавить новый факт\n"
        "/new - рассылка всем пользователям"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

# Основная функция
def main() -> None:
    """Запуск бота"""
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("fact", get_fact))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("add_fact", add_fact))
    application.add_handler(CommandHandler("new", broadcast))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запуск бота
    logger.info("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
