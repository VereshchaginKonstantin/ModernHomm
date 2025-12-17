# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Post-Change Workflow (ALWAYS EXECUTE AFTER ANY CODE CHANGES)

After completing ANY code changes, Claude MUST automatically execute the following steps IN ORDER:

### 1. Fix All Errors
- Run syntax checks on modified Python files: `python3 -m py_compile <file>`
- Fix any syntax or import errors before proceeding

### 2. Write Tests (if needed)
- Write integration tests for new functionality in `tests/`
- Write acceptance/smoke tests for API endpoints

### 3. Rebuild and Restart ALL Containers
```bash
# Rebuild ALL containers with latest changes
docker compose build --no-cache

# Restart containers
docker compose up -d

# Restart nginx to pickup new upstream IPs
docker compose restart nginx

# Wait for containers to start
sleep 3

# Verify containers are running
docker compose ps
```

### 4. Apply Migrations (if db/models changed)
```bash
goose -dir migrations postgres "user=postgres password=postgres host=localhost port=5434 dbname=telegram_bot sslmode=disable" up
```

### 5. Run Tests
```bash
# Run all tests
pytest -v

# If tests fail, fix them before proceeding
```

### 6. Verify Services via Diagnostic Endpoints
Check that all services are running with the latest version:

```bash
# Check web service
curl -s http://localhost/api/version | jq .

# Check bot service
curl -s http://localhost:8080/api/version | jq .

# Check health
curl -s http://localhost/api/health | jq .
curl -s http://localhost:8080/api/health | jq .
```

Expected response should include current VERSION timestamp (e.g., `2025.12.17-15:30:00`).
If version doesn't match, rebuild and restart containers again.

### 7. Export Godot (if godot-arena changed)
```bash
# Export Godot project for web
cd godot-arena && godot --headless --export-release "Web" build/index.html

# Update version in index.html for cache busting
# Add ?v=YYYYMMDDHHMMSS to index.js script tag

# Rebuild godot-arena container
docker compose build godot-arena
docker compose up -d godot-arena
docker compose restart nginx
```

### 8. Push Changes
```bash
git add -A
git commit -m "Description of changes"
git push
```

### 9. Update Domain Model (if db/models changed)
If any changes were made to `db/models/`, update `domain_model.puml`:
- Generate PlantUML diagram reflecting current database models
- Include all tables, relationships, and key fields

### 10. Final Verification
- Run smoke/acceptance tests again after push
- Confirm all containers are healthy via `/api/health`
- Confirm versions match via `/api/version`
- Report completion status

### 11. Background Tasks
- Wait for ALL background tasks to complete
- Report what each background task is doing and why

**IMPORTANT**: Do NOT skip any step. Do NOT proceed to next prompt until all steps are complete.

---

## Diagnostic Endpoints

All services expose diagnostic endpoints:

| Service | Version Endpoint | Health Endpoint |
|---------|-----------------|-----------------|
| Web (port 80) | `/api/version` | `/api/health` |
| Bot (port 8080) | `/api/version` | `/api/health` |
| Arena | `/arena/api/public/debug/status` | via web |

### Admin Debug Panel
Admins (user_id 1, 4) can access debug tools at `/help`:
- Toggle client logging on/off
- View Godot client logs
- Clear old logs

Client logs are stored in `client_logs` table and can be viewed via:
- Admin panel at `/help`
- API at `/admin/logs`

---

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
- `migrations/00001_create_schema.sql` - Creates all database tables with complete schema (structure)
- `migrations/00002_seed_reference_data.sql` - Seeds reference data (units and fields)

All migrations support both `up` (apply) and `down` (rollback) operations.

**Migration Structure:**
- **Schema migrations** (00001) contain only database structure (tables, indexes, constraints)
- **Seed migrations** (00002) contain reference data population
- This separation allows for better version control and cleaner rollback scenarios

### Running the Bot

#### Option 1: Using Docker (Recommended for Production)

```bash
# Initialize containers (first time only)
./init.sh

# Start containers
./start.sh

# Apply migrations to database
goose -dir migrations postgres "user=postgres password=postgres host=localhost port=5434 dbname=telegram_bot sslmode=disable" up

# View logs
docker compose logs -f app

# Stop containers
./stop.sh

# Clean up everything (removes containers and data)
./cleanup.sh
```

See [DOCKER_README.md](DOCKER_README.md) for detailed Docker management instructions.

#### Option 2: Direct Python Execution (Development)

```bash
python bot.py
# or
python3 bot.py
```

Stop the bot with `Ctrl+C`.

### Nginx Reverse Proxy

The project uses nginx as a reverse proxy for the admin panel. Nginx is configured in Docker and handles requests on port 80.

**Configuration:**
- `nginx/nginx.conf` - Nginx configuration file
- Proxies requests to admin panel (port 5000)
- Supports domains: `modernhomm.ru`, `www.modernhomm.ru`
- Supports IP access: `130.49.176.128`

**Access admin panel:**
- http://modernhomm.ru (requires DNS setup)
- http://www.modernhomm.ru (requires DNS setup)
- http://130.49.176.128
- http://localhost (on server)

**Nginx management:**
```bash
# Restart nginx
docker compose restart nginx

# View nginx logs
docker compose logs nginx

# Test nginx configuration
docker compose exec nginx nginx -t

# Reload configuration
docker compose exec nginx nginx -s reload
```

See [NGINX_README.md](NGINX_README.md) for detailed nginx configuration and troubleshooting.

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
- `User` model - stores Telegram user information (telegram_id, username, first_seen, last_seen)
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
- **test_reference_data.py** - Integration tests for reference data (units and fields initialization)

### Test Database Configuration

The test suite uses a separate test database. There are two options for setup:

**Option 1: Using Docker (Recommended)**
```bash
# Start test database container
docker compose -f docker-compose.test.yml up -d

# Apply migrations to test database
goose -dir migrations postgres "user=postgres password=postgres host=localhost port=5433 dbname=telegram_bot_test sslmode=disable" up

# Run tests
pytest

# Stop test database
docker compose -f docker-compose.test.yml down
```

**Option 2: Using local PostgreSQL**
```bash
# Create test database
psql -U postgres -c "CREATE DATABASE telegram_bot_test;"

# Apply migrations to test database
goose -dir migrations postgres "user=postgres dbname=telegram_bot_test sslmode=disable" up

# Run tests
pytest
```

Test database connection (Docker): `postgresql://postgres:postgres@localhost:5433/telegram_bot_test`

The test suite verifies:
- All 5 unit types are created with correct attributes (Мечник, Лучник, Рыцарь, Маг, Дракон)
- All 3 field sizes are created (5x5, 7x7, 10x10)
- All reference data has valid values and constraints
