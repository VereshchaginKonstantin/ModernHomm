#!/usr/bin/env python3
"""
Репозиторий для работы с базой данных
"""

import os
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, User, Message, GameUser, UserUnit


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

    def save_user(self, telegram_id: int, username: str = None,
                  first_name: str = None, last_name: str = None) -> User:
        """
        Сохранение или обновление информации о пользователе

        Args:
            telegram_id: ID пользователя в Telegram
            username: Имя пользователя (username)
            first_name: Имя
            last_name: Фамилия

        Returns:
            User: Объект пользователя
        """
        with self.get_session() as session:
            user = session.query(User).filter_by(telegram_id=telegram_id).first()

            if user:
                # Обновляем существующего пользователя
                user.username = username
                user.first_name = first_name
                user.last_name = last_name
                user.last_seen = datetime.utcnow()
            else:
                # Создаем нового пользователя
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                session.add(user)

            session.flush()
            session.refresh(user)
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
                _ = user.first_name
                _ = user.last_name
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
                _ = user.first_name
                _ = user.last_name
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

    # ===== CRUD методы для GameUser =====

    def create_game_user(self, telegram_id: int, name: str, initial_balance: float = 1000) -> GameUser:
        """
        Создание нового игрового пользователя

        Args:
            telegram_id: ID пользователя в Telegram
            name: Имя игрока
            initial_balance: Начальный баланс (по умолчанию 1000)

        Returns:
            GameUser: Объект игрового пользователя
        """
        with self.get_session() as session:
            game_user = GameUser(
                telegram_id=telegram_id,
                name=name,
                balance=initial_balance
            )
            session.add(game_user)
            session.flush()
            session.refresh(game_user)

            # Загружаем все атрибуты
            _ = game_user.id
            _ = game_user.telegram_id
            _ = game_user.name
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
                _ = game_user.name
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
            _ = game_user.name
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

    def get_or_create_game_user(self, telegram_id: int, name: str, initial_balance: float = 1000) -> tuple:
        """
        Получение или создание игрового пользователя

        Args:
            telegram_id: ID пользователя в Telegram
            name: Имя игрока
            initial_balance: Начальный баланс (по умолчанию 1000)

        Returns:
            tuple: (GameUser, created) - объект и флаг создания нового пользователя
        """
        game_user = self.get_game_user(telegram_id)

        if game_user:
            return game_user, False

        game_user = self.create_game_user(telegram_id, name, initial_balance)
        return game_user, True

    # ===== CRUD методы для UserUnit =====

    def add_unit(self, telegram_id: int, unit_type_id: int, count: int = 1) -> UserUnit:
        """
        Добавление юнитов пользователю

        Args:
            telegram_id: ID пользователя в Telegram
            unit_type_id: ID типа юнита
            count: Количество юнитов для добавления

        Returns:
            UserUnit: Объект юнита пользователя
        """
        with self.get_session() as session:
            # Получаем игрового пользователя
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()

            if not game_user:
                raise ValueError(f"Игровой пользователь с telegram_id={telegram_id} не найден")

            # Проверяем, есть ли уже такой юнит
            user_unit = session.query(UserUnit).filter_by(
                game_user_id=game_user.id,
                unit_type_id=unit_type_id
            ).first()

            if user_unit:
                # Увеличиваем количество существующих юнитов
                user_unit.count += count
            else:
                # Создаем новую запись
                user_unit = UserUnit(
                    game_user_id=game_user.id,
                    unit_type_id=unit_type_id,
                    count=count
                )
                session.add(user_unit)

            session.flush()
            session.refresh(user_unit)

            # Загружаем все атрибуты
            _ = user_unit.id
            _ = user_unit.game_user_id
            _ = user_unit.unit_type_id
            _ = user_unit.count

            session.expunge_all()
            return user_unit

    def get_user_units(self, telegram_id: int) -> list:
        """
        Получение всех юнитов пользователя

        Args:
            telegram_id: ID пользователя в Telegram

        Returns:
            list: Список юнитов пользователя
        """
        with self.get_session() as session:
            # Получаем игрового пользователя
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()

            if not game_user:
                return []

            # Получаем все юниты пользователя
            units = session.query(UserUnit).filter_by(game_user_id=game_user.id).all()

            # Загружаем все атрибуты
            for unit in units:
                _ = unit.id
                _ = unit.game_user_id
                _ = unit.unit_type_id
                _ = unit.count

            session.expunge_all()
            return units

    def update_unit_count(self, telegram_id: int, unit_type_id: int, count: int) -> UserUnit:
        """
        Обновление количества юнитов

        Args:
            telegram_id: ID пользователя в Telegram
            unit_type_id: ID типа юнита
            count: Новое количество юнитов

        Returns:
            UserUnit: Обновленный объект юнита
        """
        with self.get_session() as session:
            # Получаем игрового пользователя
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()

            if not game_user:
                raise ValueError(f"Игровой пользователь с telegram_id={telegram_id} не найден")

            # Получаем юнит
            user_unit = session.query(UserUnit).filter_by(
                game_user_id=game_user.id,
                unit_type_id=unit_type_id
            ).first()

            if not user_unit:
                raise ValueError(f"Юнит с unit_type_id={unit_type_id} не найден")

            user_unit.count = count
            session.flush()
            session.refresh(user_unit)

            # Загружаем все атрибуты
            _ = user_unit.id
            _ = user_unit.game_user_id
            _ = user_unit.unit_type_id
            _ = user_unit.count

            session.expunge_all()
            return user_unit

    def remove_unit(self, telegram_id: int, unit_type_id: int, count: int = None) -> bool:
        """
        Удаление юнитов пользователя

        Args:
            telegram_id: ID пользователя в Telegram
            unit_type_id: ID типа юнита
            count: Количество юнитов для удаления (если None, удаляет всех)

        Returns:
            bool: True если юниты были удалены, False если не найдены
        """
        with self.get_session() as session:
            # Получаем игрового пользователя
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()

            if not game_user:
                return False

            # Получаем юнит
            user_unit = session.query(UserUnit).filter_by(
                game_user_id=game_user.id,
                unit_type_id=unit_type_id
            ).first()

            if not user_unit:
                return False

            if count is None:
                # Удаляем всех юнитов этого типа
                session.delete(user_unit)
            else:
                # Уменьшаем количество
                user_unit.count -= count
                if user_unit.count <= 0:
                    session.delete(user_unit)

            return True
