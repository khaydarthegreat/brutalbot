from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputTextMessageContent, InlineQueryResultArticle, ReplyKeyboardMarkup, ReplyKeyboardRemove, ParseMode
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, InlineQueryHandler, CallbackQueryHandler, ConversationHandler
from cashier import invoice, handle_payment, go_back, handle_screenshot, approve_invoice, decline_invoice, do_nothing
from reports import reports, sales_book_report, clients_book_report, input_date, generate_sales_report, generate_clients_report, set_today, set_yesterday, set_this_month, set_this_week,  set_30_days, set_custom_period, START, INPUT_DATE, GENERATE_SALES_BOOK_REPORT, GENERATE_CLIENTS_BOOK_REPORT
from settings import conv_handler_payments
from config import PAYMENT_MANAGERS, SALES_MANAGERS, ANALYTICS, BOT_TOKEN, MANAGER_URL, get_card_number, set_card_number
import re
import traceback
import uuid
import random
import database
import logging
import datetime
import json
import html

# Set up logging at the top of your file
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


main_menu_options = [
    ['Reports'],
    ['Manage payments']
]

def get_payment_message(amount):
    card_number, bank = database.get_current_card_and_bank()
    
    return f"""
    🧾 Новый счет. К оплате: {amount} рублей.  

Для оплаты, переведите деньги на карту банка РФ

👉🏻 Реквизиты карты:
{bank} {card_number}

Перевели деньги? Нажмите на кнопку Я оплатил внизу 👇 

Если не получилось или есть вопросы, нажми на кнопку 👨🏻‍💼 Помощь. """



def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    name = user.first_name + " " + user.last_name if user.last_name else user.first_name
    username = user.username if user.username else 'null'
    user_id = user.id

    # Log user details
    logger.info(f'Start command received from user: id={user_id}, name={name}, username={username}')

    # Extract the amount and product from the text of the message
    message_text = update.message.text  # It should be in the format "/start amount_amount_product_product"
    start_data = message_text.split()[1].split('_') if len(message_text.split()) > 1 else None

    if user_id in PAYMENT_MANAGERS or user_id in SALES_MANAGERS or user_id in ANALYTICS:
        # Create the main menu keyboard markup
        reply_markup = ReplyKeyboardMarkup(main_menu_options, resize_keyboard=True)

        # Send the menu to the user
        update.message.reply_text('Выберите действие:', reply_markup=reply_markup)
    
    elif start_data and len(start_data) == 4 and start_data[0] == 'amount' and start_data[2] == 'product':
        amount = int(start_data[1])
        product = start_data[3]

        # Log parsed amount and product
        logger.info(f'Parsed amount={amount} and product={product} from message text: {message_text}')

        invoice_id = int(database.get_latest_invoice_id()) + 1
        while database.check_invoice_id(invoice_id):
            invoice_id += 1

        # Log created invoice_id
        logger.info(f'Generated unique invoice_id={invoice_id} for user_id={user_id}')

        # Store new invoice in the db
        database.add_invoice(invoice_id, amount, product, user_id, name)

        # Saving invoice_id in context.chat_data
        context.chat_data['invoice_id'] = invoice_id

        # Add the customer details to the database
        database.update_customer_details(invoice_id, name, username, user_id)

        # Update the Date column in the invoice
        database.update_invoice_date(invoice_id)

        # Log success of database operations
        logger.info(f'Added new invoice and updated customer details in database for invoice_id={invoice_id}, user_id={user_id}')

        # Now we're ready to send the payment message
        payment_message = get_payment_message(amount)
        card_number = database.get_current_card_and_bank()

        # Store the amount and card number as context attributes
        context.chat_data['amount'] = amount
        context.chat_data['_CARD_NUMBER'] = card_number

        # Creating InlineKeyboardMarkup
        keyboard = [[InlineKeyboardButton("✅ Я оплатил", callback_data='i_paid'),
                     InlineKeyboardButton("👨‍💼 Помощь", url=MANAGER_URL)]]  # Replace with the actual username of the sales manager

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send the message with InlineKeyboardMarkup
        update.message.reply_text(payment_message, reply_markup=reply_markup, parse_mode=ParseMode.MARKDOWN)

        # Log sent payment message
        logger.info(f'Sent payment message to user_id={user_id} with invoice_id={invoice_id}, amount={amount}, product={product}')
    else:
        update.message.reply_text('Hi!')


def cancel(update: Update, context: CallbackContext) -> int:
    user = update.effective_user
    logger.info(f"User {user.id} canceled the conversation.")
    update.message.reply_text('Действие было отменено.', reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def error_callback(update: Update, context: CallbackContext) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f'An exception was raised while handling an update\n'
        f'<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    # Finally, send the message
    context.bot.send_message(chat_id=56424449, text=message, parse_mode=ParseMode.HTML)


def main() -> None:
    # You should replace 'YOUR BOT TOKEN' with your actual token
    updater = Updater(BOT_TOKEN, use_context=True) 

    dispatcher = updater.dispatcher
    dispatcher.add_handler(conv_handler_payments)

    conv_handler = ConversationHandler(
    entry_points=[
        CommandHandler('reports', reports),
        MessageHandler(Filters.regex('^Reports$'), reports)
    ],
    states={
        START: [
            CallbackQueryHandler(sales_book_report, pattern='sales_book'),
            CallbackQueryHandler(clients_book_report, pattern='clients_book')
        ],
        INPUT_DATE: [
            CallbackQueryHandler(set_today, pattern='today'),
            CallbackQueryHandler(set_yesterday, pattern='yesterday'),
            CallbackQueryHandler(set_this_month, pattern='this_month'),
            CallbackQueryHandler(set_this_week, pattern='this_week'),
            CallbackQueryHandler(set_30_days, pattern='30_days'),
            CallbackQueryHandler(set_custom_period, pattern='custom_period'),
            MessageHandler(Filters.text & ~Filters.command, input_date)
        ],
        GENERATE_SALES_BOOK_REPORT: [MessageHandler(Filters.text & ~Filters.command, generate_sales_report)],
        GENERATE_CLIENTS_BOOK_REPORT: [MessageHandler(Filters.text & ~Filters.command, generate_clients_report)],
    },
    fallbacks=[CommandHandler('cancel', cancel)],
)




    dispatcher.add_handler(conv_handler)
    logger.info(f"Handlers: {dispatcher.handlers}")

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(InlineQueryHandler(invoice))
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_screenshot))
    dispatcher.add_handler(CallbackQueryHandler(handle_payment, pattern='i_paid'))
    dispatcher.add_handler(CallbackQueryHandler(go_back, pattern='go_back'))
    dispatcher.add_handler(CallbackQueryHandler(approve_invoice, pattern='approve_.*'))
    dispatcher.add_handler(CallbackQueryHandler(decline_invoice, pattern='decline_.*'))
    dispatcher.add_handler(CallbackQueryHandler(do_nothing, pattern='do_nothing'))
    dispatcher.add_handler(MessageHandler(Filters.photo | Filters.document, handle_screenshot))

    dispatcher.add_error_handler(error_callback)

    updater.start_polling()

    updater.idle()

if __name__ == '__main__':
    database.create_table()
    main()


