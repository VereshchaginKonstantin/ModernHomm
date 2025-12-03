#!/usr/bin/env python3
"""
Админка Flask для управления юнитами
"""

import os
import json
import zipfile
import shutil
from io import BytesIO
from flask import Flask, render_template_string, request, redirect, url_for, flash, send_file
from werkzeug.utils import secure_filename
from db import Database
from db.models import Unit
from decimal import Decimal

# Создать Flask приложение
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static/unit_images'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max file size

def calculate_unit_price(damage: int, defense: int, health: int, unit_range: int, speed: int, luck: float, crit_chance: float) -> Decimal:
    """
    Автоматический расчет стоимости юнита по формуле:
    Урон + Защита + Здоровье + 100*Дальность + 50*Скорость + 100*Удача + 100*Крит

    Args:
        damage: Урон юнита
        defense: Защита юнита
        health: Здоровье юнита
        unit_range: Дальность атаки
        speed: Скорость перемещения
        luck: Вероятность удачи (0-1)
        crit_chance: Вероятность критического удара (0-1)

    Returns:
        Decimal: Рассчитанная стоимость
    """
    price = (
        damage +
        defense +
        health +
        100 * unit_range +
        50 * speed +
        100 * luck +
        100 * crit_chance
    )
    return Decimal(str(round(price, 2)))


# Инициализировать базу данных
config_path = 'config.json'
try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
except FileNotFoundError:
    print(f"Файл конфигурации {config_path} не найден!")
    exit(1)

db_url = os.getenv('DATABASE_URL', config.get('database', {}).get('url'))
db = Database(db_url)

# HTML шаблоны для админки
HEADER_TEMPLATE = """
<nav class="navbar">
    <div class="nav-links">
        <a href="{{ url_for('index') }}" class="nav-link {{ 'active' if active_page == 'images' else '' }}">Картинки юнитов</a>
        <a href="{{ url_for('units_list') }}" class="nav-link {{ 'active' if active_page == 'units' else '' }}">Управление юнитами</a>
        <a href="{{ url_for('help_page') }}" class="nav-link {{ 'active' if active_page == 'help' else '' }}">Справка</a>
        <a href="{{ url_for('export_units') }}" class="nav-link">Экспорт юнитов</a>
    </div>
</nav>
"""

BASE_STYLE = """
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 0;
            background-color: #f5f5f5;
        }
        .navbar {
            background-color: #2c3e50;
            padding: 15px 20px;
            margin-bottom: 30px;
        }
        .nav-links {
            display: flex;
            gap: 20px;
        }
        .nav-link {
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 4px;
            transition: background-color 0.3s;
        }
        .nav-link:hover {
            background-color: #34495e;
        }
        .nav-link.active {
            background-color: #3498db;
        }
        .content {
            padding: 0 20px 20px 20px;
        }
        h1 {
            color: #333;
            text-align: center;
            margin: 20px 0;
        }
        .units-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .unit-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .unit-card h2 {
            margin-top: 0;
            color: #444;
            font-size: 20px;
        }
        .unit-info {
            margin: 10px 0;
            color: #666;
            font-size: 14px;
        }
        .unit-image {
            width: 150px;
            height: 150px;
            object-fit: contain;
            border: 2px solid #ddd;
            border-radius: 4px;
            margin: 10px 0;
            background-color: #f9f9f9;
        }
        .no-image {
            width: 150px;
            height: 150px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #eee;
            border: 2px dashed #ccc;
            border-radius: 4px;
            margin: 10px 0;
            color: #999;
            font-size: 14px;
        }
        .upload-form {
            margin-top: 15px;
        }
        .file-input {
            margin: 10px 0;
        }
        .btn {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn:hover {
            background-color: #45a049;
        }
        .btn-danger {
            background-color: #f44336;
        }
        .btn-danger:hover {
            background-color: #da190b;
        }
        .alert {
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .alert-success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .stats {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }
        .stats-item {
            display: inline-block;
            margin: 0 20px;
        }
        .stats-number {
            font-size: 32px;
            font-weight: bold;
            color: #4CAF50;
        }
        .stats-label {
            font-size: 14px;
            color: #666;
        }
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        .form-control {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }
        .btn-primary {
            background-color: #3498db;
        }
        .btn-primary:hover {
            background-color: #2980b9;
        }
        .unit-params-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .unit-params-table th,
        .unit-params-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .unit-params-table th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        .import-form {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
    </style>
"""

