#!/usr/bin/env python3
"""
Модели базы данных для Telegram бота

Модели разделены на три категории:
- core: базовые модели (User, Message, Config, GameUser)
- battle: модели боевой системы (Game, BattleUnit, GameLog, Field, Obstacle)
- army: модели армии и рас (GameRace, RaceUnit, Army, ArmyUnit, etc.)
"""

from .base import Base

# Базовые модели
from .core import User, Message, Config, ClientLog, GameUser, JobLog

# Модели боевой системы
from .battle import (
    GameStatus, DecorationType, Field,
    BattleFieldTemplate, BattleFieldObstacle, BattleFieldDecoration,
    Game, BattleUnit, Obstacle, GameLog
)

# Модели армии и рас
from .army import (
    GameRace, RaceUnit, RaceUnitSkin, UnitLevel, UserUnitLimit, UserRaceUnitLimit,
    UserRace, UserRaceUnit,
    Army, ArmyUnit
)

__all__ = [
    # Base
    'Base',
    # Core
    'User', 'Message', 'Config', 'ClientLog', 'GameUser', 'JobLog',
    # Battle
    'GameStatus', 'DecorationType', 'Field',
    'BattleFieldTemplate', 'BattleFieldObstacle', 'BattleFieldDecoration',
    'Game', 'BattleUnit', 'Obstacle', 'GameLog',
    # Army & Races
    'GameRace', 'RaceUnit', 'RaceUnitSkin', 'UnitLevel', 'UserUnitLimit', 'UserRaceUnitLimit',
    'UserRace', 'UserRaceUnit',
    'Army', 'ArmyUnit'
]
