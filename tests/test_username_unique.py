#!/usr/bin/env python3
"""
Интеграционные тесты для функционала уникального username
"""

import pytest
from sqlalchemy.exc import IntegrityError
from db.models import GameUser


class TestUsernameUniqueness:
    """Тесты для проверки уникальности username"""

    def test_username_can_be_null_for_backward_compatibility(self, db):
        """Тест: username может быть NULL для обратной совместимости"""
        with db.get_session() as session:
            # Создаем пользователя без username (для обратной совместимости)
            game_user = GameUser(
                telegram_id=123456789,
                name="TestUser",
                balance=1000
            )
            session.add(game_user)
            session.commit()

            # Проверяем, что пользователь создан
            assert game_user.id is not None
            assert game_user.username is None

    def test_username_must_be_unique(self, db):
        """Тест: username должен быть уникальным"""
        username = "test_user"

        # Создаем первого пользователя
        with db.get_session() as session:
            game_user1 = GameUser(
                telegram_id=111111111,
                name="User1",
                username=username,
                balance=1000
            )
            session.add(game_user1)
            session.commit()

        # Попытка создать второго пользователя с тем же username
        with db.get_session() as session:
            with pytest.raises(IntegrityError):
                game_user2 = GameUser(
                    telegram_id=222222222,
                    name="User2",
                    username=username,  # Тот же username
                    balance=1000
                )
                session.add(game_user2)
                session.commit()

    def test_create_user_with_username(self, db):
        """Тест: создание пользователя с username"""
        telegram_id = 333333333
        username = "unique_user"
        name = "Test User"

        # Создаем пользователя с username
        game_user, created = db.get_or_create_game_user(
            telegram_id=telegram_id,
            name=name,
            username=username,
            initial_balance=1500
        )

        assert created is True
        assert game_user.username == username
        assert game_user.name == name
        assert game_user.telegram_id == telegram_id
        assert game_user.balance == 1500

    def test_get_existing_user_by_telegram_id(self, db):
        """Тест: получение существующего пользователя по telegram_id"""
        telegram_id = 444444444
        username = "existing_user"
        name = "Existing User"

        # Создаем пользователя
        game_user1, created1 = db.get_or_create_game_user(
            telegram_id=telegram_id,
            name=name,
            username=username
        )
        assert created1 is True

        # Получаем того же пользователя
        game_user2, created2 = db.get_or_create_game_user(
            telegram_id=telegram_id,
            name="Different Name",  # Другое имя
            username="different_username"  # Другой username (не будет использован)
        )

        assert created2 is False
        assert game_user2.telegram_id == telegram_id
        assert game_user2.username == username  # Username остался прежним
        assert game_user2.name == name  # Имя тоже

    def test_username_with_special_characters(self, db):
        """Тест: username может содержать специальные символы"""
        valid_usernames = [
            "user_123",
            "test-user",
            "User.Name",
            "username123"
        ]

        for idx, username in enumerate(valid_usernames):
            game_user, created = db.get_or_create_game_user(
                telegram_id=500000000 + idx,
                name=f"User{idx}",
                username=username
            )
            assert created is True
            assert game_user.username == username

    def test_different_users_different_usernames(self, db):
        """Тест: разные пользователи имеют разные username"""
        users_data = [
            (600000001, "Alice", "alice"),
            (600000002, "Bob", "bob"),
            (600000003, "Charlie", "charlie"),
        ]

        # Создаем пользователей
        created_users = []
        for telegram_id, name, username in users_data:
            game_user, created = db.get_or_create_game_user(
                telegram_id=telegram_id,
                name=name,
                username=username
            )
            assert created is True
            created_users.append(game_user)

        # Проверяем, что все username уникальны
        usernames = [user.username for user in created_users]
        assert len(set(usernames)) == len(usernames)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