# Шаблон главной страницы (управление картинками)
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Админка - Управление картинками юнитов</title>
""" + BASE_STYLE + """
</head>
<body>
""" + HEADER_TEMPLATE + """
    <div class="content">
        <h1>Управление картинками юнитов</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <div class="stats">
        <div class="stats-item">
            <div class="stats-number">{{ stats.total }}</div>
            <div class="stats-label">Всего юнитов</div>
        </div>
        <div class="stats-item">
            <div class="stats-number">{{ stats.with_images }}</div>
            <div class="stats-label">С картинками</div>
        </div>
        <div class="stats-item">
            <div class="stats-number">{{ stats.without_images }}</div>
            <div class="stats-label">Без картинок</div>
        </div>
    </div>

    <div class="units-grid">
        {% for unit in units %}
        <div class="unit-card">
            <h2>{{ unit.icon }} {{ unit.name }}</h2>
            <div class="unit-info">
                <strong>Цена:</strong> {{ unit.price }} |
                <strong>Урон:</strong> {{ unit.damage }} |
                <strong>Защита:</strong> {{ unit.defense }}
            </div>
            <div class="unit-info">
                <strong>Здоровье:</strong> {{ unit.health }} |
                <strong>Дальность:</strong> {{ unit.range }} |
                <strong>Скорость:</strong> {{ unit.speed }}
            </div>

            {% if unit.image_path and unit.has_image %}
                <img src="/{{ unit.image_path }}" alt="{{ unit.name }}" class="unit-image">
                <form action="{{ url_for('delete_image', unit_id=unit.id) }}" method="POST" style="display: inline;">
                    <button type="submit" class="btn btn-danger" onclick="return confirm('Удалить картинку?')">Удалить картинку</button>
                </form>
            {% else %}
                <div class="no-image">Нет картинки</div>
            {% endif %}

            <form action="{{ url_for('upload_image', unit_id=unit.id) }}" method="POST" enctype="multipart/form-data" class="upload-form">
                <input type="file" name="image" accept="image/png,image/jpeg,image/jpg" class="file-input" required>
                <button type="submit" class="btn">Загрузить</button>
            </form>
        </div>
        {% endfor %}
    </div>
    </div>
