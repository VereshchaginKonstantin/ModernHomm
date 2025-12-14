#!/usr/bin/env python3
"""
Репозиторий для работы с базой данных
"""

import os
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import (
    Base,
    # Core
    User, Message, Config, GameUser,
    # Battle
    Game, GameStatus, Field, BattleUnit,
    # Army
    GameRace, RaceUnit, Army, ArmyUnit, UserRace, UserRaceUnit
)
from decimal import Decimal


def format_coins(amount):
    """Форматирование монет с правильным склонением"""
    # Получаем последнюю цифру и две последние цифры
    amount_int = int(amount) if isinstance(amount, (int, float, Decimal)) else int(float(amount))
    last_digit = amount_int % 10
    last_two_digits = amount_int % 100

    # Определяем правильное склонение
    if last_two_digits >= 11 and last_two_digits <= 19:
        word = "монет"
    elif last_digit == 1:
        word = "монета"
    elif last_digit >= 2 and last_digit <= 4:
        word = "монеты"
    else:
        word = "монет"

    return f"{amount} {word}"


class Database:
    """Класс для управления подключением к базе данных"""

    def __init__(self, connection_string=None):
        """
        Инициализация подключения к базе данных

        Args:
            connection_string: Строка подключения к БД. Если не указана,
                             берется из переменной окружения DATABASE_URL
        """
        if connection_string is None:
            connection_string = os.getenv(
                'DATABASE_URL',
                'postgresql://postgres:postgres@localhost:5432/telegram_bot'
            )

        self.engine = create_engine(connection_string, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self):
        """Создание всех таблиц в базе данных"""
        Base.metadata.create_all(self.engine)

    def drop_tables(self):
        """Удаление всех таблиц (используется в тестах)"""
        Base.metadata.drop_all(self.engine)

    @contextmanager
    def get_session(self) -> Session:
        """
        Контекстный менеджер для получения сессии БД

        Yields:
            Session: Сессия SQLAlchemy
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def save_user(self, telegram_id: int, username: str = None) -> User:
        """
        Сохранение или обновление информации о пользователе

        Args:
            telegram_id: ID пользователя в Telegram
            username: Имя пользователя (username)

        Returns:
            User: Объект пользователя
        """
        with self.get_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()

            if user:
                # Обновляем существующего пользователя
                user.username = username
                user.last_seen = datetime.utcnow()
            else:
                # Создаем нового пользователя
                user = User(
                    telegram_id=telegram_id,
                    username=username
                )
                session.add(user)

            session.flush()
            session.refresh(user)
            # Eager load attributes before session closes
            _ = (user.id, user.telegram_id, user.username,
                 user.last_seen, user.first_seen)
            session.expunge(user)
            return user

    def save_message(self, telegram_user_id: int, message_text: str,
                    username: str = None) -> Message:
        """
        Сохранение сообщения пользователя

        Args:
            telegram_user_id: ID пользователя в Telegram
            message_text: Текст сообщения
            username: Имя пользователя (username)

        Returns:
            Message: Объект сообщения
        """
        with self.get_session() as session:
            message = Message(
                telegram_user_id=telegram_user_id,
                message_text=message_text,
                username=username
            )
            session.add(message)
            session.flush()
            session.refresh(message)
            # Eager load attributes before session closes
            _ = (message.id, message.telegram_user_id, message.message_text,
                 message.username, message.message_date)
            session.expunge(message)
            return message

    def get_user_messages(self, telegram_id: int) -> list:
        """
        Получение всех сообщений пользователя

        Args:
            telegram_id: ID пользователя в Telegram

        Returns:
            list: Список сообщений
        """
        with self.get_session() as session:
            messages = session.query(Message).filter_by(
                telegram_user_id=telegram_id
            ).order_by(Message.message_date.desc()).all()

            # Принудительно загружаем все атрибуты перед закрытием сессии
            for msg in messages:
                _ = msg.id
                _ = msg.telegram_user_id
                _ = msg.message_text
                _ = msg.message_date
                _ = msg.username

            session.expunge_all()
            return messages

    def get_all_users(self) -> list:
        """
        Получение всех пользователей

        Returns:
            list: Список пользователей
        """
        with self.get_session() as session:
            users = session.query(User).all()

            # Принудительно загружаем все атрибуты перед закрытием сессии
            for user in users:
                _ = user.id
                _ = user.telegram_id
                _ = user.username
                _ = user.first_seen
                _ = user.last_seen

            session.expunge_all()
            return users

    def get_users_paginated(self, offset: int = 0, limit: int = 10) -> tuple:
        """
        Получение пользователей с пагинацией

        Args:
            offset: Смещение для пагинации
            limit: Количество пользователей на странице

        Returns:
            tuple: (список пользователей, общее количество пользователей)
        """
        with self.get_session() as session:
            # Получаем общее количество пользователей
            total_count = session.query(User).count()

            # Получаем пользователей с пагинацией, сортируем по последней активности
            users = session.query(User).order_by(
                User.last_seen.desc()
            ).offset(offset).limit(limit).all()

            # Принудительно загружаем все атрибуты перед закрытием сессии
            for user in users:
                _ = user.id
                _ = user.telegram_id
                _ = user.username
                _ = user.first_seen
                _ = user.last_seen

            session.expunge_all()
            return users, total_count

    def get_user_messages_paginated(self, telegram_id: int, offset: int = 0, limit: int = 10) -> tuple:
        """
        Получение сообщений пользователя с пагинацией

        Args:
            telegram_id: ID пользователя в Telegram
            offset: Смещение для пагинации
            limit: Количество сообщений на странице

        Returns:
            tuple: (список сообщений, общее количество сообщений)
        """
        with self.get_session() as session:
            # Получаем общее количество сообщений
            total_count = session.query(Message).filter_by(
                telegram_user_id=telegram_id
            ).count()

            # Получаем сообщения с пагинацией
            messages = session.query(Message).filter_by(
                telegram_user_id=telegram_id
            ).order_by(Message.message_date.desc()).offset(offset).limit(limit).all()

            # Принудительно загружаем все атрибуты перед закрытием сессии
            for msg in messages:
                _ = msg.id
                _ = msg.telegram_user_id
                _ = msg.message_text
                _ = msg.message_date
                _ = msg.username

            session.expunge_all()
            return messages, total_count

    def search_messages_by_username(self, username: str, offset: int = 0, limit: int = 10) -> tuple:
        """
        Поиск сообщений по username пользователя с пагинацией

        Args:
            username: Username пользователя (без @)
            offset: Смещение для пагинации
            limit: Количество сообщений на странице

        Returns:
            tuple: (список сообщений, общее количество сообщений)
        """
        with self.get_session() as session:
            # Нормализуем username - убираем @ если есть
            clean_username = username.lstrip('@').lower()

            # Получаем общее количество сообщений
            total_count = session.query(Message).filter(
                Message.username.ilike(clean_username)
            ).count()

            # Получаем сообщения с пагинацией
            messages = session.query(Message).filter(
                Message.username.ilike(clean_username)
            ).order_by(Message.message_date.desc()).offset(offset).limit(limit).all()

            # Принудительно загружаем все атрибуты перед закрытием сессии
            for msg in messages:
                # Обращаемся к атрибутам, чтобы они были загружены в память
                _ = msg.id
                _ = msg.telegram_user_id
                _ = msg.message_text
                _ = msg.message_date
                _ = msg.username

            # Отключаем объекты от сессии, чтобы они оставались доступными после закрытия
            session.expunge_all()

            return messages, total_count

    # ===== CRUD методы для Config =====

    def get_config(self, key: str, default: str = None) -> str:
        """
        Получение значения конфигурации по ключу

        Args:
            key: Ключ конфигурации
            default: Значение по умолчанию, если ключ не найден

        Returns:
            str: Значение конфигурации или default
        """
        with self.get_session() as session:
            config = session.query(Config).filter_by(key=key).first()

            if config:
                return config.value

            return default

    def set_config(self, key: str, value: str, description: str = None) -> Config:
        """
        Установка значения конфигурации

        Args:
            key: Ключ конфигурации
            value: Значение конфигурации
            description: Описание конфигурации (опционально)

        Returns:
            Config: Объект конфигурации
        """
        with self.get_session() as session:
            config = session.query(Config).filter_by(key=key).first()

            if config:
                # Обновляем существующее значение
                config.value = value
                if description is not None:
                    config.description = description
                config.updated_at = datetime.utcnow()
            else:
                # Создаем новое значение
                config = Config(
                    key=key,
                    value=value,
                    description=description
                )
                session.add(config)

            session.flush()
            session.refresh(config)

            # Загружаем все атрибуты
            _ = config.id
            _ = config.key
            _ = config.value
            _ = config.description
            _ = config.created_at
            _ = config.updated_at

            session.expunge_all()
            return config

    # ===== CRUD методы для GameUser =====

    def create_game_user(self, telegram_id: int, username: str, initial_balance: float = 1000) -> GameUser:
        """
        Создание нового игрового пользователя

        Args:
            telegram_id: ID пользователя в Telegram
            username: Username пользователя в Telegram
            initial_balance: Начальный баланс (по умолчанию 1000)

        Returns:
            GameUser: Объект игрового пользователя
        """
        with self.get_session() as session:
            game_user = GameUser(
                telegram_id=telegram_id,
                username=username,
                balance=initial_balance
            )
            session.add(game_user)
            session.flush()
            session.refresh(game_user)

            # Загружаем все атрибуты
            _ = game_user.id
            _ = game_user.telegram_id
            _ = game_user.username
            _ = game_user.balance
            _ = game_user.wins
            _ = game_user.losses
            _ = game_user.created_at
            _ = game_user.updated_at

            session.expunge_all()
            return game_user

    def get_game_user(self, telegram_id: int) -> GameUser:
        """
        Получение игрового пользователя по telegram_id

        Args:
            telegram_id: ID пользователя в Telegram

        Returns:
            GameUser: Объект игрового пользователя или None
        """
        with self.get_session() as session:
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()

            if game_user:
                # Загружаем все атрибуты
                _ = game_user.id
                _ = game_user.telegram_id
                _ = game_user.username
                _ = game_user.balance
                _ = game_user.wins
                _ = game_user.losses
                _ = game_user.created_at
                _ = game_user.updated_at

                session.expunge_all()

            return game_user

    def update_game_user(self, telegram_id: int, **kwargs) -> GameUser:
        """
        Обновление данных игрового пользователя

        Args:
            telegram_id: ID пользователя в Telegram
            **kwargs: Поля для обновления (name, balance, wins, losses)

        Returns:
            GameUser: Обновленный объект игрового пользователя
        """
        with self.get_session() as session:
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()

            if not game_user:
                raise ValueError(f"Игровой пользователь с telegram_id={telegram_id} не найден")

            # Обновляем только переданные поля
            for key, value in kwargs.items():
                if hasattr(game_user, key):
                    setattr(game_user, key, value)

            session.flush()
            session.refresh(game_user)

            # Загружаем все атрибуты
            _ = game_user.id
            _ = game_user.telegram_id
            _ = game_user.username
            _ = game_user.balance
            _ = game_user.wins
            _ = game_user.losses
            _ = game_user.created_at
            _ = game_user.updated_at

            session.expunge_all()
            return game_user

    def delete_game_user(self, telegram_id: int) -> bool:
        """
        Удаление игрового пользователя

        Args:
            telegram_id: ID пользователя в Telegram

        Returns:
            bool: True если пользователь был удален, False если не найден
        """
        with self.get_session() as session:
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()

            if game_user:
                session.delete(game_user)
                return True

            return False

    def get_all_game_users(self) -> list:
        """
        Получение всех игровых пользователей

        Returns:
            list: Список всех игровых пользователей
        """
        with self.get_session() as session:
            game_users = session.query(GameUser).all()

            # Загружаем все атрибуты перед закрытием сессии
            for user in game_users:
                _ = user.id
                _ = user.telegram_id
                _ = user.username
                _ = user.balance
                _ = user.wins
                _ = user.losses
                _ = user.created_at
                _ = user.updated_at

            session.expunge_all()
            return game_users

    def get_or_create_game_user(self, telegram_id: int, username: str, initial_balance: float = 1000) -> tuple:
        """
        Получение или создание игрового пользователя

        Args:
            telegram_id: ID пользователя в Telegram
            username: Username пользователя (обязательное поле)
            initial_balance: Начальный баланс (по умолчанию 1000)

        Returns:
            tuple: (GameUser, created) - объект и флаг создания нового пользователя
        """
        game_user = self.get_game_user(telegram_id)

        if game_user:
            return game_user, False

        game_user = self.create_game_user(telegram_id, username, initial_balance)
        return game_user, True

    def get_random_game_users(self, limit: int = 10, exclude_telegram_id: int = None) -> list:
        """
        Получение случайных игровых пользователей

        Args:
            limit: Максимальное количество пользователей (по умолчанию 10)
            exclude_telegram_id: ID пользователя, которого нужно исключить из выборки

        Returns:
            list: Список объектов GameUser
        """
        from sqlalchemy import func

        with self.get_session() as session:
            query = session.query(GameUser)

            # Исключаем указанного пользователя
            if exclude_telegram_id:
                query = query.filter(GameUser.telegram_id != exclude_telegram_id)

            # Сортируем случайным образом и ограничиваем количество
            game_users = query.order_by(func.random()).limit(limit).all()

            # Загружаем все атрибуты для каждого пользователя
            for game_user in game_users:
                _ = game_user.id
                _ = game_user.telegram_id
                _ = game_user.username
                _ = game_user.balance
                _ = game_user.wins
                _ = game_user.losses
                _ = game_user.created_at
                _ = game_user.updated_at

            session.expunge_all()
            return game_users

    def get_players_by_army_value(self, telegram_id: int, limit: int = 3, variance: float = 0.3) -> list:
        """
        Получение игроков с близкой стоимостью армии (по армиям, а не отдельным юнитам)

        Args:
            telegram_id: ID текущего игрока
            limit: Максимальное количество игроков (по умолчанию 3)
            variance: Допустимая разница в стоимости армии (по умолчанию 0.3 = ±30%)

        Returns:
            list: Список кортежей (GameUser, army_value)
        """
        from decimal import Decimal
        import random

        with self.get_session() as session:
            # Получаем текущего игрока
            current_player = session.query(GameUser).filter_by(telegram_id=telegram_id).first()
            if not current_player:
                return []

            # Получаем всех остальных игроков с армиями
            all_players = session.query(GameUser).filter(GameUser.telegram_id != telegram_id).all()
            candidates = []

            for player in all_players:
                # Проверяем, есть ли у игрока армии через UserRace -> Army
                user_races = session.query(UserRace).filter_by(user_id=player.id).all()
                has_army = False
                for user_race in user_races:
                    armies = session.query(Army).filter_by(user_race_id=user_race.id).all()
                    if armies:
                        has_army = True
                        break

                if has_army:
                    candidates.append(player)

            # Выбираем случайных кандидатов
            if len(candidates) > limit:
                candidates = random.sample(candidates, limit)

            # Загружаем атрибуты
            result = []
            for game_user in candidates:
                _ = game_user.id
                _ = game_user.telegram_id
                _ = game_user.username
                _ = game_user.balance
                _ = game_user.wins
                _ = game_user.losses
                _ = game_user.created_at
                _ = game_user.updated_at
                result.append((game_user, Decimal('0')))  # Army value is computed elsewhere

            session.expunge_all()
            return result

    def get_available_opponents_by_username(self, username: str, limit: int = 3, variance: float = 0.3) -> tuple:
        """
        Получение противников для пользователя по username.
        Используется в веб-интерфейсе арены.

        Args:
            username: Username текущего игрока
            limit: Максимальное количество противников (по умолчанию 3)
            variance: Допустимая разница в стоимости армии (по умолчанию 0.3 = ±30%)

        Returns:
            tuple: (current_player_data, opponents_list)
                - current_player_data: dict с данными текущего игрока
                - opponents_list: list[dict] со списком противников
        """
        from decimal import Decimal
        import random

        with self.get_session() as session:
            # Получаем текущего игрока по username
            current_player = session.query(GameUser).filter_by(username=username).first()
            if not current_player:
                return None, []

            # Данные текущего игрока
            current_player_data = {
                'id': current_player.id,
                'telegram_id': current_player.telegram_id,
                'name': current_player.username,
                'balance': float(current_player.balance),
                'wins': current_player.wins,
                'losses': current_player.losses,
                'army_value': 0  # Calculated when army is selected
            }

            # Получаем всех остальных игроков с армиями
            all_players = session.query(GameUser).filter(GameUser.id != current_player.id).all()
            candidates_with_value = []

            for player in all_players:
                # Проверяем, есть ли у игрока армии через UserRace -> Army
                user_races = session.query(UserRace).filter_by(user_id=player.id).all()
                has_army = False
                for user_race in user_races:
                    armies = session.query(Army).filter_by(user_race_id=user_race.id).all()
                    if armies:
                        has_army = True
                        break

                if has_army:
                    candidates_with_value.append((player, Decimal('0')))

            # Выбираем случайных кандидатов
            if len(candidates_with_value) > limit:
                candidates_with_value = random.sample(candidates_with_value, limit)

            # Формируем результат
            opponents = []
            for player, army_value in candidates_with_value:
                win_rate = 0
                if player.wins + player.losses > 0:
                    win_rate = (player.wins / (player.wins + player.losses)) * 100

                opponents.append({
                    'id': player.id,
                    'telegram_id': player.telegram_id,
                    'name': player.username,
                    'balance': float(player.balance),
                    'wins': player.wins,
                    'losses': player.losses,
                    'army_value': float(army_value),
                    'win_rate': win_rate
                })

            return current_player_data, opponents

    # ===== CRUD методы для Game =====

    def get_game_by_id(self, game_id: int) -> Game:
        """
        Получение игры по ID

        Args:
            game_id: ID игры

        Returns:
            Game: Объект игры или None
        """
        with self.get_session() as session:
            game = session.query(Game).filter_by(id=game_id).first()

            if game:
                # Загружаем все атрибуты
                _ = game.id
                _ = game.player1_id
                _ = game.player2_id
                _ = game.field_id
                _ = game.status
                _ = game.current_player_id
                _ = game.winner_id
                _ = game.created_at
                _ = game.started_at
                _ = game.completed_at
                _ = game.last_move_at

                session.expunge_all()

            return game

    def get_user_games(self, telegram_id: int, status: GameStatus = None) -> list:
        """
        Получение всех игр пользователя

        Args:
            telegram_id: ID пользователя в Telegram
            status: Фильтр по статусу (опционально)

        Returns:
            list: Список игр
        """
        with self.get_session() as session:
            # Получаем игрового пользователя
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()

            if not game_user:
                return []

            # Формируем запрос
            query = session.query(Game).filter(
                (Game.player1_id == game_user.id) | (Game.player2_id == game_user.id)
            )

            if status:
                query = query.filter(Game.status == status)

            games = query.order_by(Game.created_at.desc()).all()

            # Загружаем все атрибуты
            for game in games:
                _ = game.id
                _ = game.player1_id
                _ = game.player2_id
                _ = game.field_id
                _ = game.status
                _ = game.current_player_id
                _ = game.winner_id
                _ = game.created_at
                _ = game.started_at
                _ = game.completed_at
                _ = game.last_move_at

            session.expunge_all()
            return games

    def get_active_game(self, telegram_id: int) -> Game:
        """
        Получение активной игры пользователя (ожидание или в процессе)

        Args:
            telegram_id: ID пользователя в Telegram

        Returns:
            Game: Активная игра или None
        """
        with self.get_session() as session:
            # Получаем игрового пользователя
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()

            if not game_user:
                return None

            # Ищем активную игру
            game = session.query(Game).filter(
                ((Game.player1_id == game_user.id) | (Game.player2_id == game_user.id)),
                Game.status.in_([GameStatus.WAITING, GameStatus.IN_PROGRESS])
            ).first()

            if game:
                # Загружаем все атрибуты
                _ = game.id
                _ = game.player1_id
                _ = game.player2_id
                _ = game.field_id
                _ = game.status
                _ = game.current_player_id
                _ = game.winner_id
                _ = game.created_at
                _ = game.started_at
                _ = game.completed_at
                _ = game.last_move_at

                session.expunge_all()

            return game

    def get_active_games(self, telegram_id: int) -> list:
        """
        Получение всех активных игр пользователя (ожидание или в процессе)

        Args:
            telegram_id: ID пользователя в Telegram

        Returns:
            list: Список активных игр
        """
        with self.get_session() as session:
            # Получаем игрового пользователя
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()

            if not game_user:
                return []

            # Ищем все активные игры
            games = session.query(Game).filter(
                ((Game.player1_id == game_user.id) | (Game.player2_id == game_user.id)),
                Game.status.in_([GameStatus.WAITING, GameStatus.IN_PROGRESS])
            ).order_by(Game.created_at.desc()).all()

            # Загружаем все атрибуты для каждой игры
            for game in games:
                _ = game.id
                _ = game.player1_id
                _ = game.player2_id
                _ = game.field_id
                _ = game.status
                _ = game.current_player_id
                _ = game.winner_id
                _ = game.created_at
                _ = game.started_at
                _ = game.completed_at
                _ = game.last_move_at

            session.expunge_all()
            return games

    def get_game_user_by_id(self, game_user_id: int) -> GameUser:
        """
        Получение игрового пользователя по внутреннему ID

        Args:
            game_user_id: Внутренний ID игрового пользователя

        Returns:
            GameUser: Объект игрового пользователя или None
        """
        with self.get_session() as session:
            game_user = session.query(GameUser).filter_by(id=game_user_id).first()

            if game_user:
                # Загружаем все атрибуты
                _ = game_user.id
                _ = game_user.telegram_id
                _ = game_user.username
                _ = game_user.balance
                _ = game_user.wins
                _ = game_user.losses
                _ = game_user.created_at
                _ = game_user.updated_at

                session.expunge_all()

            return game_user

    def transfer_money(self, from_telegram_id: int, to_telegram_id: int, amount: float) -> tuple:
        """
        Перевод денег от одного пользователя другому

        Args:
            from_telegram_id: ID отправителя в Telegram
            to_telegram_id: ID получателя в Telegram
            amount: Сумма перевода

        Returns:
            tuple: (success: bool, message: str)
        """
        from decimal import Decimal

        if amount <= 0:
            return False, "Сумма перевода должна быть положительной"

        with self.get_session() as session:
            # Получаем отправителя
            sender = session.query(GameUser).filter_by(telegram_id=from_telegram_id).first()
            if not sender:
                return False, "Ваш профиль не найден"

            # Получаем получателя
            receiver = session.query(GameUser).filter_by(telegram_id=to_telegram_id).first()
            if not receiver:
                return False, "Получатель не найден"

            # Проверяем что это не один и тот же человек
            if sender.id == receiver.id:
                return False, "Нельзя переводить деньги самому себе"

            # Проверяем баланс отправителя
            if sender.balance < Decimal(str(amount)):
                return False, f"Недостаточно средств. Ваш баланс: {format_coins(sender.balance)}"

            # Выполняем перевод
            sender.balance -= Decimal(str(amount))
            receiver.balance += Decimal(str(amount))

            session.flush()

            message = f"✅ Перевод выполнен!\nВы перевели {format_coins(amount)} пользователю {receiver.name}\nВаш новый баланс: {format_coins(sender.balance)}"
            return True, message
