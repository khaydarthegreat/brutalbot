import os
import psycopg2
from psycopg2 import sql
from datetime import datetime, timedelta
import time
import pytz
import logging

# Set up logging at the top of your file
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


DATABASE_URL = os.environ['DATABASE_URL']  # provided by Heroku

def create_connection():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    cur = conn.cursor()
    cur.execute("SET TIMEZONE='Europe/Moscow';") 

    # Fetch and print the current timezone setting
    cur.execute("SHOW timezone;")
    tz_setting = cur.fetchone()[0]
    print(f"Database timezone setting: {tz_setting}")

    return conn

def close_connection(conn):
    conn.close()

def create_table():
    conn = create_connection()
    cur = conn.cursor()

    # Create salesman table
    cur.execute(sql.SQL("""CREATE TABLE IF NOT EXISTS salesman (
                        id SERIAL PRIMARY KEY, 
                        name TEXT NOT NULL,
                        is_current BOOLEAN DEFAULT FALSE)"""))

    # Create invoices table
    cur.execute(sql.SQL("""CREATE TABLE IF NOT EXISTS invoices (
                        invoice_id INTEGER PRIMARY KEY, 
                        amount INTEGER,
                        name TEXT, 
                        username TEXT, 
                        user_id BIGINT, 
                        product TEXT, 
                        status TEXT, 
                        type TEXT,
                        date TIMESTAMPTZ, 
                        screenshot_id INTEGER, 
                        salesman TEXT,
                        subscription_length INTEGER)""")) 

    # Create cards table
    cur.execute(sql.SQL("""
        CREATE TABLE IF NOT EXISTS cards (
            id SERIAL PRIMARY KEY,
            card_number VARCHAR(255),
            bank VARCHAR(255),
            is_current BOOLEAN DEFAULT FALSE
        )
    """))


    cur.execute(sql.SQL("""
    CREATE TABLE IF NOT EXISTS vip (
        name TEXT,
        username TEXT,
        user_id BIGINT PRIMARY KEY,
        duration INTEGER,
        kick_date TIMESTAMP WITH TIME ZONE,
        paid BOOLEAN DEFAULT FALSE,
        renewal_times INTEGER DEFAULT 0
    );
    """))

    
    # Save (commit) the changes and close the connection
    conn.commit()
    close_connection(conn)


def add_invoice(invoice_id, amount, product, user_id, name, username, current_salesman, subscription_length=None):
    conn = create_connection()

    date = datetime.now(pytz.timezone('Europe/Moscow'))
    
    cur = conn.cursor()

    cur.execute(sql.SQL("INSERT INTO invoices (invoice_id, amount, product, user_id, name, username, salesman, date, subscription_length) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"), 
                (invoice_id, amount, product, user_id, name, username, current_salesman, date, subscription_length))

    conn.commit()
    close_connection(conn)


def add_subscription(name, username, user_id, subscription_length):
    logger.info(f"add_subscription called with parameters name={name}, username={username}, user_id={user_id}, subscription_length={subscription_length}")
    conn = create_connection()

    now = datetime.now(pytz.timezone('Europe/Moscow')) 
    kick_date = now + timedelta(days=int(subscription_length))
    logger.info(f'Kick date calculated: {kick_date}')
        
    cur = conn.cursor()

    cur.execute(sql.SQL("INSERT INTO vip (name, username, user_id, duration, kick_date) VALUES (%s, %s, %s, %s, %s)"),
            (name, username, user_id, subscription_length, kick_date))


    conn.commit()
    close_connection(conn)


def get_latest_invoice_id():
    conn = create_connection()
    cur = conn.cursor()

    cur.execute(sql.SQL("SELECT MAX(invoice_id) FROM invoices"))
    result = cur.fetchone()

    close_connection(conn)

    # Return the maximum invoice_id if it exists, else return 0
    return result[0] if result[0] is not None else 0


    # Return the maximum invoice_id if it exists, else return 0
    return result[0] if result[0] is not None else 0

def get_users_to_kick():
    conn = create_connection()
    cur = conn.cursor()

    cur.execute(
        "SELECT user_id FROM vip WHERE kick_date <= NOW()"
    )

    # Fetch all the rows
    rows = cur.fetchall()

    # Close communication with the database
    cur.close()
    conn.close()

    return [row[0] for row in rows]


