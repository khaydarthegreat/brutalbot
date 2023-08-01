from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import CallbackContext, MessageHandler, Filters, CallbackQueryHandler, ConversationHandler
import config
import database
import re

MANAGE_PAYMENTS, CHOOSE_EDIT, ADD_CARD_NUMBER, ADD_CARD_BANK, CONFIRM_ADD_CARD, DELETE_CARD, CONFIRM_DELETE_CARD, \
MANAGE_SALESMAN, CHOOSE_EDIT_SALESMAN, ADD_SALESMAN, CONFIRM_ADD_SALESMAN, DELETE_SALESMAN = range(2, 14)


def manage_payments(update: Update, context: CallbackContext):
    end_current_conversation(context)
    user_id = update.message.from_user.id
    if user_id in config.PAYMENT_MANAGERS:
        # Get all card numbers from the database
        cards = database.get_all_cards()

        # Convert each card number to a button
        buttons = [[InlineKeyboardButton(f"{card['card_number'][-4:]} {card['bank']}", callback_data=f"choose_{card['card_number']}")] for card in cards]

        # Fetch the current card number and bank
        current_card, current_bank = database.get_current_card_and_bank()

        update.message.reply_text(
            f"""🎛️ Меню управления картами для платежей. 
            
▶️ Активная карта:  {current_bank} {current_card} 

            
👉🏻 Если вы хотите изменить активную карту, выберите карту из списка.

📝 Если вы хотите добавить или удалить карту, нажмите Редактировать карты    
""",
            reply_markup=InlineKeyboardMarkup(buttons + [[InlineKeyboardButton('📝 Редактировать карты', callback_data='edit_cards')]])
        )
        context.user_data['current_state'] = MANAGE_PAYMENTS
        return MANAGE_PAYMENTS
    else:
        update.message.reply_text("❌ You don't have the necessary permissions.")
        return ConversationHandler.END


def edit_card(update: Update, context: CallbackContext):
    query = update.callback_query
    card_number = query.data.split("_")[1]
    
    # Set the selected card as the current card in the database
    database.set_current_card(card_number)

    query.answer()
    query.edit_message_text(f'Активная карта была изменена на : {card_number}')
    return ConversationHandler.END


def change_card_number(update: Update, context: CallbackContext):
    config.set_card_number(update.message.text.strip())
    update.message.reply_text(f'Активная карты бал изменена на: {config.get_card_number()}')
    return ConversationHandler.END

def cancel_manage_payments(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text('❌ Изменения не были внесены')
    return ConversationHandler.END

def choose_edit(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text('👉🏻 Выберите действие',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('➕ Добавить карту', callback_data='add_card')],
            [InlineKeyboardButton('🗑️ Удалить карту', callback_data='delete_card')]
        ])
    )
    return CHOOSE_EDIT

def confirm_add_card(update: Update, context: CallbackContext):
    context.user_data['bank'] = update.message.text.strip()
    update.message.reply_text(
        f"""Вы хотите добавить новую карту:

🔢 Номер: {context.user_data["card_number"]} 
🏦 Банк: {context.user_data["bank"]}. 

Сохранить?""", 
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('💾 Да', callback_data='yes_add')],
            [InlineKeyboardButton('❌ Нет', callback_data='no_add')]
        ])
    )
    return CONFIRM_ADD_CARD


def confirm_add_card_yes(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    database.add_card(context.user_data['card_number'], context.user_data['bank'])
    context.user_data['new_card_number'] = context.user_data['card_number']  # Store the new card number for possible usage
    query.edit_message_text(
        '✅ Карта была успешно добавлена. Хотите сделать ее текущей картой?',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('Да', callback_data='yes_set_current')],
            [InlineKeyboardButton('Нет', callback_data='no_set_current')]
        ])
    )
    return SET_CURRENT_CARD

SET_CURRENT_CARD = range(9)

...

