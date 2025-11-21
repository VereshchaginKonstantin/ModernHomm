#!/usr/bin/env python3
"""
Модели базы данных и функции для работы с PostgreSQL
"""

import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

Base = declarative_base()


class User(Base):
    """Модель пользователя Telegram"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class Message(Base):
    """Модель сообщения от пользователя"""
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_user_id = Column(BigInteger, nullable=False, index=True)
    message_text = Column(Text, nullable=False)
    message_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    username = Column(String(255), nullable=True)

    def __repr__(self):
        return f"<Message(id={self.id}, telegram_user_id={self.telegram_user_id})>"


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
