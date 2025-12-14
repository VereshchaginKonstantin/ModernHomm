#!/usr/bin/env python3
"""
Джоб для сброса ежедневных лимитов найма юнитов.

Запускается ежедневно (через cron или telegram-bot JobQueue).
Обновляет available_count для всех пользователей на основе их daily_speed.
"""

import logging
from datetime import datetime, timedelta

from db.repository import Database
from db.models import UserUnitLimit, UnitLevel, GameUser

logger = logging.getLogger(__name__)


def reset_daily_unit_limits(db: Database) -> int:
    """
    Сброс ежедневных лимитов найма юнитов.

    Для каждого UserUnitLimit:
    - Если прошло больше 24 часов с last_reset_at
    - Увеличивает available_count на daily_speed
    - Обновляет last_reset_at

    Args:
        db: Database instance

    Returns:
        int: Количество обновленных записей
    """
    updated_count = 0
    now = datetime.utcnow()
    yesterday = now - timedelta(hours=24)

    with db.get_session() as session:
        # Находим все записи, которые не обновлялись более 24 часов
        limits = session.query(UserUnitLimit).filter(
            UserUnitLimit.last_reset_at < yesterday,
            UserUnitLimit.level_unlocked == True
        ).all()

        for limit in limits:
            # Добавляем daily_speed к available_count
            limit.available_count += limit.daily_speed
            limit.last_reset_at = now
            limit.updated_at = now
            updated_count += 1

            logger.info(f"Reset unit limit for user {limit.user_id}, level {limit.unit_level_id}: "
                       f"available_count={limit.available_count}, daily_speed={limit.daily_speed}")

        session.commit()

    logger.info(f"Daily unit limits reset completed. Updated {updated_count} records.")
    return updated_count


def initialize_user_unit_limits(db: Database, user_id: int) -> int:
    """
    Инициализация лимитов найма для нового пользователя.

    Создает записи UserUnitLimit для всех уровней юнитов.
    Уровни 1 и 2 разблокированы по умолчанию.

    Args:
        db: Database instance
        user_id: ID пользователя

    Returns:
        int: Количество созданных записей
    """
    created_count = 0

    with db.get_session() as session:
        # Проверяем, есть ли уже записи для этого пользователя
        existing = session.query(UserUnitLimit).filter_by(user_id=user_id).count()
        if existing > 0:
            logger.debug(f"User {user_id} already has unit limits initialized")
            return 0

        # Получаем все уровни юнитов
        unit_levels = session.query(UnitLevel).all()

        for level in unit_levels:
            # Уровни 1 и 2 разблокированы по умолчанию
            is_unlocked = level.level in (1, 2)
            initial_available = level.daily_recruit_speed if is_unlocked else 0

            limit = UserUnitLimit(
                user_id=user_id,
                unit_level_id=level.id,
                available_count=initial_available,
                daily_speed=level.daily_recruit_speed,
                level_unlocked=is_unlocked,
                last_reset_at=datetime.utcnow()
            )
            session.add(limit)
            created_count += 1

        session.commit()

    logger.info(f"Initialized unit limits for user {user_id}. Created {created_count} records.")
    return created_count


def get_user_unit_limit(db: Database, user_id: int, unit_level_id: int) -> dict:
    """
    Получение лимита найма для конкретного уровня юнита.

    Args:
        db: Database instance
        user_id: ID пользователя
        unit_level_id: ID уровня юнита

    Returns:
        dict: Данные о лимите или None
    """
    with db.get_session() as session:
        limit = session.query(UserUnitLimit).filter_by(
            user_id=user_id,
            unit_level_id=unit_level_id
        ).first()

        if not limit:
            return None

        return {
            'available_count': limit.available_count,
            'daily_speed': limit.daily_speed,
            'level_unlocked': limit.level_unlocked,
            'last_reset_at': limit.last_reset_at
        }


