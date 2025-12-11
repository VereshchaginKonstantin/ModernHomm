#!/usr/bin/env python3
"""
Модуль для работы с базой данных Telegram бота

Содержит модели данных и репозиторий для работы с PostgreSQL

Модели разделены на категории:
- core: базовые модели (User, Message, Config, GameUser)
- battle: модели боевой системы (Game, BattleUnit, GameLog, Field, Obstacle)
- army: модели армии и юнитов (Unit, UserUnit, GameRace, RaceUnit, Army, etc.)
"""

from .models import (
    Base,
    # Core
    User, Message, Config, GameUser,
    # Battle
    GameStatus, Field, Game, BattleUnit, Obstacle, GameLog,
    # Army
    Unit, UnitCustomIcon, UserUnit,
    GameRace, RaceUnit, RaceUnitSkin, UnitLevel,
    UserRace, UserRaceUnit,
    Army, ArmyUnit
)
from .repository import Database

__all__ = [
    'Base', 'Database',
    # Core
    'User', 'Message', 'Config', 'GameUser',
    # Battle
    'GameStatus', 'Field', 'Game', 'BattleUnit', 'Obstacle', 'GameLog',
    # Army
    'Unit', 'UnitCustomIcon', 'UserUnit',
    'GameRace', 'RaceUnit', 'RaceUnitSkin', 'UnitLevel',
    'UserRace', 'UserRaceUnit',
    'Army', 'ArmyUnit'
]
