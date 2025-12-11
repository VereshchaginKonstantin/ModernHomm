#!/usr/bin/env python3
"""
Веб-интерфейс Flask для управления юнитами
"""

import os
import json
import zipfile
import shutil
import hashlib
from io import BytesIO
from functools import wraps
from flask import Flask, render_template_string, request, redirect, url_for, flash, send_file, session
from werkzeug.utils import secure_filename
from db import Database
from db.models import Unit, GameUser
from decimal import Decimal
from web_arena import arena_bp
from web_races import races_bp
from web_army import army_bp
from web_templates import get_web_version, get_bot_version, HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE

# Создать Flask приложение
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static/unit_images'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max file size

# Регистрация Blueprint для арены
app.register_blueprint(arena_bp)
# Регистрация Blueprint для управления расами
app.register_blueprint(races_bp)
# Регистрация Blueprint для управления армией
app.register_blueprint(army_bp)


@app.context_processor
def inject_versions():
    """Добавить версии и баланс пользователя во все шаблоны"""
    web_version = get_web_version()
    bot_version = get_bot_version()
    user_balance = None

    # Добавить баланс пользователя, если он авторизован
    if 'username' in session:
        try:
            from db.repository import Database
            db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
            db_instance = Database(db_url)
            with db_instance.get_session() as db_session:
                user = db_session.query(GameUser).filter_by(username=session['username']).first()
                if user:
                    user_balance = {
                        'coins': int(user.balance) if user.balance else 0,
                        'glory': user.glory or 0,
                        'crystals': user.crystals or 0
                    }
        except Exception:
            pass  # Если не удалось получить баланс, просто не показываем его

    return {
        'web_version': web_version,
        'bot_version': bot_version,
        'user_balance': user_balance
    }


def get_static_version():
    """Получить версию для cache busting статических файлов"""
    web_ver = get_web_version()
    # Создаём короткий хеш для URL
    return hashlib.md5(web_ver.encode()).hexdigest()[:8]


@app.template_filter('versioned')
def versioned_filter(url):
    """Jinja2 фильтр для добавления версии к URL статического файла.

    Использование в шаблоне: {{ '/static/file.css'|versioned }}
    Результат: /static/file.css?v=a1b2c3d4
    """
    version = get_static_version()
    separator = '&' if '?' in url else '?'
    return f"{url}{separator}v={version}"


@app.context_processor
def inject_static_version():
    """Добавить функцию versioned_static в контекст шаблонов"""
    def versioned_static(filename):
        """Генерирует URL для статического файла с версией для cache busting.

        Использование в шаблоне: {{ versioned_static('arena/css/arena.css') }}
        Результат: /static/arena/css/arena.css?v=a1b2c3d4
        """
        version = get_static_version()
        return f"/static/{filename}?v={version}"

    return {'versioned_static': versioned_static}

