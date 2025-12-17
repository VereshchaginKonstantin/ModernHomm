#!/usr/bin/env python3
"""
Модуль Godot Arena API
REST API для Godot клиента арены
"""

import json
import os
import requests
import logging
import hashlib
import jwt
from datetime import datetime, timedelta
from decimal import Decimal
from flask import Blueprint, request, jsonify, make_response, redirect
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

from db.models import GameUser, Game, GameStatus, BattleUnit, Field, GameLog, Obstacle, Army, ArmyUnit, UserRace, RaceUnit, RaceUnitSkin, ClientLog, Config
from db.repository import Database
from core.game_engine import GameEngine

# JWT Configuration
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'modernhomm-arena-secret-key-2024')
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24 * 7  # 7 days


def verify_password(stored_hash: str, password: str) -> bool:
    """
    Проверяет пароль против хеша.
    Поддерживает два формата:
    - werkzeug (scrypt:...) - используется при set_password в арене
    - SHA-256 (64 hex chars) - используется в Telegram боте
    """
    if not stored_hash or not password:
        return False

    # Werkzeug format starts with algorithm name (scrypt:, pbkdf2:, etc.)
    if ':' in stored_hash and stored_hash.split(':')[0] in ('scrypt', 'pbkdf2'):
        return check_password_hash(stored_hash, password)

    # Simple SHA-256 (64 character hex string) - legacy format from Telegram bot
    if len(stored_hash) == 64:
        sha256_hash = hashlib.sha256(password.encode()).hexdigest()
        return stored_hash == sha256_hash

    return False

logger = logging.getLogger(__name__)

# Blueprint для арены
arena_bp = Blueprint('arena', __name__, url_prefix='/arena')


@arena_bp.route('/')
def index():
    """Главная страница арены - перенаправление на Godot Arena"""
    return redirect('/godot-arena/')


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


# JWT Helper Functions
def generate_jwt_token(player_id: int, username: str) -> str:
    """Generate JWT token for authenticated player"""
    payload = {
        'player_id': player_id,
        'username': username,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict:
    """Verify JWT token and return payload or None"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_from_request():
    """Extract token from Authorization header"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    return None


def token_required(f):
    """Decorator to require valid JWT token for API endpoints"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_request()
        if not token:
            return jsonify({'error': 'Token is required', 'code': 'TOKEN_MISSING'}), 401

        payload = verify_jwt_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token', 'code': 'TOKEN_INVALID'}), 401

        # Add player info to request context
        request.player_id = payload.get('player_id')
        request.username = payload.get('username')
        return f(*args, **kwargs)
    return decorated


class GameState:
    """Класс для представления состояния игры для Godot API"""

    def __init__(self, game, units, obstacles, logs, session):
        self.game = game
        self.units = units
        self.obstacles = obstacles
        self.logs = logs
        self.session = session

    @classmethod
    def _find_static_unit_image(cls, race_unit_id: int) -> str:
        """Найти статическое изображение юнита по ID"""
        import glob
        static_path = 'web/static/unit_images'
        patterns = [
            f'{static_path}/unit_{race_unit_id}_*.jpg',
            f'{static_path}/unit_{race_unit_id}_*.jpeg',
            f'{static_path}/unit_{race_unit_id}_*.png'
        ]
        for pattern in patterns:
            files = glob.glob(pattern)
            if files:
                # Возвращаем URL относительно /static/
                filename = os.path.basename(files[0])
                return f'/static/unit_images/{filename}'
        return None

    @classmethod
    def from_game(cls, game: Game, session) -> 'GameState':
        """Создать GameState из объекта Game"""
        units = []
        for bu in game.battle_units:
            if bu.total_count > 0:
                race_unit = bu.army_unit.race_unit if bu.army_unit else None
                if race_unit:
                    # Получаем скин юнита если есть
                    skin = race_unit.skins[0] if race_unit.skins else None
                    skin_id = skin.id if skin else None
                    has_image = skin and skin.image_data is not None
                    has_sprite = skin and skin.sprite_frames_data is not None

                    # Формируем URL изображения: приоритет спрайт-лист > статика > image_data
                    image_url = None
                    sprite_url = None
                    sprite_params = None

                    if has_sprite:
                        # Приоритет: анимированный спрайт-лист
                        sprite_url = f'/arena/api/public/skins/{skin_id}/sprite'
                        sprite_params = {
                            'frame_count': skin.sprite_frame_count or 1,
                            'fps': skin.sprite_fps or 10,
                            'columns': skin.sprite_columns or 1,
                            'rows': skin.sprite_rows or 1
                        }

                    if has_image:
                        image_url = f'/arena/api/public/skins/{skin_id}/image'
                    else:
                        # Fallback на статическое изображение
                        image_url = cls._find_static_unit_image(race_unit.id)

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
                            'attack_range': race_unit.range,
                            'skin_id': skin_id,
                            'has_image': has_image or (image_url is not None),
                            'has_sprite': has_sprite,
                            'image_url': image_url,
                            'sprite_url': sprite_url,
                            'sprite_params': sprite_params
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


def json_serial(obj):
    """JSON serializer для объектов, которые не сериализуются по умолчанию"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")



