#!/usr/bin/env python3
"""
Модуль арены для веб-интерфейса
Позволяет просматривать записи боёв и играть в реальном времени через браузер
"""

import json
import os
import requests
import logging
from datetime import datetime
from decimal import Decimal
from flask import Blueprint, render_template_string, request, jsonify, session, redirect, url_for
from sqlalchemy import text, desc
from functools import wraps

from db.models import Base, GameUser, Unit, UserUnit, Game, GameStatus, BattleUnit, Field, GameLog, Obstacle
from db.repository import Database
from game_engine import GameEngine
from web_templates import HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE, get_web_version, get_bot_version
import hashlib


def get_static_version():
    """Получить версию для cache busting статических файлов"""
    web_ver = get_web_version()
    return hashlib.md5(web_ver.encode()).hexdigest()[:8]

logger = logging.getLogger(__name__)

# Blueprint для арены
arena_bp = Blueprint('arena', __name__, url_prefix='/arena')

# Получаем подключение к БД
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
db = Database(db_url)

# Загружаем конфигурацию для Telegram бота
def get_telegram_bot_token():
    """Получить токен Telegram бота из config.json"""
    try:
        config_path = 'config.json'
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config.get('telegram', {}).get('bot_token')
    except Exception as e:
        logger.error(f"Ошибка загрузки конфигурации: {e}")
        return None


def send_telegram_notification(chat_id: int, message: str, reply_markup: dict = None):
    """Отправить уведомление в Telegram"""
    bot_token = get_telegram_bot_token()
    if not bot_token:
        logger.warning("Telegram bot token not configured")
        return False

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }
        if reply_markup:
            payload['reply_markup'] = json.dumps(reply_markup)

        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            logger.info(f"Telegram notification sent to {chat_id}")
            return True
        else:
            logger.error(f"Failed to send Telegram notification: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Error sending Telegram notification: {e}")
        return False


def notify_opponent(game_id: int, player_id: int, message: str, action_type: str = 'move'):
    """Отправить уведомление противнику о действии"""
    with db.get_session() as session_db:
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return

        # Определяем противника
        opponent_id = game.player2_id if game.player1_id == player_id else game.player1_id
        opponent = session_db.query(GameUser).filter_by(id=opponent_id).first()

        if opponent and opponent.telegram_id:
            # Формируем кнопку для перехода к игре
            reply_markup = {
                'inline_keyboard': [[
                    {'text': '🎮 Текущая игра', 'callback_data': f'show_game:{game_id}'}
                ]]
            }

            # Отправляем уведомление
            emoji = '⚔️' if action_type == 'attack' else '📍'
            full_message = f"{emoji} Противник: {message}"
            send_telegram_notification(opponent.telegram_id, full_message, reply_markup)


