from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
import logging
import re
import traceback
import datetime
import database
import csv
import io
import tempfile
from pytz import timezone
from datetime import timedelta



# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


(START, INPUT_DATE, GENERATE_SALES_BOOK_REPORT, GENERATE_CLIENTS_BOOK_REPORT) = range(4)
tz = timezone('Europe/Moscow')  # Change this to your actual timezone



def reports(update: Update, context: CallbackContext) -> int:
    # Construct the InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton("💰 Отчет по продажам", callback_data='sales_book')],
        [InlineKeyboardButton("👤 Отчет по клиентам", callback_data='clients_book')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the message
    update.message.reply_text("👉🏻 Выберите тип отчета :", reply_markup=reply_markup)

    return START


def sales_book_report(update: Update, context: CallbackContext) -> int:
    logger.info('sales_book_report called')
    query = update.callback_query
    query.answer()
    context.user_data['report_type'] = 'sales'  # Add this line
    logger.info(f"report_type set as: {context.user_data['report_type']}")

    keyboard = [
        [InlineKeyboardButton("Сегодня", callback_data='today'),
        InlineKeyboardButton("Вчера", callback_data='yesterday')],
        [InlineKeyboardButton("Текущий месяц", callback_data='this_month'),
        InlineKeyboardButton("Текущая неделя", callback_data='this_week')],
        [InlineKeyboardButton("30 дней", callback_data='30_days'),
        InlineKeyboardButton("Задать свой период", callback_data='custom_period')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        text="""💰 Вы выбрали отчет по продажам. 
        
👉🏻 Пожалуйста, выберите период для отчета или задайте свой период нажав на кнопку Задать свой период""",
        reply_markup=reply_markup
    )
    return INPUT_DATE


def clients_book_report(update: Update, context: CallbackContext) -> None:
    logger.info('clients_book_report called')
    query = update.callback_query
    query.answer()
    context.user_data['report_type'] = 'clients'  # Add this line
    logger.info(f"report_type set as: {context.user_data['report_type']}")
    
    keyboard = [
        [InlineKeyboardButton("Сегодня", callback_data='today'),
        InlineKeyboardButton("Вчераш", callback_data='yesterday')],
        [InlineKeyboardButton("Текущий месяц", callback_data='this_month'),
        InlineKeyboardButton("Текущая неделя", callback_data='this_week')],
        [InlineKeyboardButton("30 дней", callback_data='30_days'),
        InlineKeyboardButton("Задать свой период", callback_data='custom_period')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text(
        text="""👤 Вы выбрали отчет по клиентам. 
        
👉🏻 Пожалуйста, выберите период для отчета или задайте свой период нажав на кнопку Задать свой период""",
        reply_markup=reply_markup
    )
    return INPUT_DATE

def set_today(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    # Get current datetime in your timezone
    now = datetime.datetime.now(tz)

    # Today's date at 00:00:00 and now
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now

    context.user_data['start_date'] = start_date
    context.user_data['end_date'] = end_date

    if context.user_data['report_type'] == 'sales':
        return generate_sales_report(update, context)
    else:
        return generate_clients_report(update, context)
    return INPUT_DATE

def set_yesterday(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    now = datetime.datetime.now(tz)

    start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = (now - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999999)

    context.user_data['start_date'] = start_date
    context.user_data['end_date'] = end_date

    if context.user_data['report_type'] == 'sales':
        return generate_sales_report(update, context)
    else:
        return generate_clients_report(update, context)
    return INPUT_DATE


def set_this_month(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    now = datetime.datetime.now(tz)

    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_date = now

    context.user_data['start_date'] = start_date
    context.user_data['end_date'] = end_date

    if context.user_data['report_type'] == 'sales':
        return generate_sales_report(update, context)
    else:
        return generate_clients_report(update, context)
    return INPUT_DATE


def set_this_week(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    now = datetime.datetime.now(tz)

    start_date = now - timedelta(days=now.weekday())
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now

    context.user_data['start_date'] = start_date
    context.user_data['end_date'] = end_date

    if context.user_data['report_type'] == 'sales':
        return generate_sales_report(update, context)
    else:
        return generate_clients_report(update, context)
    return INPUT_DATE


def set_30_days(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    now = datetime.datetime.now(tz)

    start_date = now - timedelta(days=30)
    start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = now

    context.user_data['start_date'] = start_date
    context.user_data['end_date'] = end_date

    if context.user_data['report_type'] == 'sales':
        return generate_sales_report(update, context)
    else:
        return generate_clients_report(update, context)
    return INPUT_DATE
        

def set_custom_period(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    query.answer()

    query.edit_message_text(text="Пожалуйста введите дату для периода в следующем формате:\n\nДД.MM.ГГГГ - ДД.ММ.ГГГГ (если вам нужен отчет за один день, введите только одну дату)\n\nК примеру, если вы желаете получить отчет за 7 июля 2023 по 8 июля 2023, вы должны ввести:\n\n07.07.2023 - 08.07.2023")

    return INPUT_DATE

def input_date(update: Update, context: CallbackContext) -> int:
    logger.info('input_date called')
    user_message = update.message.text.strip()
    single_date_regex = r"^\d{2}\.\d{2}\.\d{4}$"
    date_range_regex = r"^\d{2}\.\d{2}\.\d{4} - \d{2}\.\d{2}\.\d{4}$"

    if re.match(date_range_regex, user_message):
        start_date, end_date = map(lambda x: datetime.datetime.strptime(x.strip(), '%d.%m.%Y'), user_message.split('-'))
        end_date += datetime.timedelta(days=1, seconds=-1) # Change this line
    elif re.match(single_date_regex, user_message):
        start_date = datetime.datetime.strptime(user_message, '%d.%m.%Y')
        end_date = start_date + datetime.timedelta(days=1, seconds=-1)
    else:
        logger.info('date format does not match')
        update.message.reply_text("""❌ Неправильный формат. 
        
Пожалуйста, введите дату в следующем формате: 

ДД.ММ.ГГГГ (отчет за один день) 
ДД.ММ.ГГГГ - ДД.ММ.ГГГГ (отчет за период)""")
        return INPUT_DATE

    # Add timezone information

    context.user_data['start_date'] = tz.localize(start_date)
    context.user_data['end_date'] = tz.localize(end_date)

    logger.info(f'start_date = {context.user_data["start_date"]}, end_date = {context.user_data["end_date"]}')
    
    report_type = context.user_data.get('report_type')
    logger.info(f'report_type = {report_type}')

    if report_type == 'sales':
        logger.info('Report type is sales, transitioning to GENERATE_SALES_BOOK_REPORT')
        return generate_sales_report(update, context)
    elif report_type == 'clients':
        logger.info('Report type is clients, transitioning to GENERATE_CLIENTS_BOOK_REPORT')
        return generate_clients_report(update, context)
    else:
        logger.info('Report type is unknown')
        return ConversationHandler.END
        

def calculate_report_stats(start_date, end_date):
    total_income = database.get_total_income(start_date, end_date)
    deal_quantity = database.get_deal_quantity(start_date, end_date)
    unique_customers = database.get_unique_customers(start_date, end_date)
    new_customers = database.get_new_customers(start_date, end_date)
    new_customers_income = database.get_income_from_new_customers(start_date, end_date)
    incoming_deal_quantity = database.get_incoming_deal_quantity(start_date, end_date)
    outgoing_deal_quantity = database.get_outgoing_deal_quantity(start_date, end_date)
    total_amount_incoming = database.get_total_amount_incoming(start_date, end_date)
    total_amount_outgoing = database.get_total_amount_outgoing(start_date, end_date)
    average_deal_amount = database.get_average_deal_amount(start_date, end_date)

    return {
        "total_income": total_income,
        "deal_quantity": deal_quantity,
        "unique_customers": unique_customers,
        "new_customers": new_customers,
        "new_customers_income": new_customers_income,
        "incoming_deal_quantity": incoming_deal_quantity,
        "outgoing_deal_quantity": outgoing_deal_quantity,
        "total_amount_incoming": total_amount_incoming,
        "total_amount_outgoing": total_amount_outgoing,
        "average_deal_amount": average_deal_amount
    }



def generate_sales_report(update, context):
    # Ensure dates have been set in user_data.
    logger.info("generate_sales_report called")
    if 'start_date' not in context.user_data or 'end_date' not in context.user_data:
        update.message.reply_text("Error: Report dates not specified")
        return ConversationHandler.END

    # New Message Here
    context.bot.send_message(chat_id=update.effective_chat.id, text="⏳ Отчет загружается...")

    start_date = context.user_data['start_date']
    end_date = context.user_data['end_date']
    stats = calculate_report_stats(start_date, end_date)
    context.bot.send_message(
    chat_id=update.effective_chat.id, 
    text=f"""✅ Отчет готов! 
Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}
        
💰 Доход за период: {stats['total_income']} рублей
🔢 Количество сделок: {stats['deal_quantity']}
🧾 Средний чек: {stats['average_deal_amount']} рублей

👤 Всего покупателей: {stats['unique_customers']}
🆕 Новых покупателей: {stats['new_customers']}
💸 Доход от новых покупателей: {stats['new_customers_income']} рублей

🗄️ Входящих / Исходящих: 📥 {stats['incoming_deal_quantity']} /  📤 {stats['outgoing_deal_quantity']}
↘️ Сумма входящих: {stats['total_amount_incoming']} рублей
↗️ Сумма исходящих: {stats['total_amount_outgoing']} рублей"""
)


    report_data = database.generate_sales_book_report(start_date, end_date)

    logger.info(f'report_data: {report_data}')  


    if report_data:
    # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
        # Create a CSV writer
            writer = csv.writer(tmp_file)

        # Write the header row
            header_row = ["Invoice ID", "Amount", "Date", "Name", "Username", "User ID", "In/Out"]
            writer.writerow(header_row)

        # Write the data rows
            for row in report_data:
                writer.writerow(row)

        # Get the file path
            file_path = tmp_file.name

    # Send the CSV file
        with open(file_path, 'rb') as doc:
            context.bot.send_document(chat_id=update.effective_chat.id, document=doc, filename='sales_report.csv')

        return ConversationHandler.END
    else:
        logger.info('No data available for the selected period')
        update.message.reply_text('Нет данных для отчета в заданный период. Попробуйте другие даты')
        return ConversationHandler.END



def generate_clients_report(update, context):
    logger.info("generate_clients_report called")
    # Ensure dates have been set in user_data.
    if 'start_date' not in context.user_data or 'end_date' not in context.user_data:
        update.message.reply_text("Error: Report dates not specified")
        return ConversationHandler.END

    # New Message Here
    context.bot.send_message(chat_id=update.effective_chat.id, text="⏳ Отчет загружается...")

    start_date = context.user_data['start_date']
    end_date = context.user_data['end_date']
    stats = calculate_report_stats(start_date, end_date)
    context.bot.send_message(
    chat_id=update.effective_chat.id, 
    text=f"""✅ Отчет готов! 
Период: {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}
        
💰 Доход за период: {stats['total_income']} рублей
🔢 Количество сделок: {stats['deal_quantity']}
🧾 Средний чек: {stats['average_deal_amount']} рублей

👤 Всего покупателей: {stats['unique_customers']}
🆕 Новых покупателей: {stats['new_customers']}
💸 Доход от новых покупателей: {stats['new_customers_income']} рублей

🗄️ Входящих / Исходящих: 📥 {stats['incoming_deal_quantity']} /  📤 {stats['outgoing_deal_quantity']}
↘️ Сумма входящих: {stats['total_amount_incoming']} рублей
↗️ Сумма исходящих: {stats['total_amount_outgoing']} рублей"""
)
    

    report_data = database.generate_clients_book_report(start_date, end_date)

    if report_data:
    # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp_file:
        # Create a CSV writer
            writer = csv.writer(tmp_file)

        # Write the header row
            header_row = ["Client ID", "Username", "Name", "Date of First Deal", "Date of Last Deal", "Total Deals", "Total Amount"]
            writer.writerow(header_row)

        # Write the data rows
            for row in report_data:
                writer.writerow(row)

        # Get the file path
            file_path = tmp_file.name

    # Send the CSV file
        with open(file_path, 'rb') as doc:
            context.bot.send_document(chat_id=update.effective_chat.id, document=doc, filename='clients_report.csv')

        return ConversationHandler.END
    else:
        update.message.reply_text('Нет данных для отчета в заданный пероид. Попробуйте другие даты')
        return ConversationHandler.END