def get_subscription_duration(user_id):
    conn = create_connection()
    cur = conn.cursor()

    # Execute a query
    cur.execute(
        "SELECT duration FROM vip WHERE user_id = %s", (user_id,)
    )

    # Fetch the first row
    row = cur.fetchone()

    # Close communication with the database
    cur.close()
    conn.close()

    if row:
        # If a row was found, return the duration
        return row[0]
    else:
        # If no row was found, return None
        return None

def get_invite_link(user_id):
    conn = create_connection()
    cur = conn.cursor()

    # Execute a query
    cur.execute(
        "SELECT link FROM vip WHERE user_id = %s", (user_id,)
    )

    result = cur.fetchone()

    close_connection(conn)

    if result is not None:
        return result[0]  # Return the amount
    else:
        return None  # or some default value



def check_invoice_id(invoice_id):
    conn = create_connection()
    cur = conn.cursor()
    
    cur.execute(sql.SQL('SELECT * FROM invoices WHERE invoice_id=%s'), (invoice_id,))
    
    result = cur.fetchone()
    close_connection(conn)

    logger.info(f'Checking existence of invoice_id={invoice_id} in database. Found? {"Yes" if result else "No"}')

    if result is None:
        return False  # The invoice_id does not exist in the database
    else:
        return True  # The invoice_id exists in the database


def add_customer_details():
    conn = create_connection()
    cur = conn.cursor()

    cur.execute(sql.SQL("ALTER TABLE invoices ADD COLUMN IF NOT EXISTS name TEXT, ADD COLUMN IF NOT EXISTS username TEXT, ADD COLUMN IF NOT EXISTS user_id INTEGER"))
    
    conn.commit()
    close_connection(conn)
    
    return result is not None

def get_kickdate(user_id):
    conn = create_connection()

    cur = conn.cursor()
    
    cur.execute("SELECT kick_date FROM vip WHERE user_id = %s", (user_id,))
    result = cur.fetchone()

    if result is not None:
        return result[0]
    else:
        return None


def update_invoice_date(invoice_id):
    conn = create_connection()
    cur = conn.cursor()

    # Get current time in UTC+3 timezone
    current_time = datetime.now(pytz.timezone('Europe/Moscow'))  # Moscow is in the UTC+3 timezone

    # Update the Date column for this invoice
    cur.execute(sql.SQL("UPDATE invoices SET Date=%s WHERE invoice_id=%s"), (current_time, invoice_id))

    conn.commit()
    close_connection(conn)


def get_invoice_amount(invoice_id):
    conn = create_connection()
    cur = conn.cursor()
    
    cur.execute(sql.SQL('SELECT amount FROM invoices WHERE invoice_id=%s'), (invoice_id,))
    result = cur.fetchone()

    close_connection(conn)

    if result is not None:
        return result[0]  # Return the amount
    else:
        return None  # or some default value


def get_last_invoice_id_for_user(user_id):
    conn = create_connection()
    cur = conn.cursor()

    cur.execute(sql.SQL('SELECT invoice_id FROM invoices WHERE user_id=%s ORDER BY date DESC LIMIT 1'), (user_id,))

    result = cur.fetchone()

    close_connection(conn)

    return result[0] if result else None


def get_invoice_details(invoice_id):
    logger.info("Fetching invoice details for invoice_id: %s", invoice_id)

    conn = create_connection()
    cur = conn.cursor()

    cur.execute(sql.SQL('SELECT user_id, invoice_id, amount, product, name, username, subscription_length FROM invoices WHERE invoice_id=%s'), (invoice_id,))
    result = cur.fetchone()

    close_connection(conn)
    
    if result is None:
        logger.warning("No result found for invoice_id: %s", invoice_id)
        return None
    else:
        invoice_details = {
            "user_id": result[0],
            "invoice_id": result[1],
            "amount": result[2],
            "product": result[3],
            "name": result[4],
            "username": result[5],
            "subscription_length": result[6]
        }

        logger.info("Fetched invoice details: %s", invoice_details)
        return invoice_details
        

def update_vip_status(user_id):
    conn = create_connection()
    cur = conn.cursor()

    # Update status
    cur.execute("UPDATE vip SET paid = true WHERE user_id = %s", (user_id,))

    conn.commit()
    close_connection(conn)



def update_invoice_status(invoice_id: str, new_status: str) -> None:
    conn = create_connection()
    cur = conn.cursor()

    # Update status
    cur.execute(sql.SQL("UPDATE invoices SET status = %s WHERE invoice_id = %s"),
                (new_status, invoice_id))

    conn.commit()
    close_connection(conn)


