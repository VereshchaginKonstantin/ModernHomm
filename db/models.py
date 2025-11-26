#!/usr/bin/env python3
"""
Модели базы данных для Telegram бота
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

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


class GameUser(Base):
    """Модель игрового профиля пользователя"""
    __tablename__ = 'game_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    balance = Column(Numeric(12, 2), nullable=False, default=1000)
    wins = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связь с юнитами
    units = relationship("UserUnit", back_populates="game_user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GameUser(telegram_id={self.telegram_id}, name={self.name}, balance={self.balance})>"


class Unit(Base):
    """Модель типа юнита (базовый справочник юнитов)"""
    __tablename__ = 'units'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    price = Column(Numeric(12, 2), nullable=False)
    damage = Column(Integer, nullable=False)
    defense = Column(Integer, nullable=False, default=0)  # Показатель защиты
    range = Column(Integer, nullable=False)
    health = Column(Integer, nullable=False)
    speed = Column(Integer, nullable=False, default=1)  # Число перемещений за ход
    luck = Column(Numeric(5, 4), nullable=False, default=0)  # Вероятность максимального урона (0-1)
    crit_chance = Column(Numeric(5, 4), nullable=False, default=0)  # Вероятность критического удара (0-1)

    def __repr__(self):
        return f"<Unit(id={self.id}, name={self.name}, price={self.price})>"


class UserUnit(Base):
    """Модель юнитов пользователя"""
    __tablename__ = 'user_units'

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_user_id = Column(Integer, ForeignKey('game_users.id', ondelete='CASCADE'), nullable=False, index=True)
    unit_type_id = Column(Integer, ForeignKey('units.id', ondelete='CASCADE'), nullable=False, index=True)
    count = Column(Integer, nullable=False, default=0)

    # Связь с игровым пользователем
    game_user = relationship("GameUser", back_populates="units")
    # Связь с типом юнита
    unit = relationship("Unit")

    def __repr__(self):
        return f"<UserUnit(game_user_id={self.game_user_id}, unit_type_id={self.unit_type_id}, count={self.count})>"
