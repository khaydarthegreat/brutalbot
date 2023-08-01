import database

PAYMENT_MANAGERS = [236030478]
SALES_MANAGERS = [1499768187,56424449]
ANALYTICS = [56424449]  # Add your analytics group's user IDs here

BOT_TOKEN = "6327221288:AAEuqPM37vR62GLtcwb7bfk8ZAGJMg8HEr4"
MANAGER_URL = "https://t.me/BRUTAL_S"
BOT_URL = "https://t.me/brubetbot"
GROUP_ID = "-1001974358724"

def get_card_number():
    return database.get_current_card()  # Fetches the current card number from the database


def set_card_number(new_number):
    global _CARD_NUMBER
    _CARD_NUMBER = new_number

INVOICE_TEXT = """🧾 К оплате: {amount} рублей.

Для оплаты, жми кнопку внизу ⬇️"""

INVOICE_TEXT_VIP = """🧾 Вип-подписка  

Подписка на {days} дней.
К оплате: {amount} рублей.

Для оплаты, нажмите кнопку Оплатить ⬇️"""

INVOICE_PAY_BUTTON = "💳 Оплатить"
 

PAYMENT_MESSAGE = """
🧾 Новый счет. К оплате: {amount} рублей.  


Перевели деньги? Нажмите на кнопку Я оплатил внизу 👇 

Если не получилось или есть вопросы, нажми на кнопку 👨🏻 Помощь."""

VIP_PAYMENT_MESSAGE = """
🧾 Для получения доступа к VIP на {subscription_length} дней, необходимо оплатить {amount} рублей.

Для оплаты, переведите деньги на карту банка РФ

👉🏻 Реквизиты карты:
{bank} {card_number}

    
Перевели деньги? Нажмите на кнопку Я оплатил внизу 👇 

Если не получилось или есть вопросы, нажми на кнопку 👨🏻 Помощь. """


I_PAID_TEXT = "✅ Я оплатил"
CONTACT_MANAGER_TEXT = "👨🏻 Помощь""

ASK_SCREEN_TEXT = """📎🧾 Для проверки, отправьте скриншот перевода."""

CHECK_SCREEN_TEXT = """Скрин получен. 
            
🔎 Проверяем. """


GO_BACK_TEXT = "🔙 К реквизитам "

DEAL_DONE_TEXT = """ 👊🏼 Скриншот прошел проверку! 

👇🏻 Нажмите кнопку внизу и забирай свой прогноз! """

VIP_INVITE_TEXT = """👊🏼 Скриншот прошел проверку! 

⌛️ Дата окончания VIP-подписки: {kick_date}
Вы можете всегда запросить бота информацию о вашей подписке отправив ему комманду /myvip

Чтобы вступить в группу, нажмите кнопку внизу. 👇🏻 (❗️Важно! Ссылка одноразовая)
"""

GET_SERVICE_TEXT = "👉🏻 Забрать прогноз"

SCREEN_DECLINED_TEXT = """🚫 Бро, что-то пошло не так. 

Скриншот не прошел проверку. Если ты думаешь, что произошла ошибка, напиши менеджеру."""

BOT_CANCEL_TEXT = """❌ Действие было отменено. 

Для продолжения работы с ботом, отправьте комманду /start"""

MY_VIP_TEXT = """⌛️ Ваша подписка на Вип-Чат действительно до {}.

👉🏻 Количество дней до кноца подписки: {}.

↪️ Вы продлили свою подписку {} раз. """


