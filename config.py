import database

PAYMENT_MANAGERS = [236030478]
SALES_MANAGERS = [1499768187,56424449]
ANALYTICS = [56424449]  # Add your analytics group's user IDs here

BOT_TOKEN = "6327221288:AAEuqPM37vR62GLtcwb7bfk8ZAGJMg8HEr4"
MANAGER_URL = "https://t.me/BRUTAL_S"
BOT_URL = "https://t.me/brubetbot"




def get_card_number():
    return database.get_current_card()  # Fetches the current card number from the database


def set_card_number(new_number):
    global _CARD_NUMBER
    _CARD_NUMBER = new_number
