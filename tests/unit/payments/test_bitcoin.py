"""
Tests for Bitcoin address management
"""
import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch, MagicMock

from bot.payments.bitcoin import (
    load_bitcoin_addresses_from_file,
    get_available_bitcoin_address,
    mark_bitcoin_address_used,
    add_bitcoin_address,
    add_bitcoin_addresses_bulk,
    get_bitcoin_address_stats,
    BTC_ADDRESSES_FILE
)
from bot.database.models.main import BitcoinAddress


@pytest.mark.unit
@pytest.mark.bitcoin
@pytest.mark.database
class TestBitcoinAddressLoading:
    """Tests for loading Bitcoin addresses from file"""

    def test_load_bitcoin_addresses_from_file(self, db_session):
        """Test loading addresses from file"""
        # Create temporary file with test addresses
        with NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("bc1qtest1234567890abcdefghijklmnopqrstuvwxyz\n")
            f.write("bc1qtest2345678901bcdefghijklmnopqrstuvwxyza\n")
            f.write("# This is a comment\n")
            f.write("\n")  # Empty line
            f.write("bc1qtest3456789012cdefghijklmnopqrstuvwxyzab\n")
            temp_path = Path(f.name)

        # Patch BTC_ADDRESSES_FILE to point to our temp file
        with patch('bot.payments.bitcoin.BTC_ADDRESSES_FILE', temp_path):
            count = load_bitcoin_addresses_from_file()

        # Should load 3 addresses (skipping comment and empty line)
        assert count == 3

        # Cleanup
        temp_path.unlink()

    def test_load_bitcoin_addresses_duplicate(self, db_session):
        """Test loading duplicate addresses doesn't create duplicates"""
        # Add an address first
        btc_addr = BitcoinAddress(address="bc1qtest1234567890")
        db_session.add(btc_addr)
        db_session.commit()

        # Create file with same address
        with NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("bc1qtest1234567890\n")
            f.write("bc1qtest2345678901\n")
            temp_path = Path(f.name)

        # Patch BTC_ADDRESSES_FILE to point to our temp file
        with patch('bot.payments.bitcoin.BTC_ADDRESSES_FILE', temp_path):
            count = load_bitcoin_addresses_from_file()

        # Should only load 1 new address
        assert count == 1

        # Cleanup
        temp_path.unlink()


@pytest.mark.unit
@pytest.mark.bitcoin
@pytest.mark.database
class TestBitcoinAddressRetrieval:
    """Tests for retrieving Bitcoin addresses"""

    def test_get_available_bitcoin_address(self, db_session, test_bitcoin_address):
        """Test getting an available address"""
        address = get_available_bitcoin_address()

        assert address is not None
        assert address == test_bitcoin_address.address

    def test_get_available_bitcoin_address_none_available(self, db_session, test_bitcoin_address):
        """Test getting address when none available"""
        test_bitcoin_address.is_used = True
        db_session.commit()

        address = get_available_bitcoin_address()
        assert address is None

    def test_get_available_bitcoin_address_with_session_locks(self, db_session, test_bitcoin_address):
        """Selecting within a session (FOR UPDATE SKIP LOCKED path) returns the address.

        This is the atomic pick-and-mark path used at checkout to prevent two
        concurrent orders from being assigned the same address.
        """
        address = get_available_bitcoin_address(session=db_session)
        assert address == test_bitcoin_address.address


@pytest.mark.unit
@pytest.mark.bitcoin
@pytest.mark.database
class TestBitcoinAddressUsage:
    """Tests for marking Bitcoin addresses as used"""

    @patch('bot.payments.bitcoin.remove_bitcoin_address_from_file')
    @patch('bot.payments.bitcoin.log_bitcoin_address_assigned')
    def test_mark_bitcoin_address_used(self, mock_log, mock_remove, db_session, test_bitcoin_address, test_user, test_order):
        """Test marking an address as used"""
        success = mark_bitcoin_address_used(
            address=test_bitcoin_address.address,
            user_id=test_user.telegram_id,
            user_username="test_user",
            order_id=test_order.id,
            session=db_session,
            order_code=test_order.order_code
        )
        db_session.commit()  # Function doesn't commit when session is passed

        assert success == True

        db_session.refresh(test_bitcoin_address)
        assert test_bitcoin_address.is_used == True
        assert test_bitcoin_address.used_by == test_user.telegram_id
        assert test_bitcoin_address.order_id == test_order.id

        mock_remove.assert_called_once_with(test_bitcoin_address.address)
        mock_log.assert_called_once()

    @patch('bot.payments.bitcoin.remove_bitcoin_address_from_file')
    def test_mark_nonexistent_address_used(self, mock_remove, db_session, test_user, test_order):
        """Test marking non-existent address as used"""
        success = mark_bitcoin_address_used(
            address="bc1qnonexistent",
            user_id=test_user.telegram_id,
            user_username="test_user",
            order_id=test_order.id,
            session=db_session
        )

        assert success == False


@pytest.mark.unit
@pytest.mark.bitcoin
@pytest.mark.database
class TestBitcoinAddressAddition:
    """Tests for adding Bitcoin addresses"""

    @patch('bot.payments.bitcoin._file_lock')
    @patch('builtins.open', create=True)
    def test_add_bitcoin_address(self, mock_open, mock_lock, db_session):
        """Test adding a single Bitcoin address"""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        success = add_bitcoin_address("bc1qnewaddress123")

        assert success == True

        # Check it was added to database
        btc_addr = db_session.query(BitcoinAddress).filter_by(
            address="bc1qnewaddress123"
        ).first()
        assert btc_addr is not None

    def test_add_duplicate_bitcoin_address(self, db_session, test_bitcoin_address):
        """Test adding duplicate address"""
        with patch('builtins.open', create=True):
            success = add_bitcoin_address(test_bitcoin_address.address)

        assert success == False

    @patch('bot.payments.bitcoin._file_lock')
    @patch('builtins.open', create=True)
    def test_add_bitcoin_addresses_bulk(self, mock_open, mock_lock, db_session):
        """Test adding multiple addresses"""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        addresses = [
            "bc1qbulk1234567890",
            "bc1qbulk2345678901",
            "bc1qbulk3456789012"
        ]

        count = add_bitcoin_addresses_bulk(addresses)

        assert count == 3


@pytest.mark.unit
@pytest.mark.bitcoin
@pytest.mark.database
class TestBitcoinAddressStats:
    """Tests for Bitcoin address statistics"""

    def test_get_bitcoin_address_stats(self, db_session):
        """Test getting address statistics"""
        # Add some addresses
        for i in range(5):
            btc_addr = BitcoinAddress(address=f"bc1qstats{i:010d}")
            if i < 2:
                btc_addr.is_used = True
            db_session.add(btc_addr)
        db_session.commit()

        stats = get_bitcoin_address_stats()

        assert stats['total'] >= 5
        assert stats['used'] >= 2
        assert stats['available'] >= 3

    def test_get_bitcoin_address_stats_empty(self, db_session):
        """Test stats with no addresses"""
        # Clear all addresses
        db_session.query(BitcoinAddress).delete()
        db_session.commit()

        stats = get_bitcoin_address_stats()

        assert stats['total'] == 0
        assert stats['used'] == 0
        assert stats['available'] == 0
