# Database Migrations

Эта папка содержит миграции базы данных для проекта, управляемые через [goose](https://github.com/pressly/goose).

## Структура миграций

Миграции нумеруются последовательно и содержат два блока:
- `-- +goose Up` - применение миграции
- `-- +goose Down` - откат миграции

### Текущие миграции

1. **00001_initial_schema.sql** - Создание начальной схемы БД
   - Таблицы: users, messages, game_users, units, user_units, fields, games, battle_units
   - Индексы и ограничения целостности
   - Enum типы (game_status)

2. **00002_add_icon_to_units.sql** - Добавление поля icon
   - Добавляет колонку `icon` в таблицу `units` для отображения эмодзи юнитов

3. **00003_seed_units_and_fields.sql** - Начальные данные
   - Игровые поля: 5x5, 7x7, 10x10
   - Базовые юниты: Мечник, Лучник, Рыцарь, Маг, Дракон

## Использование

### Применение миграций

```bash
# Bash
./migrate.sh up

# Python
python3 migrate.py up
```

### Откат миграции

```bash
# Bash
./migrate.sh down

# Python
python3 migrate.py down
```

### Проверка статуса

```bash
# Bash
./migrate.sh status

# Python
python3 migrate.py status
```

### Создание новой миграции

```bash
# Bash
./migrate.sh create add_new_feature

# Python
python3 migrate.py create add_new_feature
```

Это создаст файл с timestamp префиксом в папке migrations.

### Сброс базы данных

```bash
# Bash (откатывает все миграции и применяет заново)
./migrate.sh reset

# Python
python3 migrate.py reset
```

## Правила работы с миграциями

1. **Никогда не изменяйте примененные миграции** - создавайте новые
2. **Всегда тестируйте откат** - убедитесь, что `down` работает корректно
3. **Одна миграция = одна логическая задача**
4. **Используйте транзакции** - goose автоматически оборачивает SQL в транзакции
5. **Описательные имена** - используйте понятные названия миграций

## Примеры

### Создание новой таблицы

```sql
-- +goose Up
CREATE TABLE new_table (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL
);

-- +goose Down
DROP TABLE new_table;
```

### Добавление колонки

```sql
-- +goose Up
ALTER TABLE users ADD COLUMN email VARCHAR(255);

-- +goose Down
ALTER TABLE users DROP COLUMN email;
```

### Добавление данных

```sql
-- +goose Up
INSERT INTO units (name, price, damage) VALUES ('Новый юнит', 500, 30);

-- +goose Down
DELETE FROM units WHERE name = 'Новый юнит';
```

## Конфигурация

Миграции используют DATABASE_URL из:
1. Переменной окружения `DATABASE_URL`
2. Файла `config.json` (`database.url`)

## Версионирование

Goose отслеживает примененные миграции в таблице `goose_db_version`:
- `version_id` - номер миграции
- `is_applied` - статус применения
- `tstamp` - время применения
