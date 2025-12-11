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
from web.arena import arena_bp
from web.races import races_bp
from web.army import army_bp
from web.templates import get_web_version, get_bot_version, HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE
from web.app_templates import (
    IMAGES_TEMPLATE, COMPREHENSIVE_UNITS_TEMPLATE, UNITS_TEMPLATE,
    UNIT_FORM_TEMPLATE, LEADERBOARD_TEMPLATE, HELP_TEMPLATE,
    IMPORT_TEMPLATE, LOGIN_TEMPLATE
)

# Создать Flask приложение
app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'web/static/unit_images'
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
    return render_template_string(LOGIN_TEMPLATE)


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


def main():
    """Запуск веб-приложения"""
    # Получить порт из переменной окружения или использовать 5000 по умолчанию
    port = int(os.getenv('PORT', 5000))
    print(f"Запуск веб-интерфейса на http://0.0.0.0:{port}")
    print("Используйте Ctrl+C для остановки")
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()
