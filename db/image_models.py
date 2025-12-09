#!/usr/bin/env python3
"""
Модели для управления изображениями, сеттингами (рассами) и уровнями юнитов
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Numeric, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from db.models import Base


class UnitLevel(Base):
    """Модель уровня юнита (от 1 до 7)"""
    __tablename__ = 'unit_levels'

    id = Column(Integer, primary_key=True, autoincrement=True)
    level = Column(Integer, nullable=False, unique=True)  # Номер уровня (1-7)
    name = Column(String(255), nullable=False)  # Название уровня (например "Уровень 1")
    description = Column(Text, nullable=True)  # Описание уровня

    # Диапазоны параметров для этого уровня
    min_damage = Column(Integer, nullable=False, default=1)  # Минимальный урон
    max_damage = Column(Integer, nullable=False, default=10)  # Максимальный урон
    min_defense = Column(Integer, nullable=False, default=1)  # Минимальная защита
    max_defense = Column(Integer, nullable=False, default=10)  # Максимальная защита
    min_health = Column(Integer, nullable=False, default=10)  # Минимальное здоровье
    max_health = Column(Integer, nullable=False, default=100)  # Максимальное здоровье
    min_speed = Column(Integer, nullable=False, default=1)  # Минимальная скорость
    max_speed = Column(Integer, nullable=False, default=5)  # Максимальная скорость
    min_cost = Column(Numeric(12, 2), nullable=False, default=10)  # Минимальная стоимость
    max_cost = Column(Numeric(12, 2), nullable=False, default=100)  # Максимальная стоимость

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связь с изображениями
    images = relationship("UnitImage", back_populates="unit_level")

    def __repr__(self):
        return f"<UnitLevel(id={self.id}, level={self.level}, name={self.name})>"


class Setting(Base):
    """Модель сеттинга (рассы) для изображений"""
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)  # Название сеттинга
    description = Column(Text, nullable=True)  # Описание сеттинга
    is_tournament = Column(Boolean, nullable=False, default=False)  # Турнирный сеттинг
    unlock_cost = Column(Numeric(12, 2), nullable=False, default=0)  # Стоимость открытия сеттинга
    subscription_only = Column(Boolean, nullable=False, default=False)  # Доступен только по подписке
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связь с изображениями
    images = relationship("UnitImage", back_populates="setting", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Setting(id={self.id}, name={self.name}, is_tournament={self.is_tournament})>"


class UnitImage(Base):
    """Модель изображения юнита"""
    __tablename__ = 'unit_images'

    id = Column(Integer, primary_key=True, autoincrement=True)
    description = Column(Text, nullable=True)  # Описание изображения

    # Изображение
    image_data = Column(LargeBinary, nullable=False)  # BYTEA - само изображение

    # Связь с сеттингом
    setting_id = Column(Integer, ForeignKey('settings.id', ondelete='CASCADE'), nullable=False, index=True)

    # Связь с уровнем юнита
    unit_level_id = Column(Integer, ForeignKey('unit_levels.id', ondelete='SET NULL'), nullable=True, index=True)

    # Доступность
    subscription_only = Column(Boolean, nullable=False, default=False)  # Доступно только по подписке

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связи
    setting = relationship("Setting", back_populates="images")
    unit_level = relationship("UnitLevel", back_populates="images")

    def __repr__(self):
        return f"<UnitImage(id={self.id}, setting_id={self.setting_id}, unit_level_id={self.unit_level_id})>"
