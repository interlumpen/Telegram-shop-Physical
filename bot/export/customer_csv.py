import csv
from pathlib import Path
from typing import Optional, Dict
from decimal import Decimal
import threading

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from bot.database.main import Database
from bot.database.models.main import CustomerInfo
from .custom_logging import log_customer_info_change
from bot.config import EnvKeys

# CSV file path
CUSTOMER_CSV_PATH = Path("logs/customer_list.csv")
CSV_HEADERS = [
    'Telegram ID',
    'Username',
    'Phone Number',
    'Delivery Address',
    'Delivery Note',
    'Client Total Spendings',
    'Completed Orders Total',
    'Client Bonus Balance'
]

# Lock for thread-safe CSV operations
_csv_lock = threading.Lock()

# Characters that trigger formula evaluation in Excel / LibreOffice / Google Sheets.
_CSV_INJECTION_PREFIXES = ('=', '+', '-', '@', '\t', '\r')


def _sanitize_cell(value) -> str:
    """Neutralize CSV/formula injection in a cell.

    Customer-controlled free text (username, phone, address, note) can start with
    '=', '+', '-', '@' etc. and would be executed as a formula when the export is
    opened in a spreadsheet. Prefix such values with a single quote so they are
    treated as text. Idempotent: a leading quote is not a trigger character.
    """
    if value is None:
        return ''
    text = str(value)
    if text and text[0] in _CSV_INJECTION_PREFIXES:
        return "'" + text
    return text


def initialize_customer_csv():
    """Initialize the customer CSV file with headers if it doesn't exist"""
    CUSTOMER_CSV_PATH.parent.mkdir(exist_ok=True)

    if not CUSTOMER_CSV_PATH.exists():
        with _csv_lock:
            with open(CUSTOMER_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADERS)


def get_customer_info(telegram_id: int) -> Optional[Dict]:
    """
    Get customer information from database

    Args:
        telegram_id: Telegram ID

    Returns:
        Dictionary with customer info or None
    """
    with Database().session() as session:
        customer = session.query(CustomerInfo).filter_by(telegram_id=telegram_id).first()

        if not customer:
            return None

        return {
            'telegram_id': customer.telegram_id,
            'phone_number': customer.phone_number,
            'delivery_address': customer.delivery_address,
            'delivery_note': customer.delivery_note,
            'total_spendings': float(customer.total_spendings),
            'completed_orders_count': customer.completed_orders_count,
            'bonus_balance': float(customer.bonus_balance)
        }