</body>
</html>
"""

# Шаблон для управления юнитами
UNITS_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Управление юнитами</title>
""" + BASE_STYLE + """
</head>
<body>
""" + HEADER_TEMPLATE + """
    <div class="content">
        <h1>Управление юнитами</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div style="margin-bottom: 20px;">
            <a href="{{ url_for('create_unit') }}" class="btn btn-primary">Создать нового юнита</a>
            <a href="{{ url_for('import_page') }}" class="btn btn-primary" style="margin-left: 10px;">Импортировать юнитов</a>
        </div>

        <table class="unit-params-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Иконка</th>
                    <th>Название</th>
                    <th>Цена</th>
                    <th>Урон</th>
                    <th>Защита</th>
                    <th>Здоровье</th>
                    <th>Дальность</th>
                    <th>Скорость</th>
                    <th>Удача</th>
                    <th>Крит %</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                {% for unit in units %}
                <tr>
                    <td>{{ unit.id }}</td>
                    <td>{{ unit.icon }}</td>
                    <td>{{ unit.name }}</td>
                    <td>{{ unit.price }}</td>
                    <td>{{ unit.damage }}</td>
                    <td>{{ unit.defense }}</td>
                    <td>{{ unit.health }}</td>
                    <td>{{ unit.range }}</td>
                    <td>{{ unit.speed }}</td>
                    <td>{{ "%.2f"|format(unit.luck|float) }}</td>
                    <td>{{ "%.2f"|format(unit.crit_chance|float * 100) }}%</td>
                    <td>
                        <a href="{{ url_for('edit_unit', unit_id=unit.id) }}" class="btn" style="background-color: #3498db; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; font-size: 12px;">Редактировать</a>
                        <form action="{{ url_for('delete_unit', unit_id=unit.id) }}" method="POST" style="display: inline;">
                            <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;" onclick="return confirm('Удалить юнита {{ unit.name }}?')">Удалить</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

# Шаблон для создания/редактирования юнита
UNIT_FORM_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ 'Редактирование' if unit else 'Создание' }} юнита</title>
""" + BASE_STYLE + """
</head>
<body>
""" + HEADER_TEMPLATE + """
    <div class="content">
        <h1>{{ 'Редактирование' if unit else 'Создание' }} юнита</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div style="background: white; padding: 30px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
            <form method="POST" style="margin: 0;">
                <div class="form-group">
                    <label>Название юнита *</label>
                    <input type="text" name="name" class="form-control" value="{{ unit.name if unit else '' }}" required>
                </div>

                <div class="form-group">
                    <label>Иконка (эмодзи) *</label>
                    <input type="text" name="icon" class="form-control" value="{{ unit.icon if unit else '🎮' }}" required maxlength="10">
                </div>

                <div class="form-group">
                    <label>Цена (автоматически рассчитывается)</label>
                    <input type="text" class="form-control" value="{{ unit.price if unit else 'Рассчитается автоматически' }}" readonly disabled style="background-color: #e9ecef; cursor: not-allowed;">
                    <small class="form-text text-muted">Формула: Урон + Защита + Здоровье + 100×Дальность + 50×Скорость + 100×Удача + 100×Крит</small>
                </div>

                <div class="form-group">
                    <label>Урон *</label>
                    <input type="number" name="damage" class="form-control" value="{{ unit.damage if unit else '10' }}" min="1" required>
                </div>

                <div class="form-group">
                    <label>Защита *</label>
                    <input type="number" name="defense" class="form-control" value="{{ unit.defense if unit else '0' }}" min="0" required>
                </div>

                <div class="form-group">
                    <label>Здоровье (HP) *</label>
                    <input type="number" name="health" class="form-control" value="{{ unit.health if unit else '100' }}" min="1" required>
                </div>

                <div class="form-group">
                    <label>Дальность атаки *</label>
                    <input type="number" name="range" class="form-control" value="{{ unit.range if unit else '1' }}" min="1" required>
                </div>

                <div class="form-group">
                    <label>Скорость (клеток за ход) *</label>
                    <input type="number" name="speed" class="form-control" value="{{ unit.speed if unit else '1' }}" min="1" required>
                </div>

                <div class="form-group">
                    <label>Удача (0-1, например 0.1 = 10%) *</label>
                    <input type="number" name="luck" class="form-control" value="{{ unit.luck if unit else '0' }}" step="0.01" min="0" max="1" required>
                </div>

                <div class="form-group">
                    <label>Шанс критического удара (0-1, например 0.15 = 15%) *</label>
                    <input type="number" name="crit_chance" class="form-control" value="{{ unit.crit_chance if unit else '0' }}" step="0.01" min="0" max="1" required>
                </div>

                <div class="form-group">
                    <label>Шанс уклонения (0-1, например 0.2 = 20%) *</label>
                    <input type="number" name="dodge_chance" class="form-control" value="{{ unit.dodge_chance if unit else '0' }}" step="0.01" min="0" max="1" required>
                    <small class="form-text text-muted">Вероятность полностью избежать урона от атаки</small>
                </div>

                <div style="margin-top: 20px;">
                    <button type="submit" class="btn btn-primary">Сохранить</button>
                    <a href="{{ url_for('units_list') }}" class="btn" style="background-color: #95a5a6; color: white; text-decoration: none; margin-left: 10px;">Отмена</a>
                </div>
            </form>
        </div>
    </div>
</body>
</html>
"""