def unlock_unit_level(db: Database, user_id: int, unit_level_id: int) -> tuple:
    """
    Разблокировка уровня юнита для найма (за кристаллы).

    Args:
        db: Database instance
        user_id: ID пользователя
        unit_level_id: ID уровня юнита

    Returns:
        tuple: (success, message)
    """
    with db.get_session() as session:
        # Получаем пользователя
        user = session.query(GameUser).filter_by(id=user_id).first()
        if not user:
            return False, "Пользователь не найден"

        # Получаем уровень юнита
        level = session.query(UnitLevel).filter_by(id=unit_level_id).first()
        if not level:
            return False, "Уровень юнита не найден"

        # Получаем или создаем лимит
        limit = session.query(UserUnitLimit).filter_by(
            user_id=user_id,
            unit_level_id=unit_level_id
        ).first()

        if not limit:
            limit = UserUnitLimit(
                user_id=user_id,
                unit_level_id=unit_level_id,
                available_count=0,
                daily_speed=level.daily_recruit_speed,
                level_unlocked=False,
                last_reset_at=datetime.utcnow()
            )
            session.add(limit)

        if limit.level_unlocked:
            return False, "Уровень уже разблокирован"

        # Проверяем кристаллы
        if user.crystals < level.level_access_cost_gems:
            return False, f"Недостаточно кристаллов. Нужно: {level.level_access_cost_gems}, есть: {user.crystals}"

        # Списываем кристаллы и разблокируем
        user.crystals -= level.level_access_cost_gems
        limit.level_unlocked = True
        limit.available_count = level.daily_recruit_speed
        limit.updated_at = datetime.utcnow()

        # Сохраняем значения до закрытия сессии
        level_num = level.level
        recruit_speed = level.daily_recruit_speed

        session.commit()

    return True, f"Уровень {level_num} разблокирован! Доступно для найма: {recruit_speed} юнитов"


def upgrade_recruit_speed(db: Database, user_id: int, unit_level_id: int, use_gems: bool = False) -> tuple:
    """
    Увеличение скорости найма на +1 юнит в день.

    Args:
        db: Database instance
        user_id: ID пользователя
        unit_level_id: ID уровня юнита
        use_gems: Использовать кристаллы (True) или монеты (False)

    Returns:
        tuple: (success, message)
    """
    with db.get_session() as session:
        user = session.query(GameUser).filter_by(id=user_id).first()
        if not user:
            return False, "Пользователь не найден"

        level = session.query(UnitLevel).filter_by(id=unit_level_id).first()
        if not level:
            return False, "Уровень юнита не найден"

        limit = session.query(UserUnitLimit).filter_by(
            user_id=user_id,
            unit_level_id=unit_level_id
        ).first()

        if not limit:
            return False, "Уровень не инициализирован. Сначала разблокируйте его."

        if not limit.level_unlocked:
            return False, "Уровень не разблокирован"

        if use_gems:
            cost = level.speed_upgrade_cost_gems
            if user.crystals < cost:
                return False, f"Недостаточно кристаллов. Нужно: {cost}, есть: {user.crystals}"
            user.crystals -= cost
        else:
            from decimal import Decimal
            cost = Decimal(str(level.speed_upgrade_cost))
            if user.balance < cost:
                return False, f"Недостаточно монет. Нужно: {cost}, есть: {user.balance}"
            user.balance -= cost

        limit.daily_speed += 1
        limit.updated_at = datetime.utcnow()

        # Сохраняем значение до закрытия сессии
        new_speed = limit.daily_speed

        session.commit()

    return True, f"Скорость найма увеличена до {new_speed} юнитов в день"


def recruit_unit(db: Database, user_id: int, unit_level_id: int, count: int = 1) -> tuple:
    """
    Найм юнита (уменьшение available_count).

    Args:
        db: Database instance
        user_id: ID пользователя
        unit_level_id: ID уровня юнита
        count: Количество юнитов для найма

    Returns:
        tuple: (success, message)
    """
    with db.get_session() as session:
        limit = session.query(UserUnitLimit).filter_by(
            user_id=user_id,
            unit_level_id=unit_level_id
        ).first()

        if not limit:
            return False, "Уровень не инициализирован"

        if not limit.level_unlocked:
            return False, "Уровень не разблокирован"

        if limit.available_count < count:
            return False, f"Недостаточно доступных юнитов. Доступно: {limit.available_count}"

        limit.available_count -= count
        limit.updated_at = datetime.utcnow()

        # Сохраняем значение до закрытия сессии
        remaining = limit.available_count

        session.commit()

    return True, f"Нанято {count} юнитов. Осталось доступно: {remaining}"


if __name__ == '__main__':
    # Для запуска через cron
    import os
    import sys

    # Добавляем путь к проекту
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    logging.basicConfig(level=logging.INFO)

    db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
    db = Database(db_url)

    reset_daily_unit_limits(db)
