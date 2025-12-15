#!/usr/bin/env python3
"""
Тестовый скрипт для проверки CRUD операций с игровыми пользователями
"""

import pytest
from db import Database


def test_game_user_crud(db):
    """Тестирование CRUD операций для GameUser"""

    print("=" * 50)
    print("Тестирование CRUD операций для игровых пользователей")
    print("=" * 50)

    # 1. Создание игрового пользователя
    print("\n1. Создание игрового пользователя...")
    game_user = db.create_game_user(
        telegram_id=12345,
        username="Тестовый_игрок",
        initial_balance=1500
    )
    print(f"   ✓ Создан: {game_user}")
    print(f"   - ID: {game_user.id}")
    print(f"   - Telegram ID: {game_user.telegram_id}")
    print(f"   - Username: {game_user.username}")
    print(f"   - Баланс: ${game_user.balance}")
    print(f"   - Побед: {game_user.wins}")
    print(f"   - Поражений: {game_user.losses}")

    assert game_user.telegram_id == 12345
    assert game_user.username == "Тестовый_игрок"
    assert game_user.balance == 1500

    # 2. Получение игрового пользователя
    print("\n2. Получение игрового пользователя...")
    retrieved_user = db.get_game_user(12345)
    print(f"   ✓ Получен: {retrieved_user}")

    assert retrieved_user is not None
    assert retrieved_user.telegram_id == 12345

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

    assert updated_user.balance == 2000
    assert updated_user.wins == 5
    assert updated_user.losses == 2

    # 4. Тестирование get_or_create_game_user
    print("\n4. Тестирование get_or_create_game_user...")

    # Пытаемся получить существующего пользователя
    game_user2, created = db.get_or_create_game_user(
        telegram_id=12345,
        username="Другой_username",
        initial_balance=999
    )
    print(f"   ✓ Пользователь существует: created={created}")
    print(f"   - Username остался: {game_user2.username}")
    print(f"   - Баланс остался: ${game_user2.balance}")

    assert created is False
    assert game_user2.username == "Тестовый_игрок"  # Username не изменился

    # Создаем нового пользователя
    game_user3, created = db.get_or_create_game_user(
        telegram_id=67890,
        username="Новый_игрок",
        initial_balance=1000
    )
    print(f"   ✓ Создан новый пользователь: created={created}")
    print(f"   - Username: {game_user3.username}")
    print(f"   - Баланс: ${game_user3.balance}")

    assert created is True
    assert game_user3.username == "Новый_игрок"
    assert game_user3.balance == 1000

    # 5. Удаление игрового пользователя
    print("\n5. Удаление игрового пользователя...")
    success = db.delete_game_user(67890)
    print(f"   ✓ Пользователь удален: {success}")

    assert success is True

    # Проверяем, что пользователь удален
    deleted_user = db.get_game_user(67890)
    assert deleted_user is None

    print("\n" + "=" * 50)
    print("Все тесты пройдены успешно!")
    print("=" * 50)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