def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def json_serial(obj):
    """JSON serializer для объектов, которые не сериализуются по умолчанию"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


# ==================== HTML Шаблоны ====================

ARENA_INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Арена - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <link rel="stylesheet" href="/static/arena/css/arena.css?v={{ static_version }}">
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>🏟️ Арена</h1>

        <div class="arena-modes">
            <div class="arena-mode-card">
                <h2>📜 Просмотр записей</h2>
                <p>Воспроизведение прошедших боёв с анимациями</p>
                <a href="{{ url_for('arena.replay_list') }}" class="btn btn-primary">Смотреть записи</a>
            </div>

            <div class="arena-mode-card">
                <h2>⚔️ Начать бой</h2>
                <p>Играть против других игроков в реальном времени</p>
                {% if has_active_game %}
                <a href="{{ url_for('arena.play') }}" class="btn btn-success">▶️ Продолжить активную игру</a>
                {% else %}
                <a href="{{ url_for('arena.play') }}" class="btn btn-primary">Играть</a>
                {% endif %}
            </div>
        </div>

        <div class="arena-stats">
            <h3>📊 Статистика</h3>
            <div class="stats-grid">
                <div class="stat-item">
                    <span class="stat-value">{{ total_games }}</span>
                    <span class="stat-label">Всего игр</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{{ completed_games }}</span>
                    <span class="stat-label">Завершённых</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{{ active_games }}</span>
                    <span class="stat-label">Активных</span>
                </div>
                <div class="stat-item">
                    <span class="stat-value">{{ total_players }}</span>
                    <span class="stat-label">Игроков</span>
                </div>
            </div>
        </div>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""

REPLAY_LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Записи боёв - Арена</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <link rel="stylesheet" href="/static/arena/css/arena.css?v={{ static_version }}">
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>📜 Записи боёв</h1>
        <a href="{{ url_for('arena.index') }}" class="btn btn-secondary">← Назад к арене</a>

        <div class="games-list">
            {% if games %}
                <table class="games-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Игрок 1</th>
                            <th>Игрок 2</th>
                            <th>Победитель</th>
                            <th>Поле</th>
                            <th>Дата</th>
                            <th>Действия</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for game in games %}
                        <tr>
                            <td>#{{ game.id }}</td>
                            <td>{{ game.player1_name }}</td>
                            <td>{{ game.player2_name }}</td>
                            <td>
                                {% if game.winner_name %}
                                    🏆 {{ game.winner_name }}
                                {% else %}
                                    -
                                {% endif %}
                            </td>
                            <td>{{ game.field_size }}</td>
                            <td>{{ game.created_at.strftime('%d.%m.%Y %H:%M') }}</td>
                            <td>
                                <a href="{{ url_for('arena.replay_view', game_id=game.id) }}" class="btn btn-view">▶️ Смотреть</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            {% else %}
                <p class="no-data">Нет завершённых игр для просмотра</p>
            {% endif %}
        </div>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""

REPLAY_VIEW_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Бой #{{ game.id }} - Арена</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <link rel="stylesheet" href="/static/arena/css/arena.css?v={{ static_version }}">
    <script src="https://cdn.jsdelivr.net/npm/phaser@3.60.0/dist/phaser.min.js"></script>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <div class="replay-header">
            <a href="{{ url_for('arena.replay_list') }}" class="btn btn-secondary">← К списку</a>
            <h1>⚔️ Бой #{{ game.id }}: {{ player1.name }} vs {{ player2.name }}</h1>
        </div>

        <div class="battle-container">
            <div class="battle-info">
                <div class="player-info player1">
                    <h3>{{ player1.name }}</h3>
                    <div class="player-units" id="player1-units"></div>
                </div>

                <div id="game-container"></div>

                <div class="player-info player2">
                    <h3>{{ player2.name }}</h3>
                    <div class="player-units" id="player2-units"></div>
                </div>
            </div>

            <div class="replay-controls">
                <button id="btn-prev" class="btn">⏮️ Пред.</button>
                <button id="btn-play" class="btn btn-primary">▶️ Играть</button>
                <button id="btn-next" class="btn">След. ⏭️</button>
                <select id="speed-select">
                    <option value="0.5">0.5x</option>
                    <option value="1" selected>1x</option>
                    <option value="2">2x</option>
                    <option value="4">4x</option>
                </select>
                <span id="event-counter">Событие: 0 / 0</span>
            </div>

            <div class="battle-log" id="battle-log">
                <h3>📋 Лог игры</h3>
                <div class="log-entries" id="log-entries"></div>
            </div>
        </div>
    </div>

    <script>
        // Данные игры
        const gameData = {{ game_data | safe }};
    </script>
    <script src="/static/arena/js/game.js?v={{ static_version }}"></script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""

PLAY_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Начать бой - Арена</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <link rel="stylesheet" href="/static/arena/css/arena.css?v={{ static_version }}">
    <script src="https://cdn.jsdelivr.net/npm/phaser@3.60.0/dist/phaser.min.js"></script>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>⚔️ Начать бой</h1>
        <a href="{{ url_for('arena.index') }}" class="btn btn-secondary">← Назад к арене</a>

        {% if waiting_game %}
        <div id="game-setup" class="game-setup">
            <h2>⏳ Ожидающая игра #{{ waiting_game.id }}</h2>
            <p style="color: #666; text-align: center; margin-bottom: 20px;">
                Игра ожидает принятия противником.<br>
                Дождитесь принятия или отмените игру.
            </p>
            <div class="setup-form">
                <button onclick="window.location.href='{{ url_for('arena.index') }}'" class="btn btn-secondary">← Назад к арене</button>
            </div>
        </div>
        {% elif error_message %}
        <div id="game-setup" class="game-setup">
            <h2>❌ Ошибка</h2>
            <p style="color: #c0392b; text-align: center; margin-bottom: 20px;">
                {{ error_message }}
            </p>
            <div class="setup-form">
                <button onclick="window.location.href='{{ url_for('arena.index') }}'" class="btn btn-secondary">← Назад к арене</button>
            </div>
        </div>
        {% else %}
        <div id="game-setup" class="game-setup">
            <h2>Выберите противника для боя</h2>

            <div class="setup-form">
                <div class="player-info-card" style="background: #ecf0f1; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="margin-top: 0;">👤 Вы: {{ current_player.name }}</h3>
                    <p style="margin: 5px 0;">💰 Баланс: {{ current_player.balance }}</p>
                    <p style="margin: 5px 0;">⚔️ Стоимость армии: {{ "%.0f"|format(current_player.army_value) }}</p>
                    <p style="margin: 5px 0;">🏆 Победы: {{ current_player.wins }} | 💔 Поражения: {{ current_player.losses }}</p>
                </div>

                <!-- Скрытое поле с ID и именем текущего игрока -->
                <input type="hidden" id="player1-id" value="{{ current_player.id }}" data-name="{{ current_player.name }}">

                <div class="form-group">
                    <label>Противник (игроки с близкой стоимостью армии ±50%):</label>
                    <select id="player2-select" class="form-control">
                        {% for opponent in opponents %}
                        <option value="{{ opponent.id }}" data-name="{{ opponent.name }}">
                            {{ opponent.name }} (⚔️{{ "%.0f"|format(opponent.army_value) }}, 🏆{{ opponent.wins }}/{{ opponent.losses }}, {{ "%.0f"|format(opponent.win_rate) }}% побед)
                        </option>
                        {% endfor %}
                    </select>
                </div>

                <div class="form-group">
                    <label>Размер поля:</label>
                    <select id="field-select" class="form-control">
                        <option value="5x5">5x5</option>
                        <option value="7x7">7x7</option>
                        <option value="10x10">10x10</option>
                    </select>
                </div>

                <button id="btn-start-game" class="btn btn-primary">⚔️ Начать бой</button>
            </div>
        </div>
        {% endif %}

        <div id="game-container" style="display: none;">
            <div class="battle-container">
                <div class="battle-info">
                    <div class="player-info player1">
                        <h3 id="p1-name">Игрок 1</h3>
                        <!-- Портреты юнитов для игрока 1 -->
                        <div class="unit-portrait active-portrait" id="p1-active-portrait" style="display:none;">
                            <img id="p1-active-image" src="" alt="Активный юнит">
                            <div class="unit-portrait-info">
                                <span id="p1-active-name" class="unit-portrait-name"></span>
                                <span id="p1-active-stats" class="unit-portrait-stats"></span>
                            </div>
                        </div>
                        <div class="unit-portrait target-portrait" id="p1-target-portrait" style="display:none;">
                            <img id="p1-target-image" src="" alt="Цель атаки">
                            <div class="unit-portrait-info">
                                <span id="p1-target-name" class="unit-portrait-name"></span>
                                <span id="p1-target-stats" class="unit-portrait-stats"></span>
                            </div>
                        </div>
                        <div class="player-units" id="player1-units"></div>
                        <div id="p1-turn" class="turn-indicator" style="display:none">Ваш ход!</div>
                    </div>

                    <div id="phaser-game"></div>

                    <div class="player-info player2">
                        <h3 id="p2-name">Игрок 2</h3>
                        <!-- Портреты юнитов для игрока 2 -->
                        <div class="unit-portrait active-portrait" id="p2-active-portrait" style="display:none;">
                            <img id="p2-active-image" src="" alt="Активный юнит">
                            <div class="unit-portrait-info">
                                <span id="p2-active-name" class="unit-portrait-name"></span>
                                <span id="p2-active-stats" class="unit-portrait-stats"></span>
                            </div>
                        </div>
                        <div class="unit-portrait target-portrait" id="p2-target-portrait" style="display:none;">
                            <img id="p2-target-image" src="" alt="Цель атаки">
                            <div class="unit-portrait-info">
                                <span id="p2-target-name" class="unit-portrait-name"></span>
                                <span id="p2-target-stats" class="unit-portrait-stats"></span>
                            </div>
                        </div>
                        <div class="player-units" id="player2-units"></div>
                        <div id="p2-turn" class="turn-indicator" style="display:none">Ход противника</div>
                    </div>
                </div>

                <div class="action-panel" id="action-panel" style="display: none;">
                    <h3>Выберите действие</h3>
                    <div id="selected-unit-info"></div>
                    <div class="action-buttons-main">
                        <button id="btn-move" class="btn btn-primary btn-action">🚶 Двигаться</button>
                        <button id="btn-attack" class="btn btn-danger btn-action">⚔️ Атаковать</button>
                        <button id="btn-skip" class="btn btn-secondary btn-action">⏭️ Пропустить</button>
                    </div>
                    <div class="action-buttons-escape">
                        <button id="btn-cancel" class="btn btn-escape">🏃 Сбежать с поля боя</button>
                    </div>
                </div>

                <!-- UI подсказки (не записываются в лог) -->
                <div class="game-hints" id="game-hints">
                    <div class="hint-content" id="hint-content"></div>
                </div>

                <div class="battle-log" id="battle-log">
                    <h3>📋 Лог игры</h3>
                    <div class="log-entries" id="log-entries"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const apiBase = '/arena/api';
        const currentUser = '{{ session.username }}';
    </script>
    <script src="/static/arena/js/play.js?v={{ static_version }}"></script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""

PLAY_GAME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Бой #{{ game_id }} - Арена</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <link rel="stylesheet" href="/static/arena/css/arena.css?v={{ static_version }}">
    <script src="https://cdn.jsdelivr.net/npm/phaser@3.60.0/dist/phaser.min.js"></script>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <div class="replay-header">
            <a href="{{ url_for('arena.index') }}" class="btn btn-secondary">← К арене</a>
            <h1>⚔️ Активный бой #{{ game_id }}</h1>
        </div>

        <div id="game-container">
            <div class="battle-container">
                <div class="battle-info">
                    <div class="player-info player1">
                        <h3 id="p1-name">{{ player1_name }}</h3>
                        <!-- Портреты юнитов для игрока 1 -->
                        <div class="unit-portrait active-portrait" id="p1-active-portrait" style="display:none;">
                            <img id="p1-active-image" src="" alt="Активный юнит">
                            <div class="unit-portrait-info">
                                <span id="p1-active-name" class="unit-portrait-name"></span>
                                <span id="p1-active-stats" class="unit-portrait-stats"></span>
                            </div>
                        </div>
                        <div class="unit-portrait target-portrait" id="p1-target-portrait" style="display:none;">
                            <img id="p1-target-image" src="" alt="Цель атаки">
                            <div class="unit-portrait-info">
                                <span id="p1-target-name" class="unit-portrait-name"></span>
                                <span id="p1-target-stats" class="unit-portrait-stats"></span>
                            </div>
                        </div>
                        <div class="player-units" id="player1-units"></div>
                        <div id="p1-turn" class="turn-indicator" style="display:none">Ваш ход!</div>
                    </div>

                    <div id="phaser-game"></div>

                    <div class="player-info player2">
                        <h3 id="p2-name">{{ player2_name }}</h3>
                        <!-- Портреты юнитов для игрока 2 -->
                        <div class="unit-portrait active-portrait" id="p2-active-portrait" style="display:none;">
                            <img id="p2-active-image" src="" alt="Активный юнит">
                            <div class="unit-portrait-info">
                                <span id="p2-active-name" class="unit-portrait-name"></span>
                                <span id="p2-active-stats" class="unit-portrait-stats"></span>
                            </div>
                        </div>
                        <div class="unit-portrait target-portrait" id="p2-target-portrait" style="display:none;">
                            <img id="p2-target-image" src="" alt="Цель атаки">
                            <div class="unit-portrait-info">
                                <span id="p2-target-name" class="unit-portrait-name"></span>
                                <span id="p2-target-stats" class="unit-portrait-stats"></span>
                            </div>
                        </div>
                        <div class="player-units" id="player2-units"></div>
                        <div id="p2-turn" class="turn-indicator" style="display:none">Ход противника</div>
                    </div>
                </div>

                <div class="action-panel" id="action-panel" style="display: none;">
                    <h3>Выберите действие</h3>
                    <div id="selected-unit-info"></div>
                    <div class="action-buttons-main">
                        <button id="btn-move" class="btn btn-primary btn-action">🚶 Двигаться</button>
                        <button id="btn-attack" class="btn btn-danger btn-action">⚔️ Атаковать</button>
                        <button id="btn-skip" class="btn btn-secondary btn-action">⏭️ Пропустить</button>
                    </div>
                    <div class="action-buttons-escape">
                        <button id="btn-cancel" class="btn btn-escape">🏃 Сбежать с поля боя</button>
                    </div>
                </div>

                <!-- UI подсказки (не записываются в лог) -->
                <div class="game-hints" id="game-hints">
                    <div class="hint-content" id="hint-content"></div>
                </div>

                <div class="battle-log" id="battle-log">
                    <h3>📋 Лог игры</h3>
                    <div class="log-entries" id="log-entries"></div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const apiBase = '/arena/api';
        const currentUser = '{{ session.username }}';
        // Автоматически загружаем игру
        const autoLoadGameId = {{ game_id }};
        const autoLoadPlayerId = {{ player_id }};
    </script>
    <script src="/static/arena/js/play.js?v={{ static_version }}"></script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


# ==================== Маршруты страниц ====================

@arena_bp.route('/')
@login_required
def index():
    """Главная страница арены"""
    with db.get_session() as session_db:
        total_games = session_db.query(Game).count()
        completed_games = session_db.query(Game).filter(Game.status == GameStatus.COMPLETED).count()
        active_games = session_db.query(Game).filter(Game.status == GameStatus.IN_PROGRESS).count()
        total_players = session_db.query(GameUser).count()
        # Проверяем есть ли активная игра для кнопки
        has_active_game = active_games > 0

    return render_template_string(
        ARENA_INDEX_TEMPLATE,
        active_page='arena',
        total_games=total_games,
        completed_games=completed_games,
        active_games=active_games,
        has_active_game=has_active_game,
        web_version=get_web_version(),
        bot_version=get_bot_version(),
        static_version=get_static_version(),
        total_players=total_players
    )


@arena_bp.route('/replay')
@login_required
def replay_list():
    """Список завершённых игр для просмотра"""
    games_data = []

    with db.get_session() as session_db:
        games = session_db.query(Game).filter(
            Game.status == GameStatus.COMPLETED
        ).order_by(desc(Game.completed_at)).limit(50).all()

        for game in games:
            player1 = session_db.query(GameUser).filter_by(id=game.player1_id).first()
            player2 = session_db.query(GameUser).filter_by(id=game.player2_id).first()
            winner = session_db.query(GameUser).filter_by(id=game.winner_id).first() if game.winner_id else None
            field = session_db.query(Field).filter_by(id=game.field_id).first()

            games_data.append({
                'id': game.id,
                'player1_name': (player1.username or player1.name) if player1 else 'Unknown',
                'player2_name': (player2.username or player2.name) if player2 else 'Unknown',
                'winner_name': (winner.username or winner.name) if winner else None,
                'field_size': field.name if field else 'Unknown',
                'created_at': game.created_at,
                'completed_at': game.completed_at
            })

    return render_template_string(
        REPLAY_LIST_TEMPLATE,
        active_page='arena',
        games=games_data,
        web_version=get_web_version(),
        bot_version=get_bot_version(),
        static_version=get_static_version()
    )


@arena_bp.route('/replay/<int:game_id>')
@login_required
def replay_view(game_id):
    """Просмотр конкретного боя"""
    game_data = get_game_full_data(game_id)

    if not game_data:
        return "Игра не найдена", 404

    return render_template_string(
        REPLAY_VIEW_TEMPLATE,
        active_page='arena',
        game=game_data['game'],
        player1=game_data['player1'],
        player2=game_data['player2'],
        game_data=json.dumps(game_data, default=json_serial),
        web_version=get_web_version(),
        bot_version=get_bot_version(),
        static_version=get_static_version()
    )


@arena_bp.route('/play')
@login_required
def play():
    """Страница для игры - открывает активную игру или показывает форму создания"""
    current_username = session.get('username')

    with db.get_session() as session_db:
        # Проверяем есть ли активная игра (IN_PROGRESS)
        active_game = session_db.query(Game).filter(
            Game.status == GameStatus.IN_PROGRESS
        ).first()

        if active_game:
            # Есть активная игра - редиректим на неё
            # player_id будет определён автоматически на основе текущего пользователя
            return redirect(url_for('arena.play_game', game_id=active_game.id))

        # Нет активной игры - проверяем ожидающие
        waiting_game = session_db.query(Game).filter(
            Game.status == GameStatus.WAITING
        ).first()

    # Получаем текущего игрока и список противников с близкой стоимостью армии
    current_player, opponents = db.get_available_opponents_by_username(current_username, limit=10, variance=0.5)

    if not current_player:
        # Пользователь не найден в игровой БД
        return render_template_string(
            PLAY_TEMPLATE,
            active_page='arena',
            current_player=None,
            opponents=[],
            waiting_game=waiting_game,
            web_version=get_web_version(),
            bot_version=get_bot_version(),
            static_version=get_static_version(),
            error_message="Ваш игровой профиль не найден. Зарегистрируйтесь в Telegram боте."
        )

    return render_template_string(
        PLAY_TEMPLATE,
        active_page='arena',
        current_player=current_player,
        opponents=opponents,
        waiting_game=waiting_game,
        web_version=get_web_version(),
        bot_version=get_bot_version(),
        static_version=get_static_version()
    )


@arena_bp.route('/play/<int:game_id>')
@login_required
def play_game(game_id, player_id=None):
    """Страница активной игры"""
    if player_id is None:
        player_id = request.args.get('player_id', type=int)

    # Получаем текущего пользователя
    current_username = session.get('username')

    with db.get_session() as session_db:
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return redirect(url_for('arena.play'))

        if game.status != GameStatus.IN_PROGRESS:
            # Игра не активна
            if game.status == GameStatus.COMPLETED:
                return redirect(url_for('arena.replay_view', game_id=game_id))
            return redirect(url_for('arena.play'))

        player1 = session_db.query(GameUser).filter_by(id=game.player1_id).first()
        player2 = session_db.query(GameUser).filter_by(id=game.player2_id).first()

        # Извлекаем имена внутри сессии (предпочитаем username)
        player1_name = (player1.username or player1.name) if player1 else 'Игрок 1'
        player2_name = (player2.username or player2.name) if player2 else 'Игрок 2'

        # Определяем player_id на основе текущего пользователя
        if not player_id:
            # Ищем текущего пользователя среди игроков
            current_game_user = session_db.query(GameUser).filter_by(username=current_username).first()
            if current_game_user:
                if current_game_user.id == game.player1_id:
                    player_id = game.player1_id
                elif current_game_user.id == game.player2_id:
                    player_id = game.player2_id
                else:
                    # Пользователь не участник игры - берём player1
                    player_id = game.player1_id
            else:
                player_id = game.player1_id

    return render_template_string(
        PLAY_GAME_TEMPLATE,
        active_page='arena',
        game_id=game_id,
        player_id=player_id,
        player1_name=player1_name,
        player2_name=player2_name,
        web_version=get_web_version(),
        bot_version=get_bot_version(),
        static_version=get_static_version()
    )


# ==================== API Endpoints ====================

@arena_bp.route('/api/players')
@login_required
def api_players():
    """Получить список игроков"""
    with db.get_session() as session_db:
        players = session_db.query(GameUser).order_by(GameUser.name).all()
        result = []
        for p in players:
            # Получаем юнитов игрока
            user_units = session_db.query(UserUnit).filter_by(game_user_id=p.id).all()
            units = []
            for uu in user_units:
                unit = session_db.query(Unit).filter_by(id=uu.unit_type_id).first()
                if unit and uu.count > 0:
                    units.append({
                        'unit_id': unit.id,
                        'name': unit.name,
                        'icon': unit.icon,
                        'count': uu.count
                    })

            result.append({
                'id': p.id,
                'telegram_id': p.telegram_id,
                'name': p.name,
                'balance': float(p.balance),
                'wins': p.wins,
                'losses': p.losses,
                'units': units
            })

    return jsonify(result)


@arena_bp.route('/api/games')
@login_required
def api_games():
    """Получить список игр"""
    status = request.args.get('status', 'completed')
    limit = int(request.args.get('limit', 50))

    with db.get_session() as session_db:
        query = session_db.query(Game)

        if status == 'completed':
            query = query.filter(Game.status == GameStatus.COMPLETED)
        elif status == 'active':
            query = query.filter(Game.status == GameStatus.IN_PROGRESS)
        elif status == 'waiting':
            query = query.filter(Game.status == GameStatus.WAITING)

        games = query.order_by(desc(Game.created_at)).limit(limit).all()
        result = []

        for game in games:
            player1 = session_db.query(GameUser).filter_by(id=game.player1_id).first()
            player2 = session_db.query(GameUser).filter_by(id=game.player2_id).first()
            field = session_db.query(Field).filter_by(id=game.field_id).first()

            result.append({
                'id': game.id,
                'player1': {'id': player1.id, 'name': player1.username or player1.name} if player1 else None,
                'player2': {'id': player2.id, 'name': player2.username or player2.name} if player2 else None,
                'winner_id': game.winner_id,
                'field_size': field.name if field else None,
                'status': game.status.value,
                'created_at': game.created_at,
                'completed_at': game.completed_at
            })

    return jsonify(result)


@arena_bp.route('/api/games/<int:game_id>')
@login_required
def api_game_detail(game_id):
    """Получить полные данные игры для воспроизведения"""
    game_data = get_game_full_data(game_id)

    if not game_data:
        return jsonify({'error': 'Game not found'}), 404

    return jsonify(game_data)


@arena_bp.route('/api/games/create', methods=['POST'])
@login_required
def api_create_game():
    """Создать новую игру"""
    data = request.json
    player1_id = data.get('player1_id')
    player2_name = data.get('player2_name')
    field_size = data.get('field_size', '5x5')

    with db.get_session() as session_db:
        engine = GameEngine(session_db)

        game, message = engine.create_game(player1_id, player2_name, field_size)

        if game:
            return jsonify({
                'success': True,
                'game_id': game.id,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400


@arena_bp.route('/api/games/<int:game_id>/accept', methods=['POST'])
@login_required
def api_accept_game(game_id):
    """Принять игру"""
    data = request.json
    player_id = data.get('player_id')

    with db.get_session() as session_db:
        engine = GameEngine(session_db)

        success, message = engine.accept_game(game_id, player_id)

        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400


@arena_bp.route('/api/games/<int:game_id>/state')
@login_required
def api_game_state(game_id):
    """Получить текущее состояние игры"""
    with db.get_session() as session_db:
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        # Получаем юнитов на поле
        battle_units = session_db.query(BattleUnit).filter_by(game_id=game_id).all()
        units_data = []

        for bu in battle_units:
            user_unit = session_db.query(UserUnit).filter_by(id=bu.user_unit_id).first()
            unit_type = session_db.query(Unit).filter_by(id=user_unit.unit_type_id).first() if user_unit else None

            units_data.append({
                'id': bu.id,
                'player_id': bu.player_id,
                'x': bu.position_x,
                'y': bu.position_y,
                'count': bu.total_count,
                'hp': bu.remaining_hp,
                'morale': bu.morale,
                'fatigue': bu.fatigue,
                'has_moved': bu.has_moved,
                'deferred': bu.deferred,
                'unit_type': {
                    'id': unit_type.id,
                    'name': unit_type.name,
                    'icon': unit_type.icon,
                    'damage': unit_type.damage,
                    'defense': unit_type.defense,
                    'health': unit_type.health,
                    'speed': unit_type.speed,
                    'range': unit_type.range,
                    'image_path': unit_type.image_path
                } if unit_type else None
            })

        # Препятствия
        obstacles = session_db.query(Obstacle).filter_by(game_id=game_id).all()
        obstacles_data = [{'x': o.position_x, 'y': o.position_y} for o in obstacles]

        # Поле
        field = session_db.query(Field).filter_by(id=game.field_id).first()

        # Логи игры
        logs = session_db.query(GameLog).filter_by(game_id=game_id).order_by(GameLog.created_at).all()
        logs_data = [{
            'event_type': log.event_type,
            'message': log.message,
            'created_at': log.created_at.isoformat()
        } for log in logs]

        # Имена игроков
        player1 = session_db.query(GameUser).filter_by(id=game.player1_id).first()
        player2 = session_db.query(GameUser).filter_by(id=game.player2_id).first()
        player1_name = (player1.username or player1.name) if player1 else 'Игрок 1'
        player2_name = (player2.username or player2.name) if player2 else 'Игрок 2'

        return jsonify({
            'game_id': game.id,
            'status': game.status.value,
            'player1_id': game.player1_id,
            'player2_id': game.player2_id,
            'player1_name': player1_name,
            'player2_name': player2_name,
            'current_player_id': game.current_player_id,
            'winner_id': game.winner_id,
            'field': {
                'width': field.width,
                'height': field.height
            } if field else None,
            'units': units_data,
            'obstacles': obstacles_data,
            'logs': logs_data
        })


@arena_bp.route('/api/games/<int:game_id>/units/<int:unit_id>/actions')
@login_required
def api_unit_actions(game_id, unit_id):
    """Получить доступные действия для юнита"""
    with db.get_session() as session_db:
        engine = GameEngine(session_db)

        # Получаем юнит
        battle_unit = session_db.query(BattleUnit).filter_by(id=unit_id, game_id=game_id).first()
        if not battle_unit:
            return jsonify({'error': 'Unit not found'}), 404

        # Получаем доступные клетки для перемещения
        move_cells = engine.get_available_movement_cells(game_id, unit_id)

        # Получаем доступные цели для атаки
        game = session_db.query(Game).filter_by(id=game_id).first()
        attack_targets = []

        if game:
            enemy_units = session_db.query(BattleUnit).filter(
                BattleUnit.game_id == game_id,
                BattleUnit.player_id != battle_unit.player_id,
                BattleUnit.total_count > 0
            ).all()

            user_unit = session_db.query(UserUnit).filter_by(id=battle_unit.user_unit_id).first()
            unit_type = session_db.query(Unit).filter_by(id=user_unit.unit_type_id).first() if user_unit else None

            if unit_type:
                for enemy in enemy_units:
                    # Проверяем дальность атаки
                    distance = abs(battle_unit.position_x - enemy.position_x) + abs(battle_unit.position_y - enemy.position_y)
                    if distance <= unit_type.range:
                        # Проверяем линию обзора
                        if engine._has_line_of_sight(
                            battle_unit.position_x, battle_unit.position_y,
                            enemy.position_x, enemy.position_y,
                            game
                        ):
                            attack_targets.append({
                                'id': enemy.id,
                                'x': enemy.position_x,
                                'y': enemy.position_y
                            })

        # Преобразуем кортежи в объекты для JavaScript
        move_cells_json = [{'x': x, 'y': y} for x, y in move_cells]

        return jsonify({
            'can_move': move_cells_json,
            'can_attack': attack_targets
        })


@arena_bp.route('/api/games/<int:game_id>/move', methods=['POST'])
@login_required
def api_make_move(game_id):
    """Сделать ход"""
    data = request.json
    unit_id = data.get('unit_id')
    action = data.get('action')  # 'move', 'attack', 'skip'
    target_x = data.get('target_x')
    target_y = data.get('target_y')
    target_unit_id = data.get('target_unit_id')

    # Получаем текущего пользователя
    current_username = session.get('username')
    if not current_username:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    with db.get_session() as session_db:
        engine = GameEngine(session_db)

        # Получаем game_user текущего пользователя
        current_game_user = session_db.query(GameUser).filter_by(username=current_username).first()
        if not current_game_user:
            return jsonify({'success': False, 'message': 'User not found in game database'}), 404

        # Получаем игру и проверяем, чей сейчас ход
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return jsonify({'success': False, 'message': 'Game not found'}), 404

        # Проверяем, что текущий пользователь участвует в игре
        if current_game_user.id not in [game.player1_id, game.player2_id]:
            return jsonify({'success': False, 'message': 'You are not a player in this game'}), 403

        # Проверяем, что сейчас ход текущего пользователя
        if game.current_player_id != current_game_user.id:
            return jsonify({'success': False, 'message': 'Not your turn'}), 403

        # Получаем юнит и проверяем владельца
        battle_unit = session_db.query(BattleUnit).filter_by(id=unit_id, game_id=game_id).first()
        if not battle_unit:
            return jsonify({'success': False, 'message': 'Unit not found'}), 404

        # Проверяем, что юнит принадлежит текущему игроку
        if battle_unit.player_id != current_game_user.id:
            return jsonify({'success': False, 'message': 'This unit does not belong to you'}), 403

        player_id = battle_unit.player_id

        if action == 'move':
            success, message, turn_switched = engine.move_unit(
                game_id, player_id, unit_id, target_x, target_y
            )
            action_type = 'move'
        elif action == 'attack':
            success, message, turn_switched = engine.attack(
                game_id, player_id, unit_id, target_unit_id
            )
            action_type = 'attack'
        elif action == 'skip':
            success, message, turn_switched = engine.skip_unit_turn(
                game_id, player_id, unit_id
            )
            action_type = 'skip'
        elif action == 'defer':
            success, message = engine.defer_unit(
                game_id, player_id, unit_id
            )
            turn_switched = False  # defer не переключает ход
            action_type = 'defer'
        else:
            return jsonify({'success': False, 'message': 'Invalid action'}), 400

        # Получаем обновлённое состояние
        game = session_db.query(Game).filter_by(id=game_id).first()

        # Отправляем уведомление противнику в Telegram
        if success:
            try:
                notify_opponent(game_id, player_id, message, action_type)

                # Если ход сменился - дополнительное уведомление о смене хода
                if turn_switched and game:
                    opponent_id = game.player2_id if game.player1_id == player_id else game.player1_id
                    opponent = session_db.query(GameUser).filter_by(id=opponent_id).first()
                    if opponent and opponent.telegram_id:
                        reply_markup = {
                            'inline_keyboard': [[
                                {'text': '🎮 Ваш ход!', 'callback_data': f'show_game:{game_id}'}
                            ]]
                        }
                        send_telegram_notification(
                            opponent.telegram_id,
                            '🔔 <b>Теперь ваш ход!</b>\nОткройте игру чтобы сделать ход.',
                            reply_markup
                        )
            except Exception as e:
                logger.error(f"Error sending Telegram notification: {e}")

        return jsonify({
            'success': success,
            'message': message,
            'turn_switched': turn_switched,
            'game_status': game.status.value if game else None,
            'winner_id': game.winner_id if game else None,
            'current_player_id': game.current_player_id if game else None
        })


# ==================== Вспомогательные функции ====================

def get_game_full_data(game_id):
    """Получить полные данные игры для воспроизведения"""
    with db.get_session() as session_db:
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return None

        player1 = session_db.query(GameUser).filter_by(id=game.player1_id).first()
        player2 = session_db.query(GameUser).filter_by(id=game.player2_id).first()
        field = session_db.query(Field).filter_by(id=game.field_id).first()

        # Логи игры
        logs = session_db.query(GameLog).filter_by(game_id=game_id).order_by(GameLog.created_at).all()
        logs_data = []
        for log in logs:
            logs_data.append({
                'event_type': log.event_type,
                'message': log.message,
                'created_at': log.created_at
            })

        # Юниты на поле (финальное состояние)
        battle_units = session_db.query(BattleUnit).filter_by(game_id=game_id).all()
        units_data = []

        for bu in battle_units:
            user_unit = session_db.query(UserUnit).filter_by(id=bu.user_unit_id).first()
            unit_type = session_db.query(Unit).filter_by(id=user_unit.unit_type_id).first() if user_unit else None

            units_data.append({
                'id': bu.id,
                'player_id': bu.player_id,
                'x': bu.position_x,
                'y': bu.position_y,
                'count': bu.total_count,
                'hp': bu.remaining_hp,
                'morale': bu.morale,
                'fatigue': bu.fatigue,
                'unit_type': {
                    'id': unit_type.id,
                    'name': unit_type.name,
                    'icon': unit_type.icon,
                    'damage': unit_type.damage,
                    'defense': unit_type.defense,
                    'health': unit_type.health,
                    'speed': unit_type.speed,
                    'range': unit_type.range,
                    'image_path': unit_type.image_path
                } if unit_type else None
            })

        # Препятствия
        obstacles = session_db.query(Obstacle).filter_by(game_id=game_id).all()
        obstacles_data = [{'x': o.position_x, 'y': o.position_y} for o in obstacles]

        return {
            'game': {
                'id': game.id,
                'status': game.status.value,
                'winner_id': game.winner_id,
                'created_at': game.created_at,
                'started_at': game.started_at,
                'completed_at': game.completed_at
            },
            'player1': {
                'id': player1.id,
                'name': player1.username or player1.name,
                'telegram_id': player1.telegram_id
            } if player1 else None,
            'player2': {
                'id': player2.id,
                'name': player2.username or player2.name,
                'telegram_id': player2.telegram_id
            } if player2 else None,
            'field': {
                'width': field.width,
                'height': field.height,
                'name': field.name
            } if field else None,
            'units': units_data,
            'obstacles': obstacles_data,
            'logs': logs_data
        }
