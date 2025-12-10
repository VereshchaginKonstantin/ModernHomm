#!/usr/bin/env python3
"""
Модуль управления армией для веб-интерфейса
"""

import os
import logging
from flask import Blueprint, render_template_string, session, redirect, url_for, flash
from functools import wraps

from db.models import GameUser, GameRace, UserRace, UserRaceUnit, Army, ArmyUnit
from db.repository import Database
from web_templates import HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE

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


@army_bp.route('/race')
@login_required
def user_race():
    """Настройка пользовательской расы"""
    username = session.get('username')

    template = '''
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Настройка расы</title>
''' + BASE_STYLE + '''
</head>
<body>
''' + HEADER_TEMPLATE + '''
    <div class="content">
        <h1>🏰 Настройка пользовательской расы</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="flash {{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="section">
            <h3>Выбор расы</h3>
            <p>Здесь вы сможете выбрать и настроить свою расу для игры.</p>
            <p><em>Функционал в разработке...</em></p>
        </div>
    </div>
    {{ footer_html|safe }}
</body>
</html>
    '''

    return render_template_string(template, active_page='user_race')


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
    {{ footer_html|safe }}
</body>
</html>
    '''

    return render_template_string(template, active_page='army_settings')
