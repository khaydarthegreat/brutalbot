import uuid
import database
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputTextMessageContent, InlineQueryResultArticle
from telegram.ext import CallbackContext, CallbackQueryHandler, InlineQueryHandler, MessageHandler, Filters
import config

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def invoice(update: Update, context: CallbackContext) -> None:
    user_id = update.inline_query.from_user.id
    if user_id not in config.SALES_MANAGERS:
        # This user is not allowed to issue invoices
        logging.info(f"User {user_id} tried to issue an invoice but is not in the list of sales managers.")
        return

    query = update.inline_query.query.split()

    # Log the received query
    logger.info(f'Received inline query: {query}')

    # Ignore empty queries or queries without amount
    if not query or not query[0].isdigit():
        return

    amount = int(query[0])

    products = ['Vip', 'Express', 'Ordinar', 'Combo', 'Lesenka']

    results = []

    # Fetch current salesman from the database
    current_salesman = database.get_current_salesman()

    for product in products:
        # Log the extracted amount and product
        logger.info(f'Creating invoice for amount: {amount}, product: {product}')

        pay_url = f"{config.BOT_URL}?start=amount_{amount}_product_{product}"

        results.append(InlineQueryResultArticle(
            id=str(uuid.uuid4()),  # Generate a random ID for this result
            title=f"Создать счет • {amount} рублей",
            description=f"Продукт: {product} | Продажник: {current_salesman}",  
            input_message_content=InputTextMessageContent(f"""🧾 К оплате: {amount} рублей.

Для оплаты, жми кнопку внизу ⬇️ """),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Оплатить", url=pay_url)]
            ]),
            thumb_url="https://cdn-icons-png.flaticon.com/512/1117/1117142.png",  # Replace this with your actual image URL
        ))

    # Send all results
    context.bot.answer_inline_query(update.inline_query.id, results, cache_time=0)

def handle_payment(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    # extract the invoice id from context.chat_data
    invoice_id = context.chat_data.get('invoice_id')

    # Check the invoice status in the database
    invoice_status = database.get_invoice_status(invoice_id)

    if invoice_status == 'PAID' or invoice_status == 'DECLINED':
        # This invoice has already been paid, return a message to the user
        query.edit_message_text(text="Этот счет больше не действителен.")
    else:
        # The invoice is not paid, proceed with the payment process
        query.edit_message_text(text="""📎🧾 Для проверки, отправьте скриншот перевода.
        """,
                                reply_markup=InlineKeyboardMarkup([
                                    [InlineKeyboardButton("🔙 К реквизитам", callback_data='go_back')]
                                ]))


def go_back(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    # Retrieve the amount and card number from the context attributes
    amount = context.chat_data.get('amount')
    card_number, bank = database.get_current_card_and_bank()
    
    query.edit_message_text(text=f"""
🧾 Новый счет. К оплате: {amount} рублей.  

Для оплаты, переведите деньги на карту банка РФ

👉🏻 Реквизиты карты:
{bank} {card_number}

Перевели деньги? Нажмите на кнопку Я оплатил внизу 👇 

Если не получилось или есть вопросы, нажми на кнопку 👨🏻‍💼 Помощь. """,
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton("✅ Я оплатил", callback_data='i_paid'),
                                 InlineKeyboardButton("👨🏻‍💼 Помощь", url=config.MANAGER_URL)]
                            ]))




def handle_screenshot(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    name = user.first_name + " " + user.last_name if user.last_name else user.first_name
    username = user.username
    user_id = user.id
    document_file_id = None

    if update.message.photo:
        # Choose the highest quality photo
        document_file_id = update.message.photo[-1].file_id
    elif update.message.document:
        # Accept any document, regardless of its mime_type
        logger.info(f"Received document from user: id={user_id}, name={name}, username={username}")
        document_file_id = update.message.document.file_id

    if document_file_id is not None:
        
        logger.info(f"Received screenshot from user: id={user_id}, name={name}, username={username}")

        # Retrieve the latest invoice id for the user
        invoice_id = database.get_last_invoice_id_for_user(user_id)

        logger.info(f"Latest invoice id for user {user_id}: {invoice_id}")  # Log the fetched invoice id for debugging

        if invoice_id is not None:
            # Retrieve the invoice details from the database
            database.add_screenshot_id(invoice_id, update.message.message_id)
            invoice_details = database.get_invoice_details(invoice_id)
            invoice_amount = invoice_details["amount"]
            product = invoice_details["product"]

            for manager_id in config.SALES_MANAGERS:
                # Forward the screenshot to the payment manager
                context.bot.forward_message(chat_id=manager_id, from_chat_id=update.effective_chat.id, message_id=update.message.message_id)

                logger.info(f"Forwarded screenshot to payment manager: id={manager_id}")

                # Build the message string
                msg = f"""Поступил новый скриншот оплаты. 
                
Пожалуйста, проверьте скриншот.

"""
                msg += f"Имя клиента: {name}\n"
                if username:
                    msg += f"Username клиента: {username}\n"
                msg += f"User ID клиента : {user_id}\n"
                msg += f"Номер счета: {invoice_id}\n"
                msg += f"Сумма счета: {invoice_amount}\n"
                if product != 'null':
                    msg += f"Продукт: {product}\n"

                msg += f"💳: {database.get_current_card_and_bank()}"

                # Send the invoice details to the payment manager
                context.bot.send_message(
                    chat_id=manager_id,
                    text=msg,
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✅ Подтвердить", callback_data=f'approve_{invoice_id}'),
                        InlineKeyboardButton("❌ Отклонить", callback_data=f'decline_{invoice_id}')]]
                    )
                )

                logger.info(f"Sent invoice details to payment manager: id={manager_id}")

            context.bot.send_message(chat_id=update.effective_chat.id, text=""" Скрин получен. 
            
        🔎 Проверяем.""")

            logger.info(f"Sent thank you message to user: id={user_id}")
        else:
            logger.warning(f"No invoices found for user: id={user_id}")


