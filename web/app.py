#!/usr/bin/env python3
"""
Веб-интерфейс Flask для управления юнитами
"""

import os
import json
import zipfile
import shutil
import hashlib
import logging
from io import BytesIO
from functools import wraps
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for, flash, send_file, session, jsonify
from werkzeug.utils import secure_filename
from db import Database
from db.models import GameUser
from decimal import Decimal
from web.arena import arena_bp
from web.races import races_bp
from web.army import army_bp
from web.fields import fields_bp
from web.templates import get_web_version, get_bot_version, HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE
from web.app_templates import (
    LEADERBOARD_TEMPLATE, HELP_TEMPLATE, LOGIN_TEMPLATE, JOBS_TEMPLATE
)

# Логгер для джоб
scheduler_logger = logging.getLogger('jobs')

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
# Регистрация Blueprint для редактора полей
app.register_blueprint(fields_bp)


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

def calculate_unit_price(damage: int, defense: int, health: int, unit_range: int, speed: int, luck: float, crit_chance: float, dodge_chance: float, is_kamikaze: int = 0, is_flying: int = 0, counterattack_chance: float = 0, regeneration_health: int = 0, poison_damage: int = 0, poison_turns: int = 0) -> Decimal:
    """
    Автоматический расчет стоимости юнита по формуле:
    (Урон + Защита + Здоровье + 2*Дальность*(Урон + Защита) + Скорость*(Урон + Защита) +
     2*Летающий*(Урон + Защита) + 2*Удача*Урон + 2*Крит*Урон + 10*Уклонение*(Урон + Защита) + 10*Контратака*Урон +
     10*Регенерация + 10*ЯдУрон*ЯдХодов)
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
        regeneration_health: Здоровье, восстанавливаемое за ход
        poison_damage: Урон яда за ход
        poison_turns: Количество ходов действия яда

    Returns:
        Decimal: Рассчитанная стоимость
    """
    # Для камикадзе: урон делится на 5, уклонение делится на 50
    damage_value = damage / 5 if is_kamikaze else damage
    dodge_value = dodge_chance / 50 if is_kamikaze else dodge_chance

    # Бонус для летающих юнитов (могут двигаться через препятствия)
    flying_bonus = 2 * (damage_value + defense) if is_flying else 0

    # Бонус за регенерацию и отравление
    regeneration_bonus = 10 * regeneration_health
    poison_bonus = 10 * poison_damage * poison_turns

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
        10 * counterattack_chance * damage_value +
        regeneration_bonus +
        poison_bonus
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
    """Главная страница - перенаправление на арену"""
    return redirect(url_for('arena.index'))


@app.route('/admin/images')
@login_required
def admin_images():
    """УСТАРЕВШИЙ - Картинки теперь управляются через скины юнитов в расах"""
    flash('Раздел картинок удален. Используйте раздел "Расы" для управления скинами юнитов.', 'info')
    return redirect(url_for('arena.index'))


@app.route('/upload/<int:unit_id>', methods=['POST'])
@login_required
def upload_image(unit_id):
    """УСТАРЕВШИЙ - Загрузка картинок перенесена в скины юнитов"""
    flash('Загрузка картинок перенесена в раздел "Расы" -> "Скины юнитов".', 'info')
    return redirect(url_for('arena.index'))


@app.route('/delete/<int:unit_id>', methods=['POST'])
@login_required
def delete_image(unit_id):
    """УСТАРЕВШИЙ - Удаление картинок перенесено в скины юнитов"""
    flash('Управление картинками перенесено в раздел "Расы" -> "Скины юнитов".', 'info')
    return redirect(url_for('arena.index'))


@app.route('/admin/units')
@login_required
def admin_units_list():
    """Страница управления юнитами - перенаправление на расы"""
    flash('Управление юнитами перенесено в раздел "Расы". Юниты теперь привязаны к расам.', 'info')
    return redirect(url_for('races.races_list'))


@app.route('/admin/units/create', methods=['GET', 'POST'])
@login_required
def admin_create_unit():
    """УСТАРЕВШИЙ - Создание юнитов перенесено в раздел рас"""
    flash('Создание юнитов перенесено в раздел "Расы". Юниты теперь привязаны к расам.', 'info')
    return redirect(url_for('races.races_list'))


