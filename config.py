import database

PAYMENT_MANAGERS = [236030478]
SALES_MANAGERS = [5709730059,56424449]
ANALYTICS = [56424449]  # Add your analytics group's user IDs here


def get_card_number():
    return database.get_current_card()  # Fetches the current card number from the database


def set_card_number(new_number):
    global _CARD_NUMBER
    _CARD_NUMBER = new_number
