#!/usr/bin/env python3
"""
Модуль для управления сеттингами и изображениями в админ-панели
"""

from flask import Blueprint, render_template_string, request, redirect, url_for, flash, send_file, session as flask_session
from functools import wraps
from db import Database
from db.image_models import Setting, UnitImage, UnitLevel
from decimal import Decimal
import io
from web_templates import HEADER_TEMPLATE, BASE_STYLE

# Создаем Blueprint для маршрутов
images_bp = Blueprint('images_manager', __name__, url_prefix='/admin')

# Инициализируем подключение к базе данных
db = Database()


def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in flask_session:
            flash('Требуется авторизация', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# === УПРАВЛЕНИЕ СЕТТИНГАМИ ===

@images_bp.route('/settings')
@login_required
def settings_list():
    """Список всех сеттингов"""
    username = flask_session.get('username')

    # Ограничиваем доступ только для okarien
    if username != 'okarien':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('admin_units_list'))

    with db.get_session() as db_session:
        settings = db_session.query(Setting).all()

        # Загружаем все атрибуты
        for setting in settings:
            _ = setting.id
            _ = setting.name
            _ = setting.description
            _ = setting.is_tournament
            _ = setting.unlock_cost
            _ = setting.subscription_only
            _ = setting.created_at

        db_session.expunge_all()

    template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Управление сеттингами</title>
