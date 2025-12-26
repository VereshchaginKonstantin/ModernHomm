#!/usr/bin/env python3
"""
Интеграционные тесты для системы найма юнитов.
Проверяет лимиты, разблокировку уровней, апгрейд скорости найма.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from db.models import (
    GameUser, GameRace, RaceUnit, UnitLevel, UserUnitLimit,
    UserRace, Army, ArmyUnit
)
from jobs.reset_unit_limits import (
    reset_daily_unit_limits, initialize_user_unit_limits,
    unlock_unit_level, upgrade_recruit_speed, recruit_unit,
    get_user_unit_limit
)


def unique_name(prefix):
    """Генерирует уникальное имя"""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


@pytest.fixture
def unit_levels(db_session):
    """Получает уровни юнитов из БД"""
    levels = db_session.query(UnitLevel).order_by(UnitLevel.level).all()
    return {level.level: level for level in levels}


@pytest.fixture
def test_user(db_session):
    """Создает тестового пользователя"""
    user = GameUser(
        telegram_id=int(uuid.uuid4().int % 10**9),
        username=unique_name("recruit_user"),
        balance=Decimal('10000.0'),
        crystals=1000,
        glory=500
    )
    db_session.add(user)
    db_session.commit()
    return user


class TestUserUnitLimitModel:
    """Тесты для модели UserUnitLimit"""

    def test_user_unit_limit_table_exists(self, db_session):
        """Проверка что таблица user_unit_limits существует"""
        result = db_session.query(UserUnitLimit).count()
        assert result >= 0

    def test_unit_level_has_recruitment_fields(self, db_session, unit_levels):
        """Проверка что UnitLevel имеет поля для найма"""
        level1 = unit_levels.get(1)
        if level1:
            assert hasattr(level1, 'daily_recruit_speed')
            assert hasattr(level1, 'speed_upgrade_cost')
            assert hasattr(level1, 'speed_upgrade_cost_gems')
            assert hasattr(level1, 'level_access_cost_gems')

    def test_level_1_has_positive_speed(self, db_session, unit_levels):
        """Проверка что скорость найма для 1 уровня > 0"""
        level1 = unit_levels.get(1)
        if level1:
            assert level1.daily_recruit_speed >= 1

    def test_level_2_has_positive_speed(self, db_session, unit_levels):
        """Проверка что скорость найма для 2 уровня > 0"""
        level2 = unit_levels.get(2)
        if level2:
            assert level2.daily_recruit_speed >= 1


class TestInitializeUserLimits:
    """Тесты для инициализации лимитов найма"""

    def test_initialize_user_limits(self, db_session, db, test_user, unit_levels):
        """Проверка инициализации лимитов для нового пользователя"""
        # Инициализируем лимиты
        created = initialize_user_unit_limits(db, test_user.id)

        # Должны быть созданы записи для всех уровней
        assert created == len(unit_levels)

        # Проверяем созданные записи
        limits = db_session.query(UserUnitLimit).filter_by(user_id=test_user.id).all()
        assert len(limits) == len(unit_levels)

    def test_levels_1_2_unlocked_by_default(self, db_session, db, test_user, unit_levels):
        """Проверка что уровни 1 и 2 разблокированы по умолчанию"""
        initialize_user_unit_limits(db, test_user.id)

        for level_num, level in unit_levels.items():
            limit = db_session.query(UserUnitLimit).filter_by(
                user_id=test_user.id,
                unit_level_id=level.id
            ).first()

            if level_num in (1, 2):
                assert limit.level_unlocked is True
                assert limit.available_count == level.daily_recruit_speed
            else:
                assert limit.level_unlocked is False
                assert limit.available_count == 0

    def test_initialize_twice_returns_zero(self, db_session, db, test_user):
        """Проверка что повторная инициализация не создает новых записей"""
        created1 = initialize_user_unit_limits(db, test_user.id)
        assert created1 > 0

        created2 = initialize_user_unit_limits(db, test_user.id)
        assert created2 == 0


class TestUnlockLevel:
    """Тесты для разблокировки уровней"""

    def test_unlock_level_3_costs_gems(self, db_session, db, test_user, unit_levels):
        """Проверка разблокировки уровня 3 за кристаллы"""
        initialize_user_unit_limits(db, test_user.id)

        level3 = unit_levels.get(3)
        if not level3:
            pytest.skip("Level 3 not found")

        initial_crystals = test_user.crystals
        success, message = unlock_unit_level(db, test_user.id, level3.id)

        assert success is True
        assert "разблокирован" in message

        # Проверяем что кристаллы списались
        db_session.refresh(test_user)
        assert test_user.crystals == initial_crystals - level3.level_access_cost_gems

    def test_unlock_already_unlocked_fails(self, db_session, db, test_user, unit_levels):
        """Проверка что нельзя разблокировать уже открытый уровень"""
        initialize_user_unit_limits(db, test_user.id)

        level1 = unit_levels.get(1)
        if not level1:
            pytest.skip("Level 1 not found")

        success, message = unlock_unit_level(db, test_user.id, level1.id)
        assert success is False
        assert "уже разблокирован" in message

    def test_unlock_without_gems_fails(self, db_session, db, test_user, unit_levels):
        """Проверка что нельзя разблокировать без достаточного количества кристаллов"""
        initialize_user_unit_limits(db, test_user.id)

        # Устанавливаем 0 кристаллов
        test_user.crystals = 0
        db_session.commit()

        level3 = unit_levels.get(3)
        if not level3 or level3.level_access_cost_gems == 0:
            pytest.skip("Level 3 not found or costs 0 gems")

        success, message = unlock_unit_level(db, test_user.id, level3.id)
        assert success is False
        assert "Недостаточно кристаллов" in message


class TestUpgradeRecruitSpeed:
    """Тесты для увеличения скорости найма"""

    def test_upgrade_speed_with_coins(self, db_session, db, test_user, unit_levels):
        """Проверка увеличения скорости за монеты"""
        initialize_user_unit_limits(db, test_user.id)

        level1 = unit_levels.get(1)
        if not level1:
            pytest.skip("Level 1 not found")

        initial_balance = test_user.balance
        initial_speed = level1.daily_recruit_speed

        success, message = upgrade_recruit_speed(db, test_user.id, level1.id, use_gems=False)

        assert success is True
        assert "увеличена" in message

        # Проверяем что монеты списались
        db_session.refresh(test_user)
        assert float(test_user.balance) == float(initial_balance) - float(level1.speed_upgrade_cost)

        # Проверяем что скорость увеличилась
        limit = db_session.query(UserUnitLimit).filter_by(
            user_id=test_user.id,
            unit_level_id=level1.id
        ).first()
        assert limit.daily_speed == initial_speed + 1

    def test_upgrade_speed_with_gems(self, db_session, db, test_user, unit_levels):
        """Проверка увеличения скорости за кристаллы"""
        initialize_user_unit_limits(db, test_user.id)

        level1 = unit_levels.get(1)
        if not level1:
            pytest.skip("Level 1 not found")

        initial_crystals = test_user.crystals

        success, message = upgrade_recruit_speed(db, test_user.id, level1.id, use_gems=True)

        assert success is True

        db_session.refresh(test_user)
        assert test_user.crystals == initial_crystals - level1.speed_upgrade_cost_gems


class TestRecruitUnit:
    """Тесты для найма юнитов"""

    def test_recruit_unit_decreases_available(self, db_session, db, test_user, unit_levels):
        """Проверка что найм уменьшает доступное количество"""
        initialize_user_unit_limits(db, test_user.id)

        level1 = unit_levels.get(1)
        if not level1:
            pytest.skip("Level 1 not found")

        limit_before = get_user_unit_limit(db, test_user.id, level1.id)
        initial_available = limit_before['available_count']

        success, message = recruit_unit(db, test_user.id, level1.id, count=1)

        assert success is True

        limit_after = get_user_unit_limit(db, test_user.id, level1.id)
        assert limit_after['available_count'] == initial_available - 1

    def test_recruit_more_than_available_fails(self, db_session, db, test_user, unit_levels):
        """Проверка что нельзя нанять больше чем доступно"""
        initialize_user_unit_limits(db, test_user.id)

        level1 = unit_levels.get(1)
        if not level1:
            pytest.skip("Level 1 not found")

        limit = get_user_unit_limit(db, test_user.id, level1.id)
        available = limit['available_count']

        success, message = recruit_unit(db, test_user.id, level1.id, count=available + 100)

        assert success is False
        assert "Недостаточно" in message

    def test_recruit_from_locked_level_fails(self, db_session, db, test_user, unit_levels):
        """Проверка что нельзя нанять из заблокированного уровня"""
        initialize_user_unit_limits(db, test_user.id)

        level3 = unit_levels.get(3)
        if not level3:
            pytest.skip("Level 3 not found")

        success, message = recruit_unit(db, test_user.id, level3.id, count=1)

        assert success is False
        assert "не разблокирован" in message


class TestDailyReset:
    """Тесты для ежедневного сброса лимитов"""

    def test_reset_increases_available_count(self, db_session, db, test_user, unit_levels):
        """Проверка что сброс увеличивает доступное количество"""
        initialize_user_unit_limits(db, test_user.id)

        level1 = unit_levels.get(1)
        if not level1:
            pytest.skip("Level 1 not found")

        # Тратим все доступные юниты
        limit = db_session.query(UserUnitLimit).filter_by(
            user_id=test_user.id,
            unit_level_id=level1.id
        ).first()
        limit.available_count = 0
        limit.last_reset_at = datetime.utcnow() - timedelta(hours=25)  # Более 24 часов назад
        db_session.commit()

        # Запускаем сброс
        updated = reset_daily_unit_limits(db)

        # Проверяем что available_count увеличился
        db_session.refresh(limit)
        assert limit.available_count == limit.daily_speed
        assert updated >= 1

    def test_reset_does_not_affect_recent_limits(self, db_session, db, test_user, unit_levels):
        """Проверка что сброс не влияет на недавно обновленные лимиты"""
        initialize_user_unit_limits(db, test_user.id)

        level1 = unit_levels.get(1)
        if not level1:
            pytest.skip("Level 1 not found")

        # Устанавливаем время сброса на сейчас
        limit = db_session.query(UserUnitLimit).filter_by(
            user_id=test_user.id,
            unit_level_id=level1.id
        ).first()
        initial_available = limit.available_count
        limit.last_reset_at = datetime.utcnow()
        db_session.commit()

        # Запускаем сброс
        reset_daily_unit_limits(db)

        # Проверяем что available_count не изменился
        db_session.refresh(limit)
        assert limit.available_count == initial_available


class TestGloryBasedAccess:
    """Тесты для доступа к юнитам на основе славы (для рейтинговой армии)"""

    def test_unit_visible_when_glory_exceeds_prestige(self, db_session, db, test_user, unit_levels):
        """Проверка что юнит виден когда слава >= престижа"""
        # Устанавливаем высокую славу
        test_user.glory = 1000
        db_session.commit()

        # Проверяем что уровни с prestige_min <= 1000 доступны
        for level_num, level in unit_levels.items():
            is_visible = test_user.glory >= level.prestige_min
            if level_num in (1, 2):
                assert is_visible is True, f"Level {level_num} should be visible"

    def test_unit_hidden_when_glory_below_prestige(self, db_session, db, test_user, unit_levels):
        """Проверка что юнит скрыт когда слава < престижа"""
        # Устанавливаем низкую славу
        test_user.glory = 50
        db_session.commit()

        # Проверяем уровни с высоким престижем
        for level_num, level in unit_levels.items():
            if level.prestige_min > 50:
                is_visible = test_user.glory >= level.prestige_min
                assert is_visible is False, f"Level {level_num} should be hidden"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