# Шаблон страницы справки
HELP_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Справка по параметрам юнитов</title>
""" + BASE_STYLE + """
</head>
<body>
""" + HEADER_TEMPLATE + """
    <div class="content">
        <h1>Справка по параметрам юнитов</h1>

        <div style="background: white; padding: 30px; border-radius: 8px;">
            <h2>Базовые параметры</h2>
            <table class="unit-params-table">
                <tr>
                    <th style="width: 200px;">Параметр</th>
                    <th>Описание</th>
                    <th style="width: 300px;">Как используется в формулах</th>
                </tr>
                <tr>
                    <td><strong>Цена</strong></td>
                    <td>Стоимость покупки одного юнита</td>
                    <td>Используется при покупке юнитов и расчете награды за убитых врагов</td>
                </tr>
                <tr>
                    <td><strong>Урон (Damage)</strong></td>
                    <td>Базовый урон юнита при атаке</td>
                    <td><code>Урон = damage × (0.9-1.1) × (1 - усталость×0.3) × (1 + мораль×0.2)</code></td>
                </tr>
                <tr>
                    <td><strong>Защита (Defense)</strong></td>
                    <td>Уменьшает входящий урон</td>
                    <td><code>Финальный_урон = max(1, Урон - defense)</code></td>
                </tr>
                <tr>
                    <td><strong>Здоровье (Health)</strong></td>
                    <td>Количество очков жизни каждого юнита</td>
                    <td>При получении урона >= health юнит погибает</td>
                </tr>
                <tr>
                    <td><strong>Дальность (Range)</strong></td>
                    <td>Максимальная дистанция атаки (манхэттенское расстояние)</td>
                    <td><code>Можно_атаковать = |x1-x2| + |y1-y2| ≤ range</code></td>
                </tr>
                <tr>
                    <td><strong>Скорость (Speed)</strong></td>
                    <td>Количество клеток, на которое может переместиться юнит за ход</td>
                    <td>Используется в алгоритме BFS для поиска доступных клеток</td>
                </tr>
                <tr>
                    <td><strong>Удача (Luck)</strong></td>
                    <td>Вероятность нанести максимальный урон (0-1, где 0.1 = 10%)</td>
                    <td><code>if random() < luck: Урон = Урон × 1.5</code></td>
                </tr>
                <tr>
                    <td><strong>Шанс крита (Crit Chance)</strong></td>
                    <td>Вероятность критического удара (0-1, где 0.15 = 15%)</td>
                    <td><code>Шанс = crit_chance + мораль×0.2 - усталость×0.2<br>if random() < Шанс: Урон = Урон × 2</code></td>
                </tr>
            </table>

            <h2 style="margin-top: 40px;">Динамические параметры (во время боя)</h2>
            <table class="unit-params-table">
                <tr>
                    <th style="width: 200px;">Параметр</th>
                    <th>Описание</th>
                    <th style="width: 300px;">Влияние на бой</th>
                </tr>
                <tr>
                    <td><strong>Мораль</strong></td>
                    <td>Повышается при успешных атаках (0-100%)</td>
                    <td>
                        • Увеличивает урон до +20%<br>
                        • Увеличивает шанс крита до +20%<br>
                        • +10 при успешной атаке
                    </td>
                </tr>
                <tr>
                    <td><strong>Усталость</strong></td>
                    <td>Повышается при неудачах (0-100%)</td>
                    <td>
                        • Снижает урон до -30%<br>
                        • Снижает шанс крита до -20%<br>
                        • +10 при неудачной атаке<br>
                        • -5 при успешной атаке
                    </td>
                </tr>
            </table>

            <h2 style="margin-top: 40px;">Полная формула расчета урона</h2>
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; font-family: monospace;">
                <p><strong>1.</strong> Базовый урон со случайностью: <code>base = damage × random(0.9, 1.1)</code></p>
                <p><strong>2.</strong> Модификатор усталости: <code>fatigue_mod = 1 - (усталость / 100) × 0.3</code></p>
                <p><strong>3.</strong> Модификатор морали: <code>morale_mod = 1 + (мораль / 100) × 0.2</code></p>
                <p><strong>4.</strong> Урон с модификаторами: <code>dmg = base × fatigue_mod × morale_mod</code></p>
                <p><strong>5.</strong> Проверка критического удара: <code>crit_chance_final = crit_chance + мораль×0.002 - усталость×0.002</code></p>
                <p><strong>6.</strong> Если крит: <code>dmg = dmg × 2</code></p>
                <p><strong>7.</strong> Проверка удачи: <code>if random() < luck: dmg = dmg × 1.5</code></p>
                <p><strong>8.</strong> Применение защиты: <code>dmg_final = max(1, dmg - defense)</code></p>
                <p><strong>9.</strong> Умножение на количество атакующих: <code>total_dmg = dmg_final × count</code></p>
            </div>
        </div>
    </div>