''' + BASE_STYLE + '''
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>Управление сеттингами (рассами)</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div style="margin: 20px 0;">
            <a href="{{ url_for('images_manager.setting_create') }}" class="btn btn-primary">Создать сеттинг</a>
        </div>

    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Название</th>
                <th>Описание</th>
                <th>Турнирный</th>
                <th>Стоимость открытия</th>
                <th>Только подписка</th>
                <th>Создан</th>
                <th>Действия</th>
            </tr>
        </thead>
        <tbody>
            {% for setting in settings %}
            <tr>
                <td>{{ setting.id }}</td>
                <td><strong>{{ setting.name }}</strong></td>
                <td>{{ setting.description or '-' }}</td>
                <td>{{ '✓' if setting.is_tournament else '✗' }}</td>
                <td>{{ setting.unlock_cost }}</td>
                <td>{{ '✓' if setting.subscription_only else '✗' }}</td>
                <td>{{ setting.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                <td>
                    <a href="{{ url_for('images_manager.setting_edit', setting_id=setting.id) }}" class="btn btn-edit">Редактировать</a>
                    <a href="{{ url_for('images_manager.setting_delete', setting_id=setting.id) }}"
                       class="btn btn-delete"
                       onclick="return confirm('Удалить сеттинг {{ setting.name }}?')">Удалить</a>
                </td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    {% if not settings %}
        <p>Нет сеттингов. <a href="{{ url_for('images_manager.setting_create') }}">Создать первый сеттинг</a></p>
    {% endif %}
    </div>
</body>
</html>
    '''

    return render_template_string(template, settings=settings, active_page='settings')


@images_bp.route('/settings/create', methods=['GET', 'POST'])
@login_required
def setting_create():
    """Создание нового сеттинга"""
    username = flask_session.get('username')

    if username != 'okarien':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('admin_units_list'))

    if request.method == 'POST':
        try:
            name = request.form.get('name')
            description = request.form.get('description')
            is_tournament = 'is_tournament' in request.form
            unlock_cost = Decimal(request.form.get('unlock_cost', '0'))
            subscription_only = 'subscription_only' in request.form

            with db.get_session() as db_session:
                setting = Setting(
                    name=name,
                    description=description,
                    is_tournament=is_tournament,
                    unlock_cost=unlock_cost,
                    subscription_only=subscription_only
                )
                db_session.add(setting)
                db_session.commit()

            flash(f'Сеттинг "{name}" успешно создан!', 'success')
            return redirect(url_for('images_manager.settings_list'))
        except Exception as e:
            flash(f'Ошибка при создании сеттинга: {str(e)}', 'error')

    template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Создать сеттинг</title>
''' + BASE_STYLE + '''
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>Создать новый сеттинг</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

    <form method="POST">
        <div class="form-group">
            <label for="name">Название сеттинга *:</label>
            <input type="text" id="name" name="name" required>
        </div>

        <div class="form-group">
            <label for="description">Описание:</label>
            <textarea id="description" name="description"></textarea>
        </div>

        <div class="form-group">
            <label>
                <input type="checkbox" name="is_tournament">
                Турнирный сеттинг
            </label>
        </div>

        <div class="form-group">
            <label for="unlock_cost">Стоимость открытия (в монетах):</label>
            <input type="number" id="unlock_cost" name="unlock_cost" value="0" step="0.01" min="0">
        </div>

        <div class="form-group">
            <label>
                <input type="checkbox" name="subscription_only">
                Доступен только по подписке
            </label>
        </div>

        <div class="form-group">
            <button type="submit" class="btn btn-primary">Создать сеттинг</button>
            <a href="{{ url_for('images_manager.settings_list') }}" class="btn btn-secondary">Отмена</a>
        </div>
    </form>
    </div>
</body>
</html>
    '''

    return render_template_string(template, active_page='settings')


@images_bp.route('/settings/edit/<int:setting_id>', methods=['GET', 'POST'])
@login_required
def setting_edit(setting_id):
    """Редактирование сеттинга"""
    username = flask_session.get('username')

    if username != 'okarien':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('admin_units_list'))

    with db.get_session() as db_session:
        setting = db_session.query(Setting).filter_by(id=setting_id).first()

        if not setting:
            flash('Сеттинг не найден', 'error')
            return redirect(url_for('images_manager.settings_list'))

        if request.method == 'POST':
            try:
                setting.name = request.form.get('name')
                setting.description = request.form.get('description')
                setting.is_tournament = 'is_tournament' in request.form
                setting.unlock_cost = Decimal(request.form.get('unlock_cost', '0'))
                setting.subscription_only = 'subscription_only' in request.form

                db_session.commit()

                flash(f'Сеттинг "{setting.name}" успешно обновлен!', 'success')
                return redirect(url_for('images_manager.settings_list'))
            except Exception as e:
                flash(f'Ошибка при обновлении сеттинга: {str(e)}', 'error')

        # Загружаем атрибуты для отображения
        _ = setting.id
        _ = setting.name
        _ = setting.description
        _ = setting.is_tournament
        _ = setting.unlock_cost
        _ = setting.subscription_only

        db_session.expunge_all()

    template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Редактировать сеттинг</title>
''' + BASE_STYLE + '''
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>Редактировать сеттинг "{{ setting.name }}"</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

    <form method="POST">
        <div class="form-group">
            <label for="name">Название сеттинга *:</label>
            <input type="text" id="name" name="name" value="{{ setting.name }}" required>
        </div>

        <div class="form-group">
            <label for="description">Описание:</label>
            <textarea id="description" name="description">{{ setting.description or '' }}</textarea>
        </div>

        <div class="form-group">
            <label>
                <input type="checkbox" name="is_tournament" {% if setting.is_tournament %}checked{% endif %}>
                Турнирный сеттинг
            </label>
        </div>

        <div class="form-group">
            <label for="unlock_cost">Стоимость открытия (в монетах):</label>
            <input type="number" id="unlock_cost" name="unlock_cost" value="{{ setting.unlock_cost }}" step="0.01" min="0">
        </div>

        <div class="form-group">
            <label>
                <input type="checkbox" name="subscription_only" {% if setting.subscription_only %}checked{% endif %}>
                Доступен только по подписке
            </label>
        </div>

        <div class="form-group">
            <button type="submit" class="btn btn-primary">Сохранить изменения</button>
            <a href="{{ url_for('images_manager.settings_list') }}" class="btn btn-secondary">Отмена</a>
        </div>
    </form>
    </div>
</body>
</html>
    '''

    return render_template_string(template, setting=setting, active_page='settings')


@images_bp.route('/settings/delete/<int:setting_id>')
@login_required
def setting_delete(setting_id):
    """Удаление сеттинга"""
    username = flask_session.get('username')

    if username != 'okarien':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('admin_units_list'))

    try:
        with db.get_session() as db_session:
            setting = db_session.query(Setting).filter_by(id=setting_id).first()

            if not setting:
                flash('Сеттинг не найден', 'error')
            else:
                name = setting.name
                db_session.delete(setting)
                db_session.commit()
                flash(f'Сеттинг "{name}" успешно удален!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении сеттинга: {str(e)}', 'error')

    return redirect(url_for('images_manager.settings_list'))


# === УПРАВЛЕНИЕ ИЗОБРАЖЕНИЯМИ ===

@images_bp.route('/unit_images')
@login_required
def unit_images_list():
    """Список всех изображений юнитов"""
    username = flask_session.get('username')

    if username != 'okarien':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('admin_units_list'))

    with db.get_session() as db_session:
        images = db_session.query(UnitImage).all()
        settings = db_session.query(Setting).all()

        # Загружаем все атрибуты
        for img in images:
            _ = img.id
            _ = img.description
            _ = img.setting_id
            _ = img.setting.name if img.setting else None
            _ = img.unit_level_id
            _ = img.unit_level.name if img.unit_level else None
            _ = img.subscription_only
            _ = img.created_at

        db_session.expunge_all()

    template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Управление изображениями юнитов</title>
''' + BASE_STYLE + '''
    <style>
        table { font-size: 12px; }
        th, td { padding: 8px; }
        .btn { padding: 6px 12px; font-size: 12px; }
    </style>
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>Управление изображениями юнитов</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div style="margin: 20px 0;">
            <a href="{{ url_for('images_manager.unit_image_create') }}" class="btn btn-primary">Загрузить изображение</a>
            <a href="{{ url_for('images_manager.settings_list') }}" class="btn">Управление сеттингами</a>
            <a href="{{ url_for('images_manager.unit_levels_list') }}" class="btn">Уровни юнитов</a>
        </div>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Изображение</th>
                    <th>Описание</th>
                    <th>Сеттинг</th>
                    <th>Уровень</th>
                    <th>Подписка</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                {% for img in images %}
                <tr>
                    <td>{{ img.id }}</td>
                    <td>
                        <img src="{{ url_for('images_manager.unit_image_view', image_id=img.id) }}" class="thumbnail" alt="Image">
                    </td>
                    <td>{{ img.description or '-' }}</td>
                    <td>{{ img.setting.name if img.setting else '-' }}</td>
                    <td>{{ img.unit_level.name if img.unit_level else '-' }}</td>
                    <td>{{ 'Да' if img.subscription_only else 'Нет' }}</td>
                    <td>
                        <a href="{{ url_for('images_manager.unit_image_edit', image_id=img.id) }}" class="btn btn-edit">Редактировать</a>
                        <a href="{{ url_for('images_manager.unit_image_delete', image_id=img.id) }}"
                           class="btn btn-delete"
                           onclick="return confirm('Удалить изображение?')">Удалить</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        {% if not images %}
            <p>Нет загруженных изображений. <a href="{{ url_for('images_manager.unit_image_create') }}">Загрузить первое изображение</a></p>
        {% endif %}
    </div>
</body>
</html>
    '''

    return render_template_string(template, images=images, active_page='unit_images')


@images_bp.route('/unit_images/create', methods=['GET', 'POST'])
@login_required
def unit_image_create():
    """Загрузка нового изображения юнита"""
    username = flask_session.get('username')

    if username != 'okarien':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('admin_units_list'))

    with db.get_session() as db_session:
        settings = db_session.query(Setting).all()
        unit_levels = db_session.query(UnitLevel).order_by(UnitLevel.level).all()
        db_session.expunge_all()

    if request.method == 'POST':
        try:
            # Получаем файл изображения
            if 'image' not in request.files:
                flash('Файл не выбран', 'error')
                return redirect(request.url)

            file = request.files['image']
            if file.filename == '':
                flash('Файл не выбран', 'error')
                return redirect(request.url)

            # Читаем файл в bytes
            image_data = file.read()

            # Получаем параметры
            description = request.form.get('description')
            setting_id = int(request.form.get('setting_id'))

            # Уровень юнита
            unit_level_id = request.form.get('unit_level_id')
            unit_level_id = int(unit_level_id) if unit_level_id else None

            subscription_only = 'subscription_only' in request.form

            with db.get_session() as db_session:
                unit_image = UnitImage(
                    description=description,
                    image_data=image_data,
                    setting_id=setting_id,
                    unit_level_id=unit_level_id,
                    subscription_only=subscription_only
                )
                db_session.add(unit_image)
                db_session.commit()

            flash('Изображение успешно загружено!', 'success')
            return redirect(url_for('images_manager.unit_images_list'))
        except Exception as e:
            flash(f'Ошибка при загрузке изображения: {str(e)}', 'error')

    template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Загрузить изображение</title>