def generate_sales_book_report(start_date, end_date):
    conn = create_connection()
    cur = conn.cursor()

    query = sql.SQL("""
        SELECT invoice_id, amount, date, name, username, user_id, type
        FROM invoices
        WHERE status = 'PAID'
        AND date BETWEEN %s AND %s
    """)

    cur.execute(query, (start_date, end_date))

    result_set = cur.fetchall()

    # Log the result set
    logger.info(f'Result set: {result_set}')

    close_connection(conn)
    
    logger.info(f'Result set: {result_set}')  # <--- Log the result set.

    if result_set:
        formatted_report = []

        for row in result_set:
            invoice_id, amount, date, name, username, user_id, type = row
            # Convert the date to your desired format.
            formatted_date = date.strftime("%Y-%m-%d %H:%M")
            formatted_report.append([invoice_id, amount, formatted_date, name, username, user_id, type])

        return formatted_report
    else:
        return None


def generate_clients_book_report(start_date, end_date):
    logger.info(f"Querying data for generate_clients_book_report for range: {start_date} - {end_date}")
    
    conn = create_connection()
    cur = conn.cursor()

    query = sql.SQL("""
        SELECT user_id, username, name, MIN(date) as first_deal_date, MAX(date) as last_deal_date, COUNT(*) as total_deals, SUM(amount) as total_amount
        FROM invoices
        WHERE status = 'PAID'
        AND date BETWEEN %s AND %s
        GROUP BY user_id, username, name
    """)

    logger.info(f"Executing SQL: {query}")

    cur.execute(query, (start_date, end_date))

    result_set = cur.fetchall()
   
    logger.info("Start date: %s", start_date)
    logger.info("End date: %s", end_date)
    logger.info("Result set: %s", result_set)

    
    close_connection(conn)

    if result_set:
        formatted_report = []

        for row in result_set:
            user_id, username, name, first_deal_date, last_deal_date, total_deals, total_amount = row
            # Convert the date to your desired format.
            formatted_first_deal_date = first_deal_date.strftime("%Y-%m-%d %H:%M")
            formatted_last_deal_date = last_deal_date.strftime("%Y-%m-%d %H:%M")
            formatted_report.append([user_id, username, name, formatted_first_deal_date, formatted_last_deal_date, total_deals, total_amount])

        return formatted_report
    else:
        return None


def add_screenshot_id(invoice_id, message_id):
    conn = create_connection()

    cur = conn.cursor()

    cur.execute(
        """
        UPDATE invoices
        SET screenshot_id = %s
        WHERE invoice_id = %s
        """, 
        (message_id, invoice_id)
    )

    conn.commit()
    cur.close()
    conn.close()

def get_screenshot_id(invoice_id):
    conn = create_connection()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT screenshot_id
        FROM invoices
        WHERE invoice_id = %s
        """, 
        (invoice_id,)
    )

    result = cur.fetchone()

    cur.close()
    conn.close()

    if result is not None:
        return result[0]  # return the message id
    else:
        return None

def get_invoice_status(invoice_id):
    conn = create_connection()

    cur = conn.cursor()
    
    cur.execute("SELECT status FROM invoices WHERE invoice_id = %s", (invoice_id,))
    result = cur.fetchone()

    if result is not None:
        return result[0]
    else:
        return None

def get_invoice_by_invite_link(invite_link):
    try:
        conn = create_connection()
        cur = conn.cursor()
        
        query = """
        SELECT * FROM invoices
        WHERE invite_link = %s;
        """
    
        cur.execute(query, (invite_link,))

        result = cur.fetchone()
 
        cur.close()
        conn.close()
     
        return result
    except Exception as e:
        print(f"Error getting invoice by invite link: {e}")
        return None


def get_total_income(start_date, end_date):
    conn = create_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT SUM(amount) 
        FROM invoices 
        WHERE date BETWEEN %s AND %s AND status = 'PAID'
    """, (start_date, end_date))
    
    result = cur.fetchone()
    close_connection(conn)
    
    return result[0] if result[0] is not None else 0


def get_deal_quantity(start_date, end_date):
    conn = create_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COUNT(*) 
        FROM invoices 
        WHERE date BETWEEN %s AND %s AND status = 'PAID'
    """, (start_date, end_date))
    
    result = cur.fetchone()
    close_connection(conn)
    
    return result[0] if result[0] is not None else 0

def get_unique_customers(start_date, end_date):
    conn = create_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COUNT(DISTINCT user_id) 
        FROM invoices 
        WHERE date BETWEEN %s AND %s AND status = 'PAID'
    """, (start_date, end_date))
    
    result = cur.fetchone()
    close_connection(conn)
    
    return result[0] if result[0] is not None else 0

