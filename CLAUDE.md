# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Telegram bot application written in Python that responds to all messages with a personalized phrase and saves all messages and users to a PostgreSQL database. The bot is built using the `python-telegram-bot` library (v20.7) and SQLAlchemy for database operations.

## Development Commands

### Setup and Installation
```bash
pip install -r requirements.txt
```

### Database Setup

#### Option 1: Using Migrations (Recommended)
```bash
# Create PostgreSQL database
psql -U postgres
CREATE DATABASE telegram_bot;
\q

# Run migrations using bash script
./migrate.sh up

# OR using Python script
python3 migrate.py up
```

#### Option 2: Manual Setup
```bash
# Create PostgreSQL database
psql -U postgres
CREATE DATABASE telegram_bot;
\q
```

### Database Migrations

The project uses [goose](https://github.com/pressly/goose) for database migrations with version control.

**Migration Commands:**
```bash
# Apply all pending migrations
./migrate.sh up

# Rollback last migration
./migrate.sh down

# Show migration status
./migrate.sh status

# Create new migration
./migrate.sh create migration_name

# Reset database (rollback all and reapply)
./migrate.sh reset
```

**Python alternative:**
```bash
python3 migrate.py up
python3 migrate.py status
python3 migrate.py create migration_name
```

**Migration Files:**
- `migrations/00001_initial_schema.sql` - Creates all database tables
- `migrations/00002_add_icon_to_units.sql` - Adds icon field to units table
- `migrations/00003_seed_units_and_fields.sql` - Seeds initial game data (units and fields)

All migrations support both `up` (apply) and `down` (rollback) operations.

### Running the Bot
```bash
python bot.py
# or
python3 bot.py
```

Stop the bot with `Ctrl+C`.

### Running Tests
```bash
# Start test database
docker-compose -f docker-compose.test.yml up -d

# Run tests
pytest

# Stop test database
docker-compose -f docker-compose.test.yml down
```

## Architecture

### Core Components

**bot.py** - Main bot application:
- `SimpleBot` class that encapsulates all bot functionality
- Configuration loading from JSON file
- Command handlers for `/start` and `/help`
- Message handler that saves messages to database and replies with personalized response
- Database integration for storing users and messages
- Error handling and logging setup

**database.py** - Database layer:
- `User` model - stores Telegram user information (telegram_id, username, first_name, last_name, first_seen, last_seen)
- `Message` model - stores all received messages (telegram_user_id, message_text, message_date, username)
- `Database` class - provides methods for database operations:
  - `save_user()` - saves or updates user information
  - `save_message()` - saves a message
  - `get_user_messages()` - retrieves all messages from a user
  - `get_all_users()` - retrieves all users

**config.json** - Configuration file containing:
- `telegram.bot_token` - Telegram Bot API token (from @BotFather)
- `telegram.parse_mode` - Text formatting mode (HTML, Markdown, or MarkdownV2)
- `bot.default_response` - The standard reply sent to all user messages
- `database.url` - PostgreSQL connection string

### Bot Flow

1. `SimpleBot.__init__()` loads configuration from `config.json` and initializes database connection
2. Database tables are created automatically if they don't exist
3. `SimpleBot.run()` creates the Application, registers handlers, and starts polling
4. Commands `/start` and `/help` are handled by dedicated async methods
5. All text messages trigger `handle_message()` which:
   - Saves user information to the database
   - Saves the message to the database
   - Replies with a personalized response mentioning the user's username
6. All user interactions are logged and stored in PostgreSQL

### Configuration Management

The bot expects `config.json` to exist in the same directory. Configuration is loaded once at startup. Any changes to the config require restarting the bot.

Database URL can also be set via `DATABASE_URL` environment variable, which takes precedence over config.json.

To obtain a bot token:
1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Use `/newbot` command and follow instructions
3. Copy the token to `config.json`

## Testing

The project includes comprehensive integration tests with PostgreSQL:

- **test_database.py** - Tests for database operations (saving users, messages, retrieving data)
- **test_bot_integration.py** - Integration tests for bot with database (message handling, user saving, personalized responses)

Tests use Docker Compose to run an isolated PostgreSQL instance on port 5433.

### Test Database Configuration

Test database connection: `postgresql://postgres:postgres@localhost:5433/telegram_bot_test`

The test suite automatically creates and drops tables for each test to ensure isolation.