''' + BASE_STYLE + '''
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>Загрузить новое изображение юнита</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

    <form method="POST" enctype="multipart/form-data">
        <div class="form-group">
            <label for="image">Файл изображения *:</label>
            <input type="file" id="image" name="image" accept="image/*" required>
        </div>

        <div class="form-group">
            <label for="description">Описание:</label>
            <textarea id="description" name="description"></textarea>
        </div>

        <div class="form-group">
            <label for="setting_id">Сеттинг (расса) *:</label>
            <select id="setting_id" name="setting_id" required>
                <option value="">Выберите сеттинг</option>
                {% for setting in settings %}
                <option value="{{ setting.id }}">{{ setting.name }}</option>
                {% endfor %}
            </select>
        </div>

        <div class="form-group">
            <label for="unit_level_id">Уровень юнита:</label>
            <select id="unit_level_id" name="unit_level_id">
                <option value="">Не указан</option>
                {% for level in unit_levels %}
                <option value="{{ level.id }}">{{ level.name }}</option>
                {% endfor %}
            </select>
        </div>

        <div class="section">
            <h3>Доступность</h3>

            <div class="form-group">
                <label>
                    <input type="checkbox" name="subscription_only">
                    Доступно только по подписке
                </label>
            </div>
        </div>

        <div class="form-group">
            <button type="submit" class="btn btn-primary">Загрузить изображение</button>
            <a href="{{ url_for('images_manager.unit_images_list') }}" class="btn btn-secondary">Отмена</a>
        </div>
    </form>
    </div>
