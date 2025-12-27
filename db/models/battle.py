#!/usr/bin/env python3
"""
Модели для боевой системы: игры, юниты в бою, логи, поля
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, Enum, CheckConstraint, Boolean, LargeBinary
from sqlalchemy.orm import relationship
import enum

from .base import Base


class DecorationType(enum.Enum):
    """Типы декоративных элементов"""
    TREE = "tree"
    RIVER = "river"
    ROCK = "rock"
    BUSH = "bush"
    FLOWER = "flower"
    CUSTOM = "custom"


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


class BattleFieldTemplate(Base):
    """Модель шаблона боевого поля (предустановленные поля)"""
    __tablename__ = 'battle_field_templates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)  # Название поля
    description = Column(Text, nullable=True)  # Описание поля
    field_size_id = Column(Integer, ForeignKey('fields.id', ondelete='RESTRICT'), nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)  # Активно ли поле для выбора
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связи
    field_size = relationship("Field")
    obstacles = relationship("BattleFieldObstacle", back_populates="template", cascade="all, delete-orphan")
    decorations = relationship("BattleFieldDecoration", back_populates="template", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BattleFieldTemplate(id={self.id}, name={self.name}, field_size_id={self.field_size_id})>"


class BattleFieldObstacle(Base):
    """Модель препятствия на шаблоне поля"""
    __tablename__ = 'battle_field_obstacles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey('battle_field_templates.id', ondelete='CASCADE'), nullable=False, index=True)
    position_x = Column(Integer, nullable=False)  # Позиция X внутри поля
    position_y = Column(Integer, nullable=False)  # Позиция Y внутри поля
    sprite_data = Column(LargeBinary, nullable=True)  # Спрайт препятствия
    sprite_mime_type = Column(String(50), nullable=True)  # MIME тип спрайта
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связи
    template = relationship("BattleFieldTemplate", back_populates="obstacles")

    __table_args__ = (
        CheckConstraint('position_x >= 0', name='positive_obstacle_pos_x'),
        CheckConstraint('position_y >= 0', name='positive_obstacle_pos_y'),
    )

    def __repr__(self):
        return f"<BattleFieldObstacle(id={self.id}, template_id={self.template_id}, position=({self.position_x}, {self.position_y}))>"


class BattleFieldDecoration(Base):
    """Модель декоративного элемента вокруг поля"""
    __tablename__ = 'battle_field_decorations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(Integer, ForeignKey('battle_field_templates.id', ondelete='CASCADE'), nullable=False, index=True)
    decoration_type = Column(Enum(DecorationType, values_callable=lambda obj: [e.value for e in obj], name='decoration_type', create_type=False), nullable=False, default=DecorationType.TREE)
    position_x = Column(Integer, nullable=False)  # Позиция X (может быть отрицательной)
    position_y = Column(Integer, nullable=False)  # Позиция Y (может быть отрицательной)
    sprite_data = Column(LargeBinary, nullable=True)  # Спрайт декорации
    sprite_mime_type = Column(String(50), nullable=True)  # MIME тип спрайта
    z_index = Column(Integer, nullable=False, default=0)  # Порядок отрисовки
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связи
    template = relationship("BattleFieldTemplate", back_populates="decorations")

    def __repr__(self):
        return f"<BattleFieldDecoration(id={self.id}, template_id={self.template_id}, type={self.decoration_type}, position=({self.position_x}, {self.position_y}))>"


class Game(Base):
    """Модель начатой игры"""
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True, autoincrement=True)
    player1_id = Column(Integer, ForeignKey('game_users.id', ondelete='CASCADE'), nullable=False, index=True)
    player2_id = Column(Integer, ForeignKey('game_users.id', ondelete='CASCADE'), nullable=False, index=True)
    player1_army_id = Column(Integer, ForeignKey('armies.id', ondelete='SET NULL'), nullable=True)  # Армия игрока 1
    player2_army_id = Column(Integer, ForeignKey('armies.id', ondelete='SET NULL'), nullable=True)  # Армия игрока 2
    field_id = Column(Integer, ForeignKey('fields.id', ondelete='CASCADE'), nullable=False)
    battle_field_template_id = Column(Integer, ForeignKey('battle_field_templates.id', ondelete='SET NULL'), nullable=True)  # Шаблон поля
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
    player1_army = relationship("Army", foreign_keys=[player1_army_id])
    player2_army = relationship("Army", foreign_keys=[player2_army_id])
    field = relationship("Field")
    battle_field_template = relationship("BattleFieldTemplate")
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
    army_unit_id = Column(Integer, ForeignKey('army_units.id', ondelete='CASCADE'), nullable=False)  # Ссылка на юнита из армии
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

    # Эффект отравления (применяется при атаке юнитом с poison_damage > 0)
    poison_remaining_turns = Column(Integer, nullable=False, default=0)  # Оставшееся количество ходов отравления
    poison_damage_per_turn = Column(Integer, nullable=False, default=0)  # Урон от яда за ход

    # Связи
    game = relationship("Game", back_populates="battle_units")
    army_unit = relationship("ArmyUnit")  # Связь с юнитом из армии
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