</body>
</html>
"""

# Шаблон страницы импорта
IMPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Импорт юнитов</title>
""" + BASE_STYLE + """
</head>
<body>
""" + HEADER_TEMPLATE + """
    <div class="content">
        <h1>Импорт юнитов</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="import-form">
            <h2>Загрузить архив с юнитами</h2>
            <p style="color: #666; margin-bottom: 20px;">
                <strong>Внимание!</strong> Импорт заменит все существующие юниты на юниты из архива.
                Убедитесь, что вы сделали экспорт текущих юнитов перед импортом.
            </p>
            <form method="POST" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Выберите ZIP-архив с юнитами</label>
                    <input type="file" name="archive" class="form-control" accept=".zip" required>
                </div>
                <div style="margin-top: 20px;">
                    <button type="submit" class="btn btn-danger" onclick="return confirm('Вы уверены? Это заменит всех существующих юнитов!')">Импортировать</button>
                    <a href="{{ url_for('units_list') }}" class="btn" style="background-color: #95a5a6; color: white; text-decoration: none; margin-left: 10px;">Отмена</a>
                </div>
            </form>
        </div>
    </div>
</body>
</html>
"""


@app.route('/')
def index():
    """Главная страница админки"""
    with db.get_session() as session:
        units = session.query(Unit).all()

        # Принудительно загружаем все атрибуты перед закрытием сессии
        for unit in units:
            _ = unit.id
            _ = unit.name
            _ = unit.icon
            _ = unit.image_path
            _ = unit.price
            _ = unit.damage
            _ = unit.defense
            _ = unit.range
            _ = unit.health
            _ = unit.speed

        session.expunge_all()

    # Проверить наличие файлов для каждого юнита
    for unit in units:
        unit.has_image = unit.image_path and os.path.exists(unit.image_path)

    # Подсчитать статистику
    stats = {
        'total': len(units),
        'with_images': sum(1 for u in units if u.has_image),
        'without_images': sum(1 for u in units if not u.has_image)
    }

    return render_template_string(ADMIN_TEMPLATE, units=units, stats=stats, active_page='images')


@app.route('/upload/<int:unit_id>', methods=['POST'])
def upload_image(unit_id):
    """Загрузка картинки для юнита"""
    if 'image' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))

    file = request.files['image']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))

    if file:
        # Получить юнит
        with db.get_session() as session:
            unit = session.query(Unit).filter_by(id=unit_id).first()
            if not unit:
                flash('Юнит не найден', 'error')
                return redirect(url_for('index'))

            # Создать безопасное имя файла
            filename = secure_filename(f"unit_{unit_id}_{file.filename}")
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Сохранить файл
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            file.save(filepath)

            # Обновить путь в базе данных
            unit.image_path = filepath
            session.flush()

            unit_name = unit.name

        flash(f'Картинка для {unit_name} успешно загружена!', 'success')

    return redirect(url_for('index'))


@app.route('/delete/<int:unit_id>', methods=['POST'])
def delete_image(unit_id):
    """Удаление картинки юнита"""
    with db.get_session() as session:
        unit = session.query(Unit).filter_by(id=unit_id).first()
        if not unit:
            flash('Юнит не найден', 'error')
            return redirect(url_for('index'))

        image_path = unit.image_path
        unit_name = unit.name

        if image_path and os.path.exists(image_path):
            # Удалить файл
            os.remove(image_path)
            flash(f'Картинка для {unit_name} удалена', 'success')

        # Очистить путь в базе данных
        unit.image_path = None
        session.flush()

    return redirect(url_for('index'))


@app.route('/units')
def units_list():
    """Страница управления юнитами"""
    with db.get_session() as session:
        units = session.query(Unit).all()
        session.expunge_all()

    return render_template_string(UNITS_TEMPLATE, units=units, active_page='units')


