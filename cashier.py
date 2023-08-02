import uuid
import database
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputTextMessageContent, InlineQueryResultArticle
from telegram.ext import CallbackContext, CallbackQueryHandler, InlineQueryHandler, MessageHandler, Filters
import config
from datetime import datetime

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def invoice(update: Update, context: CallbackContext) -> None:
    user_id = update.inline_query.from_user.id
    if user_id not in config.SALES_MANAGERS:
        logging.info(f"User {user_id} tried to issue an invoice but is not in the list of sales managers.")
        return

    query = update.inline_query.query.split()

    # Log the received query
    logger.info(f'Received inline query: {query}')

    if len(query) >= 2 and query[0].isdigit() and query[1].isdigit():
        # Handle VIP invoices
        amount = int(query[0])
        days = int(query[1])

        # Log the extracted amount and subscription length
        logger.info(f'Creating VIP invoice for amount: {amount}, subscription length: {days} days')
        
        pay_url = f"{config.BOT_URL}?start=vip_{amount}_days_{days}"
        current_salesman = database.get_current_salesman()
        
        results = [InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title=f"Вип-чат • {amount} рублей",
            description=f"Длительность подписки: {days} дней | Продажник: {current_salesman}",
            input_message_content=InputTextMessageContent(config.INVOICE_TEXT_VIP.format(amount=amount,days=days)),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(config.INVOICE_PAY_BUTTON, url=pay_url)]
            ]),
            thumb_url="https://cdn-icons-png.flaticon.com/512/2982/2982899.png",
        )]
    else:
        # Handle regular invoices
        if not query or not query[0].isdigit():
            return

        amount = int(query[0])

        products = ['Express', 'Ordinar', 'Combo', 'Lesenka']

        results = []

        # Fetch current salesman from the database
        current_salesman = database.get_current_salesman()

        for product in products:
            # Log the extracted amount and product
            logger.info(f'Creating invoice for amount: {amount}, product: {product}')

            pay_url = f"{config.BOT_URL}?start=amount_{amount}_product_{product}"

            results.append(InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=f"Создать счет • {amount} рублей",
                description=f"Продукт: {product} | Продажник: {current_salesman}",  
                input_message_content=InputTextMessageContent(config.INVOICE_TEXT.format(amount=amount)),
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(config.INVOICE_PAY_BUTTON, url=pay_url)]
                ]),
                thumb_url="https://cdn-icons-png.flaticon.com/512/1117/1117142.png",
            ))

    # Send all results
    context.bot.answer_inline_query(update.inline_query.id, results, cache_time=0)




def handle_payment(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    # extract the invoice id from context.chat_data
    invoice_id = context.chat_data.get('invoice_id')

    # Check the invoice status in the database
    invoice_status = database.get_invoice_status(invoice_id)
    logger.info(f'Invoice status: {invoice_status}')

    if invoice_status == 'PAID' or invoice_status == 'DECLINED':
        # This invoice has already been paid, return a message to the user
        query.edit_message_text(text="Этот счет больше не действителен.")
    else:
        # The invoice is not paid, proceed with the payment process
        query.edit_message_text(text=config.ASK_SCREEN_TEXT,
                                reply_markup=InlineKeyboardMarkup([
                                    [InlineKeyboardButton(config.GO_BACK_TEXT, callback_data='go_back')]
                                ]))


def go_back(update: Update, context: CallbackContext) -> None:
    query = update.callback_query

    # Retrieve the amount and card number from the context attributes
    amount = context.chat_data.get('amount')
    card_number, bank = database.get_current_card_and_bank()
    
    query.edit_message_text(text=config.PAYMENT_MESSAGE.format(amount=amount, bank=bank, card_number=card_number),
                            reply_markup=InlineKeyboardMarkup([
                                [InlineKeyboardButton(config.I_PAID_TEXT, callback_data='i_paid'),
                                 InlineKeyboardButton(config.CONTACT_MANAGER_TEXT, url=config.MANAGER_URL)]
                            ]))


def handle_screenshot(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    
    logger.info(f"user: {user}")  # Log user
    logger.info(f"user.first_name: {user.first_name}")  # Log user.first_name
    logger.info(f"user.last_name: {user.last_name}")  # Log user.last_name

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

            context.bot.send_message(chat_id=update.effective_chat.id, text=config.CHECK_SCREEN_TEXT)

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
        
def generate_vip_invite_link(context: CallbackContext):
    chat_id = config.GROUP_ID  # replace with your VIP chat ID
    try:
        invite_link = context.bot.create_chat_invite_link(chat_id,member_limit=1)
        return invite_link.invite_link  # return the actual URL
    except Exception as e:
        print(f"Failed to export invite link for VIP chat: {e}")
        return None



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
    username = invoice_details["username"]
    subscription_length = invoice_details["subscription_length"]

    # Update the user's subscription
   
    subscription_updated = False
    if subscription_length is not None:
        subscription_updated = database.update_vip_subscription(user_id, subscription_length)

    if not subscription_updated:
        # If the user is not in the vip table yet, add them
        invite_link = generate_vip_invite_link(context)
        if invite_link is None:
            # Handle the error if the invite link could not be generated
            return
        if subscription_length is not None: # add this check here also if needed
            database.add_subscription(name, username, user_id, subscription_length)

    kick_date = database.get_kickdate(user_id)
    kick_date = kick_date.strftime("%d.%m.%Y")

    invite_link = generate_vip_invite_link(context)
    if invite_link is None:
        # Handle the error if the invite link could not be generated
        return

    # Determine which message to send based on product type
    if subscription_length is not None: 
        msg = config.VIP_INVITE_TEXT.format(kick_date=kick_date)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Вступить в Вип-чат", url=invite_link)]])
    else:
        msg = config.DEAL_DONE_TEXT.format(amount=amount)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(config.GET_SERVICE_TEXT, url=config.MANAGER_URL)]])
        
    context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)
    database.update_vip_status(user_id)

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
    username = invoice_details["username"]
    subscription_length = invoice_details["subscription_length"]

    subscription_updated = False
    if subscription_length is not None:
        subscription_updated = database.update_vip_subscription(user_id, subscription_length)

    if not subscription_updated:
        # If the user is not in the vip table yet, add them
        invite_link = generate_vip_invite_link(context)
        if invite_link is None:
            # Handle the error if the invite link could not be generated
            return
        if subscription_length is not None: # add this check here also if needed
            database.add_subscription(name, username, user_id, subscription_length)

    kick_date = database.get_kickdate(user_id)
    kick_date = kick_date.strftime("%d.%m.%Y")

    invite_link = generate_vip_invite_link(context)
    if invite_link is None:
        # Handle the error if the invite link could not be generated
        return

    # Determine which message to send based on product type
    if subscription_length is not None: 
        msg = config.VIP_INVITE_TEXT.format(kick_date=kick_date)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Вступить в Вип-чат", url=invite_link)]])
    else:
        msg = config.DEAL_DONE_TEXT.format(amount=amount)
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(config.GET_SERVICE_TEXT, url=config.MANAGER_URL)]])

    context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)
    database.update_vip_status(user_id)

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
        msg = config.SCREEN_DECLINED_TEXT
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(config.CONTACT_MANAGER_TEXT, url=config.MANAGER_URL)]])
        context.bot.send_message(chat_id=user_id, text=msg, reply_markup=keyboard)
        query.edit_message_text(text=f"Счет {invoice_id} был отклонен.")  # This will update the confirmation message to the decline message




def do_nothing(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)




