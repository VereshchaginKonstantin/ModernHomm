#!/usr/bin/env python3
"""
Модуль управления армией для веб-интерфейса
"""

import os
import logging
from flask import Blueprint, render_template_string, session, redirect, url_for, flash, request
from functools import wraps

from db.models import GameUser, GameRace, RaceUnit, RaceUnitSkin, UnitLevel, UserRace, UserRaceUnit, Army, ArmyUnit
from db.repository import Database
from web.templates import HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE, get_web_version, get_bot_version

logger = logging.getLogger(__name__)

# Blueprint для армии
army_bp = Blueprint('army', __name__, url_prefix='/army')

# Получаем подключение к БД
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
db = Database(db_url)


def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Требуется авторизация', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# Шаблон списка пользовательских рас
USER_RACES_LIST_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Мои расы</title>
''' + BASE_STYLE + '''
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>🏰 Мои расы</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div style="margin-bottom: 20px;">
            <a href="{{ url_for('army.select_race') }}" class="btn btn-success">➕ Выбрать новую расу</a>
        </div>

        {% if user_races %}
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Раса</th>
                    <th>Юнитов настроено</th>
                    <th>Дата создания</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                {% for ur in user_races %}
                <tr>
                    <td>{{ ur.id }}</td>
                    <td>{{ ur.race.name }}</td>
                    <td>{{ ur.units_count }} / 7</td>
                    <td>{{ ur.created_at.strftime('%d.%m.%Y %H:%M') }}</td>
                    <td>
                        <a href="{{ url_for('army.edit_user_race', user_race_id=ur.id) }}" class="btn btn-edit">✏️ Редактировать</a>
                        <a href="{{ url_for('army.delete_user_race', user_race_id=ur.id) }}" class="btn btn-danger" onclick="return confirm('Удалить эту расу?');">🗑️ Удалить</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="section">
            <p>У вас пока нет настроенных рас. Выберите расу, чтобы начать!</p>
        </div>
        {% endif %}
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
'''


# Шаблон выбора расы
SELECT_RACE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Выбор расы</title>
''' + BASE_STYLE + '''
    <style>
        .races-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .race-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .race-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .race-card h3 {
            margin-top: 0;
            color: #2c3e50;
        }
        .race-card .description {
            color: #666;
            margin: 10px 0;
            min-height: 60px;
        }
        .race-card .free-badge {
            display: inline-block;
            background: #27ae60;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            margin-left: 10px;
        }
        .race-card .units-preview {
            display: flex;
            gap: 5px;
            margin: 15px 0;
            font-size: 24px;
        }
        .race-card .already-owned {
            background: #f0f0f0;
            opacity: 0.7;
        }
        .race-card .owned-badge {
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            margin-left: 10px;
        }
    </style>
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>🏰 Выбор расы</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <p style="margin-bottom: 20px;">
            <a href="{{ url_for('army.user_races_list') }}" class="btn btn-secondary">← Назад к моим расам</a>
        </p>

        <div class="races-grid">
            {% for race in races %}
            <div class="race-card {{ 'already-owned' if race.is_owned else '' }}">
                <h3>
                    {{ race.name }}
                    {% if race.is_free %}<span class="free-badge">Бесплатная</span>{% endif %}
                    {% if race.is_owned %}<span class="owned-badge">Уже выбрана</span>{% endif %}
                </h3>
                <div class="description">{{ race.description or 'Без описания' }}</div>
                <div class="units-preview">
                    {% for unit in race.race_units[:7] %}
                    <span title="{{ unit.name }} (ур. {{ unit.unit_level.level if unit.unit_level else '?' }})">{{ unit.unit_level.icon if unit.unit_level else '🎮' }}</span>
                    {% endfor %}
                </div>
                {% if not race.is_owned %}
                <form method="POST" action="{{ url_for('army.create_user_race', race_id=race.id) }}" style="display: inline;">
                    <button type="submit" class="btn btn-success">Выбрать расу</button>
                </form>
                {% else %}
                <a href="{{ url_for('army.edit_user_race', user_race_id=race.user_race_id) }}" class="btn btn-edit">✏️ Редактировать</a>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
'''