@app.route('/units/create', methods=['GET', 'POST'])
def create_unit():
    """Создание нового юнита"""
    if request.method == 'POST':
        try:
            with db.get_session() as session:
                # Получить параметры юнита
                damage = int(request.form['damage'])
                defense = int(request.form['defense'])
                health = int(request.form['health'])
                unit_range = int(request.form['range'])
                speed = int(request.form['speed'])
                luck = float(request.form['luck'])
                crit_chance = float(request.form['crit_chance'])
                dodge_chance = float(request.form['dodge_chance'])

                # Автоматически рассчитать стоимость
                price = calculate_unit_price(damage, defense, health, unit_range, speed, luck, crit_chance)

                unit = Unit(
                    name=request.form['name'],
                    icon=request.form['icon'],
                    price=price,
                    damage=damage,
                    defense=defense,
                    health=health,
                    range=unit_range,
                    speed=speed,
                    luck=Decimal(str(luck)),
                    crit_chance=Decimal(str(crit_chance)),
                    dodge_chance=Decimal(str(dodge_chance))
                )
                session.add(unit)
                session.flush()

            flash(f'Юнит "{request.form["name"]}" успешно создан с автоматически рассчитанной стоимостью {price}!', 'success')
            return redirect(url_for('units_list'))
        except Exception as e:
            flash(f'Ошибка при создании юнита: {str(e)}', 'error')

    return render_template_string(UNIT_FORM_TEMPLATE, unit=None, active_page='units')


@app.route('/units/edit/<int:unit_id>', methods=['GET', 'POST'])
def edit_unit(unit_id):
    """Редактирование юнита"""
    with db.get_session() as session:
        unit = session.query(Unit).filter_by(id=unit_id).first()
        if not unit:
            flash('Юнит не найден', 'error')
            return redirect(url_for('units_list'))

        if request.method == 'POST':
            try:
                # Получить параметры юнита
                damage = int(request.form['damage'])
                defense = int(request.form['defense'])
                health = int(request.form['health'])
                unit_range = int(request.form['range'])
                speed = int(request.form['speed'])
                luck = float(request.form['luck'])
                crit_chance = float(request.form['crit_chance'])
                dodge_chance = float(request.form['dodge_chance'])

                # Автоматически рассчитать стоимость
                price = calculate_unit_price(damage, defense, health, unit_range, speed, luck, crit_chance)

                unit.name = request.form['name']
                unit.icon = request.form['icon']
                unit.price = price
                unit.damage = damage
                unit.defense = defense
                unit.health = health
                unit.range = unit_range
                unit.speed = speed
                unit.luck = Decimal(str(luck))
                unit.crit_chance = Decimal(str(crit_chance))
                unit.dodge_chance = Decimal(str(dodge_chance))
                session.flush()

                flash(f'Юнит "{unit.name}" успешно обновлен с автоматически рассчитанной стоимостью {price}!', 'success')
                return redirect(url_for('units_list'))
            except Exception as e:
                flash(f'Ошибка при обновлении юнита: {str(e)}', 'error')

        # Принудительно загружаем все атрибуты
        _ = unit.id
        _ = unit.name
        _ = unit.icon
        _ = unit.price
        _ = unit.damage
        _ = unit.defense
        _ = unit.health
        _ = unit.range
        _ = unit.speed
        _ = unit.luck
        _ = unit.crit_chance
        _ = unit.dodge_chance
        session.expunge_all()

    return render_template_string(UNIT_FORM_TEMPLATE, unit=unit, active_page='units')


@app.route('/units/delete/<int:unit_id>', methods=['POST'])
def delete_unit(unit_id):
    """Удаление юнита"""
    with db.get_session() as session:
        unit = session.query(Unit).filter_by(id=unit_id).first()
        if not unit:
            flash('Юнит не найден', 'error')
            return redirect(url_for('units_list'))

        unit_name = unit.name

        # Удалить картинку если есть
        if unit.image_path and os.path.exists(unit.image_path):
            os.remove(unit.image_path)

        session.delete(unit)
        session.flush()

    flash(f'Юнит "{unit_name}" удален', 'success')
    return redirect(url_for('units_list'))


@app.route('/help')
def help_page():
    """Страница справки"""
    return render_template_string(HELP_TEMPLATE, active_page='help')