</body>
</html>
    '''

    return render_template_string(template, settings=settings, unit_levels=unit_levels, active_page='unit_images')


@images_bp.route('/unit_images/view/<int:image_id>')
def unit_image_view(image_id):
    """Просмотр изображения"""
    with db.get_session() as db_session:
        image = db_session.query(UnitImage).filter_by(id=image_id).first()

        if not image:
            return "Image not found", 404

        image_data = image.image_data

    return send_file(io.BytesIO(image_data), mimetype='image/png')


@images_bp.route('/unit_images/delete/<int:image_id>')
@login_required
def unit_image_delete(image_id):
    """Удаление изображения"""
    username = flask_session.get('username')

    if username != 'okarien':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('admin_units_list'))

    try:
        with db.get_session() as db_session:
            image = db_session.query(UnitImage).filter_by(id=image_id).first()

            if not image:
                flash('Изображение не найдено', 'error')
            else:
                db_session.delete(image)
                db_session.commit()
                flash('Изображение успешно удалено!', 'success')
    except Exception as e:
        flash(f'Ошибка при удалении изображения: {str(e)}', 'error')

    return redirect(url_for('images_manager.unit_images_list'))


@images_bp.route('/unit_images/edit/<int:image_id>', methods=['GET', 'POST'])
@login_required
def unit_image_edit(image_id):
    """Редактирование изображения юнита"""
    username = flask_session.get('username')

    if username != 'okarien':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('admin_units_list'))

    with db.get_session() as db_session:
        image = db_session.query(UnitImage).filter_by(id=image_id).first()
        settings = db_session.query(Setting).all()
        unit_levels = db_session.query(UnitLevel).order_by(UnitLevel.level).all()

        if not image:
            flash('Изображение не найдено', 'error')
            return redirect(url_for('images_manager.unit_images_list'))

        if request.method == 'POST':
            try:
                # Обновляем параметры
                image.description = request.form.get('description')
                image.setting_id = int(request.form.get('setting_id'))

                # Уровень юнита
                unit_level_id = request.form.get('unit_level_id')
                image.unit_level_id = int(unit_level_id) if unit_level_id else None

                image.subscription_only = 'subscription_only' in request.form

                # Обновляем изображение если загружен новый файл
                if 'image' in request.files:
                    file = request.files['image']
                    if file.filename != '':
                        image.image_data = file.read()

                db_session.commit()

                flash('Изображение успешно обновлено!', 'success')
                return redirect(url_for('images_manager.unit_images_list'))
            except Exception as e:
                flash(f'Ошибка при обновлении изображения: {str(e)}', 'error')

        # Загружаем атрибуты для отображения
        _ = image.id
        _ = image.description
        _ = image.setting_id
        _ = image.unit_level_id
        _ = image.subscription_only

        db_session.expunge_all()

    template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Редактировать изображение</title>
''' + BASE_STYLE + '''
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>Редактировать изображение #{{ image.id }}</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div style="margin: 20px 0;">
            <img src="{{ url_for('images_manager.unit_image_view', image_id=image.id) }}" style="max-width: 200px; max-height: 200px; border: 1px solid #ddd;">
        </div>

        <form method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label for="image">Заменить изображение (опционально):</label>
                <input type="file" id="image" name="image" accept="image/*">
            </div>

            <div class="form-group">
                <label for="description">Описание:</label>
                <textarea id="description" name="description">{{ image.description or '' }}</textarea>
            </div>

            <div class="form-group">
                <label for="setting_id">Сеттинг (расса) *:</label>
                <select id="setting_id" name="setting_id" required>
                    <option value="">Выберите сеттинг</option>
                    {% for setting in settings %}
                    <option value="{{ setting.id }}" {% if setting.id == image.setting_id %}selected{% endif %}>{{ setting.name }}</option>
                    {% endfor %}
                </select>
            </div>

            <div class="form-group">
                <label for="unit_level_id">Уровень юнита:</label>
                <select id="unit_level_id" name="unit_level_id">
                    <option value="">Не указан</option>
                    {% for level in unit_levels %}
                    <option value="{{ level.id }}" {% if level.id == image.unit_level_id %}selected{% endif %}>{{ level.name }}</option>
                    {% endfor %}
                </select>
            </div>

            <div class="section">
                <h3>Доступность</h3>

                <div class="form-group">
                    <label>
                        <input type="checkbox" name="subscription_only" {% if image.subscription_only %}checked{% endif %}>
                        Доступно только по подписке
                    </label>
                </div>
            </div>

            <div class="form-group">
                <button type="submit" class="btn btn-primary">Сохранить изменения</button>
                <a href="{{ url_for('images_manager.unit_images_list') }}" class="btn btn-secondary">Отмена</a>
            </div>
        </form>
    </div>
</body>
</html>
    '''

    return render_template_string(template, image=image, settings=settings, unit_levels=unit_levels, active_page='unit_images')