# =========================== Godot Public API ===========================

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


@arena_bp.route('/api/public/login', methods=['POST'])
def api_public_login():
    """Публичный эндпоинт - логин с паролем для Godot, возвращает JWT токен"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username:
        return jsonify({"error": "Username is required", "code": "USERNAME_REQUIRED"}), 400

    if not password:
        return jsonify({"error": "Password is required", "code": "PASSWORD_REQUIRED"}), 400

    with db.get_session() as session_db:
        player = session_db.query(GameUser).filter_by(username=username).first()
        if not player:
            return jsonify({"error": "Invalid username or password", "code": "INVALID_CREDENTIALS"}), 401

        # Проверяем пароль
        if not player.password_hash:
            return jsonify({"error": "Password not set. Please set password first.", "code": "PASSWORD_NOT_SET"}), 401

        if not verify_password(player.password_hash, password):
            return jsonify({"error": "Invalid username or password", "code": "INVALID_CREDENTIALS"}), 401

        # Генерируем JWT токен
        token = generate_jwt_token(player.id, player.username)

        # Получаем армии игрока
        armies = []
        max_army_cost = 0.0
        user_races = session_db.query(UserRace).filter_by(user_id=player.id).all()
        for user_race in user_races:
            for army in user_race.armies:
                army_cost = _calculate_army_cost(session_db, army)
                if army_cost > max_army_cost:
                    max_army_cost = army_cost
                armies.append({
                    'army_id': army.id,
                    'army_name': army.name,
                    'army_cost': army_cost
                })

        return jsonify({
            "token": token,
            "player": {
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


@arena_bp.route('/api/public/set_password', methods=['POST'])
def api_public_set_password():
    """Установить пароль для существующего пользователя (только если пароль не установлен)"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username:
        return jsonify({"error": "Username is required", "code": "USERNAME_REQUIRED"}), 400

    if not password:
        return jsonify({"error": "Password is required", "code": "PASSWORD_REQUIRED"}), 400

    if len(password) < 4:
        return jsonify({"error": "Password must be at least 4 characters", "code": "PASSWORD_TOO_SHORT"}), 400

    with db.get_session() as session_db:
        player = session_db.query(GameUser).filter_by(username=username).first()
        if not player:
            return jsonify({"error": "Player not found", "code": "PLAYER_NOT_FOUND"}), 404

        if player.password_hash:
            return jsonify({"error": "Password already set. Use change_password to update.", "code": "PASSWORD_ALREADY_SET"}), 400

        # Устанавливаем пароль
        player.password_hash = generate_password_hash(password)
        session_db.commit()

        # Генерируем токен после установки пароля
        token = generate_jwt_token(player.id, player.username)

        return jsonify({
            "success": True,
            "message": "Password set successfully",
            "token": token,
            "player_id": player.id
        })


