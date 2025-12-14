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
from flask import Blueprint, render_template_string, request, jsonify, session, redirect, url_for, make_response
from sqlalchemy import text, desc
from functools import wraps

from db.models import Base, GameUser, Game, GameStatus, BattleUnit, Field, GameLog, Obstacle, Army, ArmyUnit, UserRace, RaceUnit
from db.repository import Database
from core.game_engine import GameEngine
from web.templates import HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE, get_web_version, get_bot_version
import hashlib


def get_static_version():
    """Получить версию для cache busting статических файлов"""
    web_ver = get_web_version()
    return hashlib.md5(web_ver.encode()).hexdigest()[:8]

logger = logging.getLogger(__name__)

# Blueprint для арены
arena_bp = Blueprint('arena', __name__, url_prefix='/arena')


# CORS декоратор для Unity WebGL запросов
@arena_bp.after_request
def after_request(response):
    """Добавляет CORS заголовки для запросов от Unity WebGL"""
    origin = request.headers.get('Origin', '')
    # Разрешаем запросы от localhost и modernhomm.ru
    if origin or request.headers.get('X-Requested-With') == 'UnityWebRequest':
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


# Получаем подключение к БД
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
db = Database(db_url)


class GameState:
    """Класс для представления состояния игры для Godot API"""

    def __init__(self, game, units, obstacles, logs, session):
        self.game = game
        self.units = units
        self.obstacles = obstacles
        self.logs = logs
        self.session = session

    @classmethod
    def from_game(cls, game: Game, session) -> 'GameState':
        """Создать GameState из объекта Game"""
        units = []
        for bu in game.battle_units:
            if bu.total_count > 0:
                race_unit = bu.army_unit.race_unit if bu.army_unit else None
                if race_unit:
                    units.append({
                        'id': bu.id,
                        'player_id': bu.player_id,
                        'x': bu.position_x,
                        'y': bu.position_y,
                        'count': bu.total_count,
                        'has_moved': 1 if bu.has_moved else 0,
                        'unit_type': {
                            'id': race_unit.id,
                            'name': race_unit.name,
                            'icon': race_unit.unit_level.icon if race_unit.unit_level else '?',
                            'attack': race_unit.attack,
                            'defense': race_unit.defense,
                            'hp': race_unit.health,
                            'speed': race_unit.speed,
                            'attack_range': race_unit.attack_range
                        }
                    })

        obstacles = []
        for obs in session.query(Obstacle).filter_by(game_id=game.id).all():
            obstacles.append({
                'x': obs.position_x,
                'y': obs.position_y
            })

        logs = []
        for log in session.query(GameLog).filter_by(game_id=game.id).order_by(GameLog.created_at).all():
            logs.append({
                'event_type': log.event_type,
                'message': log.message,
                'timestamp': log.created_at.isoformat() if log.created_at else None
            })

        return cls(game, units, obstacles, logs, session)

    def to_dict(self) -> dict:
        """Преобразовать в словарь для JSON"""
        game = self.game
        return {
            'game_id': game.id,
            'status': game.status.value,
            'field': {
                'name': game.field.name if game.field else '5x5',
                'width': game.field.width if game.field else 5,
                'height': game.field.height if game.field else 5
            },
            'player1_id': game.player1_id,
            'player1_name': game.player1.username if game.player1 else 'Игрок 1',
            'player2_id': game.player2_id,
            'player2_name': game.player2.username if game.player2 else 'Игрок 2',
            'current_player_id': game.current_player_id,
            'is_game_over': game.status == GameStatus.COMPLETED,
            'winner_id': game.winner_id,
            'units': self.units,
            'obstacles': self.obstacles,
            'logs': self.logs
        }


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


def notify_current_player(game_id: int, player_id: int, message: str, action_type: str = 'move'):
    """Отправить уведомление текущему игроку (веб-игроку) о его собственном ходе"""
    with db.get_session() as session_db:
        player = session_db.query(GameUser).filter_by(id=player_id).first()

        if player and player.telegram_id:
            # Формируем кнопку для перехода к игре
            reply_markup = {
                'inline_keyboard': [[
                    {'text': '🎮 Текущая игра', 'callback_data': f'show_game:{game_id}'}
                ]]
            }

            # Отправляем уведомление
            emoji = '⚔️' if action_type == 'attack' else '📍'
            full_message = f"{emoji} Вы: {message}"
            send_telegram_notification(player.telegram_id, full_message, reply_markup)