def get_username_by_telegram_id(telegram_id: int) -> Optional[str]:
    """
    Get username from CSV file by telegram_id

    Args:
        telegram_id: Telegram ID

    Returns:
        Username from CSV or None if not found or empty
    """
    if not CUSTOMER_CSV_PATH.exists():
        return None

    with _csv_lock:
        try:
            with open(CUSTOMER_CSV_PATH, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('Telegram ID') == str(telegram_id):
                        username = row.get('Username', '').strip()
                        # Return username only if it's not empty and not a fallback pattern
                        if username and not username.startswith('user_'):
                            return username
                        return None
        except Exception:
            return None

    return None


def create_or_update_customer_info(telegram_id: int, username: str,
                                   phone_number: str = None,
                                   delivery_address: str = None,
                                   delivery_note: str = None) -> bool:
    """
    Create or update customer information in database

    Args:
        telegram_id: Telegram ID
        username: Telegram username
        phone_number: Phone number
        delivery_address: Delivery address
        delivery_note: Delivery note

    Returns:
        True if created, False if updated
    """
    with Database().session() as session:
        customer = session.query(CustomerInfo).filter_by(telegram_id=telegram_id).first()

        if customer:
            # Update existing customer
            is_new = False

            # Track changes for logging
            changes = []

            if phone_number and customer.phone_number != phone_number:
                old_phone = customer.phone_number or "NONE"
                changes.append(('PHONE', old_phone, phone_number))
                customer.phone_number = phone_number

            if delivery_address and customer.delivery_address != delivery_address:
                old_address = customer.delivery_address or "NONE"
                changes.append(('ADDRESS', old_address, delivery_address))
                customer.delivery_address = delivery_address

            if delivery_note is not None and customer.delivery_note != delivery_note:
                old_note = customer.delivery_note or "NONE"
                changes.append(('NOTE', old_note, delivery_note))
                customer.delivery_note = delivery_note

            session.commit()

            # Log changes
            for attr, old_val, new_val in changes:
                log_customer_info_change(telegram_id, username, attr, old_val, new_val)

        else:
            # Create new customer
            is_new = True
            customer = CustomerInfo(
                telegram_id=telegram_id,
                phone_number=phone_number,
                delivery_address=delivery_address,
                delivery_note=delivery_note
            )
            session.add(customer)
            session.commit()

    # Sync to CSV
    sync_customer_to_csv(telegram_id, username)

    return is_new


def sync_customer_to_csv(telegram_id: int, username: str):
    """
    Sync a customer's information to the CSV file

    Args:
        telegram_id: Telegram ID
        username: Telegram username
    """
    initialize_customer_csv()

    customer = get_customer_info(telegram_id)
    if not customer:
        return

    with _csv_lock:
        # Read existing CSV
        rows = []
        customer_exists = False

        with open(CUSTOMER_CSV_PATH, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Search by Telegram ID instead of Username
                if row.get('Telegram ID') == str(telegram_id):
                    # Update existing row (including username if it changed)
                    row['Telegram ID'] = str(telegram_id)
                    row['Username'] = _sanitize_cell(username)
                    row['Phone Number'] = _sanitize_cell(customer['phone_number'])
                    row['Delivery Address'] = _sanitize_cell(customer['delivery_address'])
                    row['Delivery Note'] = _sanitize_cell(customer['delivery_note'])
                    row['Client Total Spendings'] = f"{customer['total_spendings']:.2f}"
                    row['Completed Orders Total'] = str(customer['completed_orders_count'])
                    row['Client Bonus Balance'] = f"{customer['bonus_balance']:.2f}"
                    customer_exists = True
                rows.append(row)

        # Add new customer if doesn't exist
        if not customer_exists:
            rows.append({
                'Telegram ID': str(telegram_id),
                'Username': _sanitize_cell(username),
                'Phone Number': _sanitize_cell(customer['phone_number']),
                'Delivery Address': _sanitize_cell(customer['delivery_address']),
                'Delivery Note': _sanitize_cell(customer['delivery_note']),
                'Client Total Spendings': f"{customer['total_spendings']:.2f}",
                'Completed Orders Total': str(customer['completed_orders_count']),
                'Client Bonus Balance': f"{customer['bonus_balance']:.2f}"
            })

        # Write back to CSV
        with open(CUSTOMER_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            writer.writeheader()
            writer.writerows(rows)


def update_customer_spendings(telegram_id: int, username: str, amount: Decimal):
    """
    Update customer's total spendings

    Args:
        telegram_id: Telegram ID
        username: Telegram username
        amount: Amount to add to total spendings
    """
    with Database().session() as session:
        customer = session.query(CustomerInfo).filter_by(telegram_id=telegram_id).first()

        if not customer:
            # Create customer if doesn't exist
            customer = CustomerInfo(telegram_id=telegram_id)
            session.add(customer)
            session.flush()  # Flush to apply defaults before updating

        customer.total_spendings += amount
        customer.completed_orders_count += 1
        session.commit()

    # Sync to CSV
    sync_customer_to_csv(telegram_id, username)


def update_customer_bonus(telegram_id: int, username: str, amount: Decimal):
    """
    Update customer's bonus balance

    Args:
        telegram_id: Telegram ID
        username: Telegram username
        amount: Amount to add/subtract from bonus balance
    """
    with Database().session() as session:
        customer = session.query(CustomerInfo).filter_by(telegram_id=telegram_id).first()

        if not customer:
            # Create customer if doesn't exist
            customer = CustomerInfo(telegram_id=telegram_id)
            session.add(customer)
            session.flush()  # Flush to apply defaults before updating

        customer.bonus_balance += amount
        session.commit()

    # Sync to CSV
    sync_customer_to_csv(telegram_id, username)


def get_customer_bonus_balance(telegram_id: int) -> Decimal:
    """
    Get customer's bonus balance

    Args:
        telegram_id: Telegram ID

    Returns:
        Bonus balance as Decimal
    """
    with Database().session() as session:
        customer = session.query(CustomerInfo).filter_by(telegram_id=telegram_id).first()

        if customer:
            return customer.bonus_balance

    return Decimal('0')


async def sync_all_customers_to_csv():
    """
    Sync all customers from database to CSV file
    Fetches usernames from Telegram API for accurate data
    """
    initialize_customer_csv()

    # Create bot instance for fetching usernames
    bot = Bot(
        token=EnvKeys.TOKEN,
        default=DefaultBotProperties(
            parse_mode="HTML",
            link_preview_is_disabled=False,
            protect_content=False,
        ),
    )

    try:
        with Database().session() as session:
            customers = session.query(CustomerInfo).all()

            with _csv_lock:
                with open(CUSTOMER_CSV_PATH, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                    writer.writeheader()

                    for customer in customers:
                        # Get username from Telegram API
                        username = f"user_{customer.telegram_id}"  # Default fallback
                        try:
                            chat = await bot.get_chat(customer.telegram_id)
                            if chat.username:
                                username = chat.username
                        except Exception:
                            # If we can't get username from Telegram, use fallback
                            pass

                        writer.writerow({
                            'Telegram ID': str(customer.telegram_id),
                            'Username': _sanitize_cell(username),
                            'Phone Number': _sanitize_cell(customer.phone_number),
                            'Delivery Address': _sanitize_cell(customer.delivery_address),
                            'Delivery Note': _sanitize_cell(customer.delivery_note),
                            'Client Total Spendings': f"{float(customer.total_spendings):.2f}",
                            'Completed Orders Total': str(customer.completed_orders_count),
                            'Client Bonus Balance': f"{float(customer.bonus_balance):.2f}"
                        })
    finally:
        await bot.session.close()


def export_customers_csv(output_path: Path) -> bool:
    """
    Export customer CSV to a different location

    Args:
        output_path: Path to export to

    Returns:
        True if successful
    """
    if not CUSTOMER_CSV_PATH.exists():
        return False

    try:
        with _csv_lock:
            with open(CUSTOMER_CSV_PATH, 'r', encoding='utf-8') as src:
                with open(output_path, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
        return True
    except Exception:
        return False
