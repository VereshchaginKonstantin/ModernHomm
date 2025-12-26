#!/usr/bin/env python3
"""
Базовые модели: пользователи, сообщения, конфигурация
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, Numeric
from sqlalchemy.orm import relationship

from .base import Base


class User(Base):
    """Модель пользователя Telegram"""
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
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


class Config(Base):
    """Модель конфигурации приложения"""
    __tablename__ = 'config'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(255), nullable=False, unique=True, index=True)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Config(key={self.key}, value={self.value})>"


class ClientLog(Base):
    """Модель для хранения логов клиента Godot"""
    __tablename__ = 'client_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), nullable=False, index=True)  # Идентификатор сессии клиента
    player_id = Column(Integer, nullable=True, index=True)  # ID игрока (если авторизован)
    level = Column(String(20), nullable=False, default='info')  # error, warning, info, debug
    message = Column(Text, nullable=False)
    context = Column(Text, nullable=True)  # JSON с дополнительным контекстом
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    def __repr__(self):
        return f"<ClientLog(id={self.id}, level={self.level}, session={self.session_id})>"


class GameUser(Base):
    """Модель игрового профиля пользователя"""
    __tablename__ = 'game_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)  # username из Telegram (уникальный идентификатор)
    balance = Column(Numeric(12, 2), nullable=False, default=1000)  # Монеты
    crystals = Column(Integer, nullable=False, default=0)  # Кристаллы
    glory = Column(Integer, nullable=False, default=0)  # Слава
    wins = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    password_hash = Column(String(255), nullable=True)  # Хеш пароля для входа в веб-интерфейс
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<GameUser(telegram_id={self.telegram_id}, username={self.username}, balance={self.balance})>"


class JobLog(Base):
    """Модель логов выполнения джоб"""
    __tablename__ = 'job_logs'

    # Статусы
    STATUS_RUNNING = 'running'
    STATUS_SUCCESS = 'success'
    STATUS_FAILED = 'failed'

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default=STATUS_RUNNING)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    records_processed = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    details = Column(Text, nullable=True)  # JSON строка
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<JobLog(id={self.id}, job_name={self.job_name}, status={self.status})>"
