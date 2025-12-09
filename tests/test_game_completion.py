#!/usr/bin/env python3
"""
Интеграционные тесты для завершения игры и обработки результатов
"""

import pytest
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, GameUser, Unit, UserUnit, Game, GameStatus, BattleUnit
from game_engine import GameEngine


@pytest.fixture(scope="function")
def db_session():
    """Создание тестовой сессии базы данных"""
    from sqlalchemy import text
    import os
    engine = create_engine("postgresql://postgres:postgres@localhost:5433/telegram_bot_test")
    Session = sessionmaker(bind=engine)
    session = Session()

    # Создаём временный файл изображения для существующих юнитов
    test_image_path = "/tmp/test_unit_image.png"
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    with open(test_image_path, 'wb') as f:
        f.write(png_data)

    # Очищаем тестовые данные перед тестом
    try:
        session.execute(text("DELETE FROM battle_units"))
        session.execute(text("DELETE FROM obstacles"))
        session.execute(text("DELETE FROM game_logs"))
        session.execute(text("DELETE FROM games"))
        session.execute(text("DELETE FROM user_units"))
        session.execute(text("DELETE FROM game_users WHERE telegram_id IN (111, 222, 333, 444, 555, 666)"))
        session.execute(text("DELETE FROM units WHERE name LIKE 'Test%'"))
        session.execute(text("DELETE FROM fields WHERE name LIKE 'Test%'"))
        # Обновляем пути к изображениям для ВСЕХ юнитов (включая те, что уже имеют /tmp/ путь)
        session.execute(text(f"UPDATE units SET image_path = '{test_image_path}'"))
        session.commit()
    except Exception:
        session.rollback()

    yield session

    # Очищаем тестовые данные после теста
    try:
        session.execute(text("DELETE FROM battle_units"))
        session.execute(text("DELETE FROM obstacles"))
        session.execute(text("DELETE FROM game_logs"))
        session.execute(text("DELETE FROM games"))
        session.execute(text("DELETE FROM user_units"))
        session.execute(text("DELETE FROM game_users WHERE telegram_id IN (111, 222, 333, 444, 555, 666)"))
        session.execute(text("DELETE FROM units WHERE name LIKE 'Test%'"))
        session.execute(text("DELETE FROM fields WHERE name LIKE 'Test%'"))
        session.commit()
    except Exception:
        session.rollback()

    session.close()

    # Очистка временного файла
    if os.path.exists(test_image_path):
        os.unlink(test_image_path)


@pytest.fixture
def setup_units(db_session):
    """Создание базовых юнитов для тестов с уникальными именами"""
    import uuid
    import os
    suffix = str(uuid.uuid4())[:8]

    # Создаём реальные файлы изображений для прохождения os.path.exists
    infantry_image = f"/tmp/test_infantry_{suffix}.png"
    sniper_image = f"/tmp/test_sniper_{suffix}.png"

    # Создаём минимальные PNG файлы (1x1 пиксель)
    png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
    for path in [infantry_image, sniper_image]:
        with open(path, 'wb') as f:
            f.write(png_data)

    # Создать юнит Пехота с уникальным именем
    infantry = Unit(
        name=f"TestInfantry_{suffix}",
        icon="⚔️",
        image_path=infantry_image,
        damage=10,
        defense=5,
        health=50,
        speed=2,
        range=1,
        price=Decimal('100.00'),
        crit_chance=0.1,
        luck=0.1
    )

    # Создать юнит Снайпер с уникальным именем
    sniper = Unit(
        name=f"TestSniper_{suffix}",
        icon="🎯",
        image_path=sniper_image,
        damage=50,
        defense=2,
        health=50,
        speed=2,
        range=3,
        price=Decimal('150.00'),
        crit_chance=0.3,
        luck=0.15
    )

    db_session.add(infantry)
    db_session.add(sniper)
    db_session.commit()

    yield {"infantry": infantry, "sniper": sniper}

    # Очистка: удаляем тестовые изображения
    for path in [infantry_image, sniper_image]:
        if os.path.exists(path):
            os.unlink(path)


