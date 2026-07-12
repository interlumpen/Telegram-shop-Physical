from pathlib import Path
from typing import Optional, List
from datetime import datetime

from bot.database.main import Database
from bot.database.models.main import BitcoinAddress
from bot.export.custom_logging import log_bitcoin_address_assigned
import threading

# File path for Bitcoin addresses
BTC_ADDRESSES_FILE = Path("btc_addresses.txt")

# Lock for thread-safe file operations
_file_lock = threading.Lock()


def load_bitcoin_addresses_from_file() -> int:
    """
    Load Bitcoin addresses from btc_addresses.txt into the database

    Returns:
        Number of addresses loaded
    """
    if not BTC_ADDRESSES_FILE.exists():
        # Create empty file if it doesn't exist
        BTC_ADDRESSES_FILE.touch()
        return 0

    with _file_lock:
        with open(BTC_ADDRESSES_FILE, 'r') as f:
            # Filter out comments and empty lines
            addresses = [
                line.strip() for line in f
                if line.strip() and not line.strip().startswith('#')
            ]

    if not addresses:
        return 0

    loaded_count = 0
    with Database().session() as session:
        for address in addresses:
            # Check if address already exists
            existing = session.query(BitcoinAddress).filter_by(address=address).first()
            if not existing:
                btc_addr = BitcoinAddress(address=address)
                session.add(btc_addr)
                loaded_count += 1

        session.commit()

    return loaded_count


def get_available_bitcoin_address(session=None) -> Optional[str]:
    """
    Get an available (unused) Bitcoin address.

    When a session is provided the row is locked with FOR UPDATE SKIP LOCKED, so
    two concurrent checkouts can never be handed the same address. Pass the order
    transaction's session so selecting and marking-used happen atomically.

    Args:
        session: Optional SQLAlchemy session. If given, selection is locked and
                 no separate session/commit is opened.

    Returns:
        Bitcoin address string or None if no addresses available
    """
    def _select(s):
        query = s.query(BitcoinAddress).filter_by(is_used=False)
        if session is not None:
            # SKIP LOCKED so a concurrent checkout picks a different row instead
            # of blocking. (No-op on SQLite in tests.)
            query = query.with_for_update(skip_locked=True)
        btc_addr = query.first()
        return btc_addr.address if btc_addr else None

    if session is not None:
        return _select(session)

    with Database().session() as own_session:
        return _select(own_session)


def mark_bitcoin_address_used(address: str, user_id: int, user_username: str,
                               order_id: int, session=None, order_code: str = None) -> bool:
    """
    Mark a Bitcoin address as used and remove from file

    Args:
        address: Bitcoin address
        user_id: User's Telegram ID
        user_username: User's username
        order_id: Order ID
        session: Optional SQLAlchemy session (if None, creates new one)
        order_code: Order code (e.g., ECBDJI) if applicable

    Returns:
        True if successful, False otherwise
    """
    # If session provided, use it (don't commit, let caller handle it)
    if session:
        btc_addr = session.query(BitcoinAddress).filter_by(address=address).first()

        if not btc_addr:
            return False

        # Mark as used
        btc_addr.is_used = True
        btc_addr.used_by = user_id
        btc_addr.used_at = datetime.now()
        btc_addr.order_id = order_id

        # Don't commit here - caller will commit
    else:
        # Create new session (for backward compatibility)
        with Database().session() as db_session:
            btc_addr = db_session.query(BitcoinAddress).filter_by(address=address).first()

            if not btc_addr:
                return False

            # Mark as used
            btc_addr.is_used = True
            btc_addr.used_by = user_id
            btc_addr.used_at = datetime.now()
            btc_addr.order_id = order_id

            db_session.commit()

    # Remove from file
    remove_bitcoin_address_from_file(address)

    # Log assignment
    log_bitcoin_address_assigned(address, order_id, user_id, user_username, order_code=order_code)

    return True


def remove_bitcoin_address_from_file(address: str):
    """
    Remove a Bitcoin address from the btc_addresses.txt file

    Args:
        address: Bitcoin address to remove
    """
    if not BTC_ADDRESSES_FILE.exists():
        return

    with _file_lock:
        # Read all lines (including comments)
        with open(BTC_ADDRESSES_FILE, 'r') as f:
            lines = [line.rstrip('\n') for line in f]

        # Remove the specified address but keep comments
        filtered_lines = []
        for line in lines:
            stripped = line.strip()
            # Keep comments and empty lines, remove only the matching address
            if not stripped or stripped.startswith('#') or stripped != address:
                filtered_lines.append(line)

        # Write back
        with open(BTC_ADDRESSES_FILE, 'w') as f:
            for line in filtered_lines:
                f.write(f"{line}\n")


def add_bitcoin_address(address: str) -> bool:
    """
    Add a new Bitcoin address to the database and file

    Args:
        address: Bitcoin address

    Returns:
        True if successful, False if already exists
    """
    # Add to database
    with Database().session() as session:
        existing = session.query(BitcoinAddress).filter_by(address=address).first()
        if existing:
            return False

        btc_addr = BitcoinAddress(address=address)
        session.add(btc_addr)
        session.commit()

    # Add to file
    with _file_lock:
        with open(BTC_ADDRESSES_FILE, 'a') as f:
            f.write(f"{address}\n")

    return True


def add_bitcoin_addresses_bulk(addresses: List[str]) -> int:
    """
    Add multiple Bitcoin addresses

    Args:
        addresses: List of Bitcoin addresses

    Returns:
        Number of addresses added
    """
    added_count = 0

    with Database().session() as session:
        for address in addresses:
            existing = session.query(BitcoinAddress).filter_by(address=address).first()
            if not existing:
                btc_addr = BitcoinAddress(address=address)
                session.add(btc_addr)
                added_count += 1

        session.commit()

    # Add to file
    if added_count > 0:
        with _file_lock:
            with open(BTC_ADDRESSES_FILE, 'a') as f:
                for address in addresses:
                    f.write(f"{address}\n")

    return added_count


def get_bitcoin_address_stats() -> dict:
    """
    Get statistics about Bitcoin addresses

    Returns:
        Dictionary with stats
    """
    with Database().session() as session:
        total = session.query(BitcoinAddress).count()
        used = session.query(BitcoinAddress).filter_by(is_used=True).count()
        available = total - used

        return {
            'total': total,
            'used': used,
            'available': available
        }