@arena_bp.route('/api/public/change_password', methods=['POST'])
def api_public_change_password():
    """Изменить пароль (требуется старый пароль или токен)"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    # Можно использовать либо токен, либо старый пароль
    token = get_token_from_request()

    if not new_password:
        return jsonify({"error": "New password is required", "code": "PASSWORD_REQUIRED"}), 400

    if len(new_password) < 4:
        return jsonify({"error": "Password must be at least 4 characters", "code": "PASSWORD_TOO_SHORT"}), 400

    with db.get_session() as session_db:
        player = None

        # Если есть токен - используем его для авторизации
        if token:
            payload = verify_jwt_token(token)
            if payload:
                player = session_db.query(GameUser).filter_by(id=payload.get('player_id')).first()

        # Если нет токена или он невалиден - используем username + old_password
        if not player:
            if not username:
                return jsonify({"error": "Username is required", "code": "USERNAME_REQUIRED"}), 400

            player = session_db.query(GameUser).filter_by(username=username).first()
            if not player:
                return jsonify({"error": "Player not found", "code": "PLAYER_NOT_FOUND"}), 404

            if player.password_hash and not verify_password(player.password_hash, old_password):
                return jsonify({"error": "Invalid old password", "code": "INVALID_PASSWORD"}), 401

        # Устанавливаем новый пароль
        player.password_hash = generate_password_hash(new_password)
        session_db.commit()

        # Генерируем новый токен
        new_token = generate_jwt_token(player.id, player.username)

        return jsonify({
            "success": True,
            "message": "Password changed successfully",
            "token": new_token
        })


@arena_bp.route('/api/public/check_password_status', methods=['POST'])
def api_public_check_password_status():
    """Проверить, установлен ли пароль у пользователя"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()

    if not username:
        return jsonify({"error": "Username is required", "code": "USERNAME_REQUIRED"}), 400

    with db.get_session() as session_db:
        player = session_db.query(GameUser).filter_by(username=username).first()
        if not player:
            return jsonify({"exists": False, "has_password": False})

        return jsonify({
            "exists": True,
            "has_password": player.password_hash is not None,
            "player_id": player.id,
            "username": player.username
        })


@arena_bp.route('/api/public/me')
@token_required
def api_public_me():
    """Публичный эндпоинт - получить информацию о текущем игроке (требуется токен)"""
    player_id = request.player_id  # Из токена

    with db.get_session() as session_db:
        player = session_db.query(GameUser).filter_by(id=player_id).first()
        if not player:
            return jsonify({"error": "Player not found", "current_player": {}}), 404

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
@token_required
def api_public_pending_games():
    """Публичный эндпоинт - получить ожидающие игры для игрока (требуется токен)"""
    player_id = request.player_id  # Из токена

    with db.get_session() as session_db:
        player = session_db.query(GameUser).filter_by(id=player_id).first()
        if not player:
            return jsonify({"error": "Player not found", "pending_games": [], "active_games": [], "history": []}), 404

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
@token_required
def api_public_game_state(game_id):
    """Публичный эндпоинт - получить состояние игры для Godot (требуется токен)"""
    with db.get_session() as session_db:
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        game_state = GameState.from_game(game, session_db)
        return jsonify(game_state.to_dict())


@arena_bp.route('/api/public/games/<int:game_id>/units/<int:unit_id>/actions')
@token_required
def api_public_unit_actions(game_id, unit_id):
    """Публичный эндпоинт - получить доступные действия юнита для Godot (требуется токен)"""
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
@token_required
def api_public_create_game():
    """Публичный эндпоинт - создать игру для Godot (требуется токен)"""
    data = request.get_json()
    player1_id = request.player_id  # Из токена
    player2_name = data.get('player2_name')
    field_size = data.get('field_size', '7x7')
    army_id = data.get('army_id')  # ID армии для боя

    with db.get_session() as session_db:
        player1 = session_db.query(GameUser).filter_by(id=player1_id).first()
        if not player1:
            return jsonify({'error': 'Player 1 not found'}), 404

        player2 = session_db.query(GameUser).filter_by(username=player2_name).first()
        if not player2:
            return jsonify({'error': 'Player 2 not found'}), 404

        # Если армия не указана, берём первую доступную армию игрока
        if not army_id:
            user_races = session_db.query(UserRace).filter_by(user_id=player1_id).all()
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
            return jsonify({'error': 'No army available for player 1'}), 400

        # Используем GameEngine для правильного создания игры с размещением юнитов
        engine = GameEngine(session_db)
        game, message = engine.create_game(player1_id, player2_name, army_id, field_size)

        if not game:
            return jsonify({'error': message}), 400

        return jsonify({'game_id': game.id, 'status': 'waiting'})


@arena_bp.route('/api/public/games/<int:game_id>/accept', methods=['POST'])
@token_required
def api_public_accept_game(game_id):
    """Публичный эндпоинт - принять игру для Godot (требуется токен)"""
    data = request.get_json()
    player_id = request.player_id  # Из токена
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
@token_required
def api_public_move(game_id):
    """Публичный эндпоинт - выполнить ход для Godot (требуется токен)"""
    data = request.get_json()
    player_id = request.player_id  # Из токена
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