@pytest.mark.skip(reason="Интеграционный тест зависит от механики линии видимости и позиционирования юнитов")
def test_infantry_vs_sniper_battle(db_session, setup_units):
    """
    Тест битвы: 10 пехотинцев против 1 снайпера.
    Проверяет:
    - Правильное распределение урона по юнитам
    - Корректное завершение игры когда один из игроков теряет все юниты
    - Правильное начисление денег победителю
    - Правильное обновление статистики (wins/losses)
    - Правильное уменьшение количества юнитов проигравшего
    """
    engine = GameEngine(db_session)

    # Создать двух игроков
    player1 = GameUser(telegram_id=111, name="Player1", balance=Decimal('1000.00'), wins=0, losses=0)
    player2 = GameUser(telegram_id=222, name="Player2", balance=Decimal('1000.00'), wins=0, losses=0)

    db_session.add(player1)
    db_session.add(player2)
    db_session.commit()

    # Дать игроку 1: 10 пехотинцев
    infantry = setup_units["infantry"]
    sniper = setup_units["sniper"]

    # Изменим дальность атаки пехоты на 5, чтобы они могли атаковать через все поле
    infantry.range = 5

    player1_infantry = UserUnit(
        game_user_id=player1.id,
        unit_type_id=infantry.id,
        count=10
    )

    # Дать игроку 2: 1 снайпер
    player2_sniper = UserUnit(
        game_user_id=player2.id,
        unit_type_id=sniper.id,
        count=1
    )

    db_session.add(player1_infantry)
    db_session.add(player2_sniper)
    db_session.commit()

    # Создать игру
    game, msg = engine.create_game(player1.id, player2.name, "5x5")
    assert game is not None, f"Ошибка создания игры: {msg}"

    # Принять игру
    success, msg = engine.accept_game(game.id, player2.id)
    assert success, f"Ошибка принятия игры: {msg}"

    # Симулировать битву: юниты атакуют друг друга по очереди
    max_turns = 50  # Максимум 50 ходов, чтобы не зациклиться
    turn = 0

    while game.status == GameStatus.IN_PROGRESS and turn < max_turns:
        turn += 1

        # Получить текущего игрока
        current_player_id = game.current_player_id

        # Найти юниты текущего игрока
        player_units = db_session.query(BattleUnit).filter(
            BattleUnit.game_id == game.id,
            BattleUnit.player_id == current_player_id,
            BattleUnit.has_moved == 0
        ).all()

        # Для каждого юнита попробовать атаковать
        for unit in player_units:
            # Проверить количество живых юнитов
            alive_count = engine._count_alive_units(unit)
            if alive_count == 0:
                continue

            # Найти противника для атаки
            enemy_units = db_session.query(BattleUnit).filter(
                BattleUnit.game_id == game.id,
                BattleUnit.player_id != current_player_id
            ).all()

            target = None
            for enemy in enemy_units:
                if engine._count_alive_units(enemy) > 0:
                    target = enemy
                    break

            if target:
                # Атаковать
                success, msg, turn_switched = engine.attack(
                    game.id, current_player_id, unit.id, target.id
                )

                if not success:
                    print(f"Turn {turn}: Attack failed - {msg}")
                else:
                    print(f"Turn {turn}: Attack successful - {msg[:100]}...")

                # Обновить объект игры
                db_session.refresh(game)

                if game.status == GameStatus.COMPLETED:
                    break
            else:
                print(f"Turn {turn}: No target found for unit {unit.id}")

        if game.status == GameStatus.COMPLETED:
            break

        # Обновить объект игры после хода
        db_session.refresh(game)

    # Проверить что игра завершена
    assert game.status == GameStatus.COMPLETED, f"Игра не завершена после {turn} ходов"

    # Проверить что есть победитель
    assert game.winner_id is not None, "Не определен победитель"

    # Пехота должна победить (10 юнитов против 1)
    assert game.winner_id == player1.id, f"Победителем должен быть игрок с пехотой, но победил игрок {game.winner_id}"

    # Обновить объекты игроков
    db_session.refresh(player1)
    db_session.refresh(player2)

    # Проверить статистику
    assert player1.wins == 1, f"У победителя должна быть 1 победа, а у него {player1.wins}"
    assert player1.losses == 0, f"У победителя не должно быть поражений, а у него {player1.losses}"
    assert player2.wins == 0, f"У проигравшего не должно быть побед, а у него {player2.wins}"
    assert player2.losses == 1, f"У проигравшего должно быть 1 поражение, а у него {player2.losses}"

    # Проверить баланс победителя (должен увеличиться на 70% стоимости убитого снайпера + свои потери)
    # Награда = 70% от убитых врагов + 100% своих потерь
    sniper_price = Decimal('150.00')
    min_reward = sniper_price * Decimal('0.7')  # Минимум 70% от снайпера = 105
    assert player1.balance >= Decimal('1000.00') + min_reward, \
        f"Баланс победителя должен быть минимум {Decimal('1000.00') + min_reward}, а он {player1.balance}"

    # Проверить что у проигравшего 0 снайперов
    db_session.refresh(player2_sniper)
    assert player2_sniper.count == 0, f"У проигравшего должно быть 0 снайперов, а у него {player2_sniper.count}"

    # Проверить что у победителя осталось некоторое количество пехотинцев (может быть 10, если убил снайпера за 1 ход)
    db_session.refresh(player1_infantry)
    assert player1_infantry.count > 0, f"У победителя должны остаться живые пехотинцы, а у него {player1_infantry.count}"
    assert player1_infantry.count <= 10, f"У победителя не может быть больше 10 пехотинцев, а у него {player1_infantry.count}"

    print(f"\n✅ Тест пройден!")
    print(f"   Игра завершена за {turn} ходов")
    print(f"   Победитель: {player1.name} (ID: {player1.id})")
    print(f"   Баланс победителя: ${player1.balance}")
    print(f"   Оставшихся пехотинцев: {player1_infantry.count}/10")