def get_new_customers(start_date, end_date):
    conn = create_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT COUNT(*) 
        FROM (
            SELECT user_id, MIN(date) as first_purchase_date 
            FROM invoices 
            WHERE status = 'PAID' 
            GROUP BY user_id
        ) AS user_first_purchases
        WHERE first_purchase_date BETWEEN %s AND %s
    """, (start_date, end_date))
    
    result = cur.fetchone()
    close_connection(conn)
    
    return result[0] if result[0] is not None else 0

def get_income_from_new_customers(start_date, end_date):
    conn = create_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT SUM(invoices.amount) 
        FROM invoices
        INNER JOIN (
            SELECT user_id, MIN(date) as first_purchase_date 
            FROM invoices 
            WHERE status = 'PAID' 
            GROUP BY user_id
        ) AS user_first_purchases ON invoices.user_id = user_first_purchases.user_id
        WHERE first_purchase_date BETWEEN %s AND %s AND status = 'PAID'
    """, (start_date, end_date))
    
    result = cur.fetchone()
    close_connection(conn)
    
    return result[0] if result[0] is not None else 0

def add_card(card_number: str, bank: str):
    conn = create_connection()
    cur = conn.cursor()

    # Add the new card number to the table and set it as the current card
    cur.execute(sql.SQL("""
        INSERT INTO cards (card_number, bank, is_current)
        VALUES (%s, %s, false)
    """), (card_number, bank))

    # Save (commit) the changes and close the connection
    conn.commit()
    close_connection(conn)


def get_current_card_and_bank():
    conn = create_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT card_number, bank FROM cards WHERE is_current = TRUE LIMIT 1;")
    current_card_and_bank = cur.fetchone()
    close_connection(conn)

    if current_card_and_bank is not None:
        return current_card_and_bank  # Fetch the card number and bank from the tuple
    else:
        return None, None  # Return None if there is no current card


def check_vip_user(user_id):
    conn = create_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM vip WHERE user_id = %s", (user_id,))
    result = cur.fetchone()[0]

    close_connection(conn)
    
    return result > 0  # Returns True if user is in vip table, False otherwise

def update_vip_subscription(user_id, subscription_length):
    conn = create_connection()
    cur = conn.cursor()

    # Get current date in the UTC timezone
    current_date = datetime.now(pytz.timezone('Europe/Moscow'))

    # Check if user is already in the table
    cur.execute(sql.SQL("SELECT duration, kick_date, renewal_times FROM vip WHERE user_id = %s"), (user_id,))

    row = cur.fetchone()

    if row is None:  # If the user is not in the table yet, return False
        return False

    current_duration, current_kick_date, current_renewal_times = row[0], row[1], row[2]

    # If the current_kick_date is in the future, use it as the starting point
    if current_kick_date > current_date:
        base_date = current_kick_date
    else:  # Otherwise, use the current date as the starting point
        base_date = current_date

    # Calculate new duration, kick_date and renewal times
    updated_duration = current_duration + subscription_length
    updated_kick_date = base_date + timedelta(days=subscription_length)
    updated_renewal_times = current_renewal_times + 1  # Increment renewal times

    # Update the vip table
    cur.execute(sql.SQL("""
        UPDATE vip 
        SET duration = %s, kick_date = %s, renewal_times = %s
        WHERE user_id = %s
        """), (updated_duration, updated_kick_date, updated_renewal_times, user_id))

    conn.commit()
    close_connection(conn)
    
    return True  # If the user's subscription was successfully updated, return True


def get_vip_subscription(user_id):
    conn = create_connection()
    cur = conn.cursor()

    # Fetch user's subscription details
    cur.execute(sql.SQL("SELECT kick_date, renewal_times FROM vip WHERE user_id = %s"), (user_id,))

    row = cur.fetchone()

    if row is None:  # If the user is not in the table yet, return None
        return None

    kick_date, renewal_times = row[0], row[1]

    # Close the connection
    close_connection(conn)

    # Return subscription details
    return {'kick_date': kick_date, 'renewal_times': renewal_times}



def set_current_card(card_number: str):
    conn = create_connection()
    cur = conn.cursor()

    # Set all cards to not current
    cur.execute(sql.SQL("""
        UPDATE cards SET is_current = false
    """))

    # Set the specified card as current
    cur.execute(sql.SQL("""
        UPDATE cards SET is_current = true
        WHERE card_number = %s
    """), (card_number,))

    # Save (commit) the changes and close the connection
    conn.commit()
    close_connection(conn)

