#!/usr/bin/env python3
"""
Модуль управления расами для веб-интерфейса
"""

import os
import logging
from datetime import datetime
from flask import Blueprint, render_template_string, request, jsonify, session, redirect, url_for, Response
from functools import wraps

from db.models import Base, GameUser, GameRace, RaceUnit, RaceUnitSkin, UnitLevel, UserRace, UserRaceUnit, Army, ArmyUnit
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
    """ + FOOTER_TEMPLATE + """
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
    """ + FOOTER_TEMPLATE + """
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

            <div class="units-grid">
                {% for level in range(1, 8) %}
                {% set unit = units_by_level.get(level) %}
                <div class="unit-card">
                    <span class="level">Уровень {{ level }}</span>
                    {% if unit %}
                    <h4>{{ unit.icon }} {{ unit.name }}</h4>
                    <div class="stats">
                        {% if unit.is_flying %}🦅 Летающий{% endif %}
                        {% if unit.is_kamikaze %}💥 Камикадзе{% endif %}
                        <br>🎨 Скинов: {{ unit.skins|length }}
                    </div>
                    <div style="margin-top: 10px;">
                        <a href="{{ url_for('races.edit_race_unit', race_id=race.id, unit_id=unit.id) }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;">✏️ Юнит</a>
                        <a href="{{ url_for('races.unit_skins', race_id=race.id, unit_id=unit.id) }}" class="btn btn-success" style="padding: 5px 10px; font-size: 12px;">🎨 Скины уровня</a>
                    </div>
                    {% else %}
                    <h4 style="color: #666;">Не задан</h4>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""