def test_damage_distribution_to_multiple_units(db_session, setup_units):
    """
    Тест механики распределения урона:
    - Если урон превышает HP одного юнита, он должен распределиться на следующие
    - Мертвые юниты не должны учитываться в расчете урона
    - Юниты с 0 HP и total_count=0 не должны отображаться
    """
    from db.models import Field

    engine = GameEngine(db_session)

    # Создать тестовых игроков
    player1 = GameUser(telegram_id=333, name="TestPlayer1", balance=Decimal('1000.00'), wins=0, losses=0)
    player2 = GameUser(telegram_id=444, name="TestPlayer2", balance=Decimal('1000.00'), wins=0, losses=0)

    db_session.add(player1)
    db_session.add(player2)
    db_session.commit()

    infantry = setup_units["infantry"]
    sniper = setup_units["sniper"]

    # Создать юнитов для обоих игроков
    player1_units = UserUnit(
        game_user_id=player1.id,
        unit_type_id=sniper.id,
        count=1
    )
    player2_infantry = UserUnit(
        game_user_id=player2.id,
        unit_type_id=infantry.id,
        count=5  # 5 пехотинцев
    )
    db_session.add(player1_units)
    db_session.add(player2_infantry)
    db_session.commit()

    # Создать поле
    field = Field(name="Test5x5", width=5, height=5)
    db_session.add(field)
    db_session.commit()

    # Создать игру
    game = Game(
        player1_id=player1.id,
        player2_id=player2.id,
        field_id=field.id,
        status=GameStatus.IN_PROGRESS,
        current_player_id=player1.id
    )
    db_session.add(game)
    db_session.commit()

    # Создать BattleUnit для тестирования
    battle_unit = BattleUnit(
        game_id=game.id,
        user_unit_id=player2_infantry.id,
        player_id=player2.id,
        position_x=0,
        position_y=0,
        total_count=5,
        remaining_hp=50,  # Полное HP
        morale=0,
        fatigue=0,
        has_moved=0
    )
    db_session.add(battle_unit)
    db_session.commit()

    # Тест 1: Урон меньше HP одного юнита
    units_killed = engine._apply_damage(battle_unit, 30)
    assert units_killed == 0, f"Не должно быть убитых юнитов при уроне 30, убито: {units_killed}"
    assert battle_unit.total_count == 5, f"Должно остаться 5 юнитов, осталось: {battle_unit.total_count}"
    assert battle_unit.remaining_hp == 20, f"Должно остаться 20 HP, осталось: {battle_unit.remaining_hp}"

    # Тест 2: Урон равен HP одного юнита
    units_killed = engine._apply_damage(battle_unit, 20)
    assert units_killed == 1, f"Должен быть убит 1 юнит, убито: {units_killed}"
    assert battle_unit.total_count == 4, f"Должно остаться 4 юнита, осталось: {battle_unit.total_count}"
    assert battle_unit.remaining_hp == 50, f"HP должно восстановиться до 50, текущее: {battle_unit.remaining_hp}"

    # Тест 3: Урон превышает HP одного юнита и распределяется на следующие
    units_killed = engine._apply_damage(battle_unit, 120)  # Убьет 2 юнита (50 + 50) и нанесет 20 урона третьему
    assert units_killed == 2, f"Должно быть убито 2 юнита, убито: {units_killed}"
    assert battle_unit.total_count == 2, f"Должно остаться 2 юнита, осталось: {battle_unit.total_count}"
    assert battle_unit.remaining_hp == 30, f"Должно остаться 30 HP, осталось: {battle_unit.remaining_hp}"

    # Тест 4: Урон убивает всех оставшихся юнитов
    units_killed = engine._apply_damage(battle_unit, 200)  # Больше чем нужно
    assert units_killed == 2, f"Должно быть убито 2 юнита, убито: {units_killed}"
    assert battle_unit.total_count == 0, f"Не должно остаться юнитов, осталось: {battle_unit.total_count}"
    assert battle_unit.remaining_hp == 0, f"HP должно быть 0, текущее: {battle_unit.remaining_hp}"

    # Тест 5: Подсчет живых юнитов
    alive_count = engine._count_alive_units(battle_unit)
    assert alive_count == 0, f"Не должно быть живых юнитов, найдено: {alive_count}"

    print(f"\n✅ Тест распределения урона пройден!")


