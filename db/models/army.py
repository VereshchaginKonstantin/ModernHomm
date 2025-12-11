#!/usr/bin/env python3
"""
Модели для армии, юнитов и рас
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, CheckConstraint, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship

from .base import Base


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


class GameRace(Base):
    """Модель игровой расы (набор юнитов для игры)"""
    __tablename__ = 'game_races'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    is_free = Column(Boolean, nullable=False, default=False)  # Бесплатная раса
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связи
    race_units = relationship("RaceUnit", back_populates="race", cascade="all, delete-orphan")
    unit_levels = relationship("UnitLevel", back_populates="race", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<GameRace(id={self.id}, name={self.name}, is_free={self.is_free})>"


class RaceUnit(Base):
    """Модель юнита расы (7 юнитов по уровням для каждой расы)"""
    __tablename__ = 'race_units'

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_id = Column(Integer, ForeignKey('game_races.id', ondelete='CASCADE'), nullable=False, index=True)
    level = Column(Integer, nullable=False)  # Уровень юнита (1-7)
    name = Column(String(255), nullable=False)
    icon = Column(String(10), nullable=False, default='🎮')
    image_path = Column(String(512), nullable=True)
    is_flying = Column(Boolean, nullable=False, default=False)  # Летающий юнит
    is_kamikaze = Column(Boolean, nullable=False, default=False)  # Камикадзе
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связи
    race = relationship("GameRace", back_populates="race_units")
    skins = relationship("RaceUnitSkin", back_populates="race_unit", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint('level >= 1 AND level <= 7', name='race_unit_level_range'),
    )

    def __repr__(self):
        return f"<RaceUnit(id={self.id}, race_id={self.race_id}, level={self.level}, name={self.name})>"


class RaceUnitSkin(Base):
    """Модель скина юнита расы (внешний вид для юнита определённого уровня)"""
    __tablename__ = 'race_unit_skins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_unit_id = Column(Integer, ForeignKey('race_units.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # Название скина
    icon = Column(String(10), nullable=False, default='🎮')  # Иконка скина
    image_path = Column(String(512), nullable=True)  # Путь к изображению скина
    description = Column(Text, nullable=True)  # Описание скина
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связь
    race_unit = relationship("RaceUnit", back_populates="skins")

    def __repr__(self):
        return f"<RaceUnitSkin(id={self.id}, race_unit_id={self.race_unit_id}, name={self.name})>"


class UnitLevel(Base):
    """Модель уровня юнита (стоимость по уровням)"""
    __tablename__ = 'unit_levels'

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_id = Column(Integer, ForeignKey('game_races.id', ondelete='CASCADE'), nullable=False, index=True)
    level = Column(Integer, nullable=False)  # Уровень (1-7)
    cost = Column(Numeric(10, 2), nullable=False, default=100)  # Стоимость юнита этого уровня
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связь
    race = relationship("GameRace", back_populates="unit_levels")

    __table_args__ = (
        CheckConstraint('level >= 1 AND level <= 7', name='unit_level_range'),
    )

    def __repr__(self):
        return f"<UnitLevel(id={self.id}, race_id={self.race_id}, level={self.level}, cost={self.cost})>"


class UserRace(Base):
    """Модель пользовательской расы (связь пользователя с расой)"""
    __tablename__ = 'user_races'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('game_users.id', ondelete='CASCADE'), nullable=False, index=True)
    race_id = Column(Integer, ForeignKey('game_races.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связи
    user = relationship("GameUser")
    race = relationship("GameRace")
    armies = relationship("Army", back_populates="user_race", cascade="all, delete-orphan")
    user_race_units = relationship("UserRaceUnit", back_populates="user_race", cascade="all, delete-orphan")

    __table_args__ = (
        # Уникальность пользователь + раса
        {'extend_existing': True},
    )

    def __repr__(self):
        return f"<UserRace(id={self.id}, user_id={self.user_id}, race_id={self.race_id})>"


class UserRaceUnit(Base):
    """Модель пользовательского юнита расы (с боевыми характеристиками)"""
    __tablename__ = 'user_race_units'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_race_id = Column(Integer, ForeignKey('user_races.id', ondelete='CASCADE'), nullable=False, index=True)
    race_unit_id = Column(Integer, ForeignKey('race_units.id', ondelete='CASCADE'), nullable=False, index=True)
    skin_id = Column(Integer, ForeignKey('race_unit_skins.id', ondelete='RESTRICT'), nullable=False, index=True)  # Обязательная ссылка на скин

    # Боевые характеристики (наследуются от RaceUnit, но хранятся у пользователя)
    attack = Column(Integer, nullable=False, default=10)
    defense = Column(Integer, nullable=False, default=5)
    min_damage = Column(Integer, nullable=False, default=1)
    max_damage = Column(Integer, nullable=False, default=3)
    health = Column(Integer, nullable=False, default=10)
    speed = Column(Integer, nullable=False, default=4)
    initiative = Column(Integer, nullable=False, default=10)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связи
    user_race = relationship("UserRace", back_populates="user_race_units")
    race_unit = relationship("RaceUnit")
    skin = relationship("RaceUnitSkin")

    # Уникальность: один юнит расы на пользовательскую расу (один юнит на уровень)
    __table_args__ = (
        UniqueConstraint('user_race_id', 'race_unit_id', name='unique_user_race_unit'),
    )

    def __repr__(self):
        return f"<UserRaceUnit(id={self.id}, user_race_id={self.user_race_id}, race_unit_id={self.race_unit_id}, skin_id={self.skin_id})>"


class Army(Base):
    """Модель армии"""
    __tablename__ = 'armies'

    # Константы типов армий
    TYPE_RATED = "rated"  # Рейтинговая (приглашение юнитов)
    TYPE_MERCENARY = "mercenary"  # Наёмная (покупка юнитов)

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_race_id = Column(Integer, ForeignKey('user_races.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    army_type = Column(String(20), nullable=False, default=TYPE_MERCENARY)  # rated или mercenary
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связи
    user_race = relationship("UserRace", back_populates="armies")
    army_units = relationship("ArmyUnit", back_populates="army", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Army(id={self.id}, name={self.name}, army_type={self.army_type})>"


class ArmyUnit(Base):
    """Модель юнита в армии"""
    __tablename__ = 'army_units'

    id = Column(Integer, primary_key=True, autoincrement=True)
    army_id = Column(Integer, ForeignKey('armies.id', ondelete='CASCADE'), nullable=False, index=True)
    race_unit_id = Column(Integer, ForeignKey('race_units.id', ondelete='CASCADE'), nullable=False, index=True)
    unit_level_id = Column(Integer, ForeignKey('unit_levels.id', ondelete='SET NULL'), nullable=True)
    count = Column(Integer, nullable=False, default=1)  # Количество юнитов в стеке
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связи
    army = relationship("Army", back_populates="army_units")
    race_unit = relationship("RaceUnit")
    unit_level = relationship("UnitLevel")

    def __repr__(self):
        return f"<ArmyUnit(id={self.id}, army_id={self.army_id}, count={self.count})>"