def get_all_cards():
    conn = create_connection()
    cur = conn.cursor()

    # Query all card numbers and their associated banks from the cards table
    cur.execute("SELECT card_number, bank FROM cards")

    # Fetch all results and convert them to a list of dictionaries
    cards = [{'card_number': row[0], 'bank': row[1]} for row in cur.fetchall()]

    close_connection(conn)
    return cards

def delete_card(card_number):
    conn = create_connection()
    cur = conn.cursor()

    # Delete the card number from the table
    cur.execute(sql.SQL("DELETE FROM cards WHERE card_number = %s"), (card_number,))

    # Save (commit) the changes and close the connection
    conn.commit()
    close_connection(conn)


def update_invoice_type(invoice_id, type):
    conn = create_connection()
    cur = conn.cursor()

    cur.execute(sql.SQL("UPDATE invoices SET type = %s WHERE invoice_id = %s"), (type, invoice_id))

    conn.commit()
    close_connection(conn)

           

def get_incoming_deal_quantity(start_date, end_date):
    conn = create_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM invoices WHERE status = 'PAID' AND type = 'Incoming' AND date BETWEEN %s AND %s", (start_date, end_date))
    incoming_deal_quantity = cur.fetchone()[0]

    close_connection(conn)
    
    return incoming_deal_quantity

def get_outgoing_deal_quantity(start_date, end_date):
    conn = create_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM invoices WHERE status = 'PAID' AND type = 'Outgoing' AND date BETWEEN %s AND %s", (start_date, end_date))
    outgoing_deal_quantity = cur.fetchone()[0]

    close_connection(conn)
    
    return outgoing_deal_quantity


def get_total_amount_incoming(start_date, end_date):
    conn = create_connection()
    cur = conn.cursor()

    cur.execute("SELECT SUM(amount) FROM invoices WHERE status = 'PAID' AND type = 'Incoming' AND date BETWEEN %s AND %s", (start_date, end_date))
    total_amount_incoming = cur.fetchone()[0]

    close_connection(conn)
    
    return total_amount_incoming if total_amount_incoming else 0

def get_total_amount_outgoing(start_date, end_date):
    conn = create_connection()
    cur = conn.cursor()

    cur.execute("SELECT SUM(amount) FROM invoices WHERE status = 'PAID' AND type = 'Outgoing' AND date BETWEEN %s AND %s", (start_date, end_date))
    total_amount_outgoing = cur.fetchone()[0]

    close_connection(conn)
    
    return total_amount_outgoing if total_amount_outgoing else 0

    
def get_average_deal_amount(start_date, end_date):
    conn = create_connection()
    cur = conn.cursor()

    cur.execute("SELECT AVG(amount) FROM invoices WHERE status = 'PAID' AND date BETWEEN %s AND %s", (start_date, end_date))
    average_deal_amount = cur.fetchone()[0]

    close_connection(conn)
    
    return round(average_deal_amount, 2) if average_deal_amount else 0

def add_salesman(name):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO salesman (name) VALUES (%s)", (name,))
    conn.commit()
    close_connection(conn)

def get_current_salesman():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM salesman WHERE is_current = TRUE")
    current_salesman = cur.fetchone()
    close_connection(conn)
    return current_salesman

def set_current_salesman(name):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("UPDATE salesman SET is_current = FALSE WHERE is_current = TRUE")
    cur.execute("UPDATE salesman SET is_current = TRUE WHERE name = %s", (name,))
    conn.commit()
    close_connection(conn)

def get_all_salesmen():
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("SELECT name FROM salesman")
    salesmen_tuples = cur.fetchall()
    salesmen = [s[0] for s in salesmen_tuples]  # Extract names from tuples
    close_connection(conn)
    return salesmen


def set_invoice_salesman(invoice_id, salesman_name):
    conn = create_connection()
    cur = conn.cursor()
    cur.execute("UPDATE invoices SET salesman = %s WHERE invoice_id = %s", (salesman_name, invoice_id,))
    conn.commit()
    close_connection(conn)

def delete_salesman(salesman_name):
    conn = create_connection()
    cur = conn.cursor()

    # Delete the salesman from the table
    cur.execute(sql.SQL("DELETE FROM salesman WHERE name = %s"), (salesman_name,))

    # Save (commit) the changes and close the connection
    conn.commit()
    close_connection(conn)