def approve_invoice(update: Update, context: CallbackContext) -> None:
    try:
        query = update.callback_query
        data = query.data.split('_')
        invoice_id = data[1]

        if len(data) == 2:
            # This is the first click on the "Approve" button, ask for confirmation
            if not "Вы точно хотите пометить счет номер" in query.message.text:
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Да", callback_data=f'approve_{invoice_id}_confirm'),
                                                InlineKeyboardButton("❌ Нет", callback_data='do_nothing')]])
                context.bot.send_message(chat_id=query.message.chat_id, text=f"⚠️ Вы точно хотите пометить счет номер {invoice_id} как оплаченый?", reply_markup=keyboard)
        elif len(data) == 3:
            # The manager has confirmed the approval, now ask for type
            if not "Пожалуйста, выберите тип продажи:" in query.message.text:
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("📥 Входящий", callback_data=f'incoming_{invoice_id}'),
                                                  InlineKeyboardButton("📤 Исходящий", callback_data=f'outgoing_{invoice_id}')]])

                query.edit_message_text(text=f"⚠️ Выберите тип продажи. ⚠️", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"An error occurred in approve_invoice: {e}")

        



def set_invoice_type_outgoing(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    invoice_id = query.data.split('_')[1]
    database.update_invoice_status(invoice_id, 'PAID')
    database.update_invoice_type(invoice_id, 'Outgoing')  # Assuming you have this function defined
    query.edit_message_text(text=f"""✅ Счет {invoice_id} был подтвержден!
    
Тип продажи: 📤 Исходящий.""")

    invoice_details = database.get_invoice_details(invoice_id)
    if invoice_details is None:
        print("set_invoice_type_outgoing: invoice_details is None!")
        return

    user_id = invoice_details["user_id"]
    amount = invoice_details["amount"]
    name = invoice_details["name"]
    msg = f""" 👊🏼 Скриншот прошел проверку! 

👇🏻 Нажмите кнопку внизу и забирай свой прогноз!"""
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("👉🏻 Забрать прогноз", url=config.MANAGER_URL)]])
    context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)

    # Get the screenshot info from the database
    screenshot_id = database.get_screenshot_id(invoice_id)
    if screenshot_id is not None:
        from_chat_id = invoice_details["user_id"]
        for manager_id in config.PAYMENT_MANAGERS:
            # Forward the screenshot to the payment manager
            context.bot.forward_message(chat_id=manager_id, from_chat_id=from_chat_id, message_id=screenshot_id)

            # Send the message to the payment manager
            context.bot.send_message(chat_id=manager_id, text=f"""🆕 Новый перевод на сумму {amount} рублей.
    💳: {database.get_current_card_and_bank()} 

    Счет №: {invoice_id}
    Клиент: {name}
    User ID: {from_chat_id}
            """)


def set_invoice_type_incoming(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    invoice_id = query.data.split('_')[1]
    database.update_invoice_status(invoice_id, 'PAID')
    database.update_invoice_type(invoice_id, 'Incoming')  # Assuming you have this function defined
    query.edit_message_text(text=f"""✅ Счет {invoice_id} был подтвержден!
    
Тип продажи: 📥 Входящий.""")

    invoice_details = database.get_invoice_details(invoice_id)
    if invoice_details is None:
        print("set_invoice_type_incoming: invoice_details is None!")
        return

    user_id = invoice_details["user_id"]
    amount = invoice_details["amount"]
    name = invoice_details["name"]
    msg = f""" 👊🏼 Скриншот прошел проверку! 

👇🏻 Нажмите кнопку внизу и забирай свой прогноз!"""
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("👉🏻 Забрать прогноз", url=config.MANAGER_URL)]])
    context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)

    # Get the screenshot info from the database
    screenshot_id = database.get_screenshot_id(invoice_id)
    if screenshot_id is not None:
        from_chat_id = invoice_details["user_id"]
        for manager_id in config.PAYMENT_MANAGERS:
            # Forward the screenshot to the payment manager
            context.bot.forward_message(chat_id=manager_id, from_chat_id=from_chat_id, message_id=screenshot_id)

            # Send the message to the payment manager
            context.bot.send_message(chat_id=manager_id, text=f"""🆕 Новый перевод на сумму {amount} рублей.
    💳: {database.get_current_card_and_bank()} 

    Счет №: {invoice_id}
    Клиент: {name}
    User ID: {from_chat_id}
            """)



def decline_invoice(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    invoice_id = query.data.split('_')[1]

    if len(query.data.split('_')) == 2:
        # This is the first click on the "Decline" button, ask for confirmation
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Yes", callback_data=f'decline_{invoice_id}_confirm'),
                                          InlineKeyboardButton("No", callback_data='do_nothing')]])
        context.bot.send_message(chat_id=query.message.chat_id, text=f"Вы уверены, что хотите отколнить перевод счета номер {invoice_id}?", reply_markup=keyboard)
    else:
        # The manager has confirmed the decline
        database.update_invoice_status(invoice_id, 'DECLINED')
        invoice_details = database.get_invoice_details(invoice_id)
        user_id = invoice_details["user_id"]
        msg = f"🚫 Бро, что-то пошло не так. Скриншот не прошел проверку. Если ты думаешь, что произошла ошибка, напиши нам."
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Произошла ошибка", url=config.MANAGER_URL)]])
        context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)
        query.edit_message_text(text=f"Счет {invoice_id} был отклонен.")  # This will update the confirmation message to the decline message




def do_nothing(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)