def notify_game_completion(game_id: int, winner_id: int, message: str):
    """Отправить уведомление о завершении игры обоим игрокам"""
    with db.get_session() as session_db:
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return

        winner = session_db.query(GameUser).filter_by(id=winner_id).first()
        loser_id = game.player1_id if winner_id == game.player2_id else game.player2_id
        loser = session_db.query(GameUser).filter_by(id=loser_id).first()

        if not winner or not loser:
            return

        # Формируем сообщение о завершении
        result_message = f"{message}\n\n"
        result_message += "🏆 " + "=" * 20 + "\n"
        result_message += "   ИГРА ЗАВЕРШЕНА!\n"
        result_message += "=" * 20 + "\n\n"
        result_message += f"👑 <b>Победитель:</b> {winner.username}\n"
        result_message += f"💔 <b>Проигравший:</b> {loser.username}\n"

        # Отправляем уведомление победителю
        if winner.telegram_id:
            send_telegram_notification(winner.telegram_id, result_message)

        # Отправляем уведомление проигравшему
        if loser.telegram_id:
            send_telegram_notification(loser.telegram_id, result_message)


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

            <div class="arena-mode-card">
                <h2>🎮 Godot Арена</h2>
                <p>Новая арена на движке Godot (WebGL)</p>
                <a href="/godot-arena/?player_id={{ current_player_id if current_player_id else '' }}" class="btn btn-primary" target="_blank">Открыть Godot</a>
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
                    <h3 style="margin-top: 0;">👤 Вы: {{ current_player.username }}</h3>
                    <p style="margin: 5px 0;">💰 Баланс: {{ current_player.balance }}</p>
                    <p style="margin: 5px 0;">⚔️ Стоимость армии: {{ "%.0f"|format(current_player.army_value) }}</p>
                    <p style="margin: 5px 0;">🏆 Победы: {{ current_player.wins }} | 💔 Поражения: {{ current_player.losses }}</p>
                </div>

                <!-- Скрытое поле с ID и именем текущего игрока -->
                <input type="hidden" id="player1-id" value="{{ current_player.id }}" data-name="{{ current_player.username }}">

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

                        <div class="action-panel" id="action-panel" style="display: none;">
                            <div id="selected-unit-info" class="selected-unit-info"></div>
                            <div class="action-buttons-main">
                                <button id="btn-move" class="btn btn-primary btn-action">🚶 Двигаться</button>
                                <button id="btn-attack" class="btn btn-danger btn-action">⚔️ Атаковать</button>
                                <button id="btn-skip" class="btn btn-secondary btn-action">⏭️ Пропустить</button>
                            </div>
                            <div class="action-buttons-escape">
                                <button id="btn-cancel" class="btn btn-escape">🏃 Сбежать с поля боя</button>
                            </div>
                        </div>
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

                        <div class="action-panel" id="action-panel" style="display: none;">
                            <div id="selected-unit-info" class="selected-unit-info"></div>
                            <div class="action-buttons-main">
                                <button id="btn-move" class="btn btn-primary btn-action">🚶 Двигаться</button>
                                <button id="btn-attack" class="btn btn-danger btn-action">⚔️ Атаковать</button>
                                <button id="btn-skip" class="btn btn-secondary btn-action">⏭️ Пропустить</button>
                            </div>
                            <div class="action-buttons-escape">
                                <button id="btn-cancel" class="btn btn-escape">🏃 Сбежать с поля боя</button>
                            </div>
                        </div>
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
    current_username = session.get('username')
    current_player_id = None

    with db.get_session() as session_db:
        total_games = session_db.query(Game).count()
        completed_games = session_db.query(Game).filter(Game.status == GameStatus.COMPLETED).count()
        active_games = session_db.query(Game).filter(Game.status == GameStatus.IN_PROGRESS).count()
        total_players = session_db.query(GameUser).count()
        # Проверяем есть ли активная игра для кнопки
        has_active_game = active_games > 0

        # Получаем ID текущего игрока для ссылки на Godot арену
        if current_username:
            current_player = session_db.query(GameUser).filter_by(username=current_username).first()
            if current_player:
                current_player_id = current_player.id

    return render_template_string(
        ARENA_INDEX_TEMPLATE,
        active_page='arena',
        total_games=total_games,
        completed_games=completed_games,
        active_games=active_games,
        has_active_game=has_active_game,
        current_player_id=current_player_id,
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
                'player1_name': (player1.username) if player1 else 'Unknown',
                'player2_name': (player2.username) if player2 else 'Unknown',
                'winner_name': (winner.username) if winner else None,
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

    waiting_game_data = None
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

        # Извлекаем данные внутри сессии чтобы избежать DetachedInstanceError
        if waiting_game:
            waiting_game_data = {'id': waiting_game.id}

    # Получаем текущего игрока и список противников с близкой стоимостью армии
    current_player, opponents = db.get_available_opponents_by_username(current_username, limit=10, variance=0.5)

    if not current_player:
        # Пользователь не найден в игровой БД
        return render_template_string(
            PLAY_TEMPLATE,
            active_page='arena',
            current_player=None,
            opponents=[],
            waiting_game=waiting_game_data,
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
        waiting_game=waiting_game_data,
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
        player1_name = (player1.username) if player1 else 'Игрок 1'
        player2_name = (player2.username) if player2 else 'Игрок 2'

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
        players = session_db.query(GameUser).order_by(GameUser.username).all()
        result = []
        for p in players:
            # Получаем армии игрока через user_races
            armies = []
            user_races = session_db.query(UserRace).filter_by(user_id=p.id).all()
            for user_race in user_races:
                for army in user_race.armies:
                    army_units = []
                    for au in army.army_units:
                        if au.race_unit and au.count > 0:
                            army_units.append({
                                'unit_id': au.race_unit.id,
                                'name': au.race_unit.name,
                                'icon': au.race_unit.unit_level.icon if au.race_unit.unit_level else '?',
                                'count': au.count
                            })
                    armies.append({
                        'army_id': army.id,
                        'army_name': army.name,
                        'units': army_units
                    })

            result.append({
                'id': p.id,
                'telegram_id': p.telegram_id,
                'name': p.username,
                'balance': float(p.balance),
                'wins': p.wins,
                'losses': p.losses,
                'armies': armies
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
                'player1': {'id': player1.id, 'name': player1.username} if player1 else None,
                'player2': {'id': player2.id, 'name': player2.username} if player2 else None,
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
    """Создать новую игру с выбранной армией"""
    data = request.json
    player1_id = data.get('player1_id')
    player2_name = data.get('player2_name')
    army_id = data.get('army_id')  # ID армии для боя
    field_size = data.get('field_size', '7x7')

    if not army_id:
        return jsonify({'success': False, 'message': 'Выберите армию для боя'}), 400

    with db.get_session() as session_db:
        engine = GameEngine(session_db)

        game, message = engine.create_game(player1_id, player2_name, army_id, field_size)

        if game:
            # Получаем информацию об армии для уведомления
            player1 = session_db.query(GameUser).filter_by(id=player1_id).first()
            player2 = session_db.query(GameUser).filter_by(id=game.player2_id).first()
            army = session_db.query(Army).filter_by(id=army_id).first()
            army_type_text = "⭐ Рейтинговый бой" if army and army.army_type == "rated" else "💰 Наемный бой"

            if player2 and player2.telegram_id:
                challenger_name = (player1.username) if player1 else 'Неизвестный'
                army_name = army.name if army else 'Неизвестная армия'
                reply_markup = {
                    'inline_keyboard': [
                        [
                            {'text': '✅ Принять', 'callback_data': f'accept_game:{game.id}'},
                            {'text': '❌ Отклонить', 'callback_data': f'decline_game:{game.id}'}
                        ],
                        [
                            {'text': '🎮 Открыть арену', 'url': 'https://modernhomm.ru/arena/play'}
                        ]
                    ]
                }
                send_telegram_notification(
                    player2.telegram_id,
                    f"⚔️ <b>Вызов на бой!</b>\n\n"
                    f"<b>{challenger_name}</b> вызывает вас на бой!\n"
                    f"Армия: {army_name}\n"
                    f"Тип: {army_type_text}\n"
                    f"Размер поля: {field_size}\n"
                    f"Игра #{game.id}",
                    reply_markup
                )

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
    """Принять игру с выбранной армией"""
    data = request.json
    player_id = data.get('player_id')
    army_id = data.get('army_id')  # ID армии для боя

    if not army_id:
        return jsonify({'success': False, 'message': 'Выберите армию для боя'}), 400

    with db.get_session() as session_db:
        engine = GameEngine(session_db)

        success, message = engine.accept_game(game_id, player_id, army_id)

        if success:
            # Отправляем уведомление создателю игры о принятии
            game = session_db.query(Game).filter_by(id=game_id).first()
            if game:
                player1 = session_db.query(GameUser).filter_by(id=game.player1_id).first()
                player2 = session_db.query(GameUser).filter_by(id=game.player2_id).first()
                army = session_db.query(Army).filter_by(id=army_id).first()
                if player1 and player1.telegram_id:
                    opponent_name = (player2.username) if player2 else 'Противник'
                    army_name = army.name if army else 'Армия'
                    reply_markup = {
                        'inline_keyboard': [[
                            {'text': '🎮 К игре', 'callback_data': f'show_game:{game_id}'}
                        ]]
                    }
                    send_telegram_notification(
                        player1.telegram_id,
                        f"✅ <b>{opponent_name}</b> принял ваш вызов!\n"
                        f"Армия противника: {army_name}\n\n"
                        f"Игра #{game_id} началась!",
                        reply_markup
                    )

            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 400


@arena_bp.route('/api/games/pending')
@login_required
def api_pending_games():
    """Получить ожидающие вызовы для текущего пользователя"""
    current_username = session.get('username')

    with db.get_session() as session_db:
        # Находим текущего пользователя
        current_user = session_db.query(GameUser).filter_by(username=current_username).first()
        if not current_user:
            return jsonify({'challenges': []})

        # Ищем игры в статусе WAITING, где текущий пользователь - player2
        waiting_games = session_db.query(Game).filter(
            Game.status == GameStatus.WAITING,
            Game.player2_id == current_user.id
        ).all()

        challenges = []
        for game in waiting_games:
            challenger = session_db.query(GameUser).filter_by(id=game.player1_id).first()
            field = session_db.query(Field).filter_by(id=game.field_id).first()

            challenges.append({
                'game_id': game.id,
                'challenger_id': game.player1_id,
                'challenger_name': (challenger.username) if challenger else 'Неизвестный',
                'field_size': field.name if field else 'Unknown',
                'created_at': game.created_at.isoformat() if game.created_at else None
            })

        return jsonify({'challenges': challenges})


@arena_bp.route('/api/games/<int:game_id>/cancel', methods=['POST'])
@login_required
def api_cancel_game(game_id):
    """Отменить вызов (создатель игры)"""
    current_username = session.get('username')

    with db.get_session() as session_db:
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return jsonify({'success': False, 'message': 'Игра не найдена'}), 404

        if game.status != GameStatus.WAITING:
            return jsonify({'success': False, 'message': 'Можно отменить только ожидающую игру'}), 400

        # Проверяем что текущий пользователь - создатель
        current_user = session_db.query(GameUser).filter_by(username=current_username).first()
        if not current_user or current_user.id != game.player1_id:
            return jsonify({'success': False, 'message': 'Только создатель может отменить вызов'}), 403

        # Уведомляем противника об отмене
        player2 = session_db.query(GameUser).filter_by(id=game.player2_id).first()
        if player2 and player2.telegram_id:
            challenger_name = (current_user.username)
            send_telegram_notification(
                player2.telegram_id,
                f"❌ <b>{challenger_name}</b> отменил вызов на бой.\n\nИгра #{game_id} отменена."
            )

        # Удаляем игру
        session_db.delete(game)
        session_db.commit()

        return jsonify({'success': True, 'message': 'Вызов отменён'})


@arena_bp.route('/api/games/<int:game_id>/decline', methods=['POST'])
@login_required
def api_decline_game(game_id):
    """Отклонить вызов (противник)"""
    current_username = session.get('username')

    with db.get_session() as session_db:
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return jsonify({'success': False, 'message': 'Игра не найдена'}), 404

        if game.status != GameStatus.WAITING:
            return jsonify({'success': False, 'message': 'Можно отклонить только ожидающую игру'}), 400

        # Проверяем что текущий пользователь - противник
        current_user = session_db.query(GameUser).filter_by(username=current_username).first()
        if not current_user or current_user.id != game.player2_id:
            return jsonify({'success': False, 'message': 'Только приглашённый игрок может отклонить вызов'}), 403

        # Уведомляем создателя об отклонении
        player1 = session_db.query(GameUser).filter_by(id=game.player1_id).first()
        if player1 and player1.telegram_id:
            opponent_name = (current_user.username)
            send_telegram_notification(
                player1.telegram_id,
                f"❌ <b>{opponent_name}</b> отклонил ваш вызов на бой.\n\nИгра #{game_id} отменена."
            )

        # Удаляем игру
        session_db.delete(game)
        session_db.commit()

        return jsonify({'success': True, 'message': 'Вызов отклонён'})


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
            # Используем army_unit -> race_unit вместо user_unit -> unit
            army_unit = bu.army_unit
            race_unit = army_unit.race_unit if army_unit else None

            # Получаем скин юнита если есть
            skin = race_unit.skins[0] if race_unit and race_unit.skins else None
            image_path = skin.image_path if skin else None

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
                    'id': race_unit.id,
                    'name': race_unit.name,
                    'icon': race_unit.unit_level.icon if race_unit.unit_level else '?',
                    'damage': race_unit.attack,
                    'defense': race_unit.defense,
                    'health': race_unit.health,
                    'speed': race_unit.speed,
                    'range': race_unit.attack_range,
                    'image_path': image_path
                } if race_unit else None
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
            'created_at': log.created_at.isoformat(),
            'game_state': log.game_state
        } for log in logs]

        # Имена игроков
        player1 = session_db.query(GameUser).filter_by(id=game.player1_id).first()
        player2 = session_db.query(GameUser).filter_by(id=game.player2_id).first()
        player1_name = (player1.username) if player1 else 'Игрок 1'
        player2_name = (player2.username) if player2 else 'Игрок 2'

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

            # Используем army_unit -> race_unit
            race_unit = battle_unit.army_unit.race_unit if battle_unit.army_unit else None

            if race_unit:
                for enemy in enemy_units:
                    # Проверяем дальность атаки
                    distance = abs(battle_unit.position_x - enemy.position_x) + abs(battle_unit.position_y - enemy.position_y)
                    if distance <= race_unit.attack_range:
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

        # Отправляем уведомления в Telegram
        if success:
            try:
                # Уведомление текущему игроку (веб-игроку) о его собственном ходе
                notify_current_player(game_id, player_id, message, action_type)

                # Уведомление противнику
                notify_opponent(game_id, player_id, message, action_type)

                # Проверяем, завершилась ли игра
                if game and game.status == GameStatus.COMPLETED and game.winner_id:
                    # Игра завершена - отправляем уведомления обоим игрокам
                    notify_game_completion(game_id, game.winner_id, message)
                elif turn_switched and game:
                    # Если ход сменился - дополнительное уведомление о смене хода
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
                'created_at': log.created_at,
                'game_state': log.game_state
            })

        # Юниты на поле (финальное состояние)
        battle_units = session_db.query(BattleUnit).filter_by(game_id=game_id).all()
        units_data = []

        for bu in battle_units:
            # Используем army_unit -> race_unit
            army_unit = bu.army_unit
            race_unit = army_unit.race_unit if army_unit else None

            # Получаем скин юнита если есть
            skin = race_unit.skins[0] if race_unit and race_unit.skins else None
            image_path = skin.image_path if skin else None

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
                    'id': race_unit.id,
                    'name': race_unit.name,
                    'icon': race_unit.unit_level.icon if race_unit.unit_level else '?',
                    'damage': race_unit.attack,
                    'defense': race_unit.defense,
                    'health': race_unit.health,
                    'speed': race_unit.speed,
                    'range': race_unit.attack_range,
                    'image_path': image_path
                } if race_unit else None
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
                'name': player1.username,
                'telegram_id': player1.telegram_id
            } if player1 else None,
            'player2': {
                'id': player2.id,
                'name': player2.username,
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


# ==================== Public API Endpoints for Godot ====================
# Эти эндпоинты не требуют авторизации для использования из Godot WebGL


def _calculate_army_cost(session_db, army):
    """Вычисление стоимости армии"""
    total_value = 0.0
    for au in army.army_units:
        if au.count <= 0 or not au.race_unit:
            continue
        race_unit = au.race_unit
        # Базовая мощь юнита
        unit_power = (
            race_unit.attack +
            race_unit.defense +
            (race_unit.min_damage + race_unit.max_damage) / 2 +
            race_unit.health / 10 +
            race_unit.speed +
            race_unit.initiative
        )
        # Множитель престижа
        prestige_mult = race_unit.unit_level.prestige_max if race_unit.unit_level else 100
        total_value += unit_power * prestige_mult * au.count / 100
    return total_value


@arena_bp.route('/api/public/players')
def api_public_players():
    """Публичный эндпоинт - получить список игроков для Godot"""
    with db.get_session() as session_db:
        players = session_db.query(GameUser).order_by(GameUser.username).all()
        result = []
        for p in players:
            # Получаем армии игрока через user_races
            armies = []
            max_army_cost = 0.0
            all_units = []  # Для совместимости с Godot
            user_races = session_db.query(UserRace).filter_by(user_id=p.id).all()
            for user_race in user_races:
                for army in user_race.armies:
                    army_units = []
                    army_cost = _calculate_army_cost(session_db, army)
                    if army_cost > max_army_cost:
                        max_army_cost = army_cost
                    for au in army.army_units:
                        if au.race_unit and au.count > 0:
                            unit_data = {
                                'unit_id': au.race_unit.id,
                                'name': au.race_unit.name,
                                'icon': au.race_unit.unit_level.icon if au.race_unit.unit_level else '?',
                                'count': au.count
                            }
                            army_units.append(unit_data)
                            all_units.append(unit_data)
                    armies.append({
                        'army_id': army.id,
                        'army_name': army.name,
                        'army_cost': army_cost,
                        'units': army_units
                    })

            result.append({
                'id': p.id,
                'telegram_id': p.telegram_id,
                'name': p.username,
                'balance': float(p.balance),
                'wins': p.wins,
                'losses': p.losses,
                'glory': p.glory,
                'armies': armies,
                'army_cost': max_army_cost,  # Для совместимости с Godot
                'units': all_units  # Для совместимости с Godot
            })

    # Возвращаем в формате {"players": [...]} для совместимости с Godot
    return jsonify({"players": result})


@arena_bp.route('/api/public/me')
def api_public_me():
    """Публичный эндпоинт - получить информацию о текущем игроке по player_id из параметров"""
    player_id = request.args.get('player_id', type=int)
    if not player_id:
        return jsonify({"current_player": {}})

    with db.get_session() as session_db:
        player = session_db.query(GameUser).filter_by(id=player_id).first()
        if not player:
            return jsonify({"current_player": {}})

        # Получаем армии игрока через user_races
        armies = []
        max_army_cost = 0.0
        user_races = session_db.query(UserRace).filter_by(user_id=player.id).all()
        for user_race in user_races:
            for army in user_race.armies:
                army_units = []
                army_cost = _calculate_army_cost(session_db, army)
                if army_cost > max_army_cost:
                    max_army_cost = army_cost
                for au in army.army_units:
                    if au.race_unit and au.count > 0:
                        army_units.append({
                            'unit_id': au.race_unit.id,
                            'name': au.race_unit.name,
                            'icon': au.race_unit.unit_level.icon if au.race_unit.unit_level else '?',
                            'count': au.count
                        })
                armies.append({
                    'army_id': army.id,
                    'army_name': army.name,
                    'army_cost': army_cost,
                    'units': army_units
                })

        return jsonify({
            "current_player": {
                'id': player.id,
                'telegram_id': player.telegram_id,
                'name': player.username,
                'balance': float(player.balance),
                'wins': player.wins,
                'losses': player.losses,
                'glory': player.glory,
                'armies': armies,
                'army_cost': max_army_cost
            }
        })


@arena_bp.route('/api/public/games/pending')
def api_public_pending_games():
    """Публичный эндпоинт - получить ожидающие игры для игрока"""
    player_id = request.args.get('player_id', type=int)
    if not player_id:
        return jsonify({"pending_games": [], "active_games": [], "history": []})

    with db.get_session() as session_db:
        player = session_db.query(GameUser).filter_by(id=player_id).first()
        if not player:
            return jsonify({"pending_games": [], "active_games": [], "history": []})

        # Ожидающие игры (где игрок - player2 и статус waiting)
        pending = session_db.query(Game).filter(
            Game.player2_id == player_id,
            Game.status == GameStatus.WAITING
        ).all()

        # Активные игры
        active = session_db.query(Game).filter(
            (Game.player1_id == player_id) | (Game.player2_id == player_id),
            Game.status == GameStatus.IN_PROGRESS
        ).all()

        # История (завершённые игры)
        history = session_db.query(Game).filter(
            (Game.player1_id == player_id) | (Game.player2_id == player_id),
            Game.status == GameStatus.COMPLETED
        ).order_by(Game.completed_at.desc()).limit(10).all()

        def game_to_dict(game, is_pending=False):
            p1 = session_db.query(GameUser).filter_by(id=game.player1_id).first()
            p2 = session_db.query(GameUser).filter_by(id=game.player2_id).first() if game.player2_id else None

            result = {
                'game_id': game.id,
                'status': game.status.value if hasattr(game.status, 'value') else str(game.status),
                'player1_id': game.player1_id,
                'player1_name': p1.username if p1 else 'Unknown',
                'player2_id': game.player2_id,
                'player2_name': p2.username if p2 else 'Unknown',
                'field_size': f"{game.field.width}x{game.field.height}" if game.field else "5x5",
                'created_at': game.created_at.isoformat() if game.created_at else None,
                'is_my_turn': game.current_player_id == player_id
            }

            # Для ожидающих игр - добавляем информацию об армиях
            if is_pending:
                challenger_cost = 0
                if game.player1_army_id:
                    army = session_db.query(Army).filter_by(id=game.player1_army_id).first()
                    if army:
                        challenger_cost = _calculate_army_cost(session_db, army)
                        result['challenger_army'] = {
                            'army_id': army.id,
                            'army_name': army.name,
                            'army_cost': challenger_cost
                        }
                # Получаем подходящие армии игрока (всегда показываем список)
                player_armies = []
                user_races = session_db.query(UserRace).filter_by(user_id=player_id).all()
                for user_race in user_races:
                    for player_army in user_race.armies:
                        player_army_cost = _calculate_army_cost(session_db, player_army)
                        # Показываем армии в диапазоне ±50% от армии вызывающего (или все если нет армии)
                        is_matching = abs(player_army_cost - challenger_cost) <= challenger_cost * 0.5 if challenger_cost > 0 else True
                        player_armies.append({
                            'army_id': player_army.id,
                            'army_name': player_army.name,
                            'army_cost': player_army_cost,
                            'is_matching': is_matching
                        })
                result['player_armies'] = player_armies

            if game.winner_id:
                winner = session_db.query(GameUser).filter_by(id=game.winner_id).first()
                result['winner_id'] = game.winner_id
                result['winner_name'] = winner.username if winner else 'Unknown'

            return result

        return jsonify({
            "pending_games": [game_to_dict(g, is_pending=True) for g in pending],
            "active_games": [game_to_dict(g) for g in active],
            "history": [game_to_dict(g) for g in history]
        })


@arena_bp.route('/api/public/games/<int:game_id>/state')
def api_public_game_state(game_id):
    """Публичный эндпоинт - получить состояние игры для Godot"""
    with db.get_session() as session_db:
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        game_state = GameState.from_game(game, session_db)
        return jsonify(game_state.to_dict())


@arena_bp.route('/api/public/games/<int:game_id>/units/<int:unit_id>/actions')
def api_public_unit_actions(game_id, unit_id):
    """Публичный эндпоинт - получить доступные действия юнита для Godot"""
    with db.get_session() as session_db:
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        game_state = GameState.from_game(game, session_db)

        unit = None
        for u in game_state.units:
            if u.get('id') == unit_id:
                unit = u
                break

        if not unit:
            return jsonify({'error': 'Unit not found'}), 404

        engine = GameEngine(session_db)
        moves = engine.get_valid_moves(unit_id)
        attacks = engine.get_valid_attacks(unit_id)

        return jsonify({
            'unit_id': unit_id,
            'moves': moves,
            'attacks': attacks
        })


@arena_bp.route('/api/public/games/create', methods=['POST'])
def api_public_create_game():
    """Публичный эндпоинт - создать игру для Godot"""
    data = request.get_json()
    player1_id = data.get('player1_id')
    player2_name = data.get('player2_name')
    field_size = data.get('field_size', '7x7')

    with db.get_session() as session_db:
        player1 = session_db.query(GameUser).filter_by(id=player1_id).first()
        if not player1:
            return jsonify({'error': 'Player 1 not found'}), 404

        player2 = session_db.query(GameUser).filter_by(username=player2_name).first()
        if not player2:
            return jsonify({'error': 'Player 2 not found'}), 404

        field = session_db.query(Field).filter_by(name=field_size).first()
        if not field:
            return jsonify({'error': 'Field not found'}), 404

        game = Game(
            player1_id=player1.id,
            player2_id=player2.id,
            field_id=field.id,
            status=GameStatus.WAITING,
            current_player_id=player1.id
        )
        session_db.add(game)
        session_db.flush()

        game_id = game.id
        session_db.commit()

        return jsonify({'game_id': game_id, 'status': 'waiting'})


@arena_bp.route('/api/public/games/<int:game_id>/accept', methods=['POST'])
def api_public_accept_game(game_id):
    """Публичный эндпоинт - принять игру для Godot"""
    data = request.get_json()
    player_id = data.get('player_id')
    army_id = data.get('army_id')  # ID армии для боя

    with db.get_session() as session_db:
        # Если армия не указана, берём первую доступную армию игрока
        if not army_id:
            user_races = session_db.query(UserRace).filter_by(user_id=player_id).all()
            for user_race in user_races:
                for army in user_race.armies:
                    # Проверяем что в армии есть юниты
                    army_units = session_db.query(ArmyUnit).filter(
                        ArmyUnit.army_id == army.id,
                        ArmyUnit.count > 0
                    ).first()
                    if army_units:
                        army_id = army.id
                        break
                if army_id:
                    break

        if not army_id:
            return jsonify({'error': 'No army available'}), 400

        engine = GameEngine(session_db)
        success, message = engine.accept_game(game_id, player_id, army_id)

        if success:
            return jsonify({'status': 'in_progress', 'game_id': game_id})
        else:
            return jsonify({'error': message}), 400


@arena_bp.route('/api/public/games/<int:game_id>/move', methods=['POST'])
def api_public_move(game_id):
    """Публичный эндпоинт - выполнить ход для Godot"""
    data = request.get_json()
    player_id = data.get('player_id')
    unit_id = data.get('unit_id')
    action = data.get('action')
    target_x = data.get('target_x')
    target_y = data.get('target_y')
    target_id = data.get('target_id')

    with db.get_session() as session_db:
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        if game.status != GameStatus.IN_PROGRESS:
            return jsonify({'error': 'Game is not in progress'}), 400

        if game.current_player_id != player_id:
            return jsonify({'error': 'Not your turn'}), 403

        engine = GameEngine(session_db)

        success = False
        message = ""
        turn_changed = False

        if action == 'move':
            success, message, turn_changed = engine.move_unit(game_id, player_id, unit_id, target_x, target_y)
        elif action == 'attack':
            success, message, turn_changed = engine.attack_unit(game_id, player_id, unit_id, target_id)
        elif action == 'skip':
            success, message, turn_changed = engine.skip_unit(game_id, player_id, unit_id)
        elif action == 'defer':
            success, message, turn_changed = engine.defer_unit(game_id, player_id, unit_id)
        else:
            return jsonify({'error': 'Invalid action'}), 400

        if not success:
            return jsonify({'error': message}), 400

        session_db.commit()

        # Refresh game to get updated state
        session_db.refresh(game)
        new_state = GameState.from_game(game, session_db)
        return jsonify({
            'success': True,
            'message': message,
            'turn_changed': turn_changed,
            'game_state': new_state.to_dict()
        })
