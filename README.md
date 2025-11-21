# Telegram Bot с PostgreSQL

Простой Telegram бот на Python, который сохраняет все сообщения пользователей в базу данных PostgreSQL и отвечает с упоминанием их username.

## Возможности

- Отвечает на все сообщения стандартной фразой из конфига
- Сохраняет всех пользователей, обратившихся в личку
- Сохраняет все полученные сообщения в PostgreSQL
- Персонализированный ответ с упоминанием username пользователя
- Интеграционные тесты с использованием Docker

## Требования

- Python 3.8+
- PostgreSQL 12+
- Docker и Docker Compose (для запуска тестов)

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd ModernHomm
```

### 2. Создание виртуального окружения

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 3. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 4. Настройка PostgreSQL

Создайте базу данных:

```bash
psql -U postgres
CREATE DATABASE telegram_bot;
\q
```

### 5. Настройка конфигурации

Отредактируйте `config.json`:

```json
{
  "telegram": {
    "bot_token": "ВАШ_ТОКЕН_ОТ_BOTFATHER",
    "parse_mode": "HTML"
  },
  "bot": {
    "default_response": "Спасибо за ваше сообщение! Я простой бот и отвечаю всем одинаково."
  },
  "database": {
    "url": "postgresql://postgres:postgres@localhost:5432/telegram_bot"
  }
}
```

Для получения токена бота:
1. Напишите [@BotFather](https://t.me/botfather) в Telegram
2. Используйте команду `/newbot` и следуйте инструкциям
3. Скопируйте полученный токен в `config.json`

### 6. Инициализация базы данных

База данных будет автоматически инициализирована при первом запуске бота.

## Запуск

```bash
python bot.py
# или
python3 bot.py
```

Для остановки бота нажмите `Ctrl+C`.

## Структура проекта

```
ModernHomm/
├── bot.py                      # Основной файл бота
├── database.py                 # Модели и функции для работы с БД
├── config.json                 # Конфигурация бота
├── requirements.txt            # Зависимости Python
├── docker-compose.test.yml     # Docker Compose для тестов
├── pytest.ini                  # Конфигурация pytest
├── conftest.py                 # Фикстуры для тестов
├── tests/                      # Директория с тестами
│   ├── __init__.py
│   ├── test_database.py        # Тесты для database.py
│   └── test_bot_integration.py # Интеграционные тесты бота
└── README.md                   # Документация
```

## База данных

### Схема

Бот использует две таблицы:

**users** - информация о пользователях:
- `id` - первичный ключ
- `telegram_id` - ID пользователя в Telegram (уникальный)
- `username` - username пользователя
- `first_name` - имя
- `last_name` - фамилия
- `first_seen` - дата первого обращения
- `last_seen` - дата последнего обращения

**messages** - сообщения пользователей:
- `id` - первичный ключ
- `telegram_user_id` - ID пользователя в Telegram
- `message_text` - текст сообщения
- `message_date` - дата и время сообщения
- `username` - username пользователя на момент отправки

## Тестирование

Проект включает интеграционные тесты с использованием PostgreSQL в Docker.

### Подготовка к тестированию

1. Убедитесь, что Docker и Docker Compose установлены:

```bash
docker --version
docker-compose --version
```

2. Запустите тестовую базу данных PostgreSQL:

```bash
docker-compose -f docker-compose.test.yml up -d
```

3. Дождитесь запуска базы данных (около 5-10 секунд):

```bash
docker-compose -f docker-compose.test.yml ps
```

### Запуск тестов

Запуск всех тестов:

```bash
pytest
```

Запуск с подробным выводом:

```bash
pytest -v
```

Запуск конкретного файла с тестами:

```bash
pytest tests/test_database.py
pytest tests/test_bot_integration.py
```

Запуск конкретного теста:

```bash
pytest tests/test_database.py::TestDatabase::test_save_new_user
```

Запуск с покрытием кода:

```bash
pytest --cov=. --cov-report=html
```

### Остановка тестовой базы данных

После завершения тестирования остановите и удалите контейнер:

```bash
docker-compose -f docker-compose.test.yml down
```

Для полной очистки (включая volumes):

```bash
docker-compose -f docker-compose.test.yml down -v
```

### Описание тестов

**test_database.py** - тесты для модуля database:
- Создание таблиц
- Сохранение и обновление пользователей
- Сохранение сообщений
- Получение сообщений пользователя
- Обработка edge cases (пользователи без username, длинные сообщения и т.д.)

**test_bot_integration.py** - интеграционные тесты бота:
- Инициализация бота с базой данных
- Сохранение пользователей при получении сообщений
- Сохранение сообщений в базу
- Отправка персонализированных ответов
- Обработка нескольких сообщений от одного/разных пользователей
- Обработка ошибок базы данных

### Переменные окружения для тестов

По умолчанию тесты используют базу данных на порту 5433. Вы можете переопределить это через переменную окружения:

```bash
DATABASE_URL=postgresql://user:password@localhost:5433/dbname pytest
```

Или создать файл `.env.test`:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5433/telegram_bot_test
```

## Использование

1. Запустите бота
2. Найдите вашего бота в Telegram по username
3. Отправьте любое сообщение
4. Бот ответит с упоминанием вашего username и подтверждением сохранения сообщения

Пример ответа бота:
```
@username, я сохранила твое сообщение!

Спасибо за ваше сообщение! Я простой бот и отвечаю всем одинаково.
```

## Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку

## Переменные окружения

Вы можете использовать переменные окружения вместо config.json:

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/telegram_bot
python bot.py
```

## Логирование

Бот ведет логи всех операций:
- Получение сообщений от пользователей
- Сохранение данных в базу
- Ошибки при работе

Логи выводятся в консоль с уровнем INFO.

## Разработка

### Добавление новых функций

1. Обновите модели в `database.py` если нужно
2. Добавьте новые обработчики в `bot.py`
3. Напишите тесты в `tests/`
4. Запустите тесты для проверки

### Миграции базы данных

Проект использует SQLAlchemy. Для миграций можно использовать Alembic:

```bash
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Troubleshooting

### Бот не подключается к базе данных

- Проверьте, что PostgreSQL запущен
- Проверьте строку подключения в `config.json`
- Убедитесь, что база данных создана

### Тесты не проходят

- Убедитесь, что Docker контейнер с PostgreSQL запущен
- Проверьте, что порт 5433 свободен
- Проверьте логи контейнера: `docker-compose -f docker-compose.test.yml logs`

### Ошибка при установке psycopg2-binary

На некоторых системах может потребоваться установка дополнительных пакетов:

**Ubuntu/Debian:**
```bash
sudo apt-get install python3-dev libpq-dev
```

**macOS:**
```bash
brew install postgresql
```

## Лицензия

MIT

## Автор

Создано с помощью Claude Code
