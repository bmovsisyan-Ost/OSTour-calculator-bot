from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, ConversationHandler,
    MessageHandler, filters
)

# --- Настройки ставок гидов ---
guide_rates = {
    "intermediate": {"1-2":4500,"3-5":5400,"6-10":6300},
    "professional": {"1-2":6500,"3-5":7800,"6-10":9100}
}

# --- Настройки экскурсий ---
excursions = {
    "Царская прогулка по Арагацу": {
        "time_hours": 8,
        "transport_cost": 48000,
        "tickets_included": True,
        "margin": 0.2,
        "available_guides": ["Без", "Гид", "Эксперт"]
    },
    "Экскурсия в Музей вина": {
        "time_hours": 6,
        "transport_cost": 35000,
        "tickets_included": True,
        "margin": 0.15,
        "available_guides": ["Без", "Гид"]
    },
    "Трансфер в Ереван": {
        "time_hours": 2,
        "transport_cost": 15000,
        "tickets_included": False,
        "margin": 0.1,
        "available_guides": ["Без"]
    }
}

# --- Состояния ---
SELECT_TOUR, COUNT, GUIDE = range(3)

# --- Команды ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tour_list = "\n".join([f"- {name}" for name in excursions.keys()])
    await update.message.reply_text(
        f"Привет! 👋\nВыберите экскурсию:\n{tour_list}"
    )
    return SELECT_TOUR

async def select_tour(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    if choice not in excursions:
        await update.message.reply_text("Выберите экскурсию из списка!")
        return SELECT_TOUR
    context.user_data['tour'] = choice
    await update.message.reply_text("Сколько туристов? (1–9)")
    return COUNT

async def enter_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        count = int(update.message.text)
        if not (1 <= count <= 9):
            raise ValueError
        context.user_data['count'] = count
        # Доступные гиды для этой экскурсии
        guides = excursions[context.user_data['tour']]['available_guides']
        context.user_data['available_guides'] = guides
        if len(guides) == 1:
            # Только один вариант → пропускаем выбор
            context.user_data['guide'] = guides[0]
            return await calculate_cost(update, context)
        # Показываем кнопки с доступными типами гидов
        keyboard = ReplyKeyboardMarkup([guides], one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text("Выберите тип гида:", reply_markup=keyboard)
        return GUIDE
    except:
        await update.message.reply_text("Введите число от 1 до 9")
        return COUNT

async def select_guide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    guide = update.message.text
    if guide not in context.user_data['available_guides']:
        await update.message.reply_text("Выберите тип гида из доступных вариантов")
        return GUIDE
    context.user_data['guide'] = guide
    return await calculate_cost(update, context)

# --- Расчёт стоимости ---
async def calculate_cost(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tour = context.user_data['tour']
    count = context.user_data['count']
    guide = context.user_data['guide']

    data = excursions[tour]
    total = data['transport_cost']  # транспорт (комфорт)
    
    # Ставка гида
    if guide == "Гид":
        total += get_guide_rate("intermediate", count) * data['time_hours']
    elif guide == "Эксперт":
        total += get_guide_rate("professional", count) * data['time_hours']
    # Без гида → ничего не добавляем

    # Билеты включены автоматически
    if data['tickets_included']:
        total += 0  # здесь можно добавить стоимость билетов, если нужно

    # Применяем маржу
    total *= (1 + data['margin'])
    total = round(total/1000)*1000

    await update.message.reply_text(f"Итоговая стоимость: {total:,} драм")
    return ConversationHandler.END

def get_guide_rate(level, count):
    if count <= 2: return guide_rates[level]["1-2"]
    if count <= 5: return guide_rates[level]["3-5"]
    return guide_rates[level]["6-10"]

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Расчёт отменён.")
    return ConversationHandler.END

# --- Запуск бота ---
if __name__ == "__main__":
    import os
    TOKEN = os.getenv("BOT_TOKEN") or "8076734387:AAH3HYMnGrvepXuUkYS3EE_gCbgcrKnehXQ"
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_TOUR: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_tour)],
            COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_count)],
            GUIDE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_guide)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(conv_handler)
    print("Bot started")
    app.run_polling()
