#!/usr/bin/env python3
"""
Модели для управления изображениями и сеттингами (рассами)
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Numeric, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from db.models import Base


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

    # Параметры применимости изображения
    is_flying = Column(Boolean, nullable=True)  # Для летающих юнитов (null = применимо к любым)
    is_kamikaze = Column(Boolean, nullable=True)  # Для камикадзе (null = применимо к любым)
    min_damage = Column(Integer, nullable=True)  # Минимальный урон для применимости
    max_damage = Column(Integer, nullable=True)  # Максимальный урон для применимости
    min_defense = Column(Integer, nullable=True)  # Минимальная защита для применимости
    max_defense = Column(Integer, nullable=True)  # Максимальная защита для применимости

    # Изображение
    image_data = Column(LargeBinary, nullable=False)  # BYTEA - само изображение

    # Связь с сеттингом
    setting_id = Column(Integer, ForeignKey('settings.id', ondelete='CASCADE'), nullable=False, index=True)

    # Стоимость и доступность
    coin_cost = Column(Numeric(12, 2), nullable=False, default=0)  # Стоимость в монетах
    subscription_only = Column(Boolean, nullable=False, default=False)  # Доступно только по подписке

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Связь с сеттингом
    setting = relationship("Setting", back_populates="images")

    def __repr__(self):
        return f"<UnitImage(id={self.id}, setting_id={self.setting_id}, coin_cost={self.coin_cost})>"

    def is_applicable_to_unit(self, unit) -> bool:
        """
        Проверяет, применимо ли изображение к данному юниту

        Args:
            unit: Объект юнита (с полями damage, defense, is_flying, is_kamikaze)

        Returns:
            bool: True если изображение применимо к юниту
        """
        # Проверка летающего юнита
        if self.is_flying is not None and unit.is_flying != self.is_flying:
            return False

        # Проверка камикадзе
        if self.is_kamikaze is not None and unit.is_kamikaze != self.is_kamikaze:
            return False

        # Проверка урона
        if self.min_damage is not None and unit.damage < self.min_damage:
            return False
        if self.max_damage is not None and unit.damage > self.max_damage:
            return False

        # Проверка защиты
        if self.min_defense is not None and unit.defense < self.min_defense:
            return False
        if self.max_defense is not None and unit.defense > self.max_defense:
            return False

        return True
