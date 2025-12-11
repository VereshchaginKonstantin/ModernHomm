#!/usr/bin/env python3
"""
Модели базы данных для Telegram бота

Модели разделены на три категории:
- core: базовые модели (User, Message, Config, GameUser)
- battle: модели боевой системы (Game, BattleUnit, GameLog, Field, Obstacle)
- army: модели армии и юнитов (Unit, UserUnit, GameRace, RaceUnit, Army, etc.)
"""

from .base import Base

# Базовые модели
from .core import User, Message, Config, GameUser

# Модели боевой системы
from .battle import GameStatus, Field, Game, BattleUnit, Obstacle, GameLog

# Модели армии, юнитов и рас
from .army import (
    Unit, UnitCustomIcon, UserUnit,
    GameRace, RaceUnit, UnitLevel,
    UserRace, UserRaceUnit,
    Army, ArmyUnit
)

__all__ = [
    # Base
    'Base',
    # Core
    'User', 'Message', 'Config', 'GameUser',
    # Battle
    'GameStatus', 'Field', 'Game', 'BattleUnit', 'Obstacle', 'GameLog',
    # Army
    'Unit', 'UnitCustomIcon', 'UserUnit',
    'GameRace', 'RaceUnit', 'UnitLevel',
    'UserRace', 'UserRaceUnit',
    'Army', 'ArmyUnit'
]