def set_current_card_yes(update: Update, context: CallbackContext):
    query = update.callback_query
    database.set_current_card(context.user_data['new_card_number'])
    query.answer()
    query.edit_message_text('✅ Новая карта была выбрана активной.')
    return ConversationHandler.END

def set_current_card_no(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text('❌ Новая карта не была выбрана активной.')
    return ConversationHandler.END


def confirm_add_card_no(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text('❌ Вы отменили добавление новой карты.')
    return ConversationHandler.END

def add_card_number(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text('📝 Пожалуйста введите номер карты БЕЗ ПРОБЕЛОВ:')
    return ADD_CARD_NUMBER

def add_card_bank(update: Update, context: CallbackContext):
    context.user_data['card_number'] = update.message.text.strip()
    update.message.reply_text('📝 Пожалуйста введите название банка:')
    return ADD_CARD_BANK

def choose_card_to_delete(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    # Get all card numbers from the database
    cards = database.get_all_cards()

    # Convert each card number to a button
    buttons = [[InlineKeyboardButton(f"{card['card_number'][-4:]} {card['bank']}", callback_data=f"delete_{card['card_number']}")] for card in cards]

    query.edit_message_text(
        "👉🏻 Выберите карту для удаления:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return DELETE_CARD


def delete_card(update: Update, context: CallbackContext):
    query = update.callback_query
    card_number = query.data.split("_")[1]

    # Delete the card from the database
    database.delete_card(card_number)

    query.answer()
    query.edit_message_text(f"🚮 Карта номер {card_number} была успешно удалена.")
    return ConversationHandler.END


def manage_salesman(update: Update, context: CallbackContext):
    end_current_conversation(context)
    user_id = update.message.from_user.id
    if user_id in config.SALES_MANAGERS: 
        salesmen = database.get_all_salesmen()

        buttons = [[InlineKeyboardButton(salesman, callback_data=f"choose_{salesman}")] for salesman in salesmen]
        current_salesman = database.get_current_salesman()

        update.message.reply_text(
            f"""▶️ Текущая смена: {current_salesman} 

👉🏻 Если вы хотите поменять продажника на смену, выберите из списка продажников.

📝 Если вы хотите изменить список продажников, нажмите кнопку Изменить список продажников;
""",
            reply_markup=InlineKeyboardMarkup(buttons + [[InlineKeyboardButton('📝 Изменить список продажников', callback_data='edit_salesmen')]])
        )
        context.user_data['current_state'] = MANAGE_SALESMAN
        return MANAGE_SALESMAN
    else:
        update.message.reply_text("❌ У вас нет необходимого доступа. Выберите другое действие.")
        return ConversationHandler.END


def edit_salesman(update: Update, context: CallbackContext):
    query = update.callback_query
    salesman_name = query.data.split("_")[1]
    
    # Set the selected salesman as the current active salesman in the database
    database.set_current_salesman(salesman_name)

    query.answer()
    query.edit_message_text(f'✅ Текущий продажник был изменен на : {salesman_name}')
    return ConversationHandler.END


def choose_edit_salesman(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text('👉🏻 Выберите действие',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('➕ Добавить продажника', callback_data='add_salesman')],
            [InlineKeyboardButton('🗑️ Удалить продажника', callback_data='delete_salesman')]
        ])
    )
    return CHOOSE_EDIT_SALESMAN

def add_salesman(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text('📝 Укажите имя продажника:')
    return ADD_SALESMAN

def confirm_add_salesman(update: Update, context: CallbackContext):
    context.user_data['salesman'] = update.message.text.strip()
    update.message.reply_text(
        f"""Вы хотите добавить нового продажника:

👤 Имя: {context.user_data["salesman"]} 

Сохранить?""", 
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton('💾 Да', callback_data='yes_add_salesman')],
            [InlineKeyboardButton('❌ Нет', callback_data='no_add_salesman')]
        ])
    )
    return CONFIRM_ADD_SALESMAN

def cancel_manage_salesman(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text('❌ Изменения не были внесены')
    return ConversationHandler.END

def confirm_add_salesman_yes(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    database.add_salesman(context.user_data['salesman'])
    query.edit_message_text(
        '✅ Продажник был успешно добавлен в список.',
    )
    return ConversationHandler.END

def confirm_add_salesman_no(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text('❌ Изменения не были внесены.')
    return ConversationHandler.END

def delete_salesman(update: Update, context: CallbackContext):
    query = update.callback_query
    salesman = query.data.split("_")[1]
    database.delete_salesman(salesman)
    query.answer()
    query.edit_message_text(f"🚮 Продажник {salesman} был удален из списка.")
    return ConversationHandler.END

def end_current_conversation(context: CallbackContext):
    if 'current_state' in context.user_data:
        current_state = context.user_data['current_state']
        if current_state == MANAGE_PAYMENTS:
            context.user_data.pop('current_state', None)
            return ConversationHandler.END
        elif current_state == MANAGE_SALESMAN:
            context.user_data.pop('current_state', None)
            return ConversationHandler.END


conv_handler_payments_and_salesman = ConversationHandler(
    entry_points=[
        MessageHandler(Filters.regex('^Manage payments$'), manage_payments),
        MessageHandler(Filters.regex('^Manage Salesman$'), manage_salesman)
    ],
    states={
        MANAGE_PAYMENTS: [
            CallbackQueryHandler(edit_card, pattern='^choose_'),
            CallbackQueryHandler(choose_edit, pattern='^edit_cards$'),
            CallbackQueryHandler(cancel_manage_payments, pattern='^cancel$')
        ],
        CHOOSE_EDIT: [
            CallbackQueryHandler(add_card_number, pattern='add_card'),
            CallbackQueryHandler(choose_card_to_delete, pattern='delete_card')
        ],
        ADD_CARD_NUMBER: [
            MessageHandler(Filters.text & ~Filters.command, add_card_bank)
        ],
        ADD_CARD_BANK: [
            MessageHandler(Filters.text & ~Filters.command, confirm_add_card)
        ],
        CONFIRM_ADD_CARD: [
            CallbackQueryHandler(confirm_add_card_yes, pattern='yes_add'),
            CallbackQueryHandler(confirm_add_card_no, pattern='no_add')    
        ],
        DELETE_CARD: [
            CallbackQueryHandler(delete_card, pattern='^delete_'),
        ],
        SET_CURRENT_CARD: [
            CallbackQueryHandler(set_current_card_yes, pattern='^yes_set_current$'),
            CallbackQueryHandler(set_current_card_no, pattern='^no_set_current$'),
        ],
        MANAGE_SALESMAN: [
            CallbackQueryHandler(edit_salesman, pattern='^choose_'),
            CallbackQueryHandler(choose_edit_salesman, pattern='^edit_salesmen$'),
            CallbackQueryHandler(cancel_manage_salesman, pattern='^cancel$')
        ],
        CHOOSE_EDIT_SALESMAN: [
            CallbackQueryHandler(add_salesman, pattern='add_salesman'),
            CallbackQueryHandler(delete_salesman, pattern='^delete_')
        ],
        ADD_SALESMAN: [
            MessageHandler(Filters.text & ~Filters.command, confirm_add_salesman)
        ],
        CONFIRM_ADD_SALESMAN: [
            CallbackQueryHandler(confirm_add_salesman_yes, pattern='^yes_add_salesman$'),
            CallbackQueryHandler(confirm_add_salesman_no, pattern='^no_add_salesman$')   
        ],
    },
    fallbacks=[
        CallbackQueryHandler(cancel_manage_payments),
        CallbackQueryHandler(cancel_manage_salesman),
        MessageHandler(Filters.all, lambda u, c: ConversationHandler.END)
    ]
)
