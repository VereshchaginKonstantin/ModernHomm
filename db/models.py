#!/usr/bin/env python3
"""
Модели базы данных для Telegram бота
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, BigInteger, ForeignKey, Numeric, Enum, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


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


class GameUser(Base):
    """Модель игрового профиля пользователя"""
    __tablename__ = 'game_users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)  # username пользователя
    username = Column(String(255), unique=True, nullable=True, index=True)  # username из Telegram (уникальный идентификатор, требуется для входа в веб-интерфейс)
    balance = Column(Numeric(12, 2), nullable=False, default=1000)
    wins = Column(Integer, nullable=False, default=0)
    losses = Column(Integer, nullable=False, default=0)
    password_hash = Column(String(255), nullable=True)  # Хеш пароля для входа в веб-интерфейс
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
    icon = Column(String(10), nullable=False, default='🎮')  # Иконка для отображения на поле
    image_path = Column(String(512), nullable=True)  # Путь к изображению юнита
    description = Column(String(1000), nullable=True)  # Описание юнита
    price = Column(Numeric(12, 2), nullable=False)
    damage = Column(Integer, nullable=False)
    defense = Column(Integer, nullable=False, default=0)  # Показатель защиты
    range = Column(Integer, nullable=False)
    health = Column(Integer, nullable=False)
    speed = Column(Integer, nullable=False, default=1)  # Число перемещений за ход
    luck = Column(Numeric(5, 4), nullable=False, default=0)  # Вероятность максимального урона (0-1)
    crit_chance = Column(Numeric(5, 4), nullable=False, default=0)  # Вероятность критического удара (0-1)
    dodge_chance = Column(Numeric(5, 4), nullable=False, default=0)  # Вероятность уклонения от удара (0-1)
    is_kamikaze = Column(Integer, nullable=False, default=0)  # Флаг камикадзе (0 - нет, 1 - да): наносит урон 1 юнитом и уменьшается на 1 после атаки
    is_flying = Column(Integer, nullable=False, default=0)  # Флаг летающий (0 - нет, 1 - да): может двигаться через препятствия
    counterattack_chance = Column(Numeric(5, 4), nullable=False, default=0)  # Доля контратаки (0-1): при получении урона наносит ответный урон с этим коэффициентом
    effective_against_unit_id = Column(Integer, ForeignKey('units.id'), nullable=True)  # Юнит, против которого эффективен (x1.5 урона)
    owner_id = Column(Integer, ForeignKey('game_users.id'), nullable=True)  # Владелец юнита (None - базовый юнит, иначе - пользовательский)

    # Связь с пользовательской иконкой
    custom_icon = relationship("UnitCustomIcon", back_populates="unit", uselist=False)
    # Связь с эффективностью против другого юнита
    effective_against = relationship("Unit", remote_side=[id], uselist=False)
    # Связь с владельцем юнита
    owner = relationship("GameUser", foreign_keys=[owner_id])

    def __repr__(self):
        return f"<Unit(id={self.id}, name={self.name}, price={self.price})>"


class UnitCustomIcon(Base):
    """Модель для хранения пользовательских иконок юнитов"""
    __tablename__ = 'unit_custom_icons'

    id = Column(Integer, primary_key=True, autoincrement=True)
    unit_id = Column(Integer, ForeignKey('units.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    custom_icon = Column(String(10), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связь с юнитом
    unit = relationship("Unit", back_populates="custom_icon")

    def __repr__(self):
        return f"<UnitCustomIcon(unit_id={self.unit_id}, custom_icon={self.custom_icon})>"


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


class GameStatus(enum.Enum):
    """Статусы игры"""
    WAITING = "waiting"  # Ожидание принятия игры
    IN_PROGRESS = "in_progress"  # Игра в процессе
    COMPLETED = "completed"  # Игра завершена


class Field(Base):
    """Модель игрового поля"""
    __tablename__ = 'fields'

    id = Column(Integer, primary_key=True, autoincrement=True)
    width = Column(Integer, nullable=False)  # Ширина поля
    height = Column(Integer, nullable=False)  # Высота поля
    name = Column(String(50), nullable=False, unique=True)  # Например: "5x5", "7x7"

    __table_args__ = (
        CheckConstraint('width > 0 AND height > 0', name='positive_dimensions'),
    )

    def __repr__(self):
        return f"<Field(name={self.name}, width={self.width}, height={self.height})>"


class Game(Base):
    """Модель начатой игры"""
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True, autoincrement=True)
    player1_id = Column(Integer, ForeignKey('game_users.id', ondelete='CASCADE'), nullable=False, index=True)
    player2_id = Column(Integer, ForeignKey('game_users.id', ondelete='CASCADE'), nullable=False, index=True)
    field_id = Column(Integer, ForeignKey('fields.id', ondelete='CASCADE'), nullable=False)
    status = Column(Enum(GameStatus, values_callable=lambda obj: [e.value for e in obj], name='game_status', create_type=False), nullable=False, default=GameStatus.WAITING)
    current_player_id = Column(Integer, ForeignKey('game_users.id'), nullable=True)  # Чей сейчас ход
    winner_id = Column(Integer, ForeignKey('game_users.id'), nullable=True)  # Победитель
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)  # Когда игра была принята
    completed_at = Column(DateTime, nullable=True)  # Когда игра завершилась
    last_move_at = Column(DateTime, nullable=True)  # Время последнего хода

    # Связи
    player1 = relationship("GameUser", foreign_keys=[player1_id])
    player2 = relationship("GameUser", foreign_keys=[player2_id])
    field = relationship("Field")
    current_player = relationship("GameUser", foreign_keys=[current_player_id])
    winner = relationship("GameUser", foreign_keys=[winner_id])
    battle_units = relationship("BattleUnit", back_populates="game", cascade="all, delete-orphan")
    obstacles = relationship("Obstacle", back_populates="game", cascade="all, delete-orphan")
    logs = relationship("GameLog", back_populates="game", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Game(id={self.id}, status={self.status.value}, player1_id={self.player1_id}, player2_id={self.player2_id})>"


class BattleUnit(Base):
    """Модель юнита в бою"""
    __tablename__ = 'battle_units'

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey('games.id', ondelete='CASCADE'), nullable=False, index=True)
    user_unit_id = Column(Integer, ForeignKey('user_units.id', ondelete='CASCADE'), nullable=False)
    player_id = Column(Integer, ForeignKey('game_users.id', ondelete='CASCADE'), nullable=False, index=True)

    # Позиция на поле
    position_x = Column(Integer, nullable=False)
    position_y = Column(Integer, nullable=False)

    # Боевые характеристики
    total_count = Column(Integer, nullable=False)  # Общее количество юнитов в группе
    remaining_hp = Column(Integer, nullable=False)  # Оставшиеся жизни у текущего юнита
    morale = Column(Numeric(10, 2), nullable=False, default=0)  # Кураж
    fatigue = Column(Numeric(10, 2), nullable=False, default=0)  # Усталость

    # Флаг, был ли уже ход у этого юнита в текущем раунде
    has_moved = Column(Integer, nullable=False, default=0)  # 0 - нет, 1 - да

    # Связи
    game = relationship("Game", back_populates="battle_units")
    user_unit = relationship("UserUnit")
    player = relationship("GameUser")

    __table_args__ = (
        CheckConstraint('position_x >= 0', name='positive_x'),
        CheckConstraint('position_y >= 0', name='positive_y'),
        CheckConstraint('total_count >= 0', name='positive_count'),
        CheckConstraint('remaining_hp >= 0', name='non_negative_hp'),
    )

    def __repr__(self):
        return f"<BattleUnit(id={self.id}, game_id={self.game_id}, position=({self.position_x}, {self.position_y}), total_count={self.total_count})>"


class Obstacle(Base):
    """Модель препятствия на игровом поле"""
    __tablename__ = 'obstacles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey('games.id', ondelete='CASCADE'), nullable=False, index=True)
    position_x = Column(Integer, nullable=False)
    position_y = Column(Integer, nullable=False)

    # Связи
    game = relationship("Game", back_populates="obstacles")

    __table_args__ = (
        CheckConstraint('position_x >= 0', name='obstacle_positive_x'),
        CheckConstraint('position_y >= 0', name='obstacle_positive_y'),
    )

    def __repr__(self):
        return f"<Obstacle(id={self.id}, game_id={self.game_id}, position=({self.position_x}, {self.position_y}))>"


class GameLog(Base):
    """Модель для хранения лога событий игры"""
    __tablename__ = 'game_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(Integer, ForeignKey('games.id', ondelete='CASCADE'), nullable=False, index=True)
    event_type = Column(String(50), nullable=False)  # Тип события: move, attack, damage, dodge, crit, end_turn, game_start, game_end
    message = Column(Text, nullable=False)  # Текст события для отображения
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связь
    game = relationship("Game", back_populates="logs")

    def __repr__(self):
        return f"<GameLog(id={self.id}, game_id={self.game_id}, event_type={self.event_type})>"