EDIT_UNIT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Редактировать Юнит расы - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .form-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
        .form-row-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; }
        .checkbox-group { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; }
        .checkbox-group input[type="checkbox"] { width: 20px; height: 20px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>✏️ Редактировать Юнит расы уровня {{ unit.level }}: {{ race.name }}</h1>

        <form method="POST">
            <div class="form-row">
                <div class="form-group">
                    <label>Название</label>
                    <input type="text" name="name" required value="{{ unit.name }}">
                </div>
                <div class="form-group">
                    <label>Иконка</label>
                    <input type="text" name="icon" value="{{ unit.icon }}" maxlength="10">
                </div>
            </div>

            <div class="form-row">
                <div class="form-group">
                    <label>Минимальный престиж</label>
                    <input type="number" name="prestige_min" value="{{ unit.prestige_min or 0 }}" min="0">
                </div>
                <div class="form-group">
                    <label>Максимальный престиж</label>
                    <input type="number" name="prestige_max" value="{{ unit.prestige_max or 100 }}" min="0">
                </div>
            </div>

            <div class="checkbox-group">
                <input type="checkbox" name="is_flying" id="is_flying" {% if unit.is_flying %}checked{% endif %}>
                <label for="is_flying" style="margin-bottom: 0;">🦅 Летающий юнит</label>
            </div>

            <div class="checkbox-group">
                <input type="checkbox" name="is_kamikaze" id="is_kamikaze" {% if unit.is_kamikaze %}checked{% endif %}>
                <label for="is_kamikaze" style="margin-bottom: 0;">💥 Камикадзе</label>
            </div>

            <button type="submit" class="btn btn-success">💾 Сохранить</button>
            <a href="{{ url_for('races.edit_race', race_id=race.id) }}" class="btn btn-secondary">Назад</a>
        </form>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""

UNIT_SKINS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Скины уровня расы - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .skins-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }
        .skin-card { background: #333; border-radius: 8px; padding: 15px; text-align: center; }
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
        <h1>🎨 Скины уровня расы: {{ unit.icon }} {{ unit.name }} (ур. {{ unit.level }})</h1>
        <p style="color: #aaa;">Раса: {{ race.name }}</p>

        <a href="{{ url_for('races.add_unit_skin', race_id=race.id, unit_id=unit.id) }}" class="btn btn-success">➕ Добавить скин уровня расы</a>
        <a href="{{ url_for('races.edit_race', race_id=race.id) }}" class="btn btn-secondary">← Назад к расе</a>

        <div class="skins-grid">
            {% for skin in skins %}
            <div class="skin-card">
                <h4>{{ skin.name }}</h4>
                {% if skin.image_data %}
                <img src="{{ url_for('races.skin_image', skin_id=skin.id) }}" alt="Скин">
                {% else %}
                <div class="no-image">Нет изображения</div>
                {% endif %}
                <p style="font-size: 12px; color: #aaa;">{{ skin.description or 'Без описания' }}</p>
                <div>
                    <a href="{{ url_for('races.edit_unit_skin', race_id=race.id, unit_id=unit.id, skin_id=skin.id) }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;">✏️</a>
                    <button onclick="deleteSkin({{ skin.id }})" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;">🗑️</button>
                </div>
            </div>
            {% else %}
            <p style="color: #aaa;">Нет скинов уровня расы. Добавьте первый!</p>
            {% endfor %}
        </div>
    </div>

    <script>
    function deleteSkin(skinId) {
        if (confirm('Удалить этот скин?')) {
            fetch('/admin/races/skin/' + skinId + '/delete', {
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
    """ + FOOTER_TEMPLATE + """
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
            session_db.flush()  # Получаем ID расы

            # Автоматически создаём 7 юнитов (по одному на каждый уровень)
            default_unit_names = [
                'Крестьянин', 'Лучник', 'Грифон', 'Мечник',
                'Монах', 'Всадник', 'Ангел'
            ]
            for level in range(1, 8):
                unit = RaceUnit(
                    race_id=race.id,
                    level=level,
                    name=default_unit_names[level - 1],
                    icon='🎮',
                    is_flying=False,
                    is_kamikaze=False
                )
                session_db.add(unit)

            # Создаём уровни стоимости (по умолчанию)
            default_costs = [50, 100, 200, 400, 800, 1500, 3000]
            for level in range(1, 8):
                unit_level = UnitLevel(
                    race_id=race.id,
                    level=level,
                    cost=default_costs[level - 1]
                )
                session_db.add(unit_level)

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


@races_bp.route('/<int:race_id>/unit/<int:unit_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_race_unit(race_id, unit_id):
    """Редактировать юнит расы"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        unit = session_db.query(RaceUnit).filter_by(id=unit_id, race_id=race_id).first()

        if not race or not unit:
            return redirect(url_for('races.races_list'))

        if request.method == 'POST':
            unit.name = request.form.get('name')
            unit.icon = request.form.get('icon', '🎮')
            unit.is_flying = request.form.get('is_flying') == 'on'
            unit.is_kamikaze = request.form.get('is_kamikaze') == 'on'
            unit.prestige_min = int(request.form.get('prestige_min', 0) or 0)
            unit.prestige_max = int(request.form.get('prestige_max', 100) or 100)
            session_db.commit()
            return redirect(url_for('races.edit_race', race_id=race_id))

        return render_template_string(EDIT_UNIT_TEMPLATE, race=race, unit=unit)


@races_bp.route('/<int:race_id>/unit/<int:unit_id>/skins')
@admin_required
def unit_skins(race_id, unit_id):
    """Скины юнита расы"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        unit = session_db.query(RaceUnit).filter_by(id=unit_id, race_id=race_id).first()

        if not race or not unit:
            return redirect(url_for('races.races_list'))

        skins = session_db.query(RaceUnitSkin).filter_by(race_unit_id=unit_id).all()

        return render_template_string(UNIT_SKINS_TEMPLATE, race=race, unit=unit, skins=skins)


ADD_SKIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Добавить скин уровня расы - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .form-group input[type="file"] { padding: 8px; }
        .form-group textarea { min-height: 80px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
        .image-preview { max-width: 200px; max-height: 200px; margin-top: 10px; border: 2px solid #444; border-radius: 5px; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>➕ Добавить скин уровня расы для: {{ unit.icon }} {{ unit.name }}</h1>
        <p style="color: #aaa;">Раса: {{ race.name }} | Уровень: {{ unit.level }}</p>

        <form method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label>Название скина</label>
                <input type="text" name="name" required placeholder="Базовый скин">
            </div>

            <div class="form-group">
                <label>Изображение скина (PNG, JPG до 5MB)</label>
                <input type="file" name="image" accept="image/png,image/jpeg,image/gif,image/webp" onchange="previewImage(this)">
                <img id="imagePreview" class="image-preview" style="display: none;">
            </div>

            <div class="form-group">
                <label>Описание</label>
                <textarea name="description" placeholder="Описание скина (необязательно)"></textarea>
            </div>

            <button type="submit" class="btn btn-success">Создать</button>
            <a href="{{ url_for('races.unit_skins', race_id=race.id, unit_id=unit.id) }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
    <script>
    function previewImage(input) {
        if (input.files && input.files[0]) {
            var reader = new FileReader();
            reader.onload = function(e) {
                var preview = document.getElementById('imagePreview');
                preview.src = e.target.result;
                preview.style.display = 'block';
            }
            reader.readAsDataURL(input.files[0]);
        }
    }
    </script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


@races_bp.route('/<int:race_id>/unit/<int:unit_id>/skin/add', methods=['GET', 'POST'])
@admin_required
def add_unit_skin(race_id, unit_id):
    """Добавить скин юниту"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        unit = session_db.query(RaceUnit).filter_by(id=unit_id, race_id=race_id).first()

        if not race or not unit:
            return redirect(url_for('races.races_list'))

        if request.method == 'POST':
            # Обработка загруженного изображения
            image_data = None
            image_mime_type = None

            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    # Проверка размера (максимум 5MB)
                    file.seek(0, 2)  # Перейти в конец файла
                    size = file.tell()
                    file.seek(0)  # Вернуться в начало

                    if size <= 5 * 1024 * 1024:  # 5MB
                        image_data = file.read()
                        image_mime_type = file.content_type or 'image/png'

            skin = RaceUnitSkin(
                race_unit_id=unit_id,
                name=request.form.get('name'),
                image_data=image_data,
                image_mime_type=image_mime_type,
                description=request.form.get('description') or None
            )
            session_db.add(skin)
            session_db.commit()
            return redirect(url_for('races.unit_skins', race_id=race_id, unit_id=unit_id))

        return render_template_string(ADD_SKIN_TEMPLATE, race=race, unit=unit)


EDIT_SKIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Редактировать скин уровня расы - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .form-group input[type="file"] { padding: 8px; }
        .form-group textarea { min-height: 80px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .current-image { max-width: 200px; max-height: 200px; margin: 10px 0; border: 2px solid #444; border-radius: 5px; }
        .image-preview { max-width: 200px; max-height: 200px; margin-top: 10px; border: 2px solid #444; border-radius: 5px; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>✏️ Редактировать скин уровня расы: {{ skin.name }}</h1>
        <p style="color: #aaa;">Юнит: {{ unit.icon }} {{ unit.name }} | Раса: {{ race.name }}</p>

        <form method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label>Название скина</label>
                <input type="text" name="name" required value="{{ skin.name }}">
            </div>

            <div class="form-group">
                <label>Текущее изображение</label>
                {% if skin.image_data %}
                <div>
                    <img src="{{ url_for('races.skin_image', skin_id=skin.id) }}" class="current-image" alt="Текущий скин">
                    <br>
                    <label style="color: #aaa;">
                        <input type="checkbox" name="delete_image"> Удалить текущее изображение
                    </label>
                </div>
                {% else %}
                <p style="color: #666;">Изображение не загружено</p>
                {% endif %}
            </div>

            <div class="form-group">
                <label>Загрузить новое изображение (PNG, JPG до 5MB)</label>
                <input type="file" name="image" accept="image/png,image/jpeg,image/gif,image/webp" onchange="previewImage(this)">
                <img id="imagePreview" class="image-preview" style="display: none;">
            </div>

            <div class="form-group">
                <label>Описание</label>
                <textarea name="description">{{ skin.description or '' }}</textarea>
            </div>

            <button type="submit" class="btn btn-success">💾 Сохранить</button>
            <a href="{{ url_for('races.unit_skins', race_id=race.id, unit_id=unit.id) }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
    <script>
    function previewImage(input) {
        if (input.files && input.files[0]) {
            var reader = new FileReader();
            reader.onload = function(e) {
                var preview = document.getElementById('imagePreview');
                preview.src = e.target.result;
                preview.style.display = 'block';
            }
            reader.readAsDataURL(input.files[0]);
        }
    }
    </script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


@races_bp.route('/<int:race_id>/unit/<int:unit_id>/skin/<int:skin_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_unit_skin(race_id, unit_id, skin_id):
    """Редактировать скин юнита"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        unit = session_db.query(RaceUnit).filter_by(id=unit_id, race_id=race_id).first()
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id, race_unit_id=unit_id).first()

        if not race or not unit or not skin:
            return redirect(url_for('races.races_list'))

        if request.method == 'POST':
            skin.name = request.form.get('name')
            skin.description = request.form.get('description') or None

            # Удаление изображения
            if request.form.get('delete_image') == 'on':
                skin.image_data = None
                skin.image_mime_type = None

            # Загрузка нового изображения
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    # Проверка размера (максимум 5MB)
                    file.seek(0, 2)
                    size = file.tell()
                    file.seek(0)

                    if size <= 5 * 1024 * 1024:  # 5MB
                        skin.image_data = file.read()
                        skin.image_mime_type = file.content_type or 'image/png'

            session_db.commit()
            return redirect(url_for('races.unit_skins', race_id=race_id, unit_id=unit_id))

        return render_template_string(EDIT_SKIN_TEMPLATE, race=race, unit=unit, skin=skin)


@races_bp.route('/skin/<int:skin_id>/delete', methods=['POST'])
@admin_required
def delete_skin(skin_id):
    """Удалить скин"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id).first()
        if skin:
            session_db.delete(skin)
            session_db.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Скин не найден'})


@races_bp.route('/skin/<int:skin_id>/image')
def skin_image(skin_id):
    """Отдача изображения скина из БД"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id).first()
        if skin and skin.image_data:
            return Response(
                skin.image_data,
                mimetype=skin.image_mime_type or 'image/png',
                headers={'Cache-Control': 'public, max-age=3600'}
            )
        # Возвращаем пустую картинку 1x1 PNG если изображение не найдено
        empty_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        return Response(empty_png, mimetype='image/png', status=404)
