# Docker Management Scripts

Система управления приложением ModernHomm через Docker контейнеры.

## Структура

Приложение запускается в двух контейнерах:
- **modernhomm_postgres** - База данных PostgreSQL (порт 5434)
- **modernhomm_app** - Telegram бот приложение

## Скрипты управления

### 1. init.sh - Инициализация контейнеров

Создает Docker контейнеры с конкретными именами. Если контейнеры уже существуют, ничего не делает.

```bash
./init.sh
```

**Что делает:**
- Проверяет наличие Docker и Docker Compose
- Создает директорию `postgres_data/` для данных БД
- Создает контейнеры без запуска

### 2. start.sh - Запуск контейнеров

Запускает контейнеры, если они не запущены.

```bash
./start.sh
```

**Что делает:**
- Проверяет существование контейнеров
- Запускает контейнеры через Docker Compose
- Ожидает готовности базы данных
- Выводит статус контейнеров

### 3. stop.sh - Остановка контейнеров

Останавливает запущенные контейнеры без удаления.

```bash
./stop.sh
```

**Что делает:**
- Останавливает контейнеры
- Выводит статус

### 4. cleanup.sh - Удаление контейнеров и данных

Удаляет контейнеры вместе с файлами базы данных.

```bash
./cleanup.sh
```

**⚠️ ВНИМАНИЕ:** Это действие необратимо! Все данные будут удалены.

**Что делает:**
- Запрашивает подтверждение
- Останавливает и удаляет контейнеры
- Удаляет Docker образы
- Удаляет файлы базы данных из `postgres_data/`
- Удаляет Docker сеть

## Быстрый старт

```bash
# 1. Инициализация
./init.sh

# 2. Запуск
./start.sh

# 3. Применение миграций к базе данных
goose -dir migrations postgres "user=postgres password=postgres host=localhost port=5434 dbname=telegram_bot sslmode=disable" up

# 4. Просмотр логов
docker compose logs -f app

# 5. Остановка (когда нужно)
./stop.sh
```

## Структура директорий

```
ModernHomm/
├── Dockerfile              # Описание образа приложения
├── docker-compose.yml      # Конфигурация контейнеров
├── init.sh                 # Скрипт инициализации
├── start.sh                # Скрипт запуска
├── stop.sh                 # Скрипт остановки
├── cleanup.sh              # Скрипт очистки
├── postgres_data/          # Данные PostgreSQL (создается автоматически)
│   └── ...                 # Файлы БД
├── migrations/             # SQL миграции
├── db/                     # Python модули БД
├── bot.py                  # Главное приложение
├── game_engine.py          # Игровой движок
└── config.json             # Конфигурация
```

## Полезные команды

### Просмотр логов

```bash
# Все логи
docker compose logs -f

# Только приложение
docker compose logs -f app

# Только база данных
docker compose logs -f postgres

# Последние 100 строк
docker compose logs --tail=100 app
```

### Подключение к базе данных

```bash
# Из хоста
psql -U postgres -h localhost -p 5434 telegram_bot

# Из контейнера
docker exec -it modernhomm_postgres psql -U postgres telegram_bot
```

### Проверка статуса

```bash
docker compose ps
```

### Перезапуск контейнера

```bash
docker compose restart app
```

## Troubleshooting

### Порт уже занят

Если порт 5434 занят, измените его в `docker-compose.yml`:

```yaml
ports:
  - "НОВЫЙ_ПОРТ:5432"
```

### Контейнер постоянно перезапускается

Проверьте логи:

```bash
docker compose logs app
```

### Нет подключения к базе данных

1. Проверьте, что контейнер postgres запущен и healthy:
   ```bash
   docker compose ps
   ```

2. Проверьте переменную DATABASE_URL в config.json или переменных окружения

### Очистка всего

Для полной очистки (включая образы и volumes):

```bash
./cleanup.sh
docker system prune -a
```

## Переменные окружения

Переменные окружения для контейнеров определены в `docker-compose.yml`:

**PostgreSQL:**
- `POSTGRES_USER=postgres`
- `POSTGRES_PASSWORD=postgres`
- `POSTGRES_DB=telegram_bot`

**Приложение:**
- `DATABASE_URL=postgresql://postgres:postgres@postgres:5432/telegram_bot`

Для изменения переменных отредактируйте `docker-compose.yml`.