# Шаблон редактирования пользовательской расы
EDIT_USER_RACE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Редактирование расы: {{ user_race.race.name }}</title>
''' + BASE_STYLE + '''
    <style>
        .units-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .unit-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .unit-card h3 {
            margin-top: 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .unit-card .level-badge {
            background: #3498db;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
        }
        .unit-card .unit-icon {
            font-size: 32px;
        }
        .unit-card .stats {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            margin: 15px 0;
            font-size: 13px;
        }
        .unit-card .stats .stat {
            display: flex;
            justify-content: space-between;
            padding: 5px;
            background: #f8f9fa;
            border-radius: 3px;
        }
        .unit-card .stat-label {
            color: #666;
        }
        .unit-card .stat-value {
            font-weight: bold;
            color: #2c3e50;
        }
        .unit-card .skin-info {
            background: #f0f8ff;
            padding: 10px;
            border-radius: 5px;
            margin-top: 10px;
        }
        .unit-card .skin-info h4 {
            margin: 0 0 5px 0;
            color: #2c3e50;
        }
        .unit-card .no-skin {
            background: #fff3cd;
            color: #856404;
        }
        .unit-card .badges {
            display: flex;
            gap: 5px;
            margin-top: 5px;
        }
        .unit-card .badge {
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
        }
        .unit-card .badge-flying {
            background: #e3f2fd;
            color: #1976d2;
        }
        .unit-card .badge-kamikaze {
            background: #ffebee;
            color: #c62828;
        }
        .not-configured {
            border: 2px dashed #ffc107;
        }
        .configured {
            border-left: 4px solid #28a745;
        }
    </style>
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>🏰 {{ user_race.race.name }}</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <p style="margin-bottom: 20px;">
            <a href="{{ url_for('army.user_races_list') }}" class="btn btn-secondary">← Назад к моим расам</a>
        </p>

        <div class="section">
            <p><strong>Описание:</strong> {{ user_race.race.description or 'Нет описания' }}</p>
            <p><strong>Настроено юнитов:</strong> {{ configured_count }} / 7</p>
        </div>

        <h2>⚔️ Юниты расы</h2>
        <p>Для каждого юнита необходимо выбрать скин. Юниты без скина отмечены жёлтой рамкой.</p>

        <div class="units-list">
            {% for unit_data in units %}
            <div class="unit-card {{ 'configured' if unit_data.user_unit else 'not-configured' }}">
                <h3>
                    <span class="unit-icon">{{ unit_data.race_unit.unit_level.icon if unit_data.race_unit.unit_level else '🎮' }}</span>
                    {{ unit_data.race_unit.name }}
                    <span class="level-badge">Ур. {{ unit_data.race_unit.unit_level.level if unit_data.race_unit.unit_level else '?' }}</span>
                </h3>

                <div class="badges">
                    {% if unit_data.race_unit.is_flying %}
                    <span class="badge badge-flying">✈️ Летающий</span>
                    {% endif %}
                    {% if unit_data.race_unit.is_kamikaze %}
                    <span class="badge badge-kamikaze">💥 Камикадзе</span>
                    {% endif %}
                </div>

                {% if unit_data.user_unit %}
                <div class="stats">
                    <div class="stat">
                        <span class="stat-label">⚔️ Атака</span>
                        <span class="stat-value">{{ unit_data.user_unit.attack }}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">🛡️ Защита</span>
                        <span class="stat-value">{{ unit_data.user_unit.defense }}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">💥 Урон</span>
                        <span class="stat-value">{{ unit_data.user_unit.min_damage }}-{{ unit_data.user_unit.max_damage }}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">❤️ Здоровье</span>
                        <span class="stat-value">{{ unit_data.user_unit.health }}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">👟 Скорость</span>
                        <span class="stat-value">{{ unit_data.user_unit.speed }}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">⚡ Инициатива</span>
                        <span class="stat-value">{{ unit_data.user_unit.initiative }}</span>
                    </div>
                </div>

                <div class="skin-info">
                    <h4>🎨 Текущий скин:</h4>
                    <p>{{ unit_data.user_unit.skin.icon }} {{ unit_data.user_unit.skin.name }}</p>
                </div>

                <div style="margin-top: 15px;">
                    <a href="{{ url_for('army.edit_user_race_unit', user_race_id=user_race.id, race_unit_id=unit_data.race_unit.id) }}" class="btn btn-edit">✏️ Изменить</a>
                </div>
                {% else %}
                <div class="skin-info no-skin">
                    <h4>⚠️ Юнит не настроен</h4>
                    <p>Выберите скин для этого юнита</p>
                </div>

                <div style="margin-top: 15px;">
                    <a href="{{ url_for('army.edit_user_race_unit', user_race_id=user_race.id, race_unit_id=unit_data.race_unit.id) }}" class="btn btn-success">➕ Настроить</a>
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
'''


# Шаблон редактирования юнита пользовательской расы
EDIT_USER_RACE_UNIT_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Настройка юнита: {{ race_unit.name }}</title>
''' + BASE_STYLE + '''
    <style>
        .skins-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }
        .skin-card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            cursor: pointer;
            transition: all 0.2s;
            border: 2px solid transparent;
        }
        .skin-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .skin-card.selected {
            border-color: #28a745;
            background: #f0fff0;
        }
        .skin-card .skin-icon {
            font-size: 48px;
            text-align: center;
            margin-bottom: 10px;
        }
        .skin-card .skin-name {
            font-weight: bold;
            text-align: center;
            color: #2c3e50;
        }
        .skin-card .skin-desc {
            color: #666;
            font-size: 13px;
            text-align: center;
            margin-top: 5px;
        }
        .skin-card input[type="radio"] {
            display: none;
        }
        .stats-form {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-top: 20px;
        }
        .stats-form h3 {
            margin-top: 0;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
        }
        .no-skins-warning {
            background: #fff3cd;
            color: #856404;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .final-stats-box {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        .final-stats-box h3 {
            margin-top: 0;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .final-stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 10px;
        }
        .final-stat-item {
            background: rgba(255,255,255,0.15);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        .final-stat-label {
            font-size: 12px;
            opacity: 0.9;
            margin-bottom: 5px;
        }
        .final-stat-value {
            font-size: 18px;
            font-weight: bold;
        }
        .final-stat-formula {
            font-size: 10px;
            opacity: 0.7;
            margin-top: 3px;
        }
        .boost-input-group {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .boost-input-group .base-value {
            color: #666;
            font-size: 13px;
            white-space: nowrap;
        }
        .boost-input-group input {
            width: 80px;
        }
    </style>
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>{{ race_unit.unit_level.icon if race_unit.unit_level else '🎮' }} {{ race_unit.name }} (Ур. {{ race_unit.unit_level.level if race_unit.unit_level else '?' }})</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <p style="margin-bottom: 20px;">
            <a href="{{ url_for('army.edit_user_race', user_race_id=user_race_id) }}" class="btn btn-secondary">← Назад к расе</a>
        </p>

        <!-- Итоговые характеристики -->
        <div class="final-stats-box">
            <h3>📊 Итоговые характеристики</h3>
            <div class="final-stats-grid">
                <div class="final-stat-item">
                    <div class="final-stat-label">⚔️ Атака</div>
                    <div class="final-stat-value" id="final-attack">{{ race_unit.attack + (user_unit.attack_boost if user_unit else 0) }}</div>
                    <div class="final-stat-formula"><span id="base-attack">{{ race_unit.attack }}</span> + <span id="boost-attack-display">{{ user_unit.attack_boost if user_unit else 0 }}</span></div>
                </div>
                <div class="final-stat-item">
                    <div class="final-stat-label">🛡️ Защита</div>
                    <div class="final-stat-value" id="final-defense">{{ race_unit.defense + (user_unit.defense_boost if user_unit else 0) }}</div>
                    <div class="final-stat-formula"><span id="base-defense">{{ race_unit.defense }}</span> + <span id="boost-defense-display">{{ user_unit.defense_boost if user_unit else 0 }}</span></div>
                </div>
                <div class="final-stat-item">
                    <div class="final-stat-label">💥 Мин. урон</div>
                    <div class="final-stat-value" id="final-min_damage">{{ race_unit.min_damage + (user_unit.min_damage_boost if user_unit else 0) }}</div>
                    <div class="final-stat-formula"><span id="base-min_damage">{{ race_unit.min_damage }}</span> + <span id="boost-min_damage-display">{{ user_unit.min_damage_boost if user_unit else 0 }}</span></div>
                </div>
                <div class="final-stat-item">
                    <div class="final-stat-label">💥 Макс. урон</div>
                    <div class="final-stat-value" id="final-max_damage">{{ race_unit.max_damage + (user_unit.max_damage_boost if user_unit else 0) }}</div>
                    <div class="final-stat-formula"><span id="base-max_damage">{{ race_unit.max_damage }}</span> + <span id="boost-max_damage-display">{{ user_unit.max_damage_boost if user_unit else 0 }}</span></div>
                </div>
                <div class="final-stat-item">
                    <div class="final-stat-label">❤️ Здоровье</div>
                    <div class="final-stat-value" id="final-health">{{ race_unit.health + (user_unit.health_boost if user_unit else 0) }}</div>
                    <div class="final-stat-formula"><span id="base-health">{{ race_unit.health }}</span> + <span id="boost-health-display">{{ user_unit.health_boost if user_unit else 0 }}</span></div>
                </div>
                <div class="final-stat-item">
                    <div class="final-stat-label">👟 Скорость</div>
                    <div class="final-stat-value" id="final-speed">{{ race_unit.speed + (user_unit.speed_boost if user_unit else 0) }}</div>
                    <div class="final-stat-formula"><span id="base-speed">{{ race_unit.speed }}</span> + <span id="boost-speed-display">{{ user_unit.speed_boost if user_unit else 0 }}</span></div>
                </div>
                <div class="final-stat-item">
                    <div class="final-stat-label">⚡ Инициатива</div>
                    <div class="final-stat-value" id="final-initiative">{{ race_unit.initiative + (user_unit.initiative_boost if user_unit else 0) }}</div>
                    <div class="final-stat-formula"><span id="base-initiative">{{ race_unit.initiative }}</span> + <span id="boost-initiative-display">{{ user_unit.initiative_boost if user_unit else 0 }}</span></div>
                </div>
                <div class="final-stat-item">
                    <div class="final-stat-label">🎯 Дальность</div>
                    <div class="final-stat-value" id="final-range">{{ race_unit.range + (user_unit.range_boost if user_unit else 0) }}</div>
                    <div class="final-stat-formula"><span id="base-range">{{ race_unit.range }}</span> + <span id="boost-range-display">{{ user_unit.range_boost if user_unit else 0 }}</span></div>
                </div>
            </div>
        </div>

        {% if skins %}
        <form method="POST">
            <h2>🎨 Выберите скин</h2>
            <div class="skins-grid">
                {% for skin in skins %}
                <label class="skin-card {{ 'selected' if current_skin_id == skin.id else '' }}">
                    <input type="radio" name="skin_id" value="{{ skin.id }}" {{ 'checked' if current_skin_id == skin.id else '' }} required onchange="this.closest('.skin-card').classList.add('selected'); document.querySelectorAll('.skin-card').forEach(c => { if(c !== this.closest('.skin-card')) c.classList.remove('selected'); });">
                    <div class="skin-icon">{{ skin.icon }}</div>
                    <div class="skin-name">{{ skin.name }}</div>
                    {% if skin.description %}
                    <div class="skin-desc">{{ skin.description }}</div>
                    {% endif %}
                </label>
                {% endfor %}
            </div>

            <div class="stats-form">
                <h3>📈 Бусты характеристик</h3>
                <p style="color: #666; margin-bottom: 15px;">Бусты добавляются к базовым характеристикам юнита расы. По умолчанию все бусты равны 0.</p>

                <div class="stats-grid">
                    <div class="form-group">
                        <label>⚔️ Буст атаки:</label>
                        <div class="boost-input-group">
                            <span class="base-value">(база: {{ race_unit.attack }})</span>
                            <input type="number" name="attack_boost" id="attack_boost" class="form-control" value="{{ user_unit.attack_boost if user_unit else 0 }}" min="-100" max="100" onchange="updateFinalStats()">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>🛡️ Буст защиты:</label>
                        <div class="boost-input-group">
                            <span class="base-value">(база: {{ race_unit.defense }})</span>
                            <input type="number" name="defense_boost" id="defense_boost" class="form-control" value="{{ user_unit.defense_boost if user_unit else 0 }}" min="-100" max="100" onchange="updateFinalStats()">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>💥 Буст мин. урона:</label>
                        <div class="boost-input-group">
                            <span class="base-value">(база: {{ race_unit.min_damage }})</span>
                            <input type="number" name="min_damage_boost" id="min_damage_boost" class="form-control" value="{{ user_unit.min_damage_boost if user_unit else 0 }}" min="-1000" max="1000" onchange="updateFinalStats()">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>💥 Буст макс. урона:</label>
                        <div class="boost-input-group">
                            <span class="base-value">(база: {{ race_unit.max_damage }})</span>
                            <input type="number" name="max_damage_boost" id="max_damage_boost" class="form-control" value="{{ user_unit.max_damage_boost if user_unit else 0 }}" min="-1000" max="1000" onchange="updateFinalStats()">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>❤️ Буст здоровья:</label>
                        <div class="boost-input-group">
                            <span class="base-value">(база: {{ race_unit.health }})</span>
                            <input type="number" name="health_boost" id="health_boost" class="form-control" value="{{ user_unit.health_boost if user_unit else 0 }}" min="-10000" max="10000" onchange="updateFinalStats()">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>👟 Буст скорости:</label>
                        <div class="boost-input-group">
                            <span class="base-value">(база: {{ race_unit.speed }})</span>
                            <input type="number" name="speed_boost" id="speed_boost" class="form-control" value="{{ user_unit.speed_boost if user_unit else 0 }}" min="-20" max="20" onchange="updateFinalStats()">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>⚡ Буст инициативы:</label>
                        <div class="boost-input-group">
                            <span class="base-value">(база: {{ race_unit.initiative }})</span>
                            <input type="number" name="initiative_boost" id="initiative_boost" class="form-control" value="{{ user_unit.initiative_boost if user_unit else 0 }}" min="-100" max="100" onchange="updateFinalStats()">
                        </div>
                    </div>
                    <div class="form-group">
                        <label>🎯 Буст дальности:</label>
                        <div class="boost-input-group">
                            <span class="base-value">(база: {{ race_unit.range }})</span>
                            <input type="number" name="range_boost" id="range_boost" class="form-control" value="{{ user_unit.range_boost if user_unit else 0 }}" min="-10" max="10" onchange="updateFinalStats()">
                        </div>
                    </div>
                </div>
            </div>

            <div style="margin-top: 20px;">
                <button type="submit" class="btn btn-success">💾 Сохранить</button>
                <a href="{{ url_for('army.edit_user_race', user_race_id=user_race_id) }}" class="btn btn-secondary">Отмена</a>
            </div>
        </form>

        <script>
            // Базовые значения из race_unit
            const baseStats = {
                attack: {{ race_unit.attack }},
                defense: {{ race_unit.defense }},
                min_damage: {{ race_unit.min_damage }},
                max_damage: {{ race_unit.max_damage }},
                health: {{ race_unit.health }},
                speed: {{ race_unit.speed }},
                initiative: {{ race_unit.initiative }},
                range: {{ race_unit.range }}
            };

            function updateFinalStats() {
                const stats = ['attack', 'defense', 'min_damage', 'max_damage', 'health', 'speed', 'initiative', 'range'];

                stats.forEach(stat => {
                    const boostInput = document.getElementById(stat + '_boost');
                    const boost = parseInt(boostInput.value) || 0;
                    const base = baseStats[stat];
                    const final = base + boost;

                    document.getElementById('final-' + stat).textContent = final;
                    document.getElementById('boost-' + stat + '-display').textContent = boost >= 0 ? boost : boost;
                });
            }

            // Привязываем обновление к изменению любого буста
            document.querySelectorAll('input[name$="_boost"]').forEach(input => {
                input.addEventListener('input', updateFinalStats);
            });
        </script>
        {% else %}
        <div class="no-skins-warning">
            <h3>⚠️ Нет доступных скинов</h3>
            <p>Для этого юнита ещё не созданы скины. Обратитесь к администратору.</p>
            <a href="{{ url_for('army.edit_user_race', user_race_id=user_race_id) }}" class="btn btn-secondary">← Назад</a>
        </div>
        {% endif %}
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
'''


@army_bp.route('/races')
@login_required
def user_races_list():
    """Список пользовательских рас"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('index'))

        user_races = session_db.query(UserRace).filter(UserRace.user_id == game_user.id).all()

        # Подсчитываем количество настроенных юнитов для каждой расы
        user_races_data = []
        for ur in user_races:
            units_count = session_db.query(UserRaceUnit).filter(UserRaceUnit.user_race_id == ur.id).count()
            ur.units_count = units_count
            user_races_data.append(ur)

        return render_template_string(
            USER_RACES_LIST_TEMPLATE,
            active_page='user_race',
            user_races=user_races_data,
            
        )


@army_bp.route('/races/select')
@login_required
def select_race():
    """Выбор игровой расы"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('index'))

        # Получаем все игровые расы
        races = session_db.query(GameRace).all()

        # Получаем уже выбранные расы пользователя
        user_race_ids = [ur.race_id for ur in session_db.query(UserRace).filter(UserRace.user_id == game_user.id).all()]

        # Помечаем, какие расы уже выбраны
        for race in races:
            race.is_owned = race.id in user_race_ids
            if race.is_owned:
                ur = session_db.query(UserRace).filter(
                    UserRace.user_id == game_user.id,
                    UserRace.race_id == race.id
                ).first()
                race.user_race_id = ur.id if ur else None

        return render_template_string(
            SELECT_RACE_TEMPLATE,
            active_page='user_race',
            races=races,
            
        )


@army_bp.route('/races/create/<int:race_id>', methods=['POST'])
@login_required
def create_user_race(race_id):
    """Создание пользовательской расы"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('army.select_race'))

        # Проверяем, что раса существует
        race = session_db.query(GameRace).filter(GameRace.id == race_id).first()
        if not race:
            flash('Раса не найдена', 'error')
            return redirect(url_for('army.select_race'))

        # Проверяем, что у пользователя ещё нет этой расы
        existing = session_db.query(UserRace).filter(
            UserRace.user_id == game_user.id,
            UserRace.race_id == race_id
        ).first()
        if existing:
            flash('Вы уже выбрали эту расу', 'error')
            return redirect(url_for('army.edit_user_race', user_race_id=existing.id))

        # Создаём пользовательскую расу
        user_race = UserRace(user_id=game_user.id, race_id=race_id)
        session_db.add(user_race)
        session_db.flush()  # Получаем ID user_race

        # Получаем все юниты расы и создаём для каждого UserRaceUnit с дефолтным скином
        race_units = session_db.query(RaceUnit).filter(RaceUnit.race_id == race_id).all()
        units_created = 0

        for race_unit in race_units:
            # Ищем первый (дефолтный) скин для этого юнита расы
            default_skin = session_db.query(RaceUnitSkin).filter(
                RaceUnitSkin.race_unit_id == race_unit.id
            ).first()

            if default_skin:
                # Создаём UserRaceUnit с дефолтным скином и нулевыми бустами
                user_race_unit = UserRaceUnit(
                    user_race_id=user_race.id,
                    race_unit_id=race_unit.id,
                    skin_id=default_skin.id,
                    attack_boost=0,
                    defense_boost=0,
                    min_damage_boost=0,
                    max_damage_boost=0,
                    health_boost=0,
                    speed_boost=0,
                    initiative_boost=0,
                    range_boost=0
                )
                session_db.add(user_race_unit)
                units_created += 1

        session_db.commit()

        if units_created > 0:
            flash(f'Раса "{race.name}" успешно выбрана! Создано {units_created} юнитов с дефолтными скинами.', 'success')
        else:
            flash(f'Раса "{race.name}" успешно выбрана! Настройте скины для юнитов.', 'success')
        return redirect(url_for('army.edit_user_race', user_race_id=user_race.id))


@army_bp.route('/races/<int:user_race_id>')
@login_required
def edit_user_race(user_race_id):
    """Редактирование пользовательской расы"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('index'))

        # Получаем пользовательскую расу
        user_race = session_db.query(UserRace).filter(
            UserRace.id == user_race_id,
            UserRace.user_id == game_user.id
        ).first()

        if not user_race:
            flash('Раса не найдена', 'error')
            return redirect(url_for('army.user_races_list'))

        # Получаем все юниты расы (7 уровней)
        race_units = session_db.query(RaceUnit).filter(
            RaceUnit.race_id == user_race.race_id
        ).order_by(RaceUnit.unit_level_id).all()

        # Получаем настроенные юниты пользователя
        user_units = {uu.race_unit_id: uu for uu in session_db.query(UserRaceUnit).filter(
            UserRaceUnit.user_race_id == user_race_id
        ).all()}

        # Собираем данные для отображения
        units_data = []
        for ru in race_units:
            units_data.append({
                'race_unit': ru,
                'user_unit': user_units.get(ru.id)
            })

        configured_count = len(user_units)

        return render_template_string(
            EDIT_USER_RACE_TEMPLATE,
            active_page='user_race',
            user_race=user_race,
            units=units_data,
            configured_count=configured_count,
            
        )


@army_bp.route('/races/<int:user_race_id>/unit/<int:race_unit_id>', methods=['GET', 'POST'])
@login_required
def edit_user_race_unit(user_race_id, race_unit_id):
    """Редактирование юнита пользовательской расы"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('index'))

        # Проверяем, что пользовательская раса принадлежит пользователю
        user_race = session_db.query(UserRace).filter(
            UserRace.id == user_race_id,
            UserRace.user_id == game_user.id
        ).first()

        if not user_race:
            flash('Раса не найдена', 'error')
            return redirect(url_for('army.user_races_list'))

        # Получаем юнит расы
        race_unit = session_db.query(RaceUnit).filter(RaceUnit.id == race_unit_id).first()
        if not race_unit or race_unit.race_id != user_race.race_id:
            flash('Юнит не найден', 'error')
            return redirect(url_for('army.edit_user_race', user_race_id=user_race_id))

        # Получаем скины для этого юнита
        skins = session_db.query(RaceUnitSkin).filter(RaceUnitSkin.race_unit_id == race_unit_id).all()

        # Получаем текущие настройки юнита пользователя
        user_unit = session_db.query(UserRaceUnit).filter(
            UserRaceUnit.user_race_id == user_race_id,
            UserRaceUnit.race_unit_id == race_unit_id
        ).first()

        current_skin_id = user_unit.skin_id if user_unit else None

        if request.method == 'POST':
            skin_id = request.form.get('skin_id')
            if not skin_id:
                flash('Выберите скин', 'error')
                return redirect(url_for('army.edit_user_race_unit', user_race_id=user_race_id, race_unit_id=race_unit_id))

            # Проверяем, что скин существует
            skin = session_db.query(RaceUnitSkin).filter(RaceUnitSkin.id == skin_id).first()
            if not skin or skin.race_unit_id != race_unit_id:
                flash('Выбранный скин недоступен', 'error')
                return redirect(url_for('army.edit_user_race_unit', user_race_id=user_race_id, race_unit_id=race_unit_id))

            # Получаем бусты из формы (по умолчанию 0)
            attack_boost = int(request.form.get('attack_boost', 0))
            defense_boost = int(request.form.get('defense_boost', 0))
            min_damage_boost = int(request.form.get('min_damage_boost', 0))
            max_damage_boost = int(request.form.get('max_damage_boost', 0))
            health_boost = int(request.form.get('health_boost', 0))
            speed_boost = int(request.form.get('speed_boost', 0))
            initiative_boost = int(request.form.get('initiative_boost', 0))
            range_boost = int(request.form.get('range_boost', 0))

            if user_unit:
                # Обновляем существующего юнита
                user_unit.skin_id = skin_id
                user_unit.attack_boost = attack_boost
                user_unit.defense_boost = defense_boost
                user_unit.min_damage_boost = min_damage_boost
                user_unit.max_damage_boost = max_damage_boost
                user_unit.health_boost = health_boost
                user_unit.speed_boost = speed_boost
                user_unit.initiative_boost = initiative_boost
                user_unit.range_boost = range_boost
            else:
                # Создаём нового юнита
                user_unit = UserRaceUnit(
                    user_race_id=user_race_id,
                    race_unit_id=race_unit_id,
                    skin_id=skin_id,
                    attack_boost=attack_boost,
                    defense_boost=defense_boost,
                    min_damage_boost=min_damage_boost,
                    max_damage_boost=max_damage_boost,
                    health_boost=health_boost,
                    speed_boost=speed_boost,
                    initiative_boost=initiative_boost,
                    range_boost=range_boost
                )
                session_db.add(user_unit)

            session_db.commit()
            flash(f'Юнит "{race_unit.name}" успешно настроен!', 'success')
            return redirect(url_for('army.edit_user_race', user_race_id=user_race_id))

        return render_template_string(
            EDIT_USER_RACE_UNIT_TEMPLATE,
            active_page='user_race',
            user_race_id=user_race_id,
            race_unit=race_unit,
            skins=skins,
            user_unit=user_unit,
            current_skin_id=current_skin_id,
            
        )


@army_bp.route('/races/<int:user_race_id>/delete')
@login_required
def delete_user_race(user_race_id):
    """Удаление пользовательской расы"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('index'))

        user_race = session_db.query(UserRace).filter(
            UserRace.id == user_race_id,
            UserRace.user_id == game_user.id
        ).first()

        if not user_race:
            flash('Раса не найдена', 'error')
            return redirect(url_for('army.user_races_list'))

        race_name = user_race.race.name
        session_db.delete(user_race)
        session_db.commit()

        flash(f'Раса "{race_name}" удалена', 'success')
        return redirect(url_for('army.user_races_list'))


def calculate_race_unit_prestige(race_unit, user_race_unit=None):
    """Calculate prestige for a race unit (base + boosts)"""
    from web.races import calculate_unit_prestige

    # Base stats from race_unit
    attack = race_unit.attack
    defense = race_unit.defense
    health = race_unit.health
    speed = race_unit.speed
    min_damage = race_unit.min_damage
    max_damage = race_unit.max_damage
    initiative = race_unit.initiative
    range_ = race_unit.range
    luck = float(race_unit.luck) if race_unit.luck else 0.0
    crit_chance = float(race_unit.crit_chance) if race_unit.crit_chance else 0.0
    dodge_chance = float(race_unit.dodge_chance) if race_unit.dodge_chance else 0.0
    counterattack_chance = float(race_unit.counterattack_chance) if race_unit.counterattack_chance else 0.0
    regeneration_health = race_unit.regeneration_health or 0
    poison_damage = race_unit.poison_damage or 0
    poison_turns = race_unit.poison_turns or 0
    is_flying = race_unit.is_flying or False
    is_kamikaze = race_unit.is_kamikaze or False
    poison_immunity = race_unit.poison_immunity or False

    # Add boosts if user_race_unit exists
    if user_race_unit:
        attack += user_race_unit.attack_boost or 0
        defense += user_race_unit.defense_boost or 0
        health += user_race_unit.health_boost or 0
        speed += user_race_unit.speed_boost or 0
        min_damage += user_race_unit.min_damage_boost or 0
        max_damage += user_race_unit.max_damage_boost or 0
        initiative += user_race_unit.initiative_boost or 0
        range_ += user_race_unit.range_boost or 0
        luck += float(user_race_unit.luck_boost or 0)
        crit_chance += float(user_race_unit.crit_chance_boost or 0)
        dodge_chance += float(user_race_unit.dodge_chance_boost or 0)
        counterattack_chance += float(user_race_unit.counterattack_chance_boost or 0)
        regeneration_health += user_race_unit.regeneration_health_boost or 0
        poison_damage += user_race_unit.poison_damage_boost or 0
        poison_turns += user_race_unit.poison_turns_boost or 0

    return calculate_unit_prestige(
        attack=attack,
        defense=defense,
        health=health,
        speed=speed,
        min_damage=min_damage,
        max_damage=max_damage,
        initiative=initiative,
        range_=range_,
        luck=luck,
        crit_chance=crit_chance,
        dodge_chance=dodge_chance,
        counterattack_chance=counterattack_chance,
        regeneration_health=regeneration_health,
        poison_damage=poison_damage,
        poison_turns=poison_turns,
        is_flying=is_flying,
        is_kamikaze=is_kamikaze,
        poison_immunity=poison_immunity
    )


# Шаблон списка армий
ARMIES_LIST_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Управление армиями</title>
''' + BASE_STYLE + '''
    <style>
        .army-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .army-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .army-type {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
        }
        .army-type.rated {
            background: #e3f2fd;
            color: #1565c0;
        }
        .army-type.mercenary {
            background: #fff3e0;
            color: #e65100;
        }
        .army-stats {
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }
        .army-stat {
            padding: 10px 15px;
            background: #f5f5f5;
            border-radius: 6px;
            text-align: center;
        }
        .army-stat-value {
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
        }
        .army-stat-label {
            font-size: 12px;
            color: #666;
        }
        .army-actions {
            display: flex;
            gap: 10px;
        }
        .user-info {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        .user-info h3 {
            margin: 0 0 15px 0;
        }
        .user-stats {
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }
        .user-stat {
            text-align: center;
        }
        .user-stat-value {
            font-size: 24px;
            font-weight: bold;
        }
        .user-stat-label {
            font-size: 12px;
            opacity: 0.8;
        }
        .no-armies {
            background: #f5f5f5;
            padding: 40px;
            text-align: center;
            border-radius: 8px;
            color: #666;
        }
        .create-army-btn {
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>⚔️ Управление армиями</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- Информация о пользователе -->
        <div class="user-info">
            <h3>👤 {{ game_user.username }}</h3>
            <div class="user-stats">
                <div class="user-stat">
                    <div class="user-stat-value">💰 {{ "%.2f"|format(game_user.balance or 0) }}</div>
                    <div class="user-stat-label">Баланс</div>
                </div>
                <div class="user-stat">
                    <div class="user-stat-value">🏆 {{ game_user.glory or 0 }}</div>
                    <div class="user-stat-label">Слава (престиж)</div>
                </div>
                <div class="user-stat">
                    <div class="user-stat-value">💎 {{ game_user.crystals or 0 }}</div>
                    <div class="user-stat-label">Кристаллы</div>
                </div>
            </div>
        </div>

        {% if user_races %}
        <div class="create-army-btn">
            <a href="{{ url_for('army.create_army_select_race') }}" class="btn btn-success">➕ Создать армию</a>
        </div>
        {% else %}
        <div class="no-armies">
            <h3>🎮 Сначала выберите расу</h3>
            <p>Чтобы создавать армии, вам нужно сначала выбрать расу.</p>
            <a href="{{ url_for('army.select_race') }}" class="btn btn-primary">Выбрать расу</a>
        </div>
        {% endif %}

        {% if armies %}
            {% for army in armies %}
            <div class="army-card">
                <div class="army-header">
                    <div>
                        <h3 style="margin: 0;">{{ army.name }}</h3>
                        <span class="army-type {{ army.army_type }}">
                            {% if army.army_type == 'rated' %}🏆 Рейтинговая{% else %}💰 Наёмная{% endif %}
                        </span>
                        <span style="color: #666; margin-left: 10px;">{{ army.user_race.race.name }}</span>
                    </div>
                </div>

                <div class="army-stats">
                    <div class="army-stat">
                        <div class="army-stat-value">{{ army.units_count }}</div>
                        <div class="army-stat-label">Юнитов</div>
                    </div>
                    <div class="army-stat">
                        <div class="army-stat-value">{{ army.total_prestige }}</div>
                        <div class="army-stat-label">Престиж армии</div>
                    </div>
                    {% if army.army_type == 'rated' %}
                    <div class="army-stat">
                        <div class="army-stat-value">{{ game_user.glory or 0 }}</div>
                        <div class="army-stat-label">Макс. престиж</div>
                    </div>
                    {% endif %}
                </div>

                <div class="army-actions">
                    <a href="{{ url_for('army.edit_army', army_id=army.id) }}" class="btn btn-primary">⚙️ Настроить</a>
                    <a href="{{ url_for('army.hire_units', army_id=army.id) }}" class="btn btn-success">🛒 Нанять юнитов</a>
                    <a href="{{ url_for('army.delete_army', army_id=army.id) }}" class="btn btn-danger" onclick="return confirm('Удалить армию?')">🗑️ Удалить</a>
                </div>
            </div>
            {% endfor %}
        {% elif user_races %}
        <div class="no-armies">
            <h3>📋 У вас пока нет армий</h3>
            <p>Создайте свою первую армию для участия в сражениях!</p>
        </div>
        {% endif %}
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
'''


# Шаблон выбора расы для создания армии
CREATE_ARMY_SELECT_RACE_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Создание армии - Выбор расы</title>
''' + BASE_STYLE + '''
    <style>
        .race-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 20px;
        }
        .race-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            cursor: pointer;
            transition: all 0.2s;
            border: 2px solid transparent;
        }
        .race-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }
        .race-card h4 {
            margin: 0 0 10px 0;
        }
    </style>
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>➕ Создание армии</h1>

        <p><a href="{{ url_for('army.armies_list') }}" class="btn btn-secondary">← Назад к армиям</a></p>

        <h2>Выберите расу для армии:</h2>

        <div class="race-grid">
            {% for user_race in user_races %}
            <a href="{{ url_for('army.create_army_form', user_race_id=user_race.id) }}" style="text-decoration: none; color: inherit;">
                <div class="race-card">
                    <h4>{{ user_race.race.name }}</h4>
                    <p style="color: #666; margin: 0;">{{ user_race.race.description or 'Нет описания' }}</p>
                </div>
            </a>
            {% endfor %}
        </div>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
'''


# Шаблон формы создания армии
CREATE_ARMY_FORM_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Создание армии</title>
''' + BASE_STYLE + '''
    <style>
        .army-type-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 15px;
            cursor: pointer;
            border: 2px solid #ddd;
            transition: all 0.2s;
        }
        .army-type-card:hover {
            border-color: #28a745;
        }
        .army-type-card.selected {
            border-color: #28a745;
            background: #f0fff0;
        }
        .army-type-card input[type="radio"] {
            display: none;
        }
        .army-type-card h4 {
            margin: 0 0 10px 0;
        }
        .army-type-desc {
            color: #666;
            font-size: 14px;
        }
    </style>
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>➕ Создание армии</h1>

        <p><a href="{{ url_for('army.create_army_select_race') }}" class="btn btn-secondary">← Назад</a></p>

        <form method="POST">
            <div class="form-group">
                <label>Название армии:</label>
                <input type="text" name="name" class="form-control" required maxlength="255" placeholder="Введите название армии">
            </div>

            <h3>Тип армии:</h3>

            <label class="army-type-card selected" onclick="selectType(this, 'mercenary')">
                <input type="radio" name="army_type" value="mercenary" checked>
                <h4>💰 Наёмная армия</h4>
                <p class="army-type-desc">
                    <strong>Покупайте юнитов за деньги.</strong><br>
                    Стоимость юнита = его престиж.<br>
                    Нет ограничений по общему престижу армии.
                </p>
            </label>

            <label class="army-type-card" onclick="selectType(this, 'rated')">
                <input type="radio" name="army_type" value="rated">
                <h4>🏆 Рейтинговая армия</h4>
                <p class="army-type-desc">
                    <strong>Бесплатный найм юнитов.</strong><br>
                    Общий престиж армии не может превышать вашу славу ({{ game_user.glory or 0 }}).<br>
                    Для рейтинговых сражений.
                </p>
            </label>

            <div style="margin-top: 20px;">
                <button type="submit" class="btn btn-success">✅ Создать армию</button>
            </div>
        </form>
    </div>

    <script>
        function selectType(card, type) {
            document.querySelectorAll('.army-type-card').forEach(c => c.classList.remove('selected'));
            card.classList.add('selected');
        }
    </script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
'''


# Шаблон найма юнитов
HIRE_UNITS_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Наём юнитов - {{ army.name }}</title>
''' + BASE_STYLE + '''
    <style>
        .unit-shop {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .unit-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .unit-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .unit-level {
            font-size: 24px;
        }
        .unit-name {
            font-weight: bold;
            font-size: 16px;
        }
        .unit-prestige {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
        }
        .unit-stats {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin-bottom: 15px;
            font-size: 12px;
        }
        .unit-stat {
            padding: 5px;
            background: #f5f5f5;
            border-radius: 4px;
            text-align: center;
        }
        .unit-price {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .unit-price.free {
            color: #28a745;
        }
        .unit-price.paid {
            color: #e65100;
        }
        .hire-form {
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .hire-form input[type="number"] {
            width: 80px;
        }
        .army-summary {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .army-summary-stats {
            display: flex;
            gap: 30px;
            flex-wrap: wrap;
        }
        .summary-stat {
            text-align: center;
        }
        .summary-stat-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }
        .summary-stat-label {
            font-size: 12px;
            color: #666;
        }
        .prestige-warning {
            background: #fff3cd;
            color: #856404;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .already-hired {
            background: #e8f5e9;
            padding: 10px;
            border-radius: 6px;
            margin-top: 10px;
            font-size: 13px;
            color: #2e7d32;
        }
    </style>
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>🛒 Наём юнитов - {{ army.name }}</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <p><a href="{{ url_for('army.armies_list') }}" class="btn btn-secondary">← Назад к армиям</a></p>

        <!-- Сводка по армии -->
        <div class="army-summary">
            <h3>📊 Состояние армии</h3>
            <div class="army-summary-stats">
                <div class="summary-stat">
                    <div class="summary-stat-value">{{ army_units|length }}</div>
                    <div class="summary-stat-label">Юнитов в армии</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-value">{{ total_prestige }}</div>
                    <div class="summary-stat-label">Престиж армии</div>
                </div>
                {% if army.army_type == 'rated' %}
                <div class="summary-stat">
                    <div class="summary-stat-value">{{ game_user.glory or 0 }}</div>
                    <div class="summary-stat-label">Макс. престиж (слава)</div>
                </div>
                <div class="summary-stat">
                    <div class="summary-stat-value">{{ (game_user.glory or 0) - total_prestige }}</div>
                    <div class="summary-stat-label">Доступно престижа</div>
                </div>
                {% else %}
                <div class="summary-stat">
                    <div class="summary-stat-value">💰 {{ "%.2f"|format(game_user.balance or 0) }}</div>
                    <div class="summary-stat-label">Ваш баланс</div>
                </div>
                {% endif %}
            </div>
        </div>

        {% if army.army_type == 'rated' and total_prestige >= (game_user.glory or 0) %}
        <div class="prestige-warning">
            ⚠️ Престиж армии достиг максимума. Увеличьте славу в боях, чтобы добавить больше юнитов.
        </div>
        {% endif %}

        <h2>Доступные юниты:</h2>

        <div class="unit-shop">
            {% for item in available_units %}
            <div class="unit-card">
                <div class="unit-header">
                    <div>
                        <span class="unit-level">{{ item.race_unit.unit_level.icon if item.race_unit.unit_level else '⚔️' }}</span>
                        <span class="unit-name">{{ item.race_unit.name }}</span>
                    </div>
                    <span class="unit-prestige">⭐ {{ item.prestige }}</span>
                </div>

                <div class="unit-stats">
                    <div class="unit-stat">⚔️ {{ item.attack }}</div>
                    <div class="unit-stat">🛡️ {{ item.defense }}</div>
                    <div class="unit-stat">❤️ {{ item.health }}</div>
                    <div class="unit-stat">💥 {{ item.min_damage }}-{{ item.max_damage }}</div>
                    <div class="unit-stat">👟 {{ item.speed }}</div>
                    <div class="unit-stat">🎯 {{ item.range }}</div>
                </div>

                {% if army.army_type == 'mercenary' %}
                <div class="unit-price paid">💰 Цена: {{ item.prestige }} за юнита</div>
                {% else %}
                <div class="unit-price free">✅ Бесплатно (престиж: {{ item.prestige }})</div>
                {% endif %}

                {% if item.current_count > 0 %}
                <div class="already-hired">В армии: {{ item.current_count }} шт.</div>
                {% endif %}

                <form method="POST" class="hire-form">
                    <input type="hidden" name="race_unit_id" value="{{ item.race_unit.id }}">
                    <input type="number" name="count" value="1" min="1" max="100" class="form-control">
                    <button type="submit" class="btn btn-success">Нанять</button>
                </form>
            </div>
            {% endfor %}
        </div>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
'''


# Шаблон редактирования армии
EDIT_ARMY_TEMPLATE = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Настройка армии - {{ army.name }}</title>
''' + BASE_STYLE + '''
    <style>
        .army-info {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .unit-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
        }
        .unit-item {
            background: white;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .unit-item-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .unit-count {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
        }
        .unit-prestige {
            font-size: 14px;
            color: #666;
        }
        .dismiss-form {
            margin-top: 10px;
            display: flex;
            gap: 10px;
            align-items: center;
        }
        .dismiss-form input[type="number"] {
            width: 60px;
        }
    </style>
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>⚙️ Настройка армии</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <p><a href="{{ url_for('army.armies_list') }}" class="btn btn-secondary">← Назад к армиям</a></p>

        <div class="army-info">
            <h2>{{ army.name }}</h2>
            <p>
                <span style="font-weight: bold;">Тип:</span>
                {% if army.army_type == 'rated' %}🏆 Рейтинговая{% else %}💰 Наёмная{% endif %}
            </p>
            <p>
                <span style="font-weight: bold;">Раса:</span> {{ army.user_race.race.name }}
            </p>
            <p>
                <span style="font-weight: bold;">Общий престиж:</span> {{ total_prestige }}
                {% if army.army_type == 'rated' %} / {{ game_user.glory or 0 }}{% endif %}
            </p>
        </div>

        <div style="margin-bottom: 20px;">
            <a href="{{ url_for('army.hire_units', army_id=army.id) }}" class="btn btn-success">🛒 Нанять юнитов</a>
        </div>

        <h3>Юниты в армии:</h3>

        {% if army_units %}
        <div class="unit-list">
            {% for au in army_units %}
            <div class="unit-item">
                <div class="unit-item-header">
                    <div>
                        <span style="font-size: 24px;">{{ au.race_unit.unit_level.icon if au.race_unit.unit_level else '⚔️' }}</span>
                        <span style="font-weight: bold;">{{ au.race_unit.name }}</span>
                    </div>
                    <div class="unit-count">×{{ au.count }}</div>
                </div>
                <div class="unit-prestige">Престиж: {{ au.prestige }} × {{ au.count }} = {{ au.total_prestige }}</div>

                <form method="POST" action="{{ url_for('army.dismiss_unit', army_id=army.id) }}" class="dismiss-form">
                    <input type="hidden" name="army_unit_id" value="{{ au.id }}">
                    <input type="number" name="count" value="1" min="1" max="{{ au.count }}" class="form-control">
                    <button type="submit" class="btn btn-danger btn-sm">Уволить</button>
                </form>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <p style="color: #666;">В армии пока нет юнитов. <a href="{{ url_for('army.hire_units', army_id=army.id) }}">Нанять юнитов</a></p>
        {% endif %}
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
'''


@army_bp.route('/settings')
@login_required
def army_settings():
    """Перенаправление на список армий"""
    return redirect(url_for('army.armies_list'))


@army_bp.route('/armies')
@login_required
def armies_list():
    """Список армий пользователя"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('index'))

        # Получаем расы пользователя
        user_races = session_db.query(UserRace).filter(UserRace.user_id == game_user.id).all()

        # Получаем армии пользователя
        armies = []
        for ur in user_races:
            user_armies = session_db.query(Army).filter(Army.user_race_id == ur.id).all()
            for army in user_armies:
                # Подсчитываем юнитов и престиж
                army_units = session_db.query(ArmyUnit).filter(ArmyUnit.army_id == army.id).all()
                army.units_count = sum(au.count for au in army_units)

                # Считаем престиж армии
                total_prestige = 0
                for au in army_units:
                    # Получаем UserRaceUnit для расчета престижа с бустами
                    user_race_unit = session_db.query(UserRaceUnit).filter(
                        UserRaceUnit.user_race_id == army.user_race_id,
                        UserRaceUnit.race_unit_id == au.race_unit_id
                    ).first()
                    prestige = calculate_race_unit_prestige(au.race_unit, user_race_unit)
                    total_prestige += prestige * au.count

                army.total_prestige = total_prestige
                armies.append(army)

        return render_template_string(
            ARMIES_LIST_TEMPLATE,
            active_page='army_settings',
            game_user=game_user,
            user_races=user_races,
            armies=armies
        )


@army_bp.route('/armies/create/select-race')
@login_required
def create_army_select_race():
    """Выбор расы для создания армии"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('index'))

        user_races = session_db.query(UserRace).filter(UserRace.user_id == game_user.id).all()

        if not user_races:
            flash('Сначала выберите расу', 'error')
            return redirect(url_for('army.select_race'))

        return render_template_string(
            CREATE_ARMY_SELECT_RACE_TEMPLATE,
            active_page='army_settings',
            user_races=user_races
        )


@army_bp.route('/armies/create/<int:user_race_id>', methods=['GET', 'POST'])
@login_required
def create_army_form(user_race_id):
    """Форма создания армии"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('index'))

        user_race = session_db.query(UserRace).filter(
            UserRace.id == user_race_id,
            UserRace.user_id == game_user.id
        ).first()

        if not user_race:
            flash('Раса не найдена', 'error')
            return redirect(url_for('army.create_army_select_race'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            army_type = request.form.get('army_type', 'mercenary')

            if not name:
                flash('Введите название армии', 'error')
                return redirect(url_for('army.create_army_form', user_race_id=user_race_id))

            if army_type not in [Army.TYPE_RATED, Army.TYPE_MERCENARY]:
                army_type = Army.TYPE_MERCENARY

            army = Army(
                user_race_id=user_race_id,
                name=name,
                army_type=army_type
            )
            session_db.add(army)
            session_db.commit()

            flash(f'Армия "{name}" создана!', 'success')
            return redirect(url_for('army.hire_units', army_id=army.id))

        return render_template_string(
            CREATE_ARMY_FORM_TEMPLATE,
            active_page='army_settings',
            user_race=user_race,
            game_user=game_user
        )


@army_bp.route('/armies/<int:army_id>')
@login_required
def edit_army(army_id):
    """Редактирование армии"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('index'))

        # Проверяем, что армия принадлежит пользователю
        army = session_db.query(Army).filter(Army.id == army_id).first()
        if not army:
            flash('Армия не найдена', 'error')
            return redirect(url_for('army.armies_list'))

        user_race = session_db.query(UserRace).filter(
            UserRace.id == army.user_race_id,
            UserRace.user_id == game_user.id
        ).first()

        if not user_race:
            flash('Армия не найдена', 'error')
            return redirect(url_for('army.armies_list'))

        # Получаем юнитов армии с престижем
        army_units = session_db.query(ArmyUnit).filter(ArmyUnit.army_id == army_id).all()
        total_prestige = 0

        for au in army_units:
            user_race_unit = session_db.query(UserRaceUnit).filter(
                UserRaceUnit.user_race_id == army.user_race_id,
                UserRaceUnit.race_unit_id == au.race_unit_id
            ).first()
            au.prestige = calculate_race_unit_prestige(au.race_unit, user_race_unit)
            au.total_prestige = au.prestige * au.count
            total_prestige += au.total_prestige

        return render_template_string(
            EDIT_ARMY_TEMPLATE,
            active_page='army_settings',
            army=army,
            army_units=army_units,
            total_prestige=total_prestige,
            game_user=game_user
        )


@army_bp.route('/armies/<int:army_id>/hire', methods=['GET', 'POST'])
@login_required
def hire_units(army_id):
    """Наём юнитов в армию"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('index'))

        army = session_db.query(Army).filter(Army.id == army_id).first()
        if not army:
            flash('Армия не найдена', 'error')
            return redirect(url_for('army.armies_list'))

        user_race = session_db.query(UserRace).filter(
            UserRace.id == army.user_race_id,
            UserRace.user_id == game_user.id
        ).first()

        if not user_race:
            flash('Армия не найдена', 'error')
            return redirect(url_for('army.armies_list'))

        # Получаем текущие юниты армии
        army_units = session_db.query(ArmyUnit).filter(ArmyUnit.army_id == army_id).all()
        army_units_map = {au.race_unit_id: au for au in army_units}

        # Считаем текущий престиж армии
        total_prestige = 0
        for au in army_units:
            user_race_unit = session_db.query(UserRaceUnit).filter(
                UserRaceUnit.user_race_id == army.user_race_id,
                UserRaceUnit.race_unit_id == au.race_unit_id
            ).first()
            prestige = calculate_race_unit_prestige(au.race_unit, user_race_unit)
            total_prestige += prestige * au.count

        if request.method == 'POST':
            race_unit_id = int(request.form.get('race_unit_id', 0))
            count = int(request.form.get('count', 1))

            if count < 1:
                flash('Некорректное количество', 'error')
                return redirect(url_for('army.hire_units', army_id=army_id))

            # Проверяем юнит
            race_unit = session_db.query(RaceUnit).filter(
                RaceUnit.id == race_unit_id,
                RaceUnit.race_id == user_race.race_id
            ).first()

            if not race_unit:
                flash('Юнит не найден', 'error')
                return redirect(url_for('army.hire_units', army_id=army_id))

            # Получаем UserRaceUnit для расчета престижа
            user_race_unit = session_db.query(UserRaceUnit).filter(
                UserRaceUnit.user_race_id == army.user_race_id,
                UserRaceUnit.race_unit_id == race_unit_id
            ).first()

            unit_prestige = calculate_race_unit_prestige(race_unit, user_race_unit)
            total_cost = unit_prestige * count

            if army.army_type == Army.TYPE_MERCENARY:
                # Проверяем баланс
                if (game_user.balance or 0) < total_cost:
                    flash(f'Недостаточно средств. Нужно: {total_cost}, у вас: {game_user.balance or 0}', 'error')
                    return redirect(url_for('army.hire_units', army_id=army_id))

                # Списываем деньги
                game_user.balance = (game_user.balance or 0) - total_cost

            else:  # rated
                # Проверяем лимит престижа
                new_total = total_prestige + total_cost
                if new_total > (game_user.glory or 0):
                    flash(f'Превышен лимит престижа. Макс: {game_user.glory or 0}, будет: {new_total}', 'error')
                    return redirect(url_for('army.hire_units', army_id=army_id))

            # Добавляем юнитов
            existing_unit = army_units_map.get(race_unit_id)
            if existing_unit:
                existing_unit.count += count
            else:
                new_army_unit = ArmyUnit(
                    army_id=army_id,
                    race_unit_id=race_unit_id,
                    unit_level_id=race_unit.unit_level_id,
                    count=count
                )
                session_db.add(new_army_unit)

            session_db.commit()

            if army.army_type == Army.TYPE_MERCENARY:
                flash(f'Нанято {count} юнитов "{race_unit.name}" за {total_cost}', 'success')
            else:
                flash(f'Нанято {count} юнитов "{race_unit.name}"', 'success')

            return redirect(url_for('army.hire_units', army_id=army_id))

        # Получаем доступных юнитов
        race_units = session_db.query(RaceUnit).filter(
            RaceUnit.race_id == user_race.race_id
        ).order_by(RaceUnit.unit_level_id).all()

        available_units = []
        for ru in race_units:
            user_race_unit = session_db.query(UserRaceUnit).filter(
                UserRaceUnit.user_race_id == army.user_race_id,
                UserRaceUnit.race_unit_id == ru.id
            ).first()

            prestige = calculate_race_unit_prestige(ru, user_race_unit)

            # Финальные характеристики (с бустами)
            attack = ru.attack + (user_race_unit.attack_boost if user_race_unit else 0)
            defense = ru.defense + (user_race_unit.defense_boost if user_race_unit else 0)
            health = ru.health + (user_race_unit.health_boost if user_race_unit else 0)
            min_damage = ru.min_damage + (user_race_unit.min_damage_boost if user_race_unit else 0)
            max_damage = ru.max_damage + (user_race_unit.max_damage_boost if user_race_unit else 0)
            speed = ru.speed + (user_race_unit.speed_boost if user_race_unit else 0)
            range_ = ru.range + (user_race_unit.range_boost if user_race_unit else 0)

            current_unit = army_units_map.get(ru.id)

            available_units.append({
                'race_unit': ru,
                'prestige': prestige,
                'attack': attack,
                'defense': defense,
                'health': health,
                'min_damage': min_damage,
                'max_damage': max_damage,
                'speed': speed,
                'range': range_,
                'current_count': current_unit.count if current_unit else 0
            })

        return render_template_string(
            HIRE_UNITS_TEMPLATE,
            active_page='army_settings',
            army=army,
            army_units=army_units,
            total_prestige=total_prestige,
            available_units=available_units,
            game_user=game_user
        )


@army_bp.route('/armies/<int:army_id>/dismiss', methods=['POST'])
@login_required
def dismiss_unit(army_id):
    """Увольнение юнита из армии"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('index'))

        army = session_db.query(Army).filter(Army.id == army_id).first()
        if not army:
            flash('Армия не найдена', 'error')
            return redirect(url_for('army.armies_list'))

        user_race = session_db.query(UserRace).filter(
            UserRace.id == army.user_race_id,
            UserRace.user_id == game_user.id
        ).first()

        if not user_race:
            flash('Армия не найдена', 'error')
            return redirect(url_for('army.armies_list'))

        army_unit_id = int(request.form.get('army_unit_id', 0))
        count = int(request.form.get('count', 1))

        army_unit = session_db.query(ArmyUnit).filter(
            ArmyUnit.id == army_unit_id,
            ArmyUnit.army_id == army_id
        ).first()

        if not army_unit:
            flash('Юнит не найден', 'error')
            return redirect(url_for('army.edit_army', army_id=army_id))

        if count >= army_unit.count:
            session_db.delete(army_unit)
            flash(f'Все юниты "{army_unit.race_unit.name}" уволены', 'success')
        else:
            army_unit.count -= count
            flash(f'Уволено {count} юнитов "{army_unit.race_unit.name}"', 'success')

        session_db.commit()
        return redirect(url_for('army.edit_army', army_id=army_id))


@army_bp.route('/armies/<int:army_id>/delete')
@login_required
def delete_army(army_id):
    """Удаление армии"""
    username = session.get('username')

    with db.get_session() as session_db:
        game_user = session_db.query(GameUser).filter(GameUser.username == username).first()
        if not game_user:
            flash('Игровой пользователь не найден', 'error')
            return redirect(url_for('index'))

        army = session_db.query(Army).filter(Army.id == army_id).first()
        if not army:
            flash('Армия не найдена', 'error')
            return redirect(url_for('army.armies_list'))

        user_race = session_db.query(UserRace).filter(
            UserRace.id == army.user_race_id,
            UserRace.user_id == game_user.id
        ).first()

        if not user_race:
            flash('Армия не найдена', 'error')
            return redirect(url_for('army.armies_list'))

        army_name = army.name
        session_db.delete(army)
        session_db.commit()

        flash(f'Армия "{army_name}" удалена', 'success')
        return redirect(url_for('army.armies_list'))
