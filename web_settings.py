#!/usr/bin/env python3
"""
Модуль управления сеттингами для веб-интерфейса
"""

import os
import logging
from datetime import datetime
from flask import Blueprint, render_template_string, request, jsonify, session, redirect, url_for
from functools import wraps

from db.models import Base, GameUser, GameSetting, SettingUnit, SettingLevelSkin, UserSetting, Army, ArmyUnit
from db.repository import Database
from web_templates import HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE

logger = logging.getLogger(__name__)

# Blueprint для сеттингов
settings_bp = Blueprint('settings', __name__, url_prefix='/admin/settings')

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

SETTINGS_LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Сеттинги - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .settings-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }
        .setting-card { background: #2a2a2a; border-radius: 10px; padding: 20px; }
        .setting-card h3 { margin: 0 0 10px 0; color: #ffd700; }
        .setting-card .description { color: #aaa; font-size: 14px; margin-bottom: 15px; }
        .setting-card .badge { display: inline-block; padding: 3px 8px; border-radius: 5px; font-size: 12px; margin-right: 5px; }
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
        <h1>⚙️ Управление сеттингами</h1>

        <a href="{{ url_for('settings.create_setting') }}" class="btn btn-success add-btn">➕ Создать сеттинг</a>

        <div class="settings-grid">
            {% for setting in settings %}
            <div class="setting-card">
                <h3>{{ setting.name }}</h3>
                <p class="description">{{ setting.description or 'Нет описания' }}</p>
                <div>
                    {% if setting.is_free %}
                    <span class="badge badge-free">Бесплатный</span>
                    {% else %}
                    <span class="badge badge-paid">Платный</span>
                    {% endif %}
                    <span class="badge" style="background: #9b59b6;">{{ setting.setting_units|length }}/7 юнитов</span>
                </div>
                <div style="margin-top: 15px;">
                    <a href="{{ url_for('settings.edit_setting', setting_id=setting.id) }}" class="btn btn-primary btn-sm">✏️ Редактировать</a>
                    <a href="{{ url_for('settings.setting_skins', setting_id=setting.id) }}" class="btn btn-primary btn-sm">🎨 Скины</a>
                    <button onclick="deleteSetting({{ setting.id }})" class="btn btn-danger btn-sm">🗑️ Удалить</button>
                </div>
            </div>
            {% else %}
            <p style="color: #aaa;">Сеттинги не найдены. Создайте первый сеттинг!</p>
            {% endfor %}
        </div>
    </div>

    <script>
    function deleteSetting(settingId) {
        if (confirm('Вы уверены, что хотите удалить этот сеттинг?')) {
            fetch('/admin/settings/' + settingId + '/delete', {
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

CREATE_SETTING_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Создать сеттинг - Админ-панель</title>
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
        <h1>➕ Создать сеттинг</h1>

        <form method="POST" action="{{ url_for('settings.create_setting') }}">
            <div class="form-group">
                <label>Название</label>
                <input type="text" name="name" required placeholder="Название сеттинга">
            </div>

            <div class="form-group">
                <label>Описание</label>
                <textarea name="description" placeholder="Описание сеттинга (необязательно)"></textarea>
            </div>

            <div class="form-group checkbox-group">
                <input type="checkbox" name="is_free" id="is_free">
                <label for="is_free" style="margin-bottom: 0;">Бесплатный сеттинг</label>
            </div>

            <button type="submit" class="btn btn-success">Создать</button>
            <a href="{{ url_for('settings.settings_list') }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
</body>
</html>
"""

EDIT_SETTING_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Редактировать сеттинг - Админ-панель</title>
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
        <h1>✏️ Редактировать сеттинг: {{ setting.name }}</h1>

        <form method="POST" action="{{ url_for('settings.edit_setting', setting_id=setting.id) }}">
            <div class="form-group">
                <label>Название</label>
                <input type="text" name="name" required value="{{ setting.name }}">
            </div>

            <div class="form-group">
                <label>Описание</label>
                <textarea name="description">{{ setting.description or '' }}</textarea>
            </div>

            <div class="form-group checkbox-group">
                <input type="checkbox" name="is_free" id="is_free" {% if setting.is_free %}checked{% endif %}>
                <label for="is_free" style="margin-bottom: 0;">Бесплатный сеттинг</label>
            </div>

            <button type="submit" class="btn btn-success">💾 Сохранить</button>
            <a href="{{ url_for('settings.settings_list') }}" class="btn btn-secondary">Назад</a>
        </form>

        <div class="units-section">
            <h2>⚔️ Юниты сеттинга (7 уровней)</h2>
            <a href="{{ url_for('settings.add_setting_unit', setting_id=setting.id) }}" class="btn btn-primary">➕ Добавить юнит</a>

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
                        <a href="{{ url_for('settings.edit_setting_unit', setting_id=setting.id, unit_id=unit.id) }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;">✏️</a>
                        <button onclick="deleteUnit({{ unit.id }})" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;">🗑️</button>
                    </div>
                    {% else %}
                    <h4 style="color: #666;">Не задан</h4>
                    <a href="{{ url_for('settings.add_setting_unit', setting_id=setting.id) }}?level={{ level }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px; margin-top: 10px;">➕ Добавить</a>
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
        <h1>➕ Добавить юнит для: {{ setting.name }}</h1>

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
            <a href="{{ url_for('settings.edit_setting', setting_id=setting.id) }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
</body>
</html>
"""

SKINS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Скины сеттинга - Админ-панель</title>
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
        <h1>🎨 Скины для: {{ setting.name }}</h1>

        <a href="{{ url_for('settings.add_skin', setting_id=setting.id) }}" class="btn btn-success">➕ Добавить скин</a>
        <a href="{{ url_for('settings.edit_setting', setting_id=setting.id) }}" class="btn btn-secondary">← Назад к сеттингу</a>

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
                    <a href="{{ url_for('settings.edit_skin', setting_id=setting.id, skin_id=skin.id) }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;">✏️</a>
                    <button onclick="deleteSkin({{ skin.id }})" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;">🗑️</button>
                </div>
                {% else %}
                <h4 style="color: #666;">Не задан</h4>
                <div class="no-image">Нет скина</div>
                <a href="{{ url_for('settings.add_skin', setting_id=setting.id) }}?level={{ level }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;">➕</a>
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

@settings_bp.route('/')
@admin_required
def settings_list():
    """Список сеттингов"""
    with db.get_session() as session_db:
        settings = session_db.query(GameSetting).all()
        return render_template_string(SETTINGS_LIST_TEMPLATE, settings=settings)


@settings_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create_setting():
    """Создать новый сеттинг"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_free = request.form.get('is_free') == 'on'

        with db.get_session() as session_db:
            setting = GameSetting(
                name=name,
                description=description,
                is_free=is_free
            )
            session_db.add(setting)
            session_db.commit()
            return redirect(url_for('settings.edit_setting', setting_id=setting.id))

    return render_template_string(CREATE_SETTING_TEMPLATE)


@settings_bp.route('/<int:setting_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_setting(setting_id):
    """Редактировать сеттинг"""
    with db.get_session() as session_db:
        setting = session_db.query(GameSetting).filter_by(id=setting_id).first()
        if not setting:
            return redirect(url_for('settings.settings_list'))

        if request.method == 'POST':
            setting.name = request.form.get('name')
            setting.description = request.form.get('description')
            setting.is_free = request.form.get('is_free') == 'on'
            session_db.commit()
            return redirect(url_for('settings.edit_setting', setting_id=setting_id))

        # Получаем юниты по уровням
        units = session_db.query(SettingUnit).filter_by(setting_id=setting_id).all()
        units_by_level = {u.level: u for u in units}

        return render_template_string(EDIT_SETTING_TEMPLATE, setting=setting, units_by_level=units_by_level)


@settings_bp.route('/<int:setting_id>/delete', methods=['POST'])
@admin_required
def delete_setting(setting_id):
    """Удалить сеттинг"""
    with db.get_session() as session_db:
        setting = session_db.query(GameSetting).filter_by(id=setting_id).first()
        if setting:
            session_db.delete(setting)
            session_db.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Сеттинг не найден'})


@settings_bp.route('/<int:setting_id>/unit/add', methods=['GET', 'POST'])
@admin_required
def add_setting_unit(setting_id):
    """Добавить юнит в сеттинг"""
    with db.get_session() as session_db:
        setting = session_db.query(GameSetting).filter_by(id=setting_id).first()
        if not setting:
            return redirect(url_for('settings.settings_list'))

        if request.method == 'POST':
            unit = SettingUnit(
                setting_id=setting_id,
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
            return redirect(url_for('settings.edit_setting', setting_id=setting_id))

        default_level = int(request.args.get('level', 1))
        return render_template_string(ADD_UNIT_TEMPLATE, setting=setting, default_level=default_level)


@settings_bp.route('/<int:setting_id>/unit/<int:unit_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_setting_unit(setting_id, unit_id):
    """Редактировать юнит сеттинга"""
    with db.get_session() as session_db:
        setting = session_db.query(GameSetting).filter_by(id=setting_id).first()
        unit = session_db.query(SettingUnit).filter_by(id=unit_id, setting_id=setting_id).first()

        if not setting or not unit:
            return redirect(url_for('settings.settings_list'))

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
            return redirect(url_for('settings.edit_setting', setting_id=setting_id))

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

        return render_template_string(template, setting=setting, default_level=unit.level)


@settings_bp.route('/unit/<int:unit_id>/delete', methods=['POST'])
@admin_required
def delete_setting_unit(unit_id):
    """Удалить юнит сеттинга"""
    with db.get_session() as session_db:
        unit = session_db.query(SettingUnit).filter_by(id=unit_id).first()
        if unit:
            session_db.delete(unit)
            session_db.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Юнит не найден'})


@settings_bp.route('/<int:setting_id>/skins')
@admin_required
def setting_skins(setting_id):
    """Скины сеттинга"""
    with db.get_session() as session_db:
        setting = session_db.query(GameSetting).filter_by(id=setting_id).first()
        if not setting:
            return redirect(url_for('settings.settings_list'))

        skins = session_db.query(SettingLevelSkin).filter_by(setting_id=setting_id).all()
        skins_by_level = {s.level: s for s in skins}

        return render_template_string(SKINS_TEMPLATE, setting=setting, skins_by_level=skins_by_level)


@settings_bp.route('/<int:setting_id>/skin/add', methods=['GET', 'POST'])
@admin_required
def add_skin(setting_id):
    """Добавить скин"""
    with db.get_session() as session_db:
        setting = session_db.query(GameSetting).filter_by(id=setting_id).first()
        if not setting:
            return redirect(url_for('settings.settings_list'))

        if request.method == 'POST':
            skin = SettingLevelSkin(
                setting_id=setting_id,
                level=int(request.form.get('level')),
                name=request.form.get('name'),
                image_path=request.form.get('image_path') or None
            )
            session_db.add(skin)
            session_db.commit()
            return redirect(url_for('settings.setting_skins', setting_id=setting_id))

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
        <h1>➕ Добавить скин для: {{ setting.name }}</h1>

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
            <a href="{{ url_for('settings.setting_skins', setting_id=setting.id) }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
</body>
</html>
"""
        return render_template_string(template, setting=setting, default_level=default_level)


@settings_bp.route('/<int:setting_id>/skin/<int:skin_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_skin(setting_id, skin_id):
    """Редактировать скин"""
    with db.get_session() as session_db:
        setting = session_db.query(GameSetting).filter_by(id=setting_id).first()
        skin = session_db.query(SettingLevelSkin).filter_by(id=skin_id, setting_id=setting_id).first()

        if not setting or not skin:
            return redirect(url_for('settings.settings_list'))

        if request.method == 'POST':
            skin.level = int(request.form.get('level'))
            skin.name = request.form.get('name')
            skin.image_path = request.form.get('image_path') or None
            session_db.commit()
            return redirect(url_for('settings.setting_skins', setting_id=setting_id))

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
            <a href="{{ url_for('settings.setting_skins', setting_id=setting.id) }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
</body>
</html>
"""
        return render_template_string(template, setting=setting, skin=skin)


@settings_bp.route('/skin/<int:skin_id>/delete', methods=['POST'])
@admin_required
def delete_skin(skin_id):
    """Удалить скин"""
    with db.get_session() as session_db:
        skin = session_db.query(SettingLevelSkin).filter_by(id=skin_id).first()
        if skin:
            session_db.delete(skin)
            session_db.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Скин не найден'})
