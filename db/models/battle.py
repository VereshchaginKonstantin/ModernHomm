#!/usr/bin/env python3
"""
Модели для боевой системы: игры, юниты в бою, логи, поля
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, Enum, CheckConstraint
from sqlalchemy.orm import relationship
import enum

from .base import Base


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

    # Приоритет в очереди хода (чем больше, тем позже ходит)
    deferred = Column(Integer, nullable=False, default=0)

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
    game_state = Column(Text, nullable=True)  # JSON снимок состояния игры (юниты, позиции, здоровье)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связь
    game = relationship("Game", back_populates="logs")

    def __repr__(self):
        return f"<GameLog(id={self.id}, game_id={self.game_id}, event_type={self.event_type})>"