@arena_bp.route('/api/public/games/<int:game_id>/surrender', methods=['POST'])
@token_required
def api_public_surrender(game_id):
    """Публичный эндпоинт - сдаться в игре (требуется токен)"""
    player_id = request.player_id  # Из токена

    with db.get_session() as session_db:
        game = session_db.query(Game).filter_by(id=game_id).first()
        if not game:
            return jsonify({'error': 'Game not found'}), 404

        # Проверяем что игрок участник игры
        if game.player1_id != player_id and game.player2_id != player_id:
            return jsonify({'error': 'You are not a participant of this game'}), 403

        # Можно сдаться в ожидающей (отменить вызов) или в активной игре
        if game.status == GameStatus.COMPLETED:
            return jsonify({'error': 'Game is already completed'}), 400

        # Если игра в ожидании и это создатель - отменяем игру
        if game.status == GameStatus.WAITING:
            if game.player1_id == player_id:
                # Создатель отменяет вызов - удаляем игру
                session_db.delete(game)
                session_db.commit()
                return jsonify({
                    'success': True,
                    'message': 'Вызов отменён',
                    'game_deleted': True
                })
            else:
                # Вызванный отклоняет - просто удаляем игру
                session_db.delete(game)
                session_db.commit()
                return jsonify({
                    'success': True,
                    'message': 'Вызов отклонён',
                    'game_deleted': True
                })

        # Игра в процессе - определяем победителя (противник)
        winner_id = game.player2_id if game.player1_id == player_id else game.player1_id
        loser = session_db.query(GameUser).filter_by(id=player_id).first()
        winner = session_db.query(GameUser).filter_by(id=winner_id).first()

        # Завершаем игру
        game.status = GameStatus.COMPLETED
        game.winner_id = winner_id
        game.completed_at = datetime.utcnow()

        # Добавляем лог
        log_entry = GameLog(
            game_id=game_id,
            event_type='surrender',
            message=f'{loser.username if loser else "Игрок"} сдался. Победитель: {winner.username if winner else "Противник"}!'
        )
        session_db.add(log_entry)
        session_db.commit()

        return jsonify({
            'success': True,
            'message': f'Вы сдались. Победитель: {winner.username if winner else "Противник"}',
            'winner_id': winner_id,
            'winner_name': winner.username if winner else 'Unknown'
        })


@arena_bp.route('/api/public/skins/<int:skin_id>/image')
def api_public_skin_image(skin_id):
    """Публичный эндпоинт - получить изображение скина юнита"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id).first()
        if not skin or not skin.image_data:
            return '', 404

        response = make_response(skin.image_data)
        response.headers['Content-Type'] = skin.image_mime_type or 'image/png'
        response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache 24 hours
        response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        return response


@arena_bp.route('/api/public/skins/<int:skin_id>/sprite')
def api_public_skin_sprite(skin_id):
    """Публичный эндпоинт - получить спрайт-лист скина юнита"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id).first()
        if not skin or not skin.sprite_frames_data:
            return '', 404

        response = make_response(skin.sprite_frames_data)
        response.headers['Content-Type'] = skin.sprite_frames_mime_type or 'image/png'
        response.headers['Cache-Control'] = 'public, max-age=86400'  # Cache 24 hours
        response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        return response


@arena_bp.route('/api/public/skins/<int:skin_id>/info')
def api_public_skin_info(skin_id):
    """Публичный эндпоинт - получить информацию о скине для анимации"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id).first()
        if not skin:
            return jsonify({'error': 'Skin not found'}), 404

        return jsonify({
            'id': skin.id,
            'name': skin.name,
            # Idle спрайт
            'has_image': skin.image_data is not None,
            'has_sprite': skin.sprite_frames_data is not None,
            'sprite_scale_x': float(skin.sprite_scale_x) if skin.sprite_scale_x else 1.0,
            'sprite_scale_y': float(skin.sprite_scale_y) if skin.sprite_scale_y else 1.0,
            'sprite_offset_x': skin.sprite_offset_x or 0,
            'sprite_offset_y': skin.sprite_offset_y or 0,
            'sprite_rotation': float(skin.sprite_rotation) if skin.sprite_rotation else 0,
            'sprite_frame_count': skin.sprite_frame_count or 1,
            'sprite_fps': skin.sprite_fps or 10,
            # Атака
            'has_attack_image': skin.attack_image_data is not None if hasattr(skin, 'attack_image_data') else False,
            'has_attack_sprite': skin.attack_sprite_data is not None if hasattr(skin, 'attack_sprite_data') else False,
            'attack_frame_count': skin.attack_frame_count if hasattr(skin, 'attack_frame_count') else 1,
            'attack_fps': skin.attack_fps if hasattr(skin, 'attack_fps') else 10,
            # Смерть
            'has_death_image': skin.death_image_data is not None if hasattr(skin, 'death_image_data') else False,
            'has_death_sprite': skin.death_sprite_data is not None if hasattr(skin, 'death_sprite_data') else False,
            'death_frame_count': skin.death_frame_count if hasattr(skin, 'death_frame_count') else 1,
            'death_fps': skin.death_fps if hasattr(skin, 'death_fps') else 10,
        })


@arena_bp.route('/api/public/skins/<int:skin_id>/attack')
def api_public_skin_attack(skin_id):
    """Публичный эндпоинт - получить изображение атаки юнита"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id).first()
        if not skin or not hasattr(skin, 'attack_image_data') or not skin.attack_image_data:
            return '', 404

        response = make_response(skin.attack_image_data)
        response.headers['Content-Type'] = skin.attack_image_mime_type or 'image/png'
        response.headers['Cache-Control'] = 'public, max-age=86400'
        response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        return response


