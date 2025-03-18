import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
CHOOSING, TICKET_UPLOAD, REPORT_TEXT, CONFIRMATION = range(4)

# Данные пользователя будут храниться здесь
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы с ботом."""
    user = update.message.from_user
    logger.info(f"Пользователь {user.first_name} запустил бота.")
    
    await update.message.reply_text(
        f"Здравствуйте, {user.first_name}!\n\n"
        "Этот бот поможет вам создать заявку на рапорт.\n"
        "Для начала нажмите на кнопку 'Создать заявку'.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Создать заявку", callback_data="create_request")
        ]])
    )
    
    return CHOOSING

async def create_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка нажатия на кнопку 'Создать заявку'."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_data[user_id] = {}
    
    await query.edit_message_text(
        "Пожалуйста, отправьте файл с талоном.",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Отменить", callback_data="cancel")
        ]])
    )
    
    return TICKET_UPLOAD

async def ticket_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:  
    """Обработка загрузки файла с талоном."""  
    user = update.message.from_user  
    user_id = user.id  

    # Проверяем, что пользователь отправил файл  
    if update.message.document:  
        file = update.message.document  
        file_id = file.file_id  
        file_name = file.file_name  

        try:  
            # Сохраняем информацию о файле  
            user_data[user_id]['ticket_file_id'] = file_id  
            user_data[user_id]['ticket_file_name'] = file_name  

            await update.message.reply_text(  
                f"Файл '{file_name}' успешно получен.\n\n"  
                "Теперь опишите составляющее рапорта: куда направляется, цель, дополнительные детали и т.д."  
            )  

            return REPORT_TEXT  
        except Exception as e:  
            logger.error(f"Ошибка при обработке файла: {e}")  
            await update.message.reply_text(  
                "Произошла ошибка при обработке файла. Пожалуйста, попробуйте еще раз."  
            )  
            return TICKET_UPLOAD  
    else:  
        await update.message.reply_text(  
            "Пожалуйста, отправьте файл с талоном. Если у вас нет файла, "  
            "сначала подготовьте его, а затем вернитесь к созданию заявки."  
        )  

        return TICKET_UPLOAD

async def report_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка текста рапорта."""
    user = update.message.from_user
    user_id = user.id
    report_text = update.message.text
    
    # Сохраняем текст рапорта
    user_data[user_id]['report_text'] = report_text
    
    # Создаем сводку для пользователя
    summary = (
        "📋 Сводка вашей заявки:\n\n"
        f"📎 Файл: {user_data[user_id]['ticket_file_name']}\n\n"
        f"📝 Текст рапорта:\n{report_text}\n\n"
        "Всё правильно? Если да, подтвердите заявку."
    )
    
    await update.message.reply_text(
        summary,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
            [InlineKeyboardButton("❌ Отменить", callback_data="cancel")]
        ])
    )
    
    return CONFIRMATION

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка подтверждения заявки."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    # Здесь можно добавить код для сохранения заявки в базу данных
    # или отправки администратору
    
    await query.edit_message_text(
        "✅ Ваша заявка принята!\n\n"
        "Номер заявки: #" + str(user_id)[-5:] + "\n"
        "Когда заявка будет обработана, вы получите уведомление."
    )
    
    # Очищаем данные пользователя
    if user_id in user_data:
        del user_data[user_id]
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена создания заявки."""
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer()
    
    # Очищаем данные пользователя
    if user_id in user_data:
        del user_data[user_id]
    
    await query.edit_message_text("❌ Создание заявки отменено.")
    
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет справочное сообщение."""
    await update.message.reply_text(
        "🔍 Справка по использованию бота:\n\n"
        "/start - начать работу с ботом\n"
        "/help - показать справку\n\n"
        "Для создания заявки на рапорт следуйте инструкциям бота. "
        "Вам нужно будет загрузить файл с талоном и описать детали рапорта."
    )

def main() -> None:
    """Запуск бота."""
    # Создаем приложение и передаем ему токен бота
    application = Application.builder().token(os.environ.get("TELEGRAM_BOT_TOKEN")).build()

    # Создаем обработчик разговора
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [
                CallbackQueryHandler(create_request, pattern="^create_request$"),
            ],
            TICKET_UPLOAD: [
                MessageHandler(filters.Document.ALL, ticket_upload),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
            REPORT_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, report_text),
            ],
            CONFIRMATION: [
                CallbackQueryHandler(confirm, pattern="^confirm$"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))

    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
