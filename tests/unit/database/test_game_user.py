#!/usr/bin/env python3
"""
Тестовый скрипт для проверки CRUD операций с игровыми пользователями
"""

from db import Database

def test_game_user_crud():
    """Тестирование CRUD операций для GameUser и UserUnit"""
    db = Database()

    print("=" * 50)
    print("Тестирование CRUD операций для игровых пользователей")
    print("=" * 50)

    # 1. Создание игрового пользователя
    print("\n1. Создание игрового пользователя...")
    game_user = db.create_game_user(
        telegram_id=12345,
        name="Тестовый игрок",
        initial_balance=1500
    )
    print(f"   ✓ Создан: {game_user}")
    print(f"   - ID: {game_user.id}")
    print(f"   - Telegram ID: {game_user.telegram_id}")
    print(f"   - Имя: {game_user.name}")
    print(f"   - Баланс: ${game_user.balance}")
    print(f"   - Побед: {game_user.wins}")
    print(f"   - Поражений: {game_user.losses}")

    # 2. Получение игрового пользователя
    print("\n2. Получение игрового пользователя...")
    retrieved_user = db.get_game_user(12345)
    print(f"   ✓ Получен: {retrieved_user}")

    # 3. Обновление игрового пользователя
    print("\n3. Обновление игрового пользователя...")
    updated_user = db.update_game_user(
        telegram_id=12345,
        balance=2000,
        wins=5,
        losses=2
    )
    print(f"   ✓ Обновлен: {updated_user}")
    print(f"   - Новый баланс: ${updated_user.balance}")
    print(f"   - Побед: {updated_user.wins}")
    print(f"   - Поражений: {updated_user.losses}")

    # 4. Добавление юнитов
    print("\n4. Добавление юнитов...")
    unit1 = db.add_unit(telegram_id=12345, unit_type_id=1, count=10)
    print(f"   ✓ Добавлен юнит типа 1: {unit1.count} шт.")

    unit2 = db.add_unit(telegram_id=12345, unit_type_id=2, count=5)
    print(f"   ✓ Добавлен юнит типа 2: {unit2.count} шт.")

    unit3 = db.add_unit(telegram_id=12345, unit_type_id=1, count=5)
    print(f"   ✓ Добавлено еще юнитов типа 1: теперь {unit3.count} шт.")

    # 5. Получение всех юнитов пользователя
    print("\n5. Получение всех юнитов пользователя...")
    units = db.get_user_units(12345)
    print(f"   ✓ Всего типов юнитов: {len(units)}")
    for unit in units:
        print(f"   - Тип #{unit.unit_type_id}: {unit.count} шт.")

    # 6. Обновление количества юнитов
    print("\n6. Обновление количества юнитов...")
    updated_unit = db.update_unit_count(telegram_id=12345, unit_type_id=2, count=20)
    print(f"   ✓ Обновлено количество юнитов типа 2: {updated_unit.count} шт.")

    # 7. Удаление юнитов
    print("\n7. Удаление юнитов...")
    success = db.remove_unit(telegram_id=12345, unit_type_id=2, count=10)
    print(f"   ✓ Удалено 10 юнитов типа 2: {success}")

    units = db.get_user_units(12345)
    print(f"   - Осталось юнитов типа 2: {[u.count for u in units if u.unit_type_id == 2][0]} шт.")

    # 8. Тестирование get_or_create_game_user
    print("\n8. Тестирование get_or_create_game_user...")

    # Пытаемся получить существующего пользователя
    game_user2, created = db.get_or_create_game_user(
        telegram_id=12345,
        name="Другое имя",
        initial_balance=999
    )
    print(f"   ✓ Пользователь существует: created={created}")
    print(f"   - Имя осталось: {game_user2.name}")
    print(f"   - Баланс остался: ${game_user2.balance}")

    # Создаем нового пользователя
    game_user3, created = db.get_or_create_game_user(
        telegram_id=67890,
        name="Новый игрок",
        initial_balance=1000
    )
    print(f"   ✓ Создан новый пользователь: created={created}")
    print(f"   - Имя: {game_user3.name}")
    print(f"   - Баланс: ${game_user3.balance}")

    # 9. Удаление игрового пользователя
    print("\n9. Удаление игрового пользователя...")
    success = db.delete_game_user(67890)
    print(f"   ✓ Пользователь удален: {success}")

    # Проверяем, что юниты также удалены (CASCADE)
    success = db.delete_game_user(12345)
    print(f"   ✓ Пользователь с юнитами удален: {success}")

    units = db.get_user_units(12345)
    print(f"   - Юниты удаленного пользователя: {len(units)} шт. (должно быть 0)")

    print("\n" + "=" * 50)
    print("Все тесты пройдены успешно!")
    print("=" * 50)


if __name__ == '__main__':
    test_game_user_crud()
