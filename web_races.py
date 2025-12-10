#!/usr/bin/env python3
"""
Модуль управления расами для веб-интерфейса
"""

import os
import logging
from datetime import datetime
from flask import Blueprint, render_template_string, request, jsonify, session, redirect, url_for
from functools import wraps

from db.models import Base, GameUser, GameRace, RaceUnit, UnitLevel, UserRace, UserRaceUnit, Army, ArmyUnit
from db.repository import Database
from web_templates import HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE

logger = logging.getLogger(__name__)

# Blueprint для рас
races_bp = Blueprint('races', __name__, url_prefix='/admin/races')

# Получаем подключение к БД
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
db = Database(db_url)


def admin_required(f):
    """Декоратор для проверки авторизации админа"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== Шаблоны ====================

RACES_LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Расы - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .races-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }
        .race-card { background: #2a2a2a; border-radius: 10px; padding: 20px; }
        .race-card h3 { margin: 0 0 10px 0; color: #ffd700; }
        .race-card .description { color: #aaa; font-size: 14px; margin-bottom: 15px; }
        .race-card .badge { display: inline-block; padding: 3px 8px; border-radius: 5px; font-size: 12px; margin-right: 5px; }
        .badge-free { background: #2ecc71; color: white; }
        .badge-paid { background: #e74c3c; color: white; }
        .btn { display: inline-block; padding: 8px 15px; border-radius: 5px; text-decoration: none; margin-right: 5px; }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-sm { padding: 5px 10px; font-size: 12px; }
        .add-btn { margin-bottom: 20px; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>🏰 Управление расами</h1>

        <a href="{{ url_for('races.create_race') }}" class="btn btn-success add-btn">➕ Создать расу</a>

        <div class="races-grid">
            {% for race in races %}
            <div class="race-card">
                <h3>{{ race.name }}</h3>
                <p class="description">{{ race.description or 'Нет описания' }}</p>
                <div>
                    {% if race.is_free %}
                    <span class="badge badge-free">Бесплатная</span>
                    {% else %}
                    <span class="badge badge-paid">Платная</span>
                    {% endif %}
                    <span class="badge" style="background: #9b59b6;">{{ race.race_units|length }}/7 юнитов</span>
                </div>
                <div style="margin-top: 15px;">
                    <a href="{{ url_for('races.edit_race', race_id=race.id) }}" class="btn btn-primary btn-sm">✏️ Редактировать</a>
                    <a href="{{ url_for('races.race_skins', race_id=race.id) }}" class="btn btn-primary btn-sm">🎨 Скины</a>
                    <button onclick="deleteRace({{ race.id }})" class="btn btn-danger btn-sm">🗑️ Удалить</button>
                </div>
            </div>
            {% else %}
            <p style="color: #aaa;">Расы не найдены. Создайте первую расу!</p>
            {% endfor %}
        </div>
    </div>

    <script>
    function deleteRace(raceId) {
        if (confirm('Вы уверены, что хотите удалить эту расу?')) {
            fetch('/admin/races/' + raceId + '/delete', {
                method: 'POST'
            }).then(response => response.json())
              .then(data => {
                  if (data.success) {
                      location.reload();
                  } else {
                      alert('Ошибка: ' + data.message);
                  }
              });
        }
    }
    </script>
</body>
</html>
"""