@app.route('/admin/units/edit/<int:unit_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_unit(unit_id):
    """УСТАРЕВШИЙ - Редактирование юнитов перенесено в раздел рас"""
    flash('Редактирование юнитов перенесено в раздел "Расы". Юниты теперь привязаны к расам.', 'info')
    return redirect(url_for('races.races_list'))


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
            _ = player.username
            _ = player.wins
            _ = player.losses
            _ = player.balance

            # Рассчитываем винрейт
            total_games = player.wins + player.losses
            win_rate = (player.wins / total_games * 100) if total_games > 0 else 0

            # Используем glory как показатель силы игрока
            glory = player.glory if hasattr(player, 'glory') else 0

            players_data.append({
                'rank': offset + len(players_data) + 1,
                'name': player.username,
                'wins': player.wins,
                'losses': player.losses,
                'win_rate': win_rate,
                'balance': float(player.balance),
                'army_value': float(glory)  # Используем glory вместо стоимости армии
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
    # Проверяем является ли пользователь админом
    is_admin = False
    if 'username' in session:
        try:
            from db.repository import Database
            db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
            db_instance = Database(db_url)
            with db_instance.get_session() as db_session:
                user = db_session.query(GameUser).filter_by(username=session['username']).first()
                if user and user.id in [1, 4]:  # Админы
                    is_admin = True
        except Exception:
            pass
    return render_template_string(HELP_TEMPLATE, active_page='help', is_admin=is_admin)


@app.route('/admin/logs')
@login_required
def admin_logs():
    """API для получения логов клиентов (только для админов)"""
    from db.models import ClientLog
    # Проверяем права админа
    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
    db_instance = Database(db_url)
    with db_instance.get_session() as db_session:
        user = db_session.query(GameUser).filter_by(username=session['username']).first()
        if not user or user.id not in [1, 4]:
            return jsonify({'error': 'Admin access required'}), 403

        level = request.args.get('level')
        limit = min(int(request.args.get('limit', 100)), 1000)
        offset = int(request.args.get('offset', 0))

        query = db_session.query(ClientLog)
        if level:
            query = query.filter(ClientLog.level == level)

        total = query.count()
        logs = query.order_by(ClientLog.created_at.desc()).offset(offset).limit(limit).all()

        return jsonify({
            'total': total,
            'logs': [{
                'id': log.id,
                'session_id': log.session_id,
                'player_id': log.player_id,
                'level': log.level,
                'message': log.message,
                'context': json.loads(log.context) if log.context else None,
                'user_agent': log.user_agent,
                'created_at': log.created_at.isoformat()
            } for log in logs]
        })


@app.route('/admin/logs/clear', methods=['POST'])
@login_required
def admin_clear_logs():
    """API для очистки старых логов (только для админов)"""
    from db.models import ClientLog
    from datetime import timedelta

    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
    db_instance = Database(db_url)
    with db_instance.get_session() as db_session:
        user = db_session.query(GameUser).filter_by(username=session['username']).first()
        if not user or user.id not in [1, 4]:
            return jsonify({'error': 'Admin access required'}), 403

        data = request.get_json() or {}
        days = int(data.get('days', 7))
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = db_session.query(ClientLog).filter(ClientLog.created_at < cutoff).delete()
        db_session.commit()

        return jsonify({'success': True, 'deleted': deleted})


@app.route('/admin/debug/toggle', methods=['POST'])
@login_required
def admin_toggle_debug():
    """API для переключения debug mode (только для админов)"""
    from db.models import Config

    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
    db_instance = Database(db_url)
    with db_instance.get_session() as db_session:
        user = db_session.query(GameUser).filter_by(username=session['username']).first()
        if not user or user.id not in [1, 4]:
            return jsonify({'error': 'Admin access required'}), 403

        config = db_session.query(Config).filter_by(key='debug_mode').first()
        if not config:
            config = Config(key='debug_mode', value='true', description='Debug mode for client logging')
            db_session.add(config)

        new_value = 'false' if config.value.lower() == 'true' else 'true'
        config.value = new_value
        db_session.commit()

        return jsonify({'success': True, 'debug_mode': new_value == 'true'})


@app.route('/admin/debug/auth_toggle', methods=['POST'])
@login_required
def admin_toggle_debug_auth():
    """API для переключения debug auth (аутентификация через URL)"""
    from db.models import Config

    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
    db_instance = Database(db_url)
    with db_instance.get_session() as db_session:
        user = db_session.query(GameUser).filter_by(username=session['username']).first()
        if not user or user.id not in [1, 4]:
            return jsonify({'error': 'Admin access required'}), 403

        config = db_session.query(Config).filter_by(key='debug_auth').first()
        if not config:
            config = Config(key='debug_auth', value='true', description='Allow authentication via URL player_id parameter')
            db_session.add(config)

        new_value = 'false' if config.value.lower() == 'true' else 'true'
        config.value = new_value
        db_session.commit()

        return jsonify({'success': True, 'debug_auth': new_value == 'true'})


@app.route('/export')
@login_required
def export_units():
    """УСТАРЕВШИЙ - Экспорт перенесен в раздел рас"""
    flash('Экспорт юнитов перенесен в раздел "Расы". Используйте экспорт рас.', 'info')
    return redirect(url_for('races.races_list'))


@app.route('/import', methods=['GET', 'POST'])
@login_required
def import_page():
    """УСТАРЕВШИЙ - Импорт перенесен в раздел рас"""
    flash('Импорт юнитов перенесен в раздел "Расы". Используйте импорт рас.', 'info')
    return redirect(url_for('races.races_list'))


@app.route('/admin/jobs')
@login_required
def admin_jobs():
    """Страница логов выполнения джоб (только для админов)"""
    from db.models import JobLog

    # Проверяем права админа
    if 'username' not in session:
        return redirect(url_for('login'))

    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
    db_instance = Database(db_url)

    with db_instance.get_session() as db_session:
        user = db_session.query(GameUser).filter_by(username=session['username']).first()
        if not user or user.id not in [1, 4]:
            flash('Доступ запрещен. Требуются права администратора.', 'error')
            return redirect(url_for('index'))

        # Параметры пагинации и фильтрации
        page = request.args.get('page', 1, type=int)
        per_page = 50
        selected_job = request.args.get('job_name', '')
        selected_status = request.args.get('status', '')

        # Базовый запрос
        query = db_session.query(JobLog)

        # Фильтры
        if selected_job:
            query = query.filter(JobLog.job_name == selected_job)
        if selected_status:
            query = query.filter(JobLog.status == selected_status)

        # Статистика
        total_query = db_session.query(JobLog)
        stats = {
            'total': total_query.count(),
            'success': total_query.filter(JobLog.status == 'success').count(),
            'failed': total_query.filter(JobLog.status == 'failed').count(),
            'running': total_query.filter(JobLog.status == 'running').count(),
        }

        # Уникальные названия джоб для фильтра
        job_names = [row[0] for row in db_session.query(JobLog.job_name).distinct().all()]

        # Общее количество записей с фильтрами
        total_count = query.count()
        total_pages = (total_count + per_page - 1) // per_page

        # Пагинация
        offset = (page - 1) * per_page
        jobs = query.order_by(JobLog.started_at.desc()).offset(offset).limit(per_page).all()

        return render_template_string(
            JOBS_TEMPLATE,
            jobs=jobs,
            stats=stats,
            job_names=job_names,
            selected_job=selected_job,
            selected_status=selected_status,
            page=page,
            total_pages=total_pages,
            active_page='admin_jobs'
        )


@app.route('/admin/jobs/run', methods=['POST'])
@login_required
def admin_run_job():
    """API для ручного запуска джобы (только для админов)"""
    from db.models import JobLog

    if 'username' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
    db_instance = Database(db_url)

    with db_instance.get_session() as db_session:
        user = db_session.query(GameUser).filter_by(username=session['username']).first()
        if not user or user.id not in [1, 4]:
            return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json() or {}
    job_name = data.get('job_name')

    if not job_name:
        return jsonify({'error': 'job_name is required'}), 400

    # Отправляем задачу в Celery
    try:
        import redis
        redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        r.ping()  # Проверяем доступность Redis

        from jobs.celery_app import celery_app
        if job_name == 'hourly_recruit_accumulate':
            from jobs.tasks import hourly_recruit_accumulate
            task = hourly_recruit_accumulate.delay()
            return jsonify({'success': True, 'task_id': task.id, 'message': 'Job queued'})
        elif job_name == 'daily_reset_limits':
            from jobs.tasks import daily_reset_limits
            task = daily_reset_limits.delay()
            return jsonify({'success': True, 'task_id': task.id, 'message': 'Job queued'})
        else:
            return jsonify({'error': f'Unknown job: {job_name}'}), 400
    except Exception as e:
        # Если Celery/Redis недоступны, запускаем синхронно
        scheduler_logger.warning(f"Celery unavailable, running job synchronously: {e}")
        try:
            if job_name == 'hourly_recruit_accumulate':
                from jobs.hourly_recruit_accumulate import accumulate_hourly_units
                updated = accumulate_hourly_units(db_instance)
                return jsonify({'success': True, 'task_id': 'sync', 'message': f'Job completed synchronously, updated {updated} records'})
            else:
                return jsonify({'error': f'Unknown job for sync execution: {job_name}'}), 400
        except Exception as sync_error:
            return jsonify({'error': str(sync_error)}), 500


def main():
    """Запуск веб-приложения"""
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)

    # Получить порт из переменной окружения или использовать 5000 по умолчанию
    port = int(os.getenv('PORT', 5000))
    print(f"Запуск веб-интерфейса на http://0.0.0.0:{port}")
    print("Используйте Ctrl+C для остановки")
    print("Примечание: Фоновые задачи выполняются в отдельном контейнере jobs (Celery)")
    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == '__main__':
    main()
