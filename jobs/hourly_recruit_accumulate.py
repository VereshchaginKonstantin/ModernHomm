#!/usr/bin/env python3
"""
Джоб для почасового накопления юнитов для найма.

Запускается каждый час.
Накапливает юнитов на основе daily_speed / 24 для каждой расы пользователя.
"""

import logging
from datetime import datetime
from decimal import Decimal

from db.repository import Database
from db.models import UserRaceUnitLimit, UnitLevel, UserRace, GameUser

logger = logging.getLogger(__name__)


def accumulate_hourly_units(db: Database) -> int:
    """
    Почасовое накопление юнитов для найма.

    Для каждого UserRaceUnitLimit с разблокированным уровнем:
    - Вычисляет hourly_rate = daily_speed / 24
    - Добавляет hourly_rate к accumulated_fraction
    - Когда accumulated_fraction >= 1, перемещает целую часть в available_count

    Args:
        db: Database instance

    Returns:
        int: Количество обновленных записей
    """
    updated_count = 0
    now = datetime.utcnow()

    with db.get_session() as session:
        # Находим все разблокированные лимиты
        limits = session.query(UserRaceUnitLimit).filter(
            UserRaceUnitLimit.level_unlocked == True
        ).all()

        for limit in limits:
            # Вычисляем почасовую скорость: daily_speed / 24
            hourly_rate = Decimal(str(limit.daily_speed)) / Decimal('24')

            # Добавляем к накопленной дробной части
            current_fraction = Decimal(str(limit.accumulated_fraction))
            new_fraction = current_fraction + hourly_rate

            # Выделяем целую часть для добавления к available_count
            units_to_add = int(new_fraction)
            remaining_fraction = new_fraction - units_to_add

            if units_to_add > 0 or current_fraction != remaining_fraction:
                limit.accumulated_fraction = remaining_fraction
                limit.available_count += units_to_add
                limit.last_accumulate_at = now
                limit.updated_at = now
                updated_count += 1

                if units_to_add > 0:
                    logger.info(
                        f"Accumulated {units_to_add} units for user_race {limit.user_race_id}, "
                        f"level {limit.unit_level_id}: available={limit.available_count}, "
                        f"fraction={remaining_fraction:.6f}"
                    )

        session.commit()

    logger.info(f"Hourly unit accumulation completed. Updated {updated_count} records.")
    return updated_count


def initialize_user_race_unit_limits(db: Database, user_race_id: int) -> int:
    """
    Инициализация лимитов найма для расы пользователя.

    Создает записи UserRaceUnitLimit для всех уровней юнитов.
    Уровни 1 и 2 разблокированы по умолчанию.

    Args:
        db: Database instance
        user_race_id: ID расы пользователя (user_races.id)

    Returns:
        int: Количество созданных записей
    """
    created_count = 0

    with db.get_session() as session:
        # Проверяем, есть ли уже записи для этой расы пользователя
        existing = session.query(UserRaceUnitLimit).filter_by(user_race_id=user_race_id).count()
        if existing > 0:
            logger.debug(f"UserRace {user_race_id} already has unit limits initialized")
            return 0

        # Получаем все уровни юнитов
        unit_levels = session.query(UnitLevel).all()

        for level in unit_levels:
            # Уровни 1 и 2 разблокированы по умолчанию
            is_unlocked = level.level in (1, 2)
            initial_available = level.daily_recruit_speed if is_unlocked else 0

            limit = UserRaceUnitLimit(
                user_race_id=user_race_id,
                unit_level_id=level.id,
                available_count=initial_available,
                daily_speed=level.daily_recruit_speed,
                level_unlocked=is_unlocked,
                accumulated_fraction=Decimal('0'),
                last_accumulate_at=datetime.utcnow()
            )
            session.add(limit)
            created_count += 1

        session.commit()

    logger.info(f"Initialized unit limits for user_race {user_race_id}. Created {created_count} records.")
    return created_count


def get_user_race_unit_limits(db: Database, user_race_id: int) -> list:
    """
    Получение всех лимитов найма для расы пользователя.

    Args:
        db: Database instance
        user_race_id: ID расы пользователя

    Returns:
        list: Список лимитов с информацией об уровнях
    """
    with db.get_session() as session:
        limits = session.query(UserRaceUnitLimit).filter_by(
            user_race_id=user_race_id
        ).join(UnitLevel).order_by(UnitLevel.level).all()

        result = []
        for limit in limits:
            result.append({
                'id': limit.id,
                'unit_level_id': limit.unit_level_id,
                'level': limit.unit_level.level,
                'level_icon': limit.unit_level.icon,
                'available_count': limit.available_count,
                'daily_speed': limit.daily_speed,
                'level_unlocked': limit.level_unlocked,
                'accumulated_fraction': float(limit.accumulated_fraction),
                'unlock_cost_gems': limit.unit_level.level_access_cost_gems,
                'speed_upgrade_cost': float(limit.unit_level.speed_upgrade_cost),
                'speed_upgrade_cost_gems': limit.unit_level.speed_upgrade_cost_gems
            })

        return result


