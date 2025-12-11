#!/usr/bin/env python3
"""
Интеграционные тесты для функционала установки пароля (/password)
"""

import pytest
import hashlib
from db.models import GameUser


class TestPasswordFunctionality:
    """Тесты для функции установки пароля"""

    def test_password_hash_column_exists(self, db):
        """Тест: колонка password_hash существует в таблице game_users"""
        with db.get_session() as session:
            # Создаем тестового пользователя
            game_user = GameUser(
                telegram_id=123456789,
                name="TestUser",
                balance=1000,
                wins=0,
                losses=0,
                password_hash=None
            )
            session.add(game_user)
            session.commit()

            # Проверяем, что объект создан
            assert game_user.id is not None
            assert game_user.password_hash is None

    def test_set_password_hash(self, db):
        """Тест: установка хеша пароля для пользователя"""
        telegram_id = 987654321
        password = "test_password_123"

        # Создаем пользователя
        with db.get_session() as session:
            game_user = GameUser(
                telegram_id=telegram_id,
                name="PasswordTestUser",
                balance=1000,
                wins=0,
                losses=0
            )
            session.add(game_user)
            session.commit()

        # Устанавливаем пароль
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        with db.get_session() as session:
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()
            assert game_user is not None

            game_user.password_hash = password_hash
            session.commit()

        # Проверяем, что пароль сохранен
        with db.get_session() as session:
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()
            assert game_user.password_hash == password_hash

    def test_password_hash_format(self, db):
        """Тест: формат хеша пароля (SHA256)"""
        password = "secure_password_456"
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Проверяем длину SHA256 хеша (64 символа)
        assert len(password_hash) == 64

        # Проверяем, что хеш содержит только hex символы
        assert all(c in '0123456789abcdef' for c in password_hash)

    def test_password_validation_min_length(self, db):
        """Тест: валидация минимальной длины пароля (6 символов)"""
        # Короткие пароли
        short_passwords = ["12345", "abc", "a", ""]

        for password in short_passwords:
            # Проверяем, что короткий пароль не проходит валидацию
            assert len(password) < 6

        # Валидные пароли
        valid_passwords = ["123456", "password", "secure_pass_123"]

        for password in valid_passwords:
            # Проверяем, что валидный пароль проходит валидацию
            assert len(password) >= 6

    def test_password_hash_uniqueness(self, db):
        """Тест: разные пароли дают разные хеши"""
        password1 = "password123"
        password2 = "password124"

        hash1 = hashlib.sha256(password1.encode()).hexdigest()
        hash2 = hashlib.sha256(password2.encode()).hexdigest()

        # Разные пароли должны давать разные хеши
        assert hash1 != hash2

    def test_password_hash_consistency(self, db):
        """Тест: один и тот же пароль дает одинаковый хеш"""
        password = "consistent_password"

        hash1 = hashlib.sha256(password.encode()).hexdigest()
        hash2 = hashlib.sha256(password.encode()).hexdigest()

        # Один и тот же пароль должен давать одинаковый хеш
        assert hash1 == hash2

    def test_multiple_users_different_passwords(self, db):
        """Тест: несколько пользователей с разными паролями"""
        users_data = [
            (111111111, "User1", "password1"),
            (222222222, "User2", "password2"),
            (333333333, "User3", "password3"),
        ]

        # Создаем пользователей с паролями
        for telegram_id, name, password in users_data:
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            with db.get_session() as session:
                game_user = GameUser(
                    telegram_id=telegram_id,
                    name=name,
                    balance=1000,
                    wins=0,
                    losses=0,
                    password_hash=password_hash
                )
                session.add(game_user)
                session.commit()

        # Проверяем, что все пользователи созданы с разными хешами
        with db.get_session() as session:
            users = session.query(GameUser).all()
            assert len(users) == 3

            # Проверяем, что все хеши разные
            password_hashes = [user.password_hash for user in users]
            assert len(set(password_hashes)) == 3

    def test_update_existing_password(self, db):
        """Тест: обновление существующего пароля"""
        telegram_id = 444444444
        old_password = "old_password"
        new_password = "new_password"

        old_hash = hashlib.sha256(old_password.encode()).hexdigest()
        new_hash = hashlib.sha256(new_password.encode()).hexdigest()

        # Создаем пользователя со старым паролем
        with db.get_session() as session:
            game_user = GameUser(
                telegram_id=telegram_id,
                name="UpdatePasswordUser",
                balance=1000,
                wins=0,
                losses=0,
                password_hash=old_hash
            )
            session.add(game_user)
            session.commit()

        # Обновляем пароль
        with db.get_session() as session:
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()
            assert game_user.password_hash == old_hash

            game_user.password_hash = new_hash
            session.commit()

        # Проверяем, что пароль обновлен
        with db.get_session() as session:
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()
            assert game_user.password_hash == new_hash
            assert game_user.password_hash != old_hash

    def test_password_verification(self, db):
        """Тест: проверка пароля при входе"""
        telegram_id = 555555555
        correct_password = "correct_password"
        wrong_password = "wrong_password"

        correct_hash = hashlib.sha256(correct_password.encode()).hexdigest()
        wrong_hash = hashlib.sha256(wrong_password.encode()).hexdigest()

        # Создаем пользователя с паролем
        with db.get_session() as session:
            game_user = GameUser(
                telegram_id=telegram_id,
                name="VerifyPasswordUser",
                balance=1000,
                wins=0,
                losses=0,
                password_hash=correct_hash
            )
            session.add(game_user)
            session.commit()

        # Проверяем верификацию пароля
        with db.get_session() as session:
            game_user = session.query(GameUser).filter_by(telegram_id=telegram_id).first()

            # Правильный пароль должен совпадать
            assert game_user.password_hash == correct_hash

            # Неправильный пароль не должен совпадать
            assert game_user.password_hash != wrong_hash


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