# === УПРАВЛЕНИЕ УРОВНЯМИ ЮНИТОВ ===

@images_bp.route('/unit_levels')
@login_required
def unit_levels_list():
    """Список всех уровней юнитов"""
    username = flask_session.get('username')

    if username != 'okarien':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('admin_units_list'))

    with db.get_session() as db_session:
        levels = db_session.query(UnitLevel).order_by(UnitLevel.level).all()

        # Загружаем все атрибуты
        for level in levels:
            _ = level.id
            _ = level.level
            _ = level.name
            _ = level.description
            _ = level.min_damage
            _ = level.max_damage
            _ = level.min_defense
            _ = level.max_defense
            _ = level.min_health
            _ = level.max_health
            _ = level.min_speed
            _ = level.max_speed
            _ = level.min_cost
            _ = level.max_cost

        db_session.expunge_all()

    template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Управление уровнями юнитов</title>
''' + BASE_STYLE + '''
    <style>
        table { font-size: 12px; }
        th, td { padding: 8px; }
        .btn { padding: 6px 12px; font-size: 12px; }
    </style>
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>Управление уровнями юнитов</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <table>
            <thead>
                <tr>
                    <th>Уровень</th>
                    <th>Название</th>
                    <th>Описание</th>
                    <th>Урон</th>
                    <th>Защита</th>
                    <th>Здоровье</th>
                    <th>Скорость</th>
                    <th>Стоимость</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                {% for level in levels %}
                <tr>
                    <td>{{ level.level }}</td>
                    <td><strong>{{ level.name }}</strong></td>
                    <td>{{ level.description or '-' }}</td>
                    <td>{{ level.min_damage }} - {{ level.max_damage }}</td>
                    <td>{{ level.min_defense }} - {{ level.max_defense }}</td>
                    <td>{{ level.min_health }} - {{ level.max_health }}</td>
                    <td>{{ level.min_speed }} - {{ level.max_speed }}</td>
                    <td>{{ level.min_cost }} - {{ level.max_cost }}</td>
                    <td>
                        <a href="{{ url_for('images_manager.unit_level_edit', level_id=level.id) }}" class="btn btn-edit">Редактировать</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        {% if not levels %}
            <p>Нет уровней юнитов. Выполните миграцию базы данных для создания базовых уровней.</p>
        {% endif %}
    </div>
