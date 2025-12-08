#!/usr/bin/env python3
"""
Модуль для управления сеттингами и изображениями в админ-панели
"""

from flask import Blueprint, render_template_string, request, redirect, url_for, flash, send_file, session as flask_session
from functools import wraps
from db.database import Database
from db.image_models import Setting, UnitImage
from decimal import Decimal
import io

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
<html>
<head>
    <title>Управление сеттингами</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:hover { background-color: #f5f5f5; }
        .btn { padding: 8px 16px; text-decoration: none; margin: 2px; display: inline-block; }
        .btn-primary { background-color: #4CAF50; color: white; }
        .btn-edit { background-color: #2196F3; color: white; }
        .btn-delete { background-color: #f44336; color: white; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .success { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
    <h1>Управление сеттингами (рассами)</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <a href="{{ url_for('images_manager.setting_create') }}" class="btn btn-primary">Создать сеттинг</a>
    <a href="{{ url_for('admin_units_list') }}" class="btn">← Назад к админке</a>

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
</body>
</html>
    '''

    return render_template_string(template, settings=settings)


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
<html>
<head>
    <title>Создать сеттинг</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], input[type="number"], textarea {
            width: 100%; max-width: 500px; padding: 8px; box-sizing: border-box;
        }
        textarea { height: 100px; }
        input[type="checkbox"] { margin-right: 5px; }
        .btn { padding: 10px 20px; margin: 5px; cursor: pointer; border: none; }
        .btn-primary { background-color: #4CAF50; color: white; }
        .btn-secondary { background-color: #gray; color: white; text-decoration: none; display: inline-block; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .error { background-color: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
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
</body>
</html>
    '''

    return render_template_string(template)


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
<html>
<head>
    <title>Редактировать сеттинг</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], input[type="number"], textarea {
            width: 100%; max-width: 500px; padding: 8px; box-sizing: border-box;
        }
        textarea { height: 100px; }
        input[type="checkbox"] { margin-right: 5px; }
        .btn { padding: 10px 20px; margin: 5px; cursor: pointer; border: none; }
        .btn-primary { background-color: #4CAF50; color: white; }
        .btn-secondary { background-color: #gray; color: white; text-decoration: none; display: inline-block; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .success { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
    </style>
</head>
<body>
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
</body>
</html>
    '''

    return render_template_string(template, setting=setting)


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
            _ = img.is_flying
            _ = img.is_kamikaze
            _ = img.min_damage
            _ = img.max_damage
            _ = img.min_defense
            _ = img.max_defense
            _ = img.setting_id
            _ = img.setting.name if img.setting else None
            _ = img.coin_cost
            _ = img.subscription_only
            _ = img.created_at

        db_session.expunge_all()

    template = '''
<!DOCTYPE html>
<html>
<head>
    <title>Управление изображениями юнитов</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; font-size: 12px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #4CAF50; color: white; }
        tr:hover { background-color: #f5f5f5; }
        .btn { padding: 6px 12px; text-decoration: none; margin: 2px; display: inline-block; font-size: 12px; }
        .btn-primary { background-color: #4CAF50; color: white; }
        .btn-view { background-color: #2196F3; color: white; }
        .btn-delete { background-color: #f44336; color: white; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .success { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
        .thumbnail { width: 50px; height: 50px; object-fit: cover; }
    </style>
</head>
<body>
    <h1>Управление изображениями юнитов</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <a href="{{ url_for('images_manager.unit_image_create') }}" class="btn btn-primary">Загрузить изображение</a>
    <a href="{{ url_for('images_manager.settings_list') }}" class="btn">Управление сеттингами</a>
    <a href="{{ url_for('admin_units_list') }}" class="btn">← Назад к админке</a>

    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Изображение</th>
                <th>Описание</th>
                <th>Сеттинг</th>
                <th>Летающий</th>
                <th>Камикадзе</th>
                <th>Урон</th>
                <th>Защита</th>
                <th>Стоимость</th>
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
                <td>{{ '✓' if img.is_flying else ('✗' if img.is_flying == False else '-') }}</td>
                <td>{{ '✓' if img.is_kamikaze else ('✗' if img.is_kamikaze == False else '-') }}</td>
                <td>{{ img.min_damage if img.min_damage else '-' }} - {{ img.max_damage if img.max_damage else '-' }}</td>
                <td>{{ img.min_defense if img.min_defense else '-' }} - {{ img.max_defense if img.max_defense else '-' }}</td>
                <td>{{ img.coin_cost }}</td>
                <td>{{ '✓' if img.subscription_only else '✗' }}</td>
                <td>
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
</body>
</html>
    '''

    return render_template_string(template, images=images)


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

            # Параметры применимости
            is_flying = request.form.get('is_flying')
            is_flying = None if is_flying == 'any' else (is_flying == 'true')

            is_kamikaze = request.form.get('is_kamikaze')
            is_kamikaze = None if is_kamikaze == 'any' else (is_kamikaze == 'true')

            min_damage = request.form.get('min_damage')
            min_damage = int(min_damage) if min_damage else None

            max_damage = request.form.get('max_damage')
            max_damage = int(max_damage) if max_damage else None

            min_defense = request.form.get('min_defense')
            min_defense = int(min_defense) if min_defense else None

            max_defense = request.form.get('max_defense')
            max_defense = int(max_defense) if max_defense else None

            coin_cost = Decimal(request.form.get('coin_cost', '0'))
            subscription_only = 'subscription_only' in request.form

            with db.get_session() as db_session:
                unit_image = UnitImage(
                    description=description,
                    is_flying=is_flying,
                    is_kamikaze=is_kamikaze,
                    min_damage=min_damage,
                    max_damage=max_damage,
                    min_defense=min_defense,
                    max_defense=max_defense,
                    image_data=image_data,
                    setting_id=setting_id,
                    coin_cost=coin_cost,
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
<html>
<head>
    <title>Загрузить изображение</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: bold; }
        input[type="text"], input[type="number"], textarea, select, input[type="file"] {
            width: 100%; max-width: 500px; padding: 8px; box-sizing: border-box;
        }
        textarea { height: 60px; }
        .btn { padding: 10px 20px; margin: 5px; cursor: pointer; border: none; }
        .btn-primary { background-color: #4CAF50; color: white; }
        .btn-secondary { background-color: #gray; color: white; text-decoration: none; display: inline-block; }
        .flash { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .error { background-color: #f8d7da; color: #721c24; }
        .section { border: 1px solid #ddd; padding: 15px; margin: 10px 0; background: #f9f9f9; }
        .section h3 { margin-top: 0; }
    </style>
</head>
<body>
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

        <div class="section">
            <h3>Параметры применимости изображения</h3>
            <p>Оставьте "Любой" если параметр не важен</p>

            <div class="form-group">
                <label for="is_flying">Летающий юнит:</label>
                <select id="is_flying" name="is_flying">
                    <option value="any">Любой</option>
                    <option value="true">Да</option>
                    <option value="false">Нет</option>
                </select>
            </div>

            <div class="form-group">
                <label for="is_kamikaze">Камикадзе:</label>
                <select id="is_kamikaze" name="is_kamikaze">
                    <option value="any">Любой</option>
                    <option value="true">Да</option>
                    <option value="false">Нет</option>
                </select>
            </div>

            <div class="form-group">
                <label for="min_damage">Минимальный урон (оставьте пустым для любого):</label>
                <input type="number" id="min_damage" name="min_damage" min="0">
            </div>

            <div class="form-group">
                <label for="max_damage">Максимальный урон (оставьте пустым для любого):</label>
                <input type="number" id="max_damage" name="max_damage" min="0">
            </div>

            <div class="form-group">
                <label for="min_defense">Минимальная защита (оставьте пустым для любой):</label>
                <input type="number" id="min_defense" name="min_defense" min="0">
            </div>

            <div class="form-group">
                <label for="max_defense">Максимальная защита (оставьте пустым для любой):</label>
                <input type="number" id="max_defense" name="max_defense" min="0">
            </div>
        </div>

        <div class="section">
            <h3>Стоимость и доступность</h3>

            <div class="form-group">
                <label for="coin_cost">Стоимость в монетах:</label>
                <input type="number" id="coin_cost" name="coin_cost" value="0" step="0.01" min="0">
            </div>

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
</body>
</html>
    '''

    return render_template_string(template, settings=settings)


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