@app.route('/export')
def export_units():
    """Экспорт юнитов в ZIP архив"""
    try:
        # Создать временную директорию для архива
        temp_dir = 'temp_export'
        os.makedirs(temp_dir, exist_ok=True)

        with db.get_session() as session:
            units = session.query(Unit).all()

            # Создать JSON файл с данными юнитов
            units_data = []
            for unit in units:
                unit_dict = {
                    'name': unit.name,
                    'icon': unit.icon,
                    'price': float(unit.price),
                    'damage': unit.damage,
                    'defense': unit.defense,
                    'health': unit.health,
                    'range': unit.range,
                    'speed': unit.speed,
                    'luck': float(unit.luck),
                    'crit_chance': float(unit.crit_chance),
                    'image_filename': os.path.basename(unit.image_path) if unit.image_path else None
                }
                units_data.append(unit_dict)

                # Копировать изображение если есть
                if unit.image_path and os.path.exists(unit.image_path):
                    image_filename = os.path.basename(unit.image_path)
                    shutil.copy(unit.image_path, os.path.join(temp_dir, image_filename))

        # Сохранить JSON
        with open(os.path.join(temp_dir, 'units.json'), 'w', encoding='utf-8') as f:
            json.dump(units_data, f, ensure_ascii=False, indent=2)

        # Создать ZIP архив
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)

        # Удалить временную директорию
        shutil.rmtree(temp_dir)

        # Отправить файл
        memory_file.seek(0)
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name='units_export.zip'
        )

    except Exception as e:
        flash(f'Ошибка при экспорте: {str(e)}', 'error')
        return redirect(url_for('units_list'))


@app.route('/import', methods=['GET', 'POST'])
def import_page():
    """Импорт юнитов из ZIP архива"""
    if request.method == 'POST':
        if 'archive' not in request.files:
            flash('Файл не выбран', 'error')
            return redirect(url_for('import_page'))

        file = request.files['archive']
        if file.filename == '':
            flash('Файл не выбран', 'error')
            return redirect(url_for('import_page'))

        try:
            # Создать временную директорию
            temp_dir = 'temp_import'
            os.makedirs(temp_dir, exist_ok=True)

            # Сохранить и распаковать архив
            zip_path = os.path.join(temp_dir, 'upload.zip')
            file.save(zip_path)

            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(temp_dir)

            # Прочитать JSON с данными юнитов
            json_path = os.path.join(temp_dir, 'units.json')
            if not os.path.exists(json_path):
                flash('Некорректный архив: отсутствует файл units.json', 'error')
                shutil.rmtree(temp_dir)
                return redirect(url_for('import_page'))

            with open(json_path, 'r', encoding='utf-8') as f:
                units_data = json.load(f)

            # Удалить всех существующих юнитов
            with db.get_session() as session:
                session.query(Unit).delete()
                session.flush()

                # Создать новых юнитов
                for unit_data in units_data:
                    # Определить путь к изображению
                    image_path = None
                    if unit_data.get('image_filename'):
                        src_image = os.path.join(temp_dir, unit_data['image_filename'])
                        if os.path.exists(src_image):
                            # Скопировать изображение в static/unit_images
                            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                            dest_image = os.path.join(app.config['UPLOAD_FOLDER'], unit_data['image_filename'])
                            shutil.copy(src_image, dest_image)
                            image_path = dest_image

                    unit = Unit(
                        name=unit_data['name'],
                        icon=unit_data['icon'],
                        price=Decimal(str(unit_data['price'])),
                        damage=unit_data['damage'],
                        defense=unit_data['defense'],
                        health=unit_data['health'],
                        range=unit_data['range'],
                        speed=unit_data['speed'],
                        luck=Decimal(str(unit_data['luck'])),
                        crit_chance=Decimal(str(unit_data['crit_chance'])),
                        image_path=image_path
                    )
                    session.add(unit)

                session.flush()

            # Удалить временную директорию
            shutil.rmtree(temp_dir)

            flash(f'Успешно импортировано {len(units_data)} юнитов!', 'success')
            return redirect(url_for('units_list'))

        except Exception as e:
            flash(f'Ошибка при импорте: {str(e)}', 'error')
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return redirect(url_for('import_page'))

    return render_template_string(IMPORT_TEMPLATE, active_page='units')


if __name__ == '__main__':
    # Получить порт из переменной окружения или использовать 80 по умолчанию
    port = int(os.getenv('PORT', 80))
    print(f"Запуск админки на http://0.0.0.0:{port}")
    print("Используйте Ctrl+C для остановки")
    app.run(host='0.0.0.0', port=port, debug=False)
