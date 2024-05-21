import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from config import TOKEN
from handlers import start, choose_exercise, enter_weight, enter_reps, undo, end, cancel, check_timeout, button_handler

# Initialize logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for conversation states
CHOOSING_EXERCISE, ENTERING_WEIGHT, ENTERING_REPS, CONTINUE_SET = range(4)

def main() -> None:
    """Main function to start the bot."""
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CHOOSING_EXERCISE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_exercise)],
            ENTERING_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_weight)],
            ENTERING_REPS: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_reps)],
            CONTINUE_SET: [CallbackQueryHandler(button_handler)]
        },
        fallbacks=[CommandHandler('end', end), CommandHandler('cancel', cancel), CommandHandler('undo', undo)]
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("end", end))
    application.add_handler(CommandHandler("undo", undo))

    application.job_queue.run_repeating(check_timeout, interval=60, first=0)

    logger.info("Starting bot")
    application.run_polling()

if __name__ == '__main__':
    main()