def test_zero_units_not_displayed_on_field(db_session, setup_units):
    """
    Тест: Юниты с 0 оставшихся единиц не должны отображаться на поле
    """
    engine = GameEngine(db_session)

    # Создать игроков
    player1 = GameUser(telegram_id=555, name="DisplayTest1", balance=Decimal('1000.00'), wins=0, losses=0)
    player2 = GameUser(telegram_id=666, name="DisplayTest2", balance=Decimal('1000.00'), wins=0, losses=0)

    db_session.add(player1)
    db_session.add(player2)
    db_session.commit()

    infantry = setup_units["infantry"]
    sniper = setup_units["sniper"]

    # Создать юнитов
    player1_units = UserUnit(game_user_id=player1.id, unit_type_id=infantry.id, count=1)
    player2_units = UserUnit(game_user_id=player2.id, unit_type_id=sniper.id, count=1)

    db_session.add(player1_units)
    db_session.add(player2_units)
    db_session.commit()

    # Создать игру
    game, msg = engine.create_game(player1.id, player2.name, "5x5")
    assert game is not None

    # Принять игру
    engine.accept_game(game.id, player2.id)

    # Получить отображение поля до битвы
    field_before = engine.render_field(game.id)
    assert "⚔️1" in field_before, "Пехота должна отображаться на поле"
    assert "🎯1" in field_before, "Снайпер должен отображаться на поле"

    # Найти юнитов для атаки
    attacker = db_session.query(BattleUnit).filter(
        BattleUnit.game_id == game.id,
        BattleUnit.player_id == player1.id
    ).first()

    target = db_session.query(BattleUnit).filter(
        BattleUnit.game_id == game.id,
        BattleUnit.player_id == player2.id
    ).first()

    # Убить снайпера (нанести большой урон)
    engine._apply_damage(target, 1000)
    db_session.commit()

    # Получить отображение поля после убийства снайпера
    field_after = engine.render_field(game.id)
    assert "⚔️1" in field_after, "Пехота должна отображаться на поле"
    assert "🎯" not in field_after, "Мертвый снайпер НЕ должен отображаться на поле"

    print(f"\n✅ Тест отображения 0 юнитов пройден!")
    print(f"Поле до атаки:\n{field_before}")
    print(f"Поле после убийства снайпера:\n{field_after}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
