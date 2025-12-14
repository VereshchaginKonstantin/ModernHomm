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


@army_bp.route('/settings')
@login_required
def army_settings():
    """Настройка армии"""
    username = session.get('username')

    template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Настройка армии</title>
''' + BASE_STYLE + '''
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>🎖️ Настройка армии</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="section">
            <h3>Управление армией</h3>
            <p>Здесь вы сможете формировать и настраивать свои армии для сражений.</p>
            <p><em>Функционал в разработке...</em></p>
        </div>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
    '''

    return render_template_string(
        template,
        active_page='army_settings',
        
    )
