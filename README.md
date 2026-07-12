# 🛒 Telegram Physical Goods Shop Bot

A production-ready Telegram bot for selling physical goods with comprehensive inventory management, Bitcoin/cash
payments, referral system, and advanced order tracking capabilities.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Aiogram](https://img.shields.io/badge/aiogram-3.22+-green.svg)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-blue.svg)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-ready-blue.svg)](https://www.docker.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## 🔀 Looking for Digital Goods Shop?

**📦 This version is for PHYSICAL GOODS** (inventory, shipping, delivery addresses, etc.)

**💾 Need to sell DIGITAL GOODS instead?** (accounts, keys, licenses, etc.)
👉 **Use this version**: [Telegram Digital Goods Shop](https://github.com/interlumpen/Telegram-shop)

The digital goods version features instant delivery, ItemValues storage, and automatic content distribution without
inventory management.

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Requirements](#-requirements)
- [Environment Variables](#-environment-variables)
- [Installation](#-installation)
- [Bot CLI Commands](#-bot-cli-commands)
- [Order Lifecycle](#-order-lifecycle)
- [Background Tasks](#-background-tasks)
- [Database Schema](#-database-schema)
- [Security Features](#-security-features)
- [Monitoring & Logging](#-monitoring--logging)
- [Testing](#-testing)
- [License](#-license)
- [Contributing](#-contributing)
- [Acknowledgments](#-acknowledgments)
- [Support](#-support)
- [Additional Documentation](#-additional-documentation)

## 🎯 Overview

This bot is specifically designed for **physical goods** (not digital products) with:

- **Inventory management** with stock tracking and reservation system
- **Dual payment methods**: Bitcoin (address pool) and Cash on Delivery
- **Shopping cart** with checkout flow
- **Reference codes** for controlled user registration
- **Referral bonuses** for customer acquisition
- **Order tracking** with delivery time management
- **CLI tool** for comprehensive shop administration

### What Makes This Different

This is NOT a typical digital goods Telegram shop. Key differences:

- ✅ Physical inventory with stock levels
- ✅ Reservation system with timeouts
- ✅ Delivery address & phone collection
- ✅ Dual payment methods (Bitcoin + Cash on Delivery)
- ✅ Reference code requirement for registration
- ✅ Multi-stage order lifecycle (pending → reserved → confirmed → delivered)
- ✅ Admin CLI for order & inventory management

## ✨ Key Features

### 🏪 Shop Management

- **Categories & Products**: Organize items by categories
- **Stock Tracking**: Real-time inventory with `stock_quantity` and `reserved_quantity`
- **Reservation System**: Items reserved for 24 hours (configurable) during checkout
- **Shopping Cart**: Add multiple items before checkout
- **Time-Limited Sales**: Per-product percentage discount with an expiry date; the sale price is computed
  server-side and reflected in the catalog, cart, and order total
- **Promo / Discount Codes**: Percent or fixed-amount codes, optionally bound to a category or a single item,
  with total-usage limits and once-per-user enforcement; applied to the order total and stackable on top of a
  sale (sale first, then promo)
- **Lazy Loading**: Efficient pagination for large catalogs

### 💰 Payment System

**Two Payment Methods:**

#### 1. Bitcoin Payments

- **Address Pool**: Load Bitcoin addresses from `btc_addresses.txt`
- **One-Time Use**: Each address used only once per order
- **Auto-Reload**: File watcher automatically loads new addresses when file changes
- **Usage Tracking**: Complete address usage audit trail in database
- **Critical**: Must add addresses to `btc_addresses.txt` before accepting Bitcoin orders

#### 2. Cash on Delivery (COD)

- **Manual Confirmation**: Admin confirms cash receipt via CLI
- **No Prepayment**: Customer pays upon delivery
- **Flexible**: No cryptocurrency wallet required

### 👥 User Management

- **Reference Code Required**: Users must enter valid code on first `/start`
- **User Types**: Regular users and admins (with different code creation privileges)
- **User Banning**: Ban/unban users via admin panel or CLI with optional reason tracking
- **Referral System**: Track who referred whom with configurable bonus percentage
- **Bonus Balance**: Accumulated referral bonuses can be applied to orders
- **Customer Profiles**: Saved delivery address, phone, order history

### 📦 Order Management

- **Order Codes**: 6-character unique codes (e.g., ECBDJI) for easy reference
- **Order Status**: `pending` → `reserved` → `confirmed` → `delivered` → `cancelled`/`expired`
- **Delivery Information**: Address, phone number, optional delivery note
- **Delivery Time**: Admin-set planned delivery time
- **Reservation Timeout**: Configurable timeout (default 24h) with automatic cleanup
- **Order Modifications**: Add/remove items, update delivery time via CLI

### 🔧 Administration

- **Role-Based Access**: USER, ADMIN, OWNER roles with granular permissions
- **CLI Tool** (`bot_cli.py`): Comprehensive command-line interface for shop management
- **Statistics**: Real-time shop statistics and analytics
- **Broadcast**: Send messages to all users or specific groups
- **Export**: CSV export for customers, orders, reference codes

### 📊 Monitoring & Logging

- **CLI-First Monitoring**: `python bot_cli.py stats` for shop statistics; no human web UI
- **Health & Metrics Endpoints**: `/health` (Docker healthcheck) and `/metrics/prometheus` (Grafana) on port
  9090
- **Audit Log (DB + file)**: Dual-write audit trail (`audit_log` table + `audit.log`) for order status
  changes, bans, and reference-code / promo / sale / inventory admin actions; queryable via `bot_cli.py audit`
- **Structured Logging**: Separate logs for orders, reference codes, customer changes
- **Timezone Support**: Configurable timezone for all logs
- **Inventory Audit**: Complete audit trail of all inventory changes (`inventory_log`)

### 🔒 Security

- **Rate Limiting**: Configurable per-action limits with periodic pruning (bounded memory)
- **Security Middleware**: SQL injection / XSS pattern detection, CSRF + replay protection on transactional
  callbacks (checkout, payment, bonus, destructive admin actions), signed with a stable `SECRET_KEY`
- **JSON-only cache**: cached values are never unpickled (no deserialization RCE)
- **Cryptographic Codes**: Secure reference code generation
- **Bot Detection**: Automatic blocking of bot accounts
- **Transaction Safety**: Row-level locking prevents overselling; Bitcoin address assignment uses
  `FOR UPDATE SKIP LOCKED`; promo usage is atomic and once-per-user
- **CSV Export Hardening**: formula-injection neutralization for customer exports
- **Audit Trail**: dual-write audit log (file + queryable `audit_log` table)

## 🏗️ Architecture

### 📁 Project Structure

<details>
<summary>Project Structure Schema (click to expand)</summary>

```
telegram_shop/
├── run.py                          # Entry point
├── bot_cli.py                      # CLI admin tool
├── alembic.ini                     # Alembic configuration
├── migrations/                     # Alembic migration scripts (env.py + versions/)
├── btc_addresses.txt               # Bitcoin address pool
├── requirements.txt                # Python dependencies
├── Dockerfile                      # Docker image definition
├── docker-compose.yml              # Multi-container setup
├── .env.example                    # Environment template
│
├── bot/
│   ├── __init__.py
│   ├── main.py                     # Bot initialization & startup
│   ├── logger_mesh.py              # Logging configuration
│   │
│   ├── config/                     # Configuration management
│   │   ├── env.py                  # Environment variables
│   │   ├── storage.py              # Redis/Memory storage
│   │   └── timezone.py             # Timezone handling
│   │
│   ├── database/                   # Database layer
│   │   ├── main.py                 # Database engine & session
│   │   ├── dsn.py                  # Connection string builder
│   │   ├── models/                 # SQLAlchemy models
│   │   │   └── main.py             # All model definitions
│   │   ├── migrate.py              # Alembic runner (auto-migrate on startup)
│   │   └── methods/                # Database operations
│   │       ├── create.py           # INSERT operations
│   │       ├── read.py             # SELECT operations
│   │       ├── update.py           # UPDATE operations (incl. set_item_sale)
│   │       ├── delete.py           # DELETE operations
│   │       ├── inventory.py        # Inventory management
│   │       ├── promo.py            # Promo / discount code logic
│   │       ├── audit.py            # Audit-log dual-write (file + DB)
│   │       ├── cache_utils.py      # Cache invalidation
│   │       └── lazy_queries.py     # Pagination queries
│   │
│   ├── handlers/                   # Request handlers
│   │   ├── main.py                 # Handler registration
│   │   ├── other.py                # Misc handlers
│   │   ├── user/                   # User-facing handlers
│   │   │   ├── main.py             # /start, /help
│   │   │   ├── shop_and_goods.py   # Browse catalog
│   │   │   ├── cart_handler.py     # Shopping cart
│   │   │   ├── order_handler.py    # Checkout & orders
│   │   │   ├── orders_view_handler.py  # Order history
│   │   │   ├── reference_code_handler.py  # Code entry
│   │   │   └── referral_system.py  # Referral bonuses
│   │   └── admin/                  # Admin-only handlers
│   │       ├── main.py             # Admin menu
│   │       ├── broadcast.py        # Mass messaging
│   │       ├── shop_management_states.py      # Shop stats
│   │       ├── goods_management_states.py     # Product CRUD
│   │       ├── categories_management_states.py # Category CRUD
│   │       ├── adding_position_states.py      # Add products
│   │       ├── update_position_states.py      # Edit products
│   │       ├── user_management_states.py      # User admin
│   │       ├── reference_code_management.py   # Code admin
│   │       └── settings_management.py         # Bot settings
│   │
│   ├── states/                     # FSM states
│   │   ├── user_state.py           # User flow states
│   │   ├── shop_state.py           # Shopping states
│   │   ├── payment_state.py        # Payment flow
│   │   ├── goods_state.py          # Product management
│   │   ├── category_state.py       # Category management
│   │   └── broadcast_state.py      # Broadcast states
│   │
│   ├── keyboards/                  # Inline keyboards
│   │   └── inline.py               # Keyboard builders
│   │
│   ├── middleware/                 # Request middleware
│   │   ├── security.py             # CSRF, injection detection
│   │   └── rate_limit.py           # Rate limiting
│   │
│   ├── filters/                    # Custom filters
│   │   └── main.py                 # Role filters, etc.
│   │
│   ├── i18n/                       # Internationalization
│   │   ├── main.py                 # Locale manager
│   │   └── strings.py              # Translations
│   │
│   ├── payments/                   # Payment processing
│   │   ├── bitcoin.py              # BTC address management
│   │   └── notifications.py        # Payment notifications
│   │
│   ├── referrals/                  # Referral system
│   │   └── codes.py                # Code generation & validation
│   │
│   ├── tasks/                      # Background tasks
│   │   ├── reservation_cleaner.py  # Expire old reservations
│   │   └── file_watcher.py         # Watch btc_addresses.txt
│   │
│   ├── caching/                    # Caching layer
│   │   ├── cache.py                # CacheManager & decorators
│   │   ├── scheduler.py            # Cache maintenance scheduler
│   │   └── stats_cache.py          # Statistics caching
│   │
│   ├── monitoring/                 # Observability
│   │   ├── metrics.py              # MetricsCollector
│   │   ├── dashboard.py            # Health + Prometheus HTTP endpoints (no human UI)
│   │   └── recovery.py             # Error recovery
│   │
│   ├── communication/              # User communication
│   │   └── broadcast_system.py     # Mass messaging
│   │
│   └── export/                     # Data export
│       ├── customer_csv.py         # Customer data export
│       └── custom_logging.py       # Structured logging
│
├── logs/                           # Log files
│   ├── bot.log                     # Main log
│   ├── audit.log                   # Security events
│   ├── orders.log                  # Order lifecycle
│   ├── reference_code.log          # Code operations
│   └── changes.log                 # Customer changes
│
├── data/                           # Runtime data
    └── final_metrics.json          # Shutdown metrics

```

</details>

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Telegram Bot API                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   Aiogram Bot (main.py)                     │
│  ┌────────────────┬──────────────┬────────────────────────┐ │
│  │   Handlers     │  Middleware  │   Background Tasks     │ │
│  │  (user/admin)  │ (security/   │  (reservation cleanup, │ │
│  │                │  rate limit) │   file watcher)        │ │
│  └────────────────┴──────────────┴────────────────────────┘ │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────┐
│ PostgreSQL   │ │  Redis   │ │ Bot CLI   │ │  Monitoring  │
│  Database    │ │  Cache   │ │ (bot_cli. │ │   Server     │
│ (inventory,  │ │  & FSM   │ │  py)      │ │  (port 9090) │
│  orders,     │ │ Storage  │ └───────────┘ └──────────────┘
│  users, etc.)│ └──────────┘
└──────────────┘
```

### Database Models

**Core Models:**

- `User`: Telegram users with role and referral tracking
- `Role`: Permission-based access control (USER/ADMIN/OWNER)
- `Goods`: Products with `stock_quantity`, `reserved_quantity`, `price`, and an optional time-limited sale
  (`sale_percent` + `sale_until`)
- `Categories`: Product categories
- `ShoppingCart`: User cart items

**Order System:**

- `Order`: Orders with status, delivery info, payment method, reservation timeout, applied referral bonus and
  applied promo (`promo_code` + `promo_discount`)
- `OrderItem`: Individual items in orders with quantity
- `CustomerInfo`: Customer delivery preferences, spending history, bonus balance

**Inventory System:**

- `InventoryLog`: Complete audit trail of all inventory changes

**Discounts & Promotions:**

- `PromoCode`: Discount codes (percent/fixed, optional category/item binding, usage limit, expiry, active flag)
- `PromoCodeUsage`: Tracks who used which promo code (unique per user)

**Reference Code System:**

- `ReferenceCode`: Reference codes with expiry, usage limits, notes
- `ReferenceCodeUsage`: Tracking who used which code

**Payment System:**

- `BitcoinAddress`: Pool of Bitcoin addresses with usage tracking

**Referral System:**

- `ReferralEarnings`: Referral bonus transactions

**Audit & Configuration:**

- `AuditLog`: Structured, queryable audit trail (action, level, user, resource, details, IP, timestamp)
- `BotSettings`: Dynamic bot settings (timezone, bonus percentage, etc.)

### Migrations

The schema is managed with **Alembic** (`migrations/`). Migrations run **automatically on startup**
(`register_models()`), including a safe transition that stamps an existing pre-Alembic database to the baseline
before applying newer revisions — so upgrading an existing deployment needs no manual step. To run them by hand:

```bash
alembic upgrade head        # apply all migrations
alembic history             # list revisions
```

## 📋 Requirements

- Python 3.11+
- PostgreSQL 16+
- Redis 7+
- Docker & Docker Compose (recommended)

## ⚙️ Environment Variables

The application requires the following environment variables:

<details>
<summary><b>🤖 Telegram</b></summary>

| Variable   | Description                                                | Required |
|------------|------------------------------------------------------------|----------|
| `TOKEN`    | [Bot Token from @BotFather](https://telegram.me/BotFather) | ✅        |
| `OWNER_ID` | [Your Telegram ID](https://telegram.me/myidbot)            | ✅        |

</details>

<details>
<summary><b>💳 Payments</b></summary>

| Variable       | Description                            | Default |
|----------------|----------------------------------------|---------|
| `PAY_CURRENCY` | Display currency (RUB, USD, EUR, etc.) | `RUB`   |
| `MIN_AMOUNT`   | Minimum payment amount                 | `20`    |
| `MAX_AMOUNT`   | Maximum payment amount                 | `10000` |

</details>

<details>
<summary><b>🔗 Links / UI</b></summary>

| Variable      | Description                              | Default |
|---------------|------------------------------------------|---------|
| `CHANNEL_URL` | News channel link (public channels only) | -       |
| `HELPER_ID`   | Support user Telegram ID                 | -       |
| `RULES`       | Bot usage rules text                     | -       |

</details>

<details>
<summary><b>🌐 Locale & Logs</b></summary>

| Variable        | Description                   | Default |
|-----------------|-------------------------------|---------|
| `BOT_LOCALE`    | Localization language (ru/en) | `ru`    |
| `LOG_TO_STDOUT` | Console logging (1/0)         | `1`     |
| `LOG_TO_FILE`   | File logging (1/0)            | `1`     |
| `DEBUG`         | Debug mode (1/0)              | `0`     |

</details>

<details>
<summary><b>📊 Monitoring</b></summary>

| Variable          | Description                                  | Default     |
|-------------------|----------------------------------------------|-------------|
| `MONITORING_HOST` | Health/metrics server bind address           | `localhost` |
| `MONITORING_PORT` | Health/metrics server port                   | `9090`      |

Serves `/health`, `/metrics`, and `/metrics/prometheus` only (no human dashboard).
**Note**: When running in Docker, set `MONITORING_HOST=0.0.0.0` to allow external access.

</details>

<details>
<summary><b>🔒 Security</b></summary>

| Variable     | Description                                                                       | Default |
|--------------|-----------------------------------------------------------------------------------|---------|
| `SECRET_KEY` | Stable secret for signing CSRF / replay-protection tokens. If unset, a random     | -       |
|              | per-process key is used (tokens won't survive restarts). Set in production.       |         |

</details>

<details>
<summary><b>📦 Redis Storage</b></summary>

| Variable         | Description                 | Default |
|------------------|-----------------------------|---------|
| `REDIS_HOST`     | Redis server address        | `redis` |
| `REDIS_PORT`     | Redis server port           | `6379`  |
| `REDIS_DB`       | Redis database number       | `0`     |
| `REDIS_PASSWORD` | Redis password (if enabled) | -       |

</details>

<details>
<summary><b>🗄️ Database (Docker)</b></summary>

| Variable            | Description              | Default               |
|---------------------|--------------------------|-----------------------|
| `POSTGRES_DB`       | PostgreSQL database name | **Required**          |
| `POSTGRES_USER`     | PostgreSQL username      | `postgres`            |
| `POSTGRES_PASSWORD` | PostgreSQL password      | **Required**          |
| `DB_PORT`           | PostgreSQL port          | `5432`                |
| `DB_DRIVER`         | Database driver          | `postgresql+psycopg2` |

</details>

<details>
<summary><b>🗄️ Database (Manual Deploy)</b></summary>

For manual deployment, configure `DATABASE_URL` in `bot/config/env.py`:

```python
DATABASE_URL = "postgresql+psycopg2://user:password@localhost:5432/db_name"
```

[SQLAlchemy Documentation](https://docs.sqlalchemy.org/en/20/core/engines.html#postgresql)

</details>

## 🚀 Installation

### Option 1: Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/telegram_shop.git
   cd telegram_shop
   ```

2. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your values
   ```

3. **Add Bitcoin addresses** (Required ONLY if accepting Bitcoin payments)
   ```bash
   nano btc_addresses.txt
   # Add your Bitcoin addresses, one per line:
   # bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh
   # bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4
   # Note: Skip this step if using cash on delivery only
   ```

4. **Start services**
   ```bash
   docker compose up -d --build bot
   ```

5. **View logs**
   ```bash
   docker compose logs -f bot
   ```

### Option 2: Manual Installation

1. **Clone repository**
   ```bash
   git clone https://github.com/yourusername/telegram_shop.git
   cd telegram_shop
   ```

2. **Create virtual environment**
   ```bash
   python3.11 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Set up PostgreSQL**
   ```bash
   createdb telegram_shop
   createuser shop_user -P
   ```

5. **Configure environment**
    - [Set environment variables in PyCharm](https://stackoverflow.com/questions/42708389/how-to-set-environment-variables-in-pycharm)
    - Or export them in terminal:
   ```bash
   export TOKEN="your_bot_token"
   export OWNER_ID="your_telegram_id"
   # Set other required variables from .env.example
   ```

6. **Add Bitcoin addresses** (optional - only if accepting Bitcoin)
   ```bash
   nano btc_addresses.txt
   # Add addresses as shown above
   # Skip if using cash on delivery only
   ```

7. **Run the bot**
   ```bash
   python run.py
   ```

### Bot Settings (Dynamic)

These can be changed at runtime via CLI:

```bash
# Enable/disable reference codes
python bot_cli.py settings set reference_codes_enabled true

# Set referral bonus percentage (0-100)
python bot_cli.py settings set reference_bonus_percent 5

# Set timezone for logs
python bot_cli.py settings set timezone "America/New_York"

# Set order timeout (hours)
python bot_cli.py settings set cash_order_timeout_hours 24

# Set help auto-response
python bot_cli.py settings set help_auto_message "We'll respond within 24 hours"
```

## 🔧 Bot CLI Commands

The `bot_cli.py` script provides comprehensive shop management while the bot is running.

### Order Management

#### Complete Order Flow (Recommended)

```bash
# 1. User places order → order is 'pending', inventory reserved
# 2. Confirm order with delivery time
python bot_cli.py order --order-code ABCDEF --status-confirmed --delivery-time "2025-11-20 14:30"

# 3. Mark as delivered (deducts inventory from stock)
python bot_cli.py order --order-code ABCDEF --status-delivered
```

#### Cancel Order

```bash
# Cancel order (releases reserved inventory, refunds bonus if applied)
python bot_cli.py order --order-code ABCDEF --cancel
```

#### Modify Order

```bash
# Add item to order
python bot_cli.py order --order-code ABCDEF --add-item "Product Name" --quantity 2 --notify

# Remove item from order
python bot_cli.py order --order-code ABCDEF --remove-item "Product Name" --quantity 1 --notify

# Update delivery time
python bot_cli.py order --order-code ABCDEF --update-delivery-time --delivery-time "2025-11-21 16:00" --notify
```

### Inventory Management

```bash
# Set inventory to specific value
python bot_cli.py inventory "Product Name" --set 100

# Add to current inventory
python bot_cli.py inventory "Product Name" --add 50

# Remove from inventory
python bot_cli.py inventory "Product Name" --remove 25
```

### Reference Code Management

```bash
# Create admin reference code
python bot_cli.py refcode create --expires-hours 48 --max-uses 10 --note "VIP customers"

# Create unlimited code (no expiry, unlimited uses)
python bot_cli.py refcode create --expires-hours 0 --max-uses 0 --note "Permanent invite"

# Disable code
python bot_cli.py refcode disable CODE123 --reason "No longer valid"

# List all codes
python bot_cli.py refcode list

# List only active codes
python bot_cli.py refcode list --active-only
```

### Bitcoin Address Management

```bash
# Add single address
python bot_cli.py btc add --address bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh

# Add addresses from file
python bot_cli.py btc add --file new_addresses.txt

# Check address pool status
python bot_cli.py btc list

# Show all addresses with details
python bot_cli.py btc list --show-all

# Sync addresses (cleanup)
python bot_cli.py btc sync
```

### Shop Statistics

```bash
# Print shop statistics (users, admins, products, categories, orders by status, revenue)
python bot_cli.py stats
```

### Category Management

```bash
python bot_cli.py category add "Electronics"
python bot_cli.py category list
python bot_cli.py category delete "Electronics"   # also removes products in it
```

### Product Management

```bash
# Create a product (category must already exist); --stock sets the initial quantity
python bot_cli.py item add "Wireless Mouse" --description "USB-C, 2.4GHz" --price 1500 --category "Electronics" --stock 50
python bot_cli.py item list
python bot_cli.py item delete "Wireless Mouse"

# Adjust stock of an existing product
python bot_cli.py inventory "Wireless Mouse" --set 100
python bot_cli.py inventory "Wireless Mouse" --add 25
python bot_cli.py inventory "Wireless Mouse" --remove 10
```

### Time-Limited Sales

```bash
# Put a product on sale (percentage discount for a number of days)
python bot_cli.py sale "Wireless Mouse" --percent 20 --days 7

# Remove the sale
python bot_cli.py sale "Wireless Mouse" --remove
```

### Promo Codes

```bash
# Percentage promo, limited uses, expires in 48h
python bot_cli.py promo create SUMMER --type percent --value 15 --max-uses 100 --expires-hours 48

# Fixed-amount promo bound to a category (or --item for a single product)
python bot_cli.py promo create MINUS500 --type fixed --value 500 --category "Electronics"

python bot_cli.py promo list
python bot_cli.py promo list --active-only
python bot_cli.py promo disable SUMMER
python bot_cli.py promo enable SUMMER
python bot_cli.py promo delete SUMMER
```

Promo codes discount the **order total** (this shop has no user wallet), stack **on top of** any active per-product sale (sale first, then promo), are usable a limited number of times overall and **at most once per user**.

### Referral Bonus

```bash
# Grant referral bonus balance to a user
python bot_cli.py bonus 123456789 500
```

### Broadcast

```bash
# Send an HTML message to all non-banned users
python bot_cli.py broadcast "🎉 <b>New arrivals in stock!</b>"
```

### Audit Log

```bash
# View recent audit entries (order status changes, bans, refcode/promo/sale actions, etc.)
python bot_cli.py audit
python bot_cli.py audit --limit 100
python bot_cli.py audit --action order_delivered
python bot_cli.py audit --user 123456789
```

### Data Export

```bash
# Export all data
python bot_cli.py export --all --output-dir backups/

# Export only customers
python bot_cli.py export --customers --output-dir backups/

# Export only reference codes
python bot_cli.py export --refcodes --output-dir backups/

# Export only orders
python bot_cli.py export --orders --output-dir backups/
```

### Settings Management

```bash
# Set a setting
python bot_cli.py settings set reference_codes_enabled true
python bot_cli.py settings set reference_bonus_percent 5
python bot_cli.py settings set timezone "UTC"

# Get a setting value
python bot_cli.py settings get reference_codes_enabled

# List all settings
python bot_cli.py settings list
```

### User Ban Management

```bash
# Ban a user
python bot_cli.py ban 123456789 --reason "Violating terms of service" --notify

# Ban a user without notification
python bot_cli.py ban 123456789 --reason "Spam"

# Unban a user
python bot_cli.py unban 123456789 --notify

# Unban a user without notification
python bot_cli.py unban 123456789
```

## 📦 Order Lifecycle

### Complete Order Flow

```
1. User browses shop
   ↓
2. User adds items to cart
   ↓
3. User clicks "Proceed to Checkout"
   ↓
4. System asks for delivery info:
   - Delivery address
   - Phone number
   - Delivery note (optional)
   ↓
5. System asks for an optional promo code (or skip)
   ↓
6. System asks about applying referral bonus (if available)
   ↓
7. User selects payment method:
   - Bitcoin: System assigns address from pool, user receives payment instructions
   - Cash on Delivery: Order proceeds directly to confirmation
   ↓
8. Order created with status: pending → reserved
   - Inventory RESERVED for 24 hours (configurable)
   - reserved_until timestamp set
   ↓
9. Admin receives order notification
   ↓
10. Customer pays (Bitcoin) or prepares cash (COD)
    ↓
11. Admin confirms order via CLI:
    python bot_cli.py order --order-code XXXXX --status-confirmed --delivery-time "YYYY-MM-DD HH:MM"
    - Order status: reserved → confirmed
    - Delivery time set
    - Customer notified
    - For Bitcoin: After payment is verified
    - For COD: After reviewing order details
    ↓
12. Admin delivers order and marks as delivered via CLI:
    python bot_cli.py order --order-code XXXXX --status-delivered
    - Order status: confirmed → delivered
    - Inventory DEDUCTED from stock (actual reduction)
    - reserved_quantity reduced
    - stock_quantity reduced
    - Customer spending updated
    - Referral bonus credited (if applicable)
    - Customer notified
    - For COD: Cash collected at this point
```

### Order Status States

- **`pending`**: Order just created, waiting for reservation
- **`reserved`**: Inventory reserved, waiting for payment/confirmation
- **`confirmed`**: Payment confirmed, delivery time set, awaiting delivery
- **`delivered`**: Order completed, inventory deducted, customer updated
- **`cancelled`**: Manually cancelled by admin, inventory released
- **`expired`**: Reservation timeout exceeded, inventory automatically released

### Inventory Flow

#### Reserve (on order creation)

```
stock_quantity: 100
reserved_quantity: 0 → 5
available_quantity: 100 → 95
```

#### Deduct (on order delivery)

```
stock_quantity: 100 → 95
reserved_quantity: 5 → 0
available_quantity: 95 (unchanged)
```

#### Release (on cancel/expire)

```
stock_quantity: 100 (unchanged)
reserved_quantity: 5 → 0
available_quantity: 95 → 100
```

## 🔄 Background Tasks

### 1. Reservation Cleaner

**File**: `bot/tasks/reservation_cleaner.py`

Runs every 60 seconds to:

- Find orders with `order_status='reserved'` and `reserved_until < now()`
- Release reserved inventory back to available stock
- Mark orders as `expired`
- Refund referral bonus if applied
- Notify customers about expired orders
- Log all actions to `inventory_log`

### 2. Bitcoin Address File Watcher

**File**: `bot/tasks/file_watcher.py`

Monitors `btc_addresses.txt` for changes:

- Watches file for modifications
- Debounces rapid changes (2-second default)
- Automatically loads new addresses into database
- Logs all operations
- Thread-safe with locking

## 🔒 Security Features

### Middleware Chain

The bot implements a layered middleware architecture for security, performance, and observability:

```
Request Flow:
User → Telegram API → aiogram Dispatcher
         ↓
    AnalyticsMiddleware (tracks all events)
         ↓
    AuthenticationMiddleware (verifies user identity, caches roles)
         ↓
    SecurityMiddleware (CSRF protection, suspicious pattern detection)
         ↓
    RateLimitMiddleware (prevents spam, configurable limits)
         ↓
    Handler (business logic)
```

**Middleware Details:**

1. **AnalyticsMiddleware** (`bot/monitoring/metrics.py`)
    - Tracks every event (messages, callbacks)
    - Measures handler execution time
    - Records errors and conversion funnels
    - Sends metrics to Prometheus

2. **AuthenticationMiddleware** (`bot/middleware/security.py`)
    - Verifies user identity
    - Caches user roles (5-minute TTL)
    - Blocks bot accounts automatically
    - Prevents unauthorized admin access

3. **SecurityMiddleware** (`bot/middleware/security.py`)
    - Generates CSRF tokens for critical actions
    - Detects SQL injection, XSS, command injection patterns
    - Validates callback data age (1-hour max)
    - Logs all security events to audit log

4. **RateLimitMiddleware** (`bot/middleware/rate_limit.py`)
    - Global limit: 30 requests/60 seconds (configurable)
    - Action-specific limits:
        - Broadcast: 1/hour
        - Shop views: 60/minute
        - Purchases: 5/minute
    - Temporary bans: 5 minutes after limit exceeded
    - Admin bypass support

## 📊 Monitoring & Logging

### Monitoring (CLI-first)

This shop is administered from the command line, so there is **no human web dashboard**. Runtime observability
is exposed only as machine-readable endpoints (for Docker/Grafana), and operational statistics come from the CLI:

```bash
python bot_cli.py stats     # users, admins, products, categories, orders by status, revenue
python bot_cli.py audit     # recent audit trail
```

Endpoints served on `MONITORING_HOST:MONITORING_PORT` (default `localhost:9090`):

- `/health` — JSON health check (used by the Docker healthcheck)
- `/metrics` — raw metrics as JSON
- `/metrics/prometheus` — Prometheus exposition format for Grafana

**MetricsCollector** (`bot/monitoring/metrics.py`) tracks:

**1. Events:**

- Order lifecycle: created, reserved, confirmed, delivered, cancelled, expired
- Cart operations: add, remove, view, clear, checkout
- Payment events: initiated, bonus applied, completed
- Referral actions: code created/used, bonus paid
- Inventory changes: reserved, released, deducted
- Security alerts: suspicious patterns, rate limits, unauthorized access

**2. Timings:**

- Handler execution duration
- Database query latency
- Cache operation speed
- External API calls

**3. Errors:**

- Error type categorization
- Error frequency tracking
- Stack trace logging

**4. Conversions:**

```python
# Customer journey funnel
shop → category → item → cart → checkout → payment → order

# Referral funnel
code_created → code_used → bonus_paid
```

### Log Files

**Log Levels:**

- `DEBUG`: Development debugging (disabled in production)
- `INFO`: Normal operations, startup/shutdown
- `WARNING`: Recoverable issues, rate limits
- `ERROR`: Errors that need attention
- `CRITICAL`: System failures

**Specialized Logs:**

1. **bot.log** - Main application log
    - Bot startup/shutdown
    - Handler execution
    - Database operations
    - Background tasks

2. **audit.log** - Security events
    - Critical action attempts
    - Failed authorization
    - Suspicious patterns
    - Rate limit violations

3. **orders.log** - Order operations
    - Order creation
    - Status changes
    - Delivery updates
    - Completions/cancellations

4. **reference_code.log** - Code lifecycle
    - Code generation
    - Code usage
    - Code deactivation

5. **changes.log** - Customer data modifications
    - Profile updates
    - Spending changes
    - Bonus adjustments

**Log Format:**

```
[2025-11-19 14:30:45] [INFO] [bot.main:239] Starting bot: @shopbot (ID: 123456789)
[2025-11-19 14:30:46] [INFO] [bot.tasks.reservation_cleaner:14] Reservation cleaner started
```

### CSV Exports

Automatic CSV generation in `logs/`:

- `customer_list.csv`: Customer database with all details
- Updated in real-time as customer data changes

### Prometheus Metrics

Metrics available at `http://localhost:9090/metrics/prometheus` for Grafana integration.

### Health Check

System health at `http://localhost:9090/health` for uptime monitoring.

# Test Suite Documentation

Comprehensive test suite for the Telegram Physical Goods Shop Bot.

## Overview

This test suite provides comprehensive coverage for all major components of the bot:

- Database models and relationships
- CRUD operations
- Inventory management system
- Order lifecycle
- Shopping cart
- Referral system
- Reference code system
- Bitcoin payment system
- Validators and utilities

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and pytest configuration
├── unit/                    # Unit tests
│   ├── database/           # Database-related tests
│   │   ├── test_models.py       # Model tests
│   │   ├── test_crud.py         # CRUD operation tests
│   │   ├── test_inventory.py   # Inventory management tests
│   │   └── test_cart.py         # Shopping cart tests
│   ├── utils/              # Utility tests
│   │   ├── test_validators.py  # Validator tests
│   │   └── test_order_codes.py # Order code generation tests
│   ├── payments/           # Payment system tests
│   │   └── test_bitcoin.py     # Bitcoin address tests
│   └── referrals/          # Referral system tests
│       └── test_reference_codes.py  # Reference code tests
└── integration/            # Integration tests
    └── test_order_lifecycle.py  # Complete order flow tests
```

## 🧪 Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage Report

```bash
pytest --cov=bot --cov-report=html --cov-report=term-missing
```

Coverage report will be generated in `htmlcov/` directory.

### Run Specific Test Categories

Run only unit tests:

```bash
pytest -m unit
```

Run only integration tests:

```bash
pytest -m integration
```

Run only database tests:

```bash
pytest -m database
```

Run only model tests:

```bash
pytest -m models
```

### Run Specific Test Files

```bash
# Run model tests
pytest tests/unit/database/test_models.py

# Run CRUD tests
pytest tests/unit/database/test_crud.py

# Run inventory tests
pytest tests/unit/database/test_inventory.py

# Run order lifecycle tests
pytest tests/integration/test_order_lifecycle.py
```

### Run Specific Test Classes or Functions

```bash
# Run specific test class
pytest tests/unit/database/test_models.py::TestRoleModel

# Run specific test function
pytest tests/unit/database/test_models.py::TestRoleModel::test_create_role
```

### Verbose Output

```bash
pytest -v
```

### Show Print Statements

```bash
pytest -s
```

### Stop on First Failure

```bash
pytest -x
```

### Run Failed Tests Only

```bash
pytest --lf
```

### Test Markers

Tests are organized with markers for easy filtering:

- `unit` - Unit tests
- `integration` - Integration tests
- `database` - Tests requiring database
- `slow` - Slow running tests
- `models` - Database model tests
- `crud` - CRUD operation tests
- `inventory` - Inventory management tests
- `orders` - Order management tests
- `cart` - Shopping cart tests
- `referrals` - Referral system tests
- `bitcoin` - Bitcoin payment tests
- `validators` - Validator tests

### Fixtures

#### Database Fixtures

- `db_engine` - Test database engine (in-memory SQLite)
- `db_session` - Test database session
- `db_with_roles` - Database session with roles initialized

#### Model Fixtures

- `test_user` - Sample user
- `test_admin` - Sample admin user
- `test_category` - Sample category
- `test_goods` - Sample goods with stock
- `test_goods_low_stock` - Sample goods with low stock
- `test_order` - Sample order with items
- `test_customer_info` - Sample customer information
- `test_bitcoin_address` - Sample Bitcoin address
- `test_reference_code` - Sample reference code
- `test_shopping_cart` - Sample cart item
- `test_bot_settings` - Sample bot settings

#### Complex Fixtures

- `populated_database` - Database with all test data
- `multiple_products` - List of multiple products
- `multiple_categories` - List of multiple categories

### Test Coverage

#### Current Coverage Areas

1. **Database Models** (100%)
    - All model creation and validation
    - Relationships between models
    - Property calculations (e.g., available_quantity)
    - Permission system

2. **CRUD Operations** (95%)
    - Create operations for all models
    - Read operations with caching
    - Update operations with validation
    - Proper error handling

3. **Inventory Management** (100%)
    - Reservation system
    - Release mechanism
    - Deduction on order completion
    - Stock tracking and logging
    - Concurrent access handling

4. **Order System** (100%)
    - Order creation
    - Status transitions
    - Order cancellation
    - Multi-item orders
    - Order code generation

5. **Shopping Cart** (100%)
    - Adding items
    - Quantity updates
    - Stock validation
    - Total calculation

6. **Referral System** (100%)
    - Reference code generation
    - Code validation
    - Usage tracking
    - Expiration handling
    - Usage limits

7. **Bitcoin System** (95%)
    - Address loading
    - Address assignment
    - Usage tracking
    - File synchronization

8. **Validators** (100%)
    - Input validation
    - Data sanitization
    - Error handling

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🙏 Acknowledgments

- [Aiogram](https://github.com/aiogram/aiogram) - Telegram Bot framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [Redis](https://redis.io/) - Cache and FSM storage
- [PostgreSQL](https://www.postgresql.org/) - Database
- [Watchdog](https://github.com/gorakhargosh/watchdog) - File system monitoring

## 📞 Support

- **Issues**: Report bugs via GitHub Issues
- **Logs**: Check `logs/` directory for detailed error information

## 📚 Additional Documentation

- `.env.example` - Environment variable reference
- `bot_cli.py --help` - CLI usage help