</body>
</html>
    '''

    return render_template_string(template, levels=levels, active_page='unit_levels')


@images_bp.route('/unit_levels/edit/<int:level_id>', methods=['GET', 'POST'])
@login_required
def unit_level_edit(level_id):
    """Редактирование уровня юнита"""
    username = flask_session.get('username')

    if username != 'okarien':
        flash('Доступ запрещен', 'error')
        return redirect(url_for('admin_units_list'))

    with db.get_session() as db_session:
        level = db_session.query(UnitLevel).filter_by(id=level_id).first()

        if not level:
            flash('Уровень не найден', 'error')
            return redirect(url_for('images_manager.unit_levels_list'))

        if request.method == 'POST':
            try:
                level.name = request.form.get('name')
                level.description = request.form.get('description')
                level.min_damage = int(request.form.get('min_damage', 1))
                level.max_damage = int(request.form.get('max_damage', 10))
                level.min_defense = int(request.form.get('min_defense', 1))
                level.max_defense = int(request.form.get('max_defense', 10))
                level.min_health = int(request.form.get('min_health', 10))
                level.max_health = int(request.form.get('max_health', 100))
                level.min_speed = int(request.form.get('min_speed', 1))
                level.max_speed = int(request.form.get('max_speed', 5))
                level.min_cost = Decimal(request.form.get('min_cost', '10'))
                level.max_cost = Decimal(request.form.get('max_cost', '100'))

                db_session.commit()

                flash(f'Уровень "{level.name}" успешно обновлен!', 'success')
                return redirect(url_for('images_manager.unit_levels_list'))
            except Exception as e:
                flash(f'Ошибка при обновлении уровня: {str(e)}', 'error')

        # Загружаем атрибуты для отображения
        _ = level.id
        _ = level.level
        _ = level.name
        _ = level.description
        _ = level.min_damage
        _ = level.max_damage
        _ = level.min_defense
        _ = level.max_defense
        _ = level.min_health
        _ = level.max_health
        _ = level.min_speed
        _ = level.max_speed
        _ = level.min_cost
        _ = level.max_cost

        db_session.expunge_all()

    template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Редактировать уровень юнита</title>
''' + BASE_STYLE + '''
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>Редактировать уровень {{ level.level }}</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <form method="POST">
            <div class="form-group">
                <label for="name">Название *:</label>
                <input type="text" id="name" name="name" value="{{ level.name }}" required>
            </div>

            <div class="form-group">
                <label for="description">Описание:</label>
                <textarea id="description" name="description">{{ level.description or '' }}</textarea>
            </div>

            <div class="section">
                <h3>Диапазоны параметров</h3>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                    <div class="form-group">
                        <label for="min_damage">Минимальный урон:</label>
                        <input type="number" id="min_damage" name="min_damage" value="{{ level.min_damage }}" min="0" required>
                    </div>
                    <div class="form-group">
                        <label for="max_damage">Максимальный урон:</label>
                        <input type="number" id="max_damage" name="max_damage" value="{{ level.max_damage }}" min="0" required>
                    </div>

                    <div class="form-group">
                        <label for="min_defense">Минимальная защита:</label>
                        <input type="number" id="min_defense" name="min_defense" value="{{ level.min_defense }}" min="0" required>
                    </div>
                    <div class="form-group">
                        <label for="max_defense">Максимальная защита:</label>
                        <input type="number" id="max_defense" name="max_defense" value="{{ level.max_defense }}" min="0" required>
                    </div>

                    <div class="form-group">
                        <label for="min_health">Минимальное здоровье:</label>
                        <input type="number" id="min_health" name="min_health" value="{{ level.min_health }}" min="1" required>
                    </div>
                    <div class="form-group">
                        <label for="max_health">Максимальное здоровье:</label>
                        <input type="number" id="max_health" name="max_health" value="{{ level.max_health }}" min="1" required>
                    </div>

                    <div class="form-group">
                        <label for="min_speed">Минимальная скорость:</label>
                        <input type="number" id="min_speed" name="min_speed" value="{{ level.min_speed }}" min="1" required>
                    </div>
                    <div class="form-group">
                        <label for="max_speed">Максимальная скорость:</label>
                        <input type="number" id="max_speed" name="max_speed" value="{{ level.max_speed }}" min="1" required>
                    </div>

                    <div class="form-group">
                        <label for="min_cost">Минимальная стоимость:</label>
                        <input type="number" id="min_cost" name="min_cost" value="{{ level.min_cost }}" step="0.01" min="0" required>
                    </div>
                    <div class="form-group">
                        <label for="max_cost">Максимальная стоимость:</label>
                        <input type="number" id="max_cost" name="max_cost" value="{{ level.max_cost }}" step="0.01" min="0" required>
                    </div>
                </div>
            </div>

            <div class="form-group">
                <button type="submit" class="btn btn-primary">Сохранить изменения</button>
                <a href="{{ url_for('images_manager.unit_levels_list') }}" class="btn btn-secondary">Отмена</a>
            </div>
        </form>
    </div>
</body>
</html>
    '''

    return render_template_string(template, level=level, active_page='unit_levels')