@arena_bp.route('/api/public/skins/<int:skin_id>/attack_sprite')
def api_public_skin_attack_sprite(skin_id):
    """Публичный эндпоинт - получить спрайт-лист атаки юнита"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id).first()
        if not skin or not hasattr(skin, 'attack_sprite_data') or not skin.attack_sprite_data:
            return '', 404

        response = make_response(skin.attack_sprite_data)
        response.headers['Content-Type'] = skin.attack_sprite_mime_type or 'image/png'
        response.headers['Cache-Control'] = 'public, max-age=86400'
        response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        return response


@arena_bp.route('/api/public/skins/<int:skin_id>/death')
def api_public_skin_death(skin_id):
    """Публичный эндпоинт - получить изображение смерти юнита"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id).first()
        if not skin or not hasattr(skin, 'death_image_data') or not skin.death_image_data:
            return '', 404

        response = make_response(skin.death_image_data)
        response.headers['Content-Type'] = skin.death_image_mime_type or 'image/png'
        response.headers['Cache-Control'] = 'public, max-age=86400'
        response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        return response


@arena_bp.route('/api/public/skins/<int:skin_id>/death_sprite')
def api_public_skin_death_sprite(skin_id):
    """Публичный эндпоинт - получить спрайт-лист смерти юнита"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id).first()
        if not skin or not hasattr(skin, 'death_sprite_data') or not skin.death_sprite_data:
            return '', 404

        response = make_response(skin.death_sprite_data)
        response.headers['Content-Type'] = skin.death_sprite_mime_type or 'image/png'
        response.headers['Cache-Control'] = 'public, max-age=86400'
        response.headers['Cross-Origin-Resource-Policy'] = 'cross-origin'
        return response


# =========================== Army Management API ===========================

def _get_hire_cost(race_unit) -> int:
    """Рассчитать стоимость найма юнита на основе prestige_max из unit_level"""
    if race_unit.unit_level:
        return race_unit.unit_level.prestige_max
    return 100  # Default cost


@arena_bp.route('/api/public/armies')
@token_required
def api_public_armies():
    """Получить список армий текущего игрока"""
    player_id = request.player_id

    with db.get_session() as session_db:
        armies = []
        user_races = session_db.query(UserRace).filter_by(user_id=player_id).all()
        for user_race in user_races:
            for army in user_race.armies:
                army_units = []
                army_cost = _calculate_army_cost(session_db, army)
                for au in army.army_units:
                    if au.race_unit and au.count > 0:
                        skin = au.race_unit.skins[0] if au.race_unit.skins else None
                        army_units.append({
                            'army_unit_id': au.id,
                            'race_unit_id': au.race_unit.id,
                            'name': au.race_unit.name,
                            'icon': au.race_unit.unit_level.icon if au.race_unit.unit_level else '?',
                            'count': au.count,
                            'attack': au.race_unit.attack,
                            'defense': au.race_unit.defense,
                            'health': au.race_unit.health,
                            'speed': au.race_unit.speed,
                            'min_damage': au.race_unit.min_damage,
                            'max_damage': au.race_unit.max_damage,
                            'hire_cost': _get_hire_cost(au.race_unit),
                            'has_image': skin and skin.image_data is not None,
                            'image_url': f'/arena/api/public/skins/{skin.id}/image' if skin and skin.image_data else None
                        })
                armies.append({
                    'army_id': army.id,
                    'army_name': army.name,
                    'army_cost': army_cost,
                    'user_race_id': user_race.id,
                    'race_name': user_race.race.name if user_race.race else 'Unknown',
                    'units': army_units
                })

        return jsonify({'armies': armies})


@arena_bp.route('/api/public/armies/create', methods=['POST'])
@token_required
def api_public_create_army():
    """Создать новую армию"""
    player_id = request.player_id
    data = request.get_json() or {}
    army_name = data.get('name', 'Новая армия')
    user_race_id = data.get('user_race_id')

    with db.get_session() as session_db:
        # Если user_race_id не указан, берём первую расу игрока
        if not user_race_id:
            user_race = session_db.query(UserRace).filter_by(user_id=player_id).first()
            if not user_race:
                return jsonify({'error': 'У вас нет доступных рас. Выберите расу сначала.'}), 400
            user_race_id = user_race.id
        else:
            user_race = session_db.query(UserRace).filter_by(id=user_race_id, user_id=player_id).first()
            if not user_race:
                return jsonify({'error': 'Раса не найдена'}), 404

        # Создаём армию
        new_army = Army(
            name=army_name,
            user_race_id=user_race_id
        )
        session_db.add(new_army)
        session_db.commit()

        return jsonify({
            'success': True,
            'army_id': new_army.id,
            'army_name': new_army.name
        })


@arena_bp.route('/api/public/armies/<int:army_id>')
@token_required
def api_public_get_army(army_id):
    """Получить детали армии"""
    player_id = request.player_id

    with db.get_session() as session_db:
        army = session_db.query(Army).filter_by(id=army_id).first()
        if not army:
            return jsonify({'error': 'Армия не найдена'}), 404

        # Проверяем что армия принадлежит игроку
        if army.user_race.user_id != player_id:
            return jsonify({'error': 'Нет доступа к этой армии'}), 403

        army_units = []
        army_cost = _calculate_army_cost(session_db, army)
        for au in army.army_units:
            if au.race_unit and au.count > 0:
                skin = au.race_unit.skins[0] if au.race_unit.skins else None
                army_units.append({
                    'army_unit_id': au.id,
                    'race_unit_id': au.race_unit.id,
                    'name': au.race_unit.name,
                    'icon': au.race_unit.unit_level.icon if au.race_unit.unit_level else '?',
                    'count': au.count,
                    'attack': au.race_unit.attack,
                    'defense': au.race_unit.defense,
                    'health': au.race_unit.health,
                    'speed': au.race_unit.speed,
                    'min_damage': au.race_unit.min_damage,
                    'max_damage': au.race_unit.max_damage,
                    'hire_cost': _get_hire_cost(au.race_unit),
                    'has_image': skin and skin.image_data is not None,
                    'image_url': f'/arena/api/public/skins/{skin.id}/image' if skin and skin.image_data else None
                })

        return jsonify({
            'army_id': army.id,
            'army_name': army.name,
            'army_cost': army_cost,
            'user_race_id': army.user_race_id,
            'race_name': army.user_race.race.name if army.user_race and army.user_race.race else 'Unknown',
            'units': army_units
        })


@arena_bp.route('/api/public/armies/<int:army_id>/delete', methods=['POST'])
@token_required
def api_public_delete_army(army_id):
    """Удалить армию"""
    player_id = request.player_id

    with db.get_session() as session_db:
        army = session_db.query(Army).filter_by(id=army_id).first()
        if not army:
            return jsonify({'error': 'Армия не найдена'}), 404

        if army.user_race.user_id != player_id:
            return jsonify({'error': 'Нет доступа к этой армии'}), 403

        session_db.delete(army)
        session_db.commit()

        return jsonify({'success': True})


@arena_bp.route('/api/public/armies/<int:army_id>/available_units')
@token_required
def api_public_available_units(army_id):
    """Получить доступных юнитов для найма в армию"""
    player_id = request.player_id

    with db.get_session() as session_db:
        army = session_db.query(Army).filter_by(id=army_id).first()
        if not army:
            return jsonify({'error': 'Армия не найдена'}), 404

        if army.user_race.user_id != player_id:
            return jsonify({'error': 'Нет доступа к этой армии'}), 403

        # Получаем баланс игрока
        player = session_db.query(GameUser).filter_by(id=player_id).first()
        player_balance = float(player.balance) if player else 0

        # Получаем юнитов расы
        race_units = session_db.query(RaceUnit).filter_by(race_id=army.user_race.race_id).all()

        available_units = []
        for ru in race_units:
            skin = ru.skins[0] if ru.skins else None
            # Проверяем, есть ли уже этот юнит в армии
            existing_au = session_db.query(ArmyUnit).filter_by(
                army_id=army_id,
                race_unit_id=ru.id
            ).first()
            current_count = existing_au.count if existing_au else 0

            hire_cost = _get_hire_cost(ru)
            available_units.append({
                'race_unit_id': ru.id,
                'name': ru.name,
                'icon': ru.unit_level.icon if ru.unit_level else '?',
                'level': ru.unit_level.level if ru.unit_level else 1,
                'attack': ru.attack,
                'defense': ru.defense,
                'health': ru.health,
                'speed': ru.speed,
                'min_damage': ru.min_damage,
                'max_damage': ru.max_damage,
                'hire_cost': hire_cost,
                'current_count': current_count,
                'can_afford': player_balance >= hire_cost,
                'has_image': skin and skin.image_data is not None,
                'image_url': f'/arena/api/public/skins/{skin.id}/image' if skin and skin.image_data else None
            })

        return jsonify({
            'army_id': army_id,
            'player_balance': player_balance,
            'units': available_units
        })


@arena_bp.route('/api/public/armies/<int:army_id>/hire', methods=['POST'])
@token_required
def api_public_hire_unit(army_id):
    """Нанять юнитов в армию"""
    player_id = request.player_id
    data = request.get_json() or {}
    race_unit_id = data.get('race_unit_id')
    count = data.get('count', 1)

    if not race_unit_id:
        return jsonify({'error': 'race_unit_id обязателен'}), 400

    if count < 1:
        return jsonify({'error': 'count должен быть >= 1'}), 400

    with db.get_session() as session_db:
        army = session_db.query(Army).filter_by(id=army_id).first()
        if not army:
            return jsonify({'error': 'Армия не найдена'}), 404

        if army.user_race.user_id != player_id:
            return jsonify({'error': 'Нет доступа к этой армии'}), 403

        # Получаем юнита расы
        race_unit = session_db.query(RaceUnit).filter_by(id=race_unit_id).first()
        if not race_unit:
            return jsonify({'error': 'Юнит не найден'}), 404

        # Проверяем что юнит принадлежит той же расе
        if race_unit.race_id != army.user_race.race_id:
            return jsonify({'error': 'Этот юнит не доступен для данной расы'}), 400

        # Проверяем баланс
        player = session_db.query(GameUser).filter_by(id=player_id).first()
        hire_cost = _get_hire_cost(race_unit)
        total_cost = hire_cost * count
        if player.balance < total_cost:
            return jsonify({'error': f'Недостаточно средств. Нужно: {total_cost}, у вас: {player.balance}'}), 400

        # Находим или создаём ArmyUnit
        army_unit = session_db.query(ArmyUnit).filter_by(
            army_id=army_id,
            race_unit_id=race_unit_id
        ).first()

        if army_unit:
            army_unit.count += count
        else:
            army_unit = ArmyUnit(
                army_id=army_id,
                race_unit_id=race_unit_id,
                count=count
            )
            session_db.add(army_unit)

        # Списываем деньги
        player.balance -= total_cost
        session_db.commit()

        return jsonify({
            'success': True,
            'hired_count': count,
            'total_cost': total_cost,
            'new_balance': float(player.balance),
            'new_unit_count': army_unit.count
        })


@arena_bp.route('/api/public/armies/<int:army_id>/dismiss', methods=['POST'])
@token_required
def api_public_dismiss_unit(army_id):
    """Распустить юнитов из армии (частичный возврат денег)"""
    player_id = request.player_id
    data = request.get_json() or {}
    race_unit_id = data.get('race_unit_id')
    count = data.get('count', 1)

    if not race_unit_id:
        return jsonify({'error': 'race_unit_id обязателен'}), 400

    if count < 1:
        return jsonify({'error': 'count должен быть >= 1'}), 400

    with db.get_session() as session_db:
        army = session_db.query(Army).filter_by(id=army_id).first()
        if not army:
            return jsonify({'error': 'Армия не найдена'}), 404

        if army.user_race.user_id != player_id:
            return jsonify({'error': 'Нет доступа к этой армии'}), 403

        # Находим юнита в армии
        army_unit = session_db.query(ArmyUnit).filter_by(
            army_id=army_id,
            race_unit_id=race_unit_id
        ).first()

        if not army_unit or army_unit.count < count:
            return jsonify({'error': 'Недостаточно юнитов для роспуска'}), 400

        # Возвращаем 50% стоимости
        race_unit = army_unit.race_unit
        hire_cost = _get_hire_cost(race_unit)
        refund = (hire_cost * count) * 0.5

        player = session_db.query(GameUser).filter_by(id=player_id).first()
        player.balance += refund

        army_unit.count -= count
        if army_unit.count <= 0:
            session_db.delete(army_unit)

        session_db.commit()

        return jsonify({
            'success': True,
            'dismissed_count': count,
            'refund': refund,
            'new_balance': float(player.balance),
            'remaining_count': max(0, army_unit.count) if army_unit else 0
        })


@arena_bp.route('/api/public/user_races')
@token_required
def api_public_user_races():
    """Получить расы игрока"""
    player_id = request.player_id

    with db.get_session() as session_db:
        user_races = session_db.query(UserRace).filter_by(user_id=player_id).all()

        races = []
        for ur in user_races:
            races.append({
                'user_race_id': ur.id,
                'race_id': ur.race_id,
                'race_name': ur.race.name if ur.race else 'Unknown',
                'race_description': ur.race.description if ur.race else '',
                'armies_count': len(ur.armies)
            })

        return jsonify({'user_races': races})


# ============= Client Logging API =============

@arena_bp.route('/api/public/debug/status')
def api_debug_status():
    """Публичный эндпоинт - проверить статус debug mode"""
    with db.get_session() as session_db:
        config = session_db.query(Config).filter_by(key='debug_mode').first()
        debug_enabled = config.value.lower() == 'true' if config else True
        return jsonify({'debug_mode': debug_enabled})


@arena_bp.route('/api/public/logs', methods=['POST'])
def api_receive_logs():
    """Публичный эндпоинт - принять логи от клиента Godot"""
    # Проверяем включен ли debug mode
    with db.get_session() as session_db:
        config = session_db.query(Config).filter_by(key='debug_mode').first()
        debug_enabled = config.value.lower() == 'true' if config else True

        if not debug_enabled:
            return jsonify({'success': True, 'message': 'Debug mode disabled, logs ignored'})

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        logs = data.get('logs', [])
        session_id = data.get('session_id', 'unknown')
        player_id = data.get('player_id')
        user_agent = request.headers.get('User-Agent', '')[:500]

        saved_count = 0
        for log_entry in logs[:100]:  # Максимум 100 логов за раз
            try:
                client_log = ClientLog(
                    session_id=session_id[:64],
                    player_id=player_id,
                    level=log_entry.get('level', 'info')[:20],
                    message=log_entry.get('message', '')[:10000],
                    context=json.dumps(log_entry.get('context', {}))[:5000] if log_entry.get('context') else None,
                    user_agent=user_agent
                )
                session_db.add(client_log)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Failed to save log: {e}")

        session_db.commit()
        return jsonify({'success': True, 'saved': saved_count})


@arena_bp.route('/api/admin/logs')
@token_required
def api_get_logs():
    """Админский эндпоинт - получить логи клиентов"""
    player_id = request.player_id

    # Проверяем что это админ (player_id = 1 или 4)
    if player_id not in [1, 4]:
        return jsonify({'error': 'Admin access required'}), 403

    # Параметры фильтрации
    level = request.args.get('level')
    session_id = request.args.get('session_id')
    limit = min(int(request.args.get('limit', 100)), 1000)
    offset = int(request.args.get('offset', 0))

    with db.get_session() as session_db:
        query = session_db.query(ClientLog)

        if level:
            query = query.filter(ClientLog.level == level)
        if session_id:
            query = query.filter(ClientLog.session_id == session_id)

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


@arena_bp.route('/api/admin/logs/clear', methods=['POST'])
@token_required
def api_clear_logs():
    """Админский эндпоинт - очистить старые логи"""
    player_id = request.player_id

    if player_id not in [1, 4]:
        return jsonify({'error': 'Admin access required'}), 403

    data = request.get_json() or {}
    days = int(data.get('days', 7))

    with db.get_session() as session_db:
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = session_db.query(ClientLog).filter(ClientLog.created_at < cutoff).delete()
        session_db.commit()

        return jsonify({'success': True, 'deleted': deleted})


@arena_bp.route('/api/admin/debug/toggle', methods=['POST'])
@token_required
def api_toggle_debug():
    """Админский эндпоинт - переключить debug mode"""
    player_id = request.player_id

    if player_id not in [1, 4]:
        return jsonify({'error': 'Admin access required'}), 403

    with db.get_session() as session_db:
        config = session_db.query(Config).filter_by(key='debug_mode').first()
        if not config:
            config = Config(key='debug_mode', value='true', description='Debug mode for client logging')
            session_db.add(config)

        # Toggle value
        new_value = 'false' if config.value.lower() == 'true' else 'true'
        config.value = new_value
        session_db.commit()

        return jsonify({'success': True, 'debug_mode': new_value == 'true'})