def unlock_race_unit_level(db: Database, user_id: int, user_race_id: int, unit_level_id: int) -> tuple:
    """
    Разблокировка уровня юнита для расы (за кристаллы).

    Args:
        db: Database instance
        user_id: ID пользователя (для списания кристаллов)
        user_race_id: ID расы пользователя
        unit_level_id: ID уровня юнита

    Returns:
        tuple: (success, message, data)
    """
    with db.get_session() as session:
        # Получаем пользователя
        user = session.query(GameUser).filter_by(id=user_id).first()
        if not user:
            return False, "Пользователь не найден", None

        # Проверяем, что раса принадлежит пользователю
        user_race = session.query(UserRace).filter_by(id=user_race_id, user_id=user_id).first()
        if not user_race:
            return False, "Раса не найдена или не принадлежит пользователю", None

        # Получаем уровень юнита
        level = session.query(UnitLevel).filter_by(id=unit_level_id).first()
        if not level:
            return False, "Уровень юнита не найден", None

        # Получаем или создаем лимит
        limit = session.query(UserRaceUnitLimit).filter_by(
            user_race_id=user_race_id,
            unit_level_id=unit_level_id
        ).first()

        if not limit:
            limit = UserRaceUnitLimit(
                user_race_id=user_race_id,
                unit_level_id=unit_level_id,
                available_count=0,
                daily_speed=level.daily_recruit_speed,
                level_unlocked=False,
                accumulated_fraction=Decimal('0'),
                last_accumulate_at=datetime.utcnow()
            )
            session.add(limit)

        if limit.level_unlocked:
            return False, "Уровень уже разблокирован", None

        # Проверяем кристаллы
        cost = level.level_access_cost_gems
        if user.crystals < cost:
            return False, f"Недостаточно кристаллов. Нужно: {cost}, есть: {user.crystals}", None

        # Списываем кристаллы и разблокируем
        user.crystals -= cost
        limit.level_unlocked = True
        limit.available_count = level.daily_recruit_speed
        limit.updated_at = datetime.utcnow()

        session.commit()

        return True, f"Уровень {level.level} разблокирован!", {
            'level': level.level,
            'available_count': limit.available_count,
            'daily_speed': limit.daily_speed,
            'crystals_remaining': user.crystals
        }


def upgrade_race_recruit_speed(db: Database, user_id: int, user_race_id: int, unit_level_id: int, use_gems: bool = False) -> tuple:
    """
    Увеличение скорости найма для расы на +1 юнит в день.

    Args:
        db: Database instance
        user_id: ID пользователя
        user_race_id: ID расы пользователя
        unit_level_id: ID уровня юнита
        use_gems: Использовать кристаллы (True) или монеты (False)

    Returns:
        tuple: (success, message, data)
    """
    with db.get_session() as session:
        user = session.query(GameUser).filter_by(id=user_id).first()
        if not user:
            return False, "Пользователь не найден", None

        # Проверяем, что раса принадлежит пользователю
        user_race = session.query(UserRace).filter_by(id=user_race_id, user_id=user_id).first()
        if not user_race:
            return False, "Раса не найдена или не принадлежит пользователю", None

        level = session.query(UnitLevel).filter_by(id=unit_level_id).first()
        if not level:
            return False, "Уровень юнита не найден", None

        limit = session.query(UserRaceUnitLimit).filter_by(
            user_race_id=user_race_id,
            unit_level_id=unit_level_id
        ).first()

        if not limit:
            return False, "Уровень не инициализирован", None

        if not limit.level_unlocked:
            return False, "Уровень не разблокирован", None

        if use_gems:
            cost = level.speed_upgrade_cost_gems
            if user.crystals < cost:
                return False, f"Недостаточно кристаллов. Нужно: {cost}, есть: {user.crystals}", None
            user.crystals -= cost
            currency_remaining = user.crystals
        else:
            cost = Decimal(str(level.speed_upgrade_cost))
            if user.balance < cost:
                return False, f"Недостаточно монет. Нужно: {cost}, есть: {user.balance}", None
            user.balance -= cost
            currency_remaining = float(user.balance)

        limit.daily_speed += 1
        limit.updated_at = datetime.utcnow()

        session.commit()

        return True, f"Скорость найма увеличена до {limit.daily_speed} юнитов в день", {
            'daily_speed': limit.daily_speed,
            'currency_remaining': currency_remaining
        }


def recruit_race_unit(db: Database, user_race_id: int, unit_level_id: int, count: int = 1) -> tuple:
    """
    Найм юнита для расы (уменьшение available_count).

    Args:
        db: Database instance
        user_race_id: ID расы пользователя
        unit_level_id: ID уровня юнита
        count: Количество юнитов для найма

    Returns:
        tuple: (success, message, remaining_count)
    """
    with db.get_session() as session:
        limit = session.query(UserRaceUnitLimit).filter_by(
            user_race_id=user_race_id,
            unit_level_id=unit_level_id
        ).first()

        if not limit:
            return False, "Уровень не инициализирован", 0

        if not limit.level_unlocked:
            return False, "Уровень не разблокирован", 0

        if limit.available_count < count:
            return False, f"Недостаточно доступных юнитов. Доступно: {limit.available_count}", limit.available_count

        limit.available_count -= count
        limit.updated_at = datetime.utcnow()

        remaining = limit.available_count

        session.commit()

    return True, f"Нанято {count} юнитов", remaining


if __name__ == '__main__':
    # Для запуска через cron
    import os
    import sys

    # Добавляем путь к проекту
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    logging.basicConfig(level=logging.INFO)

    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
    db = Database(db_url)

    accumulate_hourly_units(db)