def calculate_unit_price(damage: int, defense: int, health: int, unit_range: int, speed: int, luck: float, crit_chance: float, dodge_chance: float, is_kamikaze: int = 0, is_flying: int = 0, counterattack_chance: float = 0) -> Decimal:
    """
    Автоматический расчет стоимости юнита по формуле:
    (Урон + Защита + Здоровье + 2*Дальность*(Урон + Защита) + Скорость*(Урон + Защита) +
     2*Летающий*(Урон + Защита) + 2*Удача*Урон + 2*Крит*Урон + 10*Уклонение*(Урон + Защита) + 10*Контратака*Урон)
    Для камикадзе: Урон/5 и Уклонение/50

    Args:
        damage: Урон юнита
        defense: Защита юнита
        health: Здоровье юнита
        unit_range: Дальность атаки
        speed: Скорость перемещения
        luck: Вероятность удачи (0-1)
        crit_chance: Вероятность критического удара (0-1)
        dodge_chance: Вероятность уклонения (0-0.9)
        is_kamikaze: Юнит-камикадзе (0 или 1)
        is_flying: Летающий юнит (0 или 1)
        counterattack_chance: Доля контратаки (0-1)

    Returns:
        Decimal: Рассчитанная стоимость
    """
    # Для камикадзе: урон делится на 5, уклонение делится на 50
    damage_value = damage / 5 if is_kamikaze else damage
    dodge_value = dodge_chance / 50 if is_kamikaze else dodge_chance

    # Бонус для летающих юнитов (могут двигаться через препятствия)
    flying_bonus = 2 * (damage_value + defense) if is_flying else 0

    price = (
        damage_value +
        defense +
        health +
        2 * unit_range * (damage_value + defense) +
        speed * (damage_value + defense) +
        flying_bonus +
        2 * luck * damage_value +
        2 * crit_chance * damage_value +
        10 * dodge_value * (damage_value + defense) +
        10 * counterattack_chance * damage_value
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


# API endpoint для получения версии (используется в smoke-тестах)
@app.route('/api/version')
def api_version():
    """Возвращает версии веб-интерфейса и бота в формате JSON"""
    from flask import jsonify
    return jsonify({
        'web_version': get_web_version(),
        'bot_version': get_bot_version(),
        'status': 'ok'
    })


# API endpoint для health check
@app.route('/api/health')
def api_health():
    """Проверка работоспособности веб-интерфейса"""
    from flask import jsonify
    from sqlalchemy import text
    try:
        # Проверяем подключение к БД
        with db.get_session() as session_db:
            session_db.execute(text('SELECT 1'))
        return jsonify({'status': 'healthy', 'database': 'connected'})
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500


# Decorator для проверки аутентификации
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Шаблон главной страницы (управление картинками)
IMAGES_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Веб-интерфейс - Управление картинками юнитов</title>
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
    {{ footer_html|safe }}
</body>
</html>
"""

# Шаблон для главной страницы (полный список юнитов)
COMPREHENSIVE_UNITS_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Список юнитов</title>
""" + BASE_STYLE + """
</head>
<body>
""" + HEADER_TEMPLATE + """
    <div class="content">
        <h1>Полный список юнитов</h1>

        {% for unit in units %}
        <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <div style="display: flex; gap: 20px; align-items: start;">
                {% if unit.has_image %}
                <div style="flex-shrink: 0;">
                    <img src="{{ '/' + unit.image_path }}" alt="{{ unit.name }}" style="width: 150px; height: 150px; object-fit: cover; border-radius: 8px; border: 2px solid #ddd;">
                </div>
                {% endif %}

                <div style="flex-grow: 1;">
                    <h2 style="margin: 0 0 10px 0; color: #2c3e50;">{{ unit.icon }} {{ unit.name }}</h2>

                    {% if unit.description %}
                    <p style="color: #7f8c8d; font-style: italic; margin: 0 0 15px 0;">{{ unit.description }}</p>
                    {% endif %}

                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px;">
                        <div><strong>💰 Цена:</strong> {{ unit.price }}</div>
                        <div><strong>⚔️ Урон:</strong> {{ unit.damage }}</div>
                        <div><strong>🛡️ Защита:</strong> {{ unit.defense }}</div>
                        <div><strong>❤️ Здоровье:</strong> {{ unit.health }}</div>
                        <div><strong>🎯 Дальность:</strong> {{ unit.range }}</div>
                        <div><strong>⚡ Скорость:</strong> {{ unit.speed }}</div>
                        <div><strong>🍀 Удача:</strong> {{ "%.2f"|format(unit.luck|float * 100) }}%</div>
                        <div><strong>💥 Крит:</strong> {{ "%.2f"|format(unit.crit_chance|float * 100) }}%</div>
                        <div><strong>🏃 Уклонение:</strong> {{ "%.2f"|format(unit.dodge_chance|float * 100) }}%</div>
                        {% if unit.is_kamikaze %}
                        <div><strong>💣 Камикадзе:</strong> Да</div>
                        {% endif %}
                        {% if unit.is_flying %}
                        <div><strong>🦅 Летающий:</strong> Да</div>
                        {% endif %}
                        {% if unit.counterattack_chance > 0 %}
                        <div><strong>🔄 Контратака:</strong> {{ "%.2f"|format(unit.counterattack_chance|float * 100) }}%</div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    {{ footer_html|safe }}
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
            <a href="{{ url_for('admin_create_unit') }}" class="btn btn-primary">Создать нового юнита</a>
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
                        <a href="{{ url_for('admin_edit_unit', unit_id=unit.id) }}" class="btn" style="background-color: #3498db; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; font-size: 12px;">Редактировать</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {{ footer_html|safe }}
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
                    <label>Описание</label>
                    <textarea name="description" class="form-control" rows="3" maxlength="1000" placeholder="Описание юнита...">{{ unit.description if unit and unit.description else '' }}</textarea>
                    <small class="form-text text-muted">Описание юнита (до 1000 символов)</small>
                </div>

                <div class="form-group">
                    <label>Цена (автоматически рассчитывается)</label>
                    <input type="text" class="form-control" value="{{ unit.price if unit else 'Рассчитается автоматически' }}" readonly disabled style="background-color: #e9ecef; cursor: not-allowed;">
                    <small class="form-text text-muted">Формула: (Урон + Защита + Здоровье + 2×Дальность×(Урон + Защита) + Скорость×(Урон + Защита) + 2×Удача×Урон + 2×Крит×Урон + 10×Уклонение×(Урон + Защита) + 10×Контратака×Урон). Для камикадзе: Урон/5 и Уклонение/50</small>
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
                    <label>Шанс уклонения (0-0.9, например 0.2 = 20%, максимум 90%) *</label>
                    <input type="number" name="dodge_chance" class="form-control" value="{{ unit.dodge_chance if unit else '0' }}" step="0.01" min="0" max="0.9" required>
                    <small class="form-text text-muted">Вероятность полностью избежать урона от атаки (максимум 90%)</small>
                </div>

                <div class="form-group form-check">
                    <input type="checkbox" name="is_kamikaze" class="form-check-input" id="is_kamikaze" value="1" {{ 'checked' if unit and unit.is_kamikaze else '' }}>
                    <label class="form-check-label" for="is_kamikaze">
                        💣 Камикадзе (урон за 1 юнита, -1 юнит после атаки)
                    </label>
                </div>

                <div class="form-group form-check">
                    <input type="checkbox" name="is_flying" class="form-check-input" id="is_flying" value="1" {{ 'checked' if unit and unit.is_flying else '' }}>
                    <label class="form-check-label" for="is_flying">
                        🦅 Летающий (может перемещаться через препятствия)
                    </label>
                </div>

                <div class="form-group">
                    <label>Доля контратаки (0-1, например 0.5 = 50%) *</label>
                    <input type="number" name="counterattack_chance" class="form-control" value="{{ unit.counterattack_chance if unit else '0' }}" step="0.01" min="0" max="1" required>
                    <small class="form-text text-muted">При получении урона наносит ответный урон с этим коэффициентом</small>
                </div>

                <div style="margin-top: 20px;">
                    <button type="submit" class="btn btn-primary">Сохранить</button>
                    <a href="{{ url_for('admin_units_list') }}" class="btn" style="background-color: #95a5a6; color: white; text-decoration: none; margin-left: 10px;">Отмена</a>
                </div>
            </form>
        </div>
    </div>
    {{ footer_html|safe }}
</body>
</html>
"""

# Шаблон страницы рейтинга
LEADERBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Рейтинг игроков - Веб-интерфейс</title>
    """ + BASE_STYLE + """
    <style>
        .leaderboard-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .leaderboard-table th,
        .leaderboard-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .leaderboard-table th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        .leaderboard-table tr:hover {
            background-color: #f5f5f5;
        }
        .rank-gold { color: #FFD700; font-weight: bold; }
        .rank-silver { color: #C0C0C0; font-weight: bold; }
        .rank-bronze { color: #CD7F32; font-weight: bold; }
        .pagination {
            margin-top: 20px;
            display: flex;
            justify-content: center;
            gap: 10px;
        }
        .pagination a {
            padding: 8px 12px;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
        .pagination a.active {
            background-color: #2980b9;
        }
        .pagination a:hover {
            background-color: #2980b9;
        }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """

    <div class="container">
        <h1>🏆 Рейтинг игроков</h1>

        <table class="leaderboard-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Игрок</th>
                    <th>🏆 Побед</th>
                    <th>💔 Поражений</th>
                    <th>📊 Винрейт</th>
                    <th>💰 Баланс</th>
                    <th>⚔️ Армия</th>
                </tr>
            </thead>
            <tbody>
                {% for player in players %}
                <tr>
                    <td class="{% if player.rank == 1 %}rank-gold{% elif player.rank == 2 %}rank-silver{% elif player.rank == 3 %}rank-bronze{% endif %}">
                        {{ player.rank }}
                    </td>
                    <td>{{ player.name }}</td>
                    <td>{{ player.wins }}</td>
                    <td>{{ player.losses }}</td>
                    <td>{{ "%.1f"|format(player.win_rate) }}%</td>
                    <td>{{ "%.2f"|format(player.balance) }}</td>
                    <td>{{ "%.2f"|format(player.army_value) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <!-- Пагинация -->
        {% if total_pages > 1 %}
        <div class="pagination">
            {% if page > 1 %}
            <a href="{{ url_for('leaderboard', page=page-1) }}">← Назад</a>
            {% endif %}

            <span style="padding: 8px 12px;">Страница {{ page }} из {{ total_pages }}</span>

            {% if page < total_pages %}
            <a href="{{ url_for('leaderboard', page=page+1) }}">Вперед →</a>
            {% endif %}
        </div>
        {% endif %}
    </div>
    {{ footer_html|safe }}
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

            <h2 style="margin-top: 40px;">Формула расчета стоимости юнита</h2>
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <p><strong>Для обычных юнитов:</strong></p>
                <div style="background-color: white; padding: 15px; border-radius: 4px; margin: 10px 0; font-family: monospace;">
                    <code>Цена = Урон + Защита + Здоровье + 100×Дальность + 100×Скорость + 1000×Удача + 1000×Крит + 5000×Уклонение + 1000×Контратака</code>
                </div>
                <p><strong>Для камикадзе:</strong></p>
                <div style="background-color: white; padding: 15px; border-radius: 4px; margin: 10px 0; font-family: monospace;">
                    <code>Цена = (Урон/5) + Защита + Здоровье + 100×Дальность + 100×Скорость + 1000×Удача + 1000×Крит + 100×Уклонение + 1000×Контратака</code>
                </div>
                <p style="color: #666; margin-top: 15px;"><em>Примечание: Для камикадзе урон учитывается с коэффициентом 1/5, а уклонение с коэффициентом 1/50 (5000/50=100), так как эти юниты жертвуют собой после атаки.</em></p>
            </div>

            <h2 style="margin-top: 40px;">Полная формула расчета урона</h2>
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; font-family: monospace;">
                <p><strong>1.</strong> Базовый урон со случайностью: <code>base = damage × random(0.9, 1.1)</code></p>
                <p><strong>2.</strong> Модификатор усталости: <code>fatigue_mod = 1 - (усталость / 100) × 0.3</code></p>
                <p><strong>3.</strong> Модификатор морали: <code>morale_mod = мораль / 100</code></p>
                <p><strong>4.</strong> Урон с модификаторами: <code>dmg = base × fatigue_mod × morale_mod</code></p>
                <p><strong>5.</strong> Проверка эффективности: <code>if эффективен: dmg = dmg × 1.5</code></p>
                <p><strong>6.</strong> Проверка критического удара: <code>crit_chance_final = crit_chance + (мораль/100)×0.2 - (усталость/100)×0.2</code></p>
                <p><strong>7.</strong> Если крит: <code>dmg = dmg × 2</code></p>
                <p><strong>8.</strong> Проверка удачи: <code>if random() < luck: dmg = dmg × 1.5</code></p>
                <p><strong>9.</strong> Умножение на количество атакующих: <code>dmg_multiplied = dmg × кол-во_атакующих</code></p>
                <p><strong>10.</strong> Расчет задетых юнитов: <code>задетые_юниты = 1 + floor(0.5 × (dmg_multiplied - здоровье) / здоровье)</code></p>
                <p><strong>11.</strong> Применение защиты: <code>defense_reduction = defense × |задетые_юниты|</code></p>
                <p><strong>12.</strong> Итоговый урон: <code>total_dmg = dmg_multiplied - defense_reduction</code></p>
            </div>

            <h2 style="margin-top: 40px;">Награда за победу</h2>
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <p><strong>При завершении игры победитель получает награду:</strong></p>
                <div style="background-color: white; padding: 15px; border-radius: 4px; margin: 10px 0; font-family: monospace;">
                    <code>Награда = (Стоимость убитых юнитов противника) × 0.9</code>
                </div>
                <p><strong>Чистая прибыль рассчитывается как:</strong></p>
                <div style="background-color: white; padding: 15px; border-radius: 4px; margin: 10px 0; font-family: monospace;">
                    <code>Чистая прибыль = Награда - Стоимость потерянных своих юнитов</code>
                </div>
                <p style="color: #666; margin-top: 15px;"><em>Примечание: Учитываются все убитые юниты обеих сторон. Победитель получает 90% от стоимости убитых юнитов противника, но теряет стоимость своих погибших юнитов.</em></p>
            </div>
        </div>
    </div>
    {{ footer_html|safe }}
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
                    <a href="{{ url_for('admin_units_list') }}" class="btn" style="background-color: #95a5a6; color: white; text-decoration: none; margin-left: 10px;">Отмена</a>
                </div>
            </form>
        </div>
    </div>
    {{ footer_html|safe }}
</body>
</html>
"""


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница логина"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Введите username и пароль', 'error')
            return redirect(url_for('login'))

        # Проверяем пользователя и пароль
        with db.get_session() as db_session:
            user = db_session.query(GameUser).filter_by(username=username).first()

            if not user:
                flash('Неверный username или пароль', 'error')
                return redirect(url_for('login'))

            if not user.password_hash:
                flash('Пароль не установлен. Используйте команду /password в боте.', 'error')
                return redirect(url_for('login'))

            # Проверяем хеш пароля
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if user.password_hash != password_hash:
                flash('Неверный username или пароль', 'error')
                return redirect(url_for('login'))

            # Успешный логин
            session['username'] = username
            session['user_id'] = user.id
            flash('Вход выполнен успешно!', 'success')
            return redirect(url_for('index'))

    # GET запрос - показываем форму
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Вход в веб-интерфейс</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background-color: #f5f5f5;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
            }
            .login-container {
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                width: 100%;
                max-width: 400px;
            }
            h1 {
                color: #2c3e50;
                text-align: center;
                margin-bottom: 30px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                color: #555;
                font-weight: bold;
            }
            input[type="text"],
            input[type="password"] {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
                box-sizing: border-box;
            }
            input[type="text"]:focus,
            input[type="password"]:focus {
                outline: none;
                border-color: #3498db;
            }
            button {
                width: 100%;
                padding: 12px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 16px;
                cursor: pointer;
                font-weight: bold;
            }
            button:hover {
                background-color: #2980b9;
            }
            .flash-messages {
                margin-bottom: 20px;
            }
            .flash {
                padding: 10px;
                border-radius: 4px;
                margin-bottom: 10px;
            }
            .flash.error {
                background-color: #e74c3c;
                color: white;
            }
            .flash.success {
                background-color: #2ecc71;
                color: white;
            }
            .info {
                text-align: center;
                margin-top: 20px;
                color: #7f8c8d;
                font-size: 14px;
            }
        </style>
    </head>
    <body>
        <div class="login-container">
            <h1>🔐 Вход в веб-интерфейс</h1>

            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    <div class="flash-messages">
                        {% for category, message in messages %}
                            <div class="flash {{ category }}">{{ message }}</div>
                        {% endfor %}
                    </div>
                {% endif %}
            {% endwith %}

            <form method="POST">
                <div class="form-group">
                    <label for="username">Username:</label>
                    <input type="text" id="username" name="username" required autofocus>
                </div>

                <div class="form-group">
                    <label for="password">Пароль:</label>
                    <input type="password" id="password" name="password" required>
                </div>

                <button type="submit">Войти</button>
            </form>

            <div class="info">
                Установите пароль через команду /password в боте
            </div>
        </div>
    </body>
    </html>
    """)


@app.route('/logout')
def logout():
    """Выход из системы"""
    session.pop('username', None)
    session.pop('user_id', None)
    flash('Вы вышли из системы', 'success')
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    """Главная страница - полный список юнитов"""
    with db.get_session() as session:
        units = session.query(Unit).all()

        # Принудительно загружаем все атрибуты перед закрытием сессии
        for unit in units:
            _ = unit.id
            _ = unit.name
            _ = unit.icon
            _ = unit.image_path
            _ = unit.description
            _ = unit.price
            _ = unit.damage
            _ = unit.defense
            _ = unit.range
            _ = unit.health
            _ = unit.speed
            _ = unit.luck
            _ = unit.crit_chance
            _ = unit.dodge_chance
            _ = unit.is_kamikaze
            _ = unit.is_flying
            _ = unit.counterattack_chance

        session.expunge_all()

    # Проверить наличие файлов для каждого юнита
    for unit in units:
        unit.has_image = unit.image_path and os.path.exists(unit.image_path)

    return render_template_string(COMPREHENSIVE_UNITS_TEMPLATE, units=units, active_page='home')


@app.route('/admin/images')
@login_required
def admin_images():
    """Управление картинками юнитов"""
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

    return render_template_string(IMAGES_TEMPLATE, units=units, stats=stats, active_page='images')


@app.route('/upload/<int:unit_id>', methods=['POST'])
@login_required
def upload_image(unit_id):
    """Загрузка картинки для юнита"""
    if 'image' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('admin_images'))

    file = request.files['image']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('admin_images'))

    if file:
        # Получить юнит
        with db.get_session() as session:
            unit = session.query(Unit).filter_by(id=unit_id).first()
            if not unit:
                flash('Юнит не найден', 'error')
                return redirect(url_for('admin_images'))

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

    return redirect(url_for('admin_images'))


@app.route('/delete/<int:unit_id>', methods=['POST'])
@login_required
def delete_image(unit_id):
    """Удаление картинки юнита"""
    with db.get_session() as session:
        unit = session.query(Unit).filter_by(id=unit_id).first()
        if not unit:
            flash('Юнит не найден', 'error')
            return redirect(url_for('admin_images'))

        image_path = unit.image_path
        unit_name = unit.name

        if image_path and os.path.exists(image_path):
            # Удалить файл
            os.remove(image_path)
            flash(f'Картинка для {unit_name} удалена', 'success')

        # Очистить путь в базе данных
        unit.image_path = None
        session.flush()

    return redirect(url_for('admin_images'))


@app.route('/admin/units')
@login_required
def admin_units_list():
    """Страница управления юнитами"""
    username = session.get('username')
    with db.get_session() as db_session:
        # Получить текущего пользователя
        current_user = db_session.query(GameUser).filter_by(username=username).first()

        # Показать базовые юниты (owner_id IS NULL) и юниты текущего пользователя
        if current_user:
            units = db_session.query(Unit).filter(
                (Unit.owner_id == None) | (Unit.owner_id == current_user.id)
            ).all()
        else:
            # Если пользователь не найден, показать только базовые юниты
            units = db_session.query(Unit).filter(Unit.owner_id == None).all()

        db_session.expunge_all()

    return render_template_string(UNITS_TEMPLATE, units=units, active_page='units', current_user_id=current_user.id if current_user else None, username=username)


@app.route('/admin/units/create', methods=['GET', 'POST'])
@login_required
def admin_create_unit():
    """Создание нового юнита"""
    username = session.get('username')
    if request.method == 'POST':
        try:
            with db.get_session() as db_session:
                # Получить текущего пользователя
                current_user = db_session.query(GameUser).filter_by(username=username).first()

                # Получить параметры юнита
                damage = int(request.form['damage'])
                defense = int(request.form['defense'])
                health = int(request.form['health'])
                unit_range = int(request.form['range'])
                speed = int(request.form['speed'])
                luck = float(request.form['luck'])
                crit_chance = float(request.form['crit_chance'])
                dodge_chance = float(request.form['dodge_chance'])
                is_kamikaze = 1 if request.form.get('is_kamikaze') else 0
                is_flying = 1 if request.form.get('is_flying') else 0
                counterattack_chance = float(request.form['counterattack_chance'])

                # Валидация: dodge_chance не более 0.9
                if dodge_chance > 0.9:
                    flash('Ошибка: Шанс уклонения не может быть больше 90% (0.9)', 'error')
                    return redirect(url_for('admin_create_unit'))

                # Автоматически рассчитать стоимость
                price = calculate_unit_price(damage, defense, health, unit_range, speed, luck, crit_chance, dodge_chance, is_kamikaze, is_flying, counterattack_chance)

                # Определить owner_id: для okarien - NULL (базовый юнит), для остальных - их ID
                owner_id = None if username == 'okarien' else (current_user.id if current_user else None)

                unit = Unit(
                    name=request.form['name'],
                    icon=request.form['icon'],
                    description=request.form.get('description', ''),
                    price=price,
                    damage=damage,
                    defense=defense,
                    health=health,
                    range=unit_range,
                    speed=speed,
                    luck=Decimal(str(luck)),
                    crit_chance=Decimal(str(crit_chance)),
                    dodge_chance=Decimal(str(dodge_chance)),
                    is_kamikaze=is_kamikaze,
                    is_flying=is_flying,
                    counterattack_chance=Decimal(str(counterattack_chance)),
                    owner_id=owner_id
                )
                db_session.add(unit)
                db_session.flush()

            flash(f'Юнит "{request.form["name"]}" успешно создан с автоматически рассчитанной стоимостью {price}!', 'success')
            return redirect(url_for('admin_units_list'))
        except Exception as e:
            flash(f'Ошибка при создании юнита: {str(e)}', 'error')

    return render_template_string(UNIT_FORM_TEMPLATE, unit=None, active_page='units')


@app.route('/admin/units/edit/<int:unit_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_unit(unit_id):
    """Редактирование юнита"""
    username = session.get('username')
    with db.get_session() as db_session:
        unit = db_session.query(Unit).filter_by(id=unit_id).first()
        if not unit:
            flash('Юнит не найден', 'error')
            return redirect(url_for('admin_units_list'))

        # Получить текущего пользователя
        current_user = db_session.query(GameUser).filter_by(username=username).first()

        # Проверить права на редактирование:
        # - okarien может редактировать базовые юниты (owner_id IS NULL) и свои
        # - остальные могут редактировать только свои юниты
        can_edit = False
        if username == 'okarien':
            can_edit = (unit.owner_id is None) or (current_user and unit.owner_id == current_user.id)
        else:
            can_edit = current_user and unit.owner_id == current_user.id

        if not can_edit:
            flash('У вас нет прав на редактирование этого юнита', 'error')
            return redirect(url_for('admin_units_list'))

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
                is_kamikaze = 1 if request.form.get('is_kamikaze') else 0
                is_flying = 1 if request.form.get('is_flying') else 0
                counterattack_chance = float(request.form['counterattack_chance'])

                # Валидация: dodge_chance не более 0.9
                if dodge_chance > 0.9:
                    flash('Ошибка: Шанс уклонения не может быть больше 90% (0.9)', 'error')
                    return redirect(url_for('admin_edit_unit', unit_id=unit_id))

                # Автоматически рассчитать стоимость
                price = calculate_unit_price(damage, defense, health, unit_range, speed, luck, crit_chance, dodge_chance, is_kamikaze, is_flying, counterattack_chance)

                unit.name = request.form['name']
                unit.icon = request.form['icon']
                unit.description = request.form.get('description', '')
                unit.price = price
                unit.damage = damage
                unit.defense = defense
                unit.health = health
                unit.range = unit_range
                unit.speed = speed
                unit.luck = Decimal(str(luck))
                unit.crit_chance = Decimal(str(crit_chance))
                unit.dodge_chance = Decimal(str(dodge_chance))
                unit.is_kamikaze = is_kamikaze
                unit.is_flying = is_flying
                unit.counterattack_chance = Decimal(str(counterattack_chance))
                db_session.flush()

                flash(f'Юнит "{unit.name}" успешно обновлен с автоматически рассчитанной стоимостью {price}!', 'success')
                return redirect(url_for('admin_units_list'))
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
        _ = unit.is_kamikaze
        _ = unit.is_flying
        _ = unit.counterattack_chance
        db_session.expunge_all()

    return render_template_string(UNIT_FORM_TEMPLATE, unit=unit, active_page='units')


@app.route('/leaderboard')
@login_required
def leaderboard():
    """Страница рейтинга игроков"""
    page = request.args.get('page', 1, type=int)
    per_page = 20  # Количество игроков на странице

    with db.get_session() as db_session:
        # Получаем всех игроков
        query = db_session.query(GameUser)

        # Общее количество игроков
        total_count = query.count()

        # Пагинация
        offset = (page - 1) * per_page
        players = query.order_by(GameUser.wins.desc()).offset(offset).limit(per_page).all()

        # Загружаем атрибуты для каждого игрока
        players_data = []
        for player in players:
            _ = player.id
            _ = player.name
            _ = player.wins
            _ = player.losses
            _ = player.balance

            # Рассчитываем винрейт
            total_games = player.wins + player.losses
            win_rate = (player.wins / total_games * 100) if total_games > 0 else 0

            # Рассчитываем стоимость армии
            player_units = db_session.query(UserUnit).filter_by(game_user_id=player.id).all()
            army_value = Decimal('0')
            for user_unit in player_units:
                unit = db_session.query(Unit).filter_by(id=user_unit.unit_type_id).first()
                if unit:
                    army_value += Decimal(str(unit.price)) * user_unit.count

            players_data.append({
                'rank': offset + len(players_data) + 1,
                'name': player.name,
                'wins': player.wins,
                'losses': player.losses,
                'win_rate': win_rate,
                'balance': float(player.balance),
                'army_value': float(army_value)
            })

        db_session.expunge_all()

    # Пагинация
    total_pages = (total_count + per_page - 1) // per_page

    return render_template_string(
        LEADERBOARD_TEMPLATE,
        players=players_data,
        page=page,
        total_pages=total_pages,
        active_page='leaderboard'
    )


@app.route('/help')
@login_required
def help_page():
    """Страница справки"""
    return render_template_string(HELP_TEMPLATE, active_page='help')


@app.route('/export')
@login_required
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
        return redirect(url_for('admin_units_list'))


@app.route('/import', methods=['GET', 'POST'])
@login_required
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
            return redirect(url_for('admin_units_list'))

        except Exception as e:
            flash(f'Ошибка при импорте: {str(e)}', 'error')
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return redirect(url_for('import_page'))

    return render_template_string(IMPORT_TEMPLATE, active_page='units')


if __name__ == '__main__':
    # Получить порт из переменной окружения или использовать 80 по умолчанию
    port = int(os.getenv('PORT', 80))
    print(f"Запуск веб-интерфейса на http://0.0.0.0:{port}")
    print("Используйте Ctrl+C для остановки")
    app.run(host='0.0.0.0', port=port, debug=False)
