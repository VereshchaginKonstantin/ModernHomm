#!/usr/bin/env python3
"""
Модели для армии, юнитов и рас
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, CheckConstraint, Boolean, UniqueConstraint, LargeBinary
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
    regeneration_health = Column(Integer, nullable=False, default=0)  # Здоровье, восстанавливаемое в начале хода
    poison_damage = Column(Integer, nullable=False, default=0)  # Урон от яда за ход
    poison_turns = Column(Integer, nullable=False, default=0)  # Количество ходов действия яда при атаке
    poison_immunity = Column(Integer, nullable=False, default=0)  # Иммунитет к яду (0 - нет, 1 - да)
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

    def __repr__(self):
        return f"<GameRace(id={self.id}, name={self.name}, is_free={self.is_free})>"


class RaceUnit(Base):
    """Модель юнита расы (7 юнитов по уровням для каждой расы)"""
    __tablename__ = 'race_units'

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_id = Column(Integer, ForeignKey('game_races.id', ondelete='CASCADE'), nullable=False, index=True)
    unit_level_id = Column(Integer, ForeignKey('unit_levels.id', ondelete='RESTRICT'), nullable=False, index=True)  # Ссылка на уровень юнита (обязательно)
    name = Column(String(255), nullable=False)
    is_flying = Column(Boolean, nullable=False, default=False)  # Летающий юнит
    is_kamikaze = Column(Boolean, nullable=False, default=False)  # Камикадзе

    # Боевые характеристики (перенесены из UserRaceUnit)
    attack = Column(Integer, nullable=False, default=10)  # Атака
    defense = Column(Integer, nullable=False, default=5)  # Защита
    min_damage = Column(Integer, nullable=False, default=1)  # Минимальный урон
    max_damage = Column(Integer, nullable=False, default=3)  # Максимальный урон
    health = Column(Integer, nullable=False, default=10)  # Здоровье
    speed = Column(Integer, nullable=False, default=4)  # Скорость
    initiative = Column(Integer, nullable=False, default=10)  # Инициатива
    luck = Column(Numeric(5, 4), nullable=False, default=0)  # Удача (0-1)
    crit_chance = Column(Numeric(5, 4), nullable=False, default=0)  # Шанс крита (0-1)
    dodge_chance = Column(Numeric(5, 4), nullable=False, default=0)  # Шанс уклонения (0-1)
    counterattack_chance = Column(Numeric(5, 4), nullable=False, default=0)  # Шанс контратаки (0-1)
    range = Column(Integer, nullable=False, default=1)  # Дальность атаки

    # Регенерация и отравление
    regeneration_health = Column(Integer, nullable=False, default=0)  # Здоровье, восстанавливаемое в начале хода
    poison_damage = Column(Integer, nullable=False, default=0)  # Урон от яда за ход
    poison_turns = Column(Integer, nullable=False, default=0)  # Количество ходов действия яда
    poison_immunity = Column(Boolean, nullable=False, default=False)  # Иммунитет к отравлению

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Уникальность: один уровень на расу (не может быть двух юнитов одного уровня в расе)
    __table_args__ = (
        UniqueConstraint('race_id', 'unit_level_id', name='unique_race_unit_level'),
    )

    # Связи
    race = relationship("GameRace", back_populates="race_units")
    unit_level = relationship("UnitLevel")
    skins = relationship("RaceUnitSkin", back_populates="race_unit", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RaceUnit(id={self.id}, race_id={self.race_id}, unit_level_id={self.unit_level_id}, name={self.name})>"


class RaceUnitSkin(Base):
    """Модель скина уровня расы (внешний вид для юнита определённого уровня)"""
    __tablename__ = 'race_unit_skins'

    id = Column(Integer, primary_key=True, autoincrement=True)
    race_unit_id = Column(Integer, ForeignKey('race_units.id', ondelete='CASCADE'), nullable=False, index=True)
    name = Column(String(255), nullable=False)  # Название скина
    image_data = Column(LargeBinary, nullable=True)  # Бинарные данные изображения
    image_mime_type = Column(String(50), nullable=True)  # MIME тип изображения (image/png, image/jpeg)
    description = Column(Text, nullable=True)  # Описание скина
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Связь
    race_unit = relationship("RaceUnit", back_populates="skins")

    def __repr__(self):
        return f"<RaceUnitSkin(id={self.id}, race_unit_id={self.race_unit_id}, name={self.name})>"


class UnitLevel(Base):
    """Модель уровня юнита (справочник уровней с диапазоном престижа)"""
    __tablename__ = 'unit_levels'

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(Integer, nullable=False, unique=True)  # Уровень (1-7)
    icon = Column(String(10), nullable=False, default='🎮')  # Иконка уровня
    prestige_min = Column(Integer, nullable=False, default=0)  # Минимальный престиж для найма
    prestige_max = Column(Integer, nullable=False, default=100)  # Максимальный престиж для найма
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        CheckConstraint('level >= 1 AND level <= 7', name='unit_level_range'),
    )

    def __repr__(self):
        return f"<UnitLevel(id={self.id}, level={self.level}, icon={self.icon}, prestige_min={self.prestige_min}, prestige_max={self.prestige_max})>"


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
    user_race_units = relationship("UserRaceUnit", back_populates="user_race", cascade="all, delete-orphan")

    __table_args__ = (
        # Уникальность пользователь + раса
        {'extend_existing': True},
    )

    def __repr__(self):
        return f"<UserRace(id={self.id}, user_id={self.user_id}, race_id={self.race_id})>"


class UserRaceUnit(Base):
    """Модель пользовательского юнита расы (бусты к базовым характеристикам из RaceUnit)"""
    __tablename__ = 'user_race_units'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_race_id = Column(Integer, ForeignKey('user_races.id', ondelete='CASCADE'), nullable=False, index=True)
    race_unit_id = Column(Integer, ForeignKey('race_units.id', ondelete='CASCADE'), nullable=False, index=True)
    skin_id = Column(Integer, ForeignKey('race_unit_skins.id', ondelete='RESTRICT'), nullable=False, index=True)  # Обязательная ссылка на скин

    # Бусты (увеличения) характеристик относительно базовых значений из RaceUnit
    attack_boost = Column(Integer, nullable=False, default=0)  # Буст атаки
    defense_boost = Column(Integer, nullable=False, default=0)  # Буст защиты
    min_damage_boost = Column(Integer, nullable=False, default=0)  # Буст минимального урона
    max_damage_boost = Column(Integer, nullable=False, default=0)  # Буст максимального урона
    health_boost = Column(Integer, nullable=False, default=0)  # Буст здоровья
    speed_boost = Column(Integer, nullable=False, default=0)  # Буст скорости
    initiative_boost = Column(Integer, nullable=False, default=0)  # Буст инициативы
    luck_boost = Column(Numeric(5, 4), nullable=False, default=0)  # Буст удачи
    crit_chance_boost = Column(Numeric(5, 4), nullable=False, default=0)  # Буст шанса крита
    dodge_chance_boost = Column(Numeric(5, 4), nullable=False, default=0)  # Буст шанса уклонения
    counterattack_chance_boost = Column(Numeric(5, 4), nullable=False, default=0)  # Буст шанса контратаки
    range_boost = Column(Integer, nullable=False, default=0)  # Буст дальности
    regeneration_health_boost = Column(Integer, nullable=False, default=0)  # Буст регенерации
    poison_damage_boost = Column(Integer, nullable=False, default=0)  # Буст урона яда
    poison_turns_boost = Column(Integer, nullable=False, default=0)  # Буст ходов яда

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

    # Вычисляемые свойства для получения итоговых характеристик (база + буст)
    @property
    def attack(self):
        return self.race_unit.attack + self.attack_boost

    @property
    def defense(self):
        return self.race_unit.defense + self.defense_boost

    @property
    def min_damage(self):
        return self.race_unit.min_damage + self.min_damage_boost

    @property
    def max_damage(self):
        return self.race_unit.max_damage + self.max_damage_boost

    @property
    def health(self):
        return self.race_unit.health + self.health_boost

    @property
    def speed(self):
        return self.race_unit.speed + self.speed_boost

    @property
    def initiative(self):
        return self.race_unit.initiative + self.initiative_boost

    @property
    def luck(self):
        return float(self.race_unit.luck) + float(self.luck_boost)

    @property
    def crit_chance(self):
        return float(self.race_unit.crit_chance) + float(self.crit_chance_boost)

    @property
    def dodge_chance(self):
        return float(self.race_unit.dodge_chance) + float(self.dodge_chance_boost)

    @property
    def counterattack_chance(self):
        return float(self.race_unit.counterattack_chance) + float(self.counterattack_chance_boost)

    @property
    def range(self):
        return self.race_unit.range + self.range_boost

    @property
    def regeneration_health(self):
        return self.race_unit.regeneration_health + self.regeneration_health_boost

    @property
    def poison_damage(self):
        return self.race_unit.poison_damage + self.poison_damage_boost

    @property
    def poison_turns(self):
        return self.race_unit.poison_turns + self.poison_turns_boost

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
    user_race = relationship("UserRace")
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