CREATE_RACE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Создать расу - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .form-group textarea { min-height: 100px; }
        .checkbox-group { display: flex; align-items: center; gap: 10px; }
        .checkbox-group input[type="checkbox"] { width: 20px; height: 20px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>➕ Создать расу</h1>

        <form method="POST" action="{{ url_for('races.create_race') }}">
            <div class="form-group">
                <label>Название</label>
                <input type="text" name="name" required placeholder="Название расы">
            </div>

            <div class="form-group">
                <label>Описание</label>
                <textarea name="description" placeholder="Описание расы (необязательно)"></textarea>
            </div>

            <div class="form-group checkbox-group">
                <input type="checkbox" name="is_free" id="is_free">
                <label for="is_free" style="margin-bottom: 0;">Бесплатная раса</label>
            </div>

            <button type="submit" class="btn btn-success">Создать</button>
            <a href="{{ url_for('races.races_list') }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
</body>
</html>
"""

EDIT_RACE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Редактировать расу - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .form-group textarea { min-height: 100px; }
        .checkbox-group { display: flex; align-items: center; gap: 10px; }
        .checkbox-group input[type="checkbox"] { width: 20px; height: 20px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
        .btn-primary { background: #3498db; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .units-section { margin-top: 30px; padding-top: 20px; border-top: 1px solid #444; }
        .units-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin-top: 15px; }
        .unit-card { background: #333; border-radius: 8px; padding: 15px; }
        .unit-card h4 { margin: 0 0 10px 0; color: #ffd700; }
        .unit-card .level { color: #3498db; font-size: 12px; }
        .unit-card .stats { font-size: 12px; color: #aaa; margin-top: 10px; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>✏️ Редактировать расу: {{ race.name }}</h1>

        <form method="POST" action="{{ url_for('races.edit_race', race_id=race.id) }}">
            <div class="form-group">
                <label>Название</label>
                <input type="text" name="name" required value="{{ race.name }}">
            </div>

            <div class="form-group">
                <label>Описание</label>
                <textarea name="description">{{ race.description or '' }}</textarea>
            </div>

            <div class="form-group checkbox-group">
                <input type="checkbox" name="is_free" id="is_free" {% if race.is_free %}checked{% endif %}>
                <label for="is_free" style="margin-bottom: 0;">Бесплатная раса</label>
            </div>

            <button type="submit" class="btn btn-success">💾 Сохранить</button>
            <a href="{{ url_for('races.races_list') }}" class="btn btn-secondary">Назад</a>
        </form>

        <div class="units-section">
            <h2>⚔️ Юниты расы (7 уровней)</h2>
            <a href="{{ url_for('races.add_race_unit', race_id=race.id) }}" class="btn btn-primary">➕ Добавить юнит</a>

            <div class="units-grid">
                {% for level in range(1, 8) %}
                {% set unit = units_by_level.get(level) %}
                <div class="unit-card">
                    <span class="level">Уровень {{ level }}</span>
                    {% if unit %}
                    <h4>{{ unit.icon }} {{ unit.name }}</h4>
                    <div class="stats">
                        ⚔️ {{ unit.attack }} | 🛡️ {{ unit.defense }} | ❤️ {{ unit.health }}<br>
                        💥 {{ unit.min_damage }}-{{ unit.max_damage }} | 🏃 {{ unit.speed }} | ⚡ {{ unit.initiative }}
                    </div>
                    <div style="margin-top: 10px;">
                        <a href="{{ url_for('races.edit_race_unit', race_id=race.id, unit_id=unit.id) }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;">✏️</a>
                        <button onclick="deleteUnit({{ unit.id }})" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;">🗑️</button>
                    </div>
                    {% else %}
                    <h4 style="color: #666;">Не задан</h4>
                    <a href="{{ url_for('races.add_race_unit', race_id=race.id) }}?level={{ level }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px; margin-top: 10px;">➕ Добавить</a>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <script>
    function deleteUnit(unitId) {
        if (confirm('Удалить этот юнит?')) {
            fetch('/admin/settings/unit/' + unitId + '/delete', {
                method: 'POST'
            }).then(response => response.json())
              .then(data => {
                  if (data.success) {
                      location.reload();
                  } else {
                      alert('Ошибка: ' + data.message);
                  }
              });
        }
    }
    </script>
</body>
</html>
"""

ADD_UNIT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Добавить юнит - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .form-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>➕ Добавить юнит для: {{ race.name }}</h1>

        <form method="POST">
            <div class="form-group">
                <label>Уровень (1-7)</label>
                <select name="level" required>
                    {% for l in range(1, 8) %}
                    <option value="{{ l }}" {% if l == default_level %}selected{% endif %}>{{ l }}</option>
                    {% endfor %}
                </select>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label>Название</label>
                    <input type="text" name="name" required placeholder="Мечник">
                </div>
                <div class="form-group">
                    <label>Иконка</label>
                    <input type="text" name="icon" value="🎮" maxlength="10">
                </div>
                <div class="form-group">
                    <label>Путь к изображению</label>
                    <input type="text" name="image_path" placeholder="/static/units/sword.png">
                </div>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label>Атака</label>
                    <input type="number" name="attack" value="10" min="1">
                </div>
                <div class="form-group">
                    <label>Защита</label>
                    <input type="number" name="defense" value="5" min="0">
                </div>
                <div class="form-group">
                    <label>Здоровье</label>
                    <input type="number" name="health" value="10" min="1">
                </div>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label>Мин. урон</label>
                    <input type="number" name="min_damage" value="1" min="1">
                </div>
                <div class="form-group">
                    <label>Макс. урон</label>
                    <input type="number" name="max_damage" value="3" min="1">
                </div>
                <div class="form-group">
                    <label>Скорость</label>
                    <input type="number" name="speed" value="4" min="1">
                </div>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label>Инициатива</label>
                    <input type="number" name="initiative" value="10" min="1">
                </div>
                <div class="form-group">
                    <label>Стоимость</label>
                    <input type="number" name="cost" value="100" min="0" step="0.01">
                </div>
            </div>

            <button type="submit" class="btn btn-success">Создать</button>
            <a href="{{ url_for('races.edit_race', race_id=race.id) }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
</body>
</html>
"""

SKINS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Скины расы - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .skins-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }
        .skin-card { background: #333; border-radius: 8px; padding: 15px; text-align: center; }
        .skin-card .level { color: #3498db; font-size: 12px; }
        .skin-card img { max-width: 100%; max-height: 150px; margin: 10px 0; border-radius: 5px; }
        .skin-card .no-image { width: 100%; height: 100px; background: #444; display: flex; align-items: center; justify-content: center; color: #666; border-radius: 5px; margin: 10px 0; }
        .btn { padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>🎨 Скины для: {{ race.name }}</h1>

        <a href="{{ url_for('races.add_skin', race_id=race.id) }}" class="btn btn-success">➕ Добавить скин</a>
        <a href="{{ url_for('races.edit_race', race_id=race.id) }}" class="btn btn-secondary">← Назад к расе</a>

        <div class="skins-grid">
            {% for level in range(1, 8) %}
            {% set skin = skins_by_level.get(level) %}
            <div class="skin-card">
                <span class="level">Уровень {{ level }}</span>
                {% if skin %}
                <h4>{{ skin.name or 'Скин ' + level|string }}</h4>
                {% if skin.image_path %}
                <img src="{{ skin.image_path }}" alt="Скин">
                {% else %}
                <div class="no-image">Нет изображения</div>
                {% endif %}
                <div>
                    <a href="{{ url_for('races.edit_skin', race_id=race.id, skin_id=skin.id) }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;">✏️</a>
                    <button onclick="deleteSkin({{ skin.id }})" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;">🗑️</button>
                </div>
                {% else %}
                <h4 style="color: #666;">Не задан</h4>
                <div class="no-image">Нет скина</div>
                <a href="{{ url_for('races.add_skin', race_id=race.id) }}?level={{ level }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;">➕</a>
                {% endif %}
            </div>
            {% endfor %}
        </div>
    </div>

    <script>
    function deleteSkin(skinId) {
        if (confirm('Удалить этот скин?')) {
            fetch('/admin/settings/skin/' + skinId + '/delete', {
                method: 'POST'
            }).then(response => response.json())
              .then(data => {
                  if (data.success) {
                      location.reload();
                  } else {
                      alert('Ошибка: ' + data.message);
                  }
              });
        }
    }
    </script>
</body>
</html>
"""


# ==================== Маршруты ====================

@races_bp.route('/')
@admin_required
def races_list():
    """Список рас"""
    with db.get_session() as session_db:
        races = session_db.query(GameRace).all()
        return render_template_string(RACES_LIST_TEMPLATE, races=races)


@races_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create_race():
    """Создать новую расу"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_free = request.form.get('is_free') == 'on'

        with db.get_session() as session_db:
            race = GameRace(
                name=name,
                description=description,
                is_free=is_free
            )
            session_db.add(race)
            session_db.commit()
            return redirect(url_for('races.edit_race', race_id=race.id))

    return render_template_string(CREATE_RACE_TEMPLATE)


@races_bp.route('/<int:race_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_race(race_id):
    """Редактировать расу"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        if not race:
            return redirect(url_for('races.races_list'))

        if request.method == 'POST':
            race.name = request.form.get('name')
            race.description = request.form.get('description')
            race.is_free = request.form.get('is_free') == 'on'
            session_db.commit()
            return redirect(url_for('races.edit_race', race_id=race_id))

        # Получаем юниты по уровням
        units = session_db.query(RaceUnit).filter_by(race_id=race_id).all()
        units_by_level = {u.level: u for u in units}

        return render_template_string(EDIT_RACE_TEMPLATE, race=race, units_by_level=units_by_level)


@races_bp.route('/<int:race_id>/delete', methods=['POST'])
@admin_required
def delete_race(race_id):
    """Удалить расу"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        if race:
            session_db.delete(race)
            session_db.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Раса не найдена'})


@races_bp.route('/<int:race_id>/unit/add', methods=['GET', 'POST'])
@admin_required
def add_race_unit(race_id):
    """Добавить юнит в расу"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        if not race:
            return redirect(url_for('races.races_list'))

        if request.method == 'POST':
            unit = RaceUnit(
                race_id=race_id,
                level=int(request.form.get('level')),
                name=request.form.get('name'),
                icon=request.form.get('icon', '🎮'),
                image_path=request.form.get('image_path') or None,
                attack=int(request.form.get('attack', 10)),
                defense=int(request.form.get('defense', 5)),
                min_damage=int(request.form.get('min_damage', 1)),
                max_damage=int(request.form.get('max_damage', 3)),
                health=int(request.form.get('health', 10)),
                speed=int(request.form.get('speed', 4)),
                initiative=int(request.form.get('initiative', 10)),
                cost=float(request.form.get('cost', 100))
            )
            session_db.add(unit)
            session_db.commit()
            return redirect(url_for('races.edit_race', race_id=race_id))

        default_level = int(request.args.get('level', 1))
        return render_template_string(ADD_UNIT_TEMPLATE, race=race, default_level=default_level)


@races_bp.route('/<int:race_id>/unit/<int:unit_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_race_unit(race_id, unit_id):
    """Редактировать юнит расы"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        unit = session_db.query(RaceUnit).filter_by(id=unit_id, race_id=race_id).first()

        if not setting or not unit:
            return redirect(url_for('races.races_list'))

        if request.method == 'POST':
            unit.level = int(request.form.get('level'))
            unit.name = request.form.get('name')
            unit.icon = request.form.get('icon', '🎮')
            unit.image_path = request.form.get('image_path') or None
            unit.attack = int(request.form.get('attack', 10))
            unit.defense = int(request.form.get('defense', 5))
            unit.min_damage = int(request.form.get('min_damage', 1))
            unit.max_damage = int(request.form.get('max_damage', 3))
            unit.health = int(request.form.get('health', 10))
            unit.speed = int(request.form.get('speed', 4))
            unit.initiative = int(request.form.get('initiative', 10))
            unit.cost = float(request.form.get('cost', 100))
            session_db.commit()
            return redirect(url_for('races.edit_race', race_id=race_id))

        # Используем тот же шаблон с предзаполненными данными
        template = ADD_UNIT_TEMPLATE.replace('Добавить юнит', 'Редактировать юнит').replace(
            'placeholder="Мечник"', f'value="{unit.name}"'
        ).replace('value="🎮"', f'value="{unit.icon}"').replace(
            'placeholder="/static/units/sword.png"', f'value="{unit.image_path or ""}"'
        ).replace('value="10" min="1">', f'value="{unit.attack}" min="1">', 1).replace(
            'value="5" min="0"', f'value="{unit.defense}" min="0"'
        ).replace('value="10" min="1">', f'value="{unit.health}" min="1">', 1).replace(
            'value="1" min="1">', f'value="{unit.min_damage}" min="1">', 1
        ).replace('value="3" min="1"', f'value="{unit.max_damage}" min="1"').replace(
            'value="4" min="1"', f'value="{unit.speed}" min="1"'
        ).replace('value="10" min="1">', f'value="{unit.initiative}" min="1">', 1).replace(
            'value="100" min="0"', f'value="{unit.cost}" min="0"'
        )

        return render_template_string(template, race=race, default_level=unit.level)


@races_bp.route('/unit/<int:unit_id>/delete', methods=['POST'])
@admin_required
def delete_race_unit(unit_id):
    """Удалить юнит расы"""
    with db.get_session() as session_db:
        unit = session_db.query(RaceUnit).filter_by(id=unit_id).first()
        if unit:
            session_db.delete(unit)
            session_db.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Юнит не найден'})


@races_bp.route('/<int:race_id>/skins')
@admin_required
def race_skins(race_id):
    """Скины расы"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        if not race:
            return redirect(url_for('races.races_list'))

        skins = session_db.query(RaceLevelSkin).filter_by(race_id=race_id).all()
        skins_by_level = {s.level: s for s in skins}

        return render_template_string(SKINS_TEMPLATE, race=race, skins_by_level=skins_by_level)


@races_bp.route('/<int:race_id>/skin/add', methods=['GET', 'POST'])
@admin_required
def add_skin(race_id):
    """Добавить скин"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        if not race:
            return redirect(url_for('races.races_list'))

        if request.method == 'POST':
            skin = RaceLevelSkin(
                race_id=race_id,
                level=int(request.form.get('level')),
                name=request.form.get('name'),
                image_path=request.form.get('image_path') or None
            )
            session_db.add(skin)
            session_db.commit()
            return redirect(url_for('races.race_skins', race_id=race_id))

        default_level = int(request.args.get('level', 1))
        template = """
<!DOCTYPE html>
<html>
<head>
    <title>Добавить скин - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>➕ Добавить скин для: {{ race.name }}</h1>

        <form method="POST">
            <div class="form-group">
                <label>Уровень (1-7)</label>
                <select name="level" required>
                    {% for l in range(1, 8) %}
                    <option value="{{ l }}" {% if l == default_level %}selected{% endif %}>{{ l }}</option>
                    {% endfor %}
                </select>
            </div>

            <div class="form-group">
                <label>Название</label>
                <input type="text" name="name" placeholder="Название скина">
            </div>

            <div class="form-group">
                <label>Путь к изображению</label>
                <input type="text" name="image_path" placeholder="/static/skins/level1.png">
            </div>

            <button type="submit" class="btn btn-success">Создать</button>
            <a href="{{ url_for('races.race_skins', race_id=race.id) }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
</body>
</html>
"""
        return render_template_string(template, race=race, default_level=default_level)


@races_bp.route('/<int:race_id>/skin/<int:skin_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_skin(race_id, skin_id):
    """Редактировать скин"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        skin = session_db.query(RaceLevelSkin).filter_by(id=skin_id, race_id=race_id).first()

        if not setting or not skin:
            return redirect(url_for('races.races_list'))

        if request.method == 'POST':
            skin.level = int(request.form.get('level'))
            skin.name = request.form.get('name')
            skin.image_path = request.form.get('image_path') or None
            session_db.commit()
            return redirect(url_for('races.race_skins', race_id=race_id))

        template = """
<!DOCTYPE html>
<html>
<head>
    <title>Редактировать скин - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>✏️ Редактировать скин</h1>

        <form method="POST">
            <div class="form-group">
                <label>Уровень (1-7)</label>
                <select name="level" required>
                    {% for l in range(1, 8) %}
                    <option value="{{ l }}" {% if l == skin.level %}selected{% endif %}>{{ l }}</option>
                    {% endfor %}
                </select>
            </div>

            <div class="form-group">
                <label>Название</label>
                <input type="text" name="name" value="{{ skin.name or '' }}">
            </div>

            <div class="form-group">
                <label>Путь к изображению</label>
                <input type="text" name="image_path" value="{{ skin.image_path or '' }}">
            </div>

            <button type="submit" class="btn btn-success">💾 Сохранить</button>
            <a href="{{ url_for('races.race_skins', race_id=race.id) }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
</body>
</html>
"""
        return render_template_string(template, race=race, skin=skin)


@races_bp.route('/skin/<int:skin_id>/delete', methods=['POST'])
@admin_required
def delete_skin(skin_id):
    """Удалить скин"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceLevelSkin).filter_by(id=skin_id).first()
        if skin:
            session_db.delete(skin)
            session_db.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Скин не найден'})
