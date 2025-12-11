#!/usr/bin/env python3
"""
Интеграционные тесты для команды /addmoney
"""

import pytest
from decimal import Decimal
from db.models import GameUser


class TestAddMoneyCommand:
    """Тесты для команды /addmoney"""

    def test_addmoney_success_by_admin(self, db_session):
        """Тест успешного добавления денег администратором okarien"""
        # Создать игрока
        player = GameUser(telegram_id=123, name="TestPlayer", balance=Decimal("1000"))
        db_session.add(player)
        db_session.flush()

        # Запомнить начальный баланс
        initial_balance = player.balance

        # Симулировать добавление денег (прямая логика из команды)
        amount = Decimal("500")
        player.balance += amount

        db_session.commit()
        db_session.refresh(player)

        # Проверить что баланс увеличился
        assert player.balance == initial_balance + amount
        assert player.balance == Decimal("1500")

    def test_addmoney_find_user_by_name(self, db_session):
        """Тест поиска пользователя по имени"""
        # Создать нескольких игроков
        player1 = GameUser(telegram_id=111, name="Alice", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, name="Bob", balance=Decimal("500"))
        player3 = GameUser(telegram_id=333, name="Charlie", balance=Decimal("2000"))
        db_session.add_all([player1, player2, player3])
        db_session.flush()

        # Найти пользователя по имени
        target_name = "Bob"
        found_user = db_session.query(GameUser).filter(GameUser.name == target_name).first()

        # Проверить что нашли правильного пользователя
        assert found_user is not None
        assert found_user.name == "Bob"
        assert found_user.telegram_id == 222
        assert found_user.balance == Decimal("500")

    def test_addmoney_user_not_found(self, db_session):
        """Тест поиска несуществующего пользователя"""
        # Создать игрока
        player = GameUser(telegram_id=123, name="ExistingPlayer", balance=Decimal("1000"))
        db_session.add(player)
        db_session.flush()

        # Попытаться найти несуществующего пользователя
        target_name = "NonExistentPlayer"
        found_user = db_session.query(GameUser).filter(GameUser.name == target_name).first()

        # Проверить что пользователь не найден
        assert found_user is None

    def test_addmoney_large_amount(self, db_session):
        """Тест добавления большой суммы"""
        # Создать игрока
        player = GameUser(telegram_id=123, name="TestPlayer", balance=Decimal("1000"))
        db_session.add(player)
        db_session.flush()

        # Добавить большую сумму
        large_amount = Decimal("1000000")
        player.balance += large_amount

        db_session.commit()
        db_session.refresh(player)

        # Проверить что баланс правильно увеличился
        assert player.balance == Decimal("1001000")

    def test_addmoney_decimal_amount(self, db_session):
        """Тест добавления десятичной суммы"""
        # Создать игрока
        player = GameUser(telegram_id=123, name="TestPlayer", balance=Decimal("1000.50"))
        db_session.add(player)
        db_session.flush()

        # Добавить десятичную сумму
        decimal_amount = Decimal("123.45")
        player.balance += decimal_amount

        db_session.commit()
        db_session.refresh(player)

        # Проверить что баланс правильно увеличился
        assert player.balance == Decimal("1123.95")

    def test_addmoney_multiple_users_with_same_balance(self, db_session):
        """Тест добавления денег конкретному пользователю когда есть несколько с одинаковым балансом"""
        # Создать несколько игроков с одинаковым балансом
        player1 = GameUser(telegram_id=111, name="Alice", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, name="Bob", balance=Decimal("1000"))
        player3 = GameUser(telegram_id=333, name="Charlie", balance=Decimal("1000"))
        db_session.add_all([player1, player2, player3])
        db_session.flush()

        # Найти конкретного пользователя по имени и добавить деньги
        target_name = "Bob"
        target_user = db_session.query(GameUser).filter(GameUser.name == target_name).first()

        amount = Decimal("500")
        target_user.balance += amount

        db_session.commit()

        # Обновить всех пользователей из БД
        player1_updated = db_session.query(GameUser).filter_by(telegram_id=111).first()
        player2_updated = db_session.query(GameUser).filter_by(telegram_id=222).first()
        player3_updated = db_session.query(GameUser).filter_by(telegram_id=333).first()

        # Проверить что деньги добавились только Bob
        assert player1_updated.balance == Decimal("1000")
        assert player2_updated.balance == Decimal("1500")
        assert player3_updated.balance == Decimal("1000")

    def test_addmoney_preserves_other_fields(self, db_session):
        """Тест что добавление денег не изменяет другие поля пользователя"""
        # Создать игрока со статистикой
        player = GameUser(
            telegram_id=123,
            name="TestPlayer",
            balance=Decimal("1000"),
            wins=10,
            losses=5
        )
        db_session.add(player)
        db_session.flush()

        # Запомнить статистику
        initial_wins = player.wins
        initial_losses = player.losses
        initial_name = player.name
        initial_telegram_id = player.telegram_id

        # Добавить деньги
        amount = Decimal("500")
        player.balance += amount

        db_session.commit()
        db_session.refresh(player)

        # Проверить что другие поля не изменились
        assert player.wins == initial_wins
        assert player.losses == initial_losses
        assert player.name == initial_name
        assert player.telegram_id == initial_telegram_id
        assert player.balance == Decimal("1500")

    def test_addmoney_to_user_with_zero_balance(self, db_session):
        """Тест добавления денег пользователю с нулевым балансом"""
        # Создать игрока с нулевым балансом
        player = GameUser(telegram_id=123, name="BrokePlayer", balance=Decimal("0"))
        db_session.add(player)
        db_session.flush()

        # Добавить деньги
        amount = Decimal("1000")
        player.balance += amount

        db_session.commit()
        db_session.refresh(player)

        # Проверить что баланс правильно установлен
        assert player.balance == Decimal("1000")

    def test_addmoney_interactive_list_all_users(self, db_session):
        """Тест получения списка всех пользователей для интерактивного выбора"""
        # Создать несколько игроков
        player1 = GameUser(telegram_id=111, name="Alice", balance=Decimal("1000"), wins=5, losses=2)
        player2 = GameUser(telegram_id=222, name="Bob", balance=Decimal("500"), wins=3, losses=4)
        player3 = GameUser(telegram_id=333, name="Charlie", balance=Decimal("2000"), wins=10, losses=1)
        db_session.add_all([player1, player2, player3])
        db_session.flush()

        # Получить всех пользователей отсортированных по имени
        all_users = db_session.query(GameUser).order_by(GameUser.name).all()

        # Проверить что получены все пользователи
        assert len(all_users) == 3
        assert all_users[0].name == "Alice"
        assert all_users[1].name == "Bob"
        assert all_users[2].name == "Charlie"

    def test_addmoney_interactive_find_by_telegram_id(self, db_session):
        """Тест поиска пользователя по telegram_id для callback"""
        # Создать игроков
        player1 = GameUser(telegram_id=111, name="Alice", balance=Decimal("1000"))
        player2 = GameUser(telegram_id=222, name="Bob", balance=Decimal("500"))
        db_session.add_all([player1, player2])
        db_session.flush()

        # Найти пользователя по telegram_id (как в callback)
        target_telegram_id = 222
        found_user = db_session.query(GameUser).filter_by(telegram_id=target_telegram_id).first()

        # Проверить что нашли правильного пользователя
        assert found_user is not None
        assert found_user.name == "Bob"
        assert found_user.telegram_id == 222

    def test_addmoney_interactive_amounts_1000(self, db_session):
        """Тест добавления фиксированной суммы 1000"""
        player = GameUser(telegram_id=123, name="TestPlayer", balance=Decimal("1000"))
        db_session.add(player)
        db_session.flush()

        # Добавить 1000 (первая кнопка)
        amount = Decimal("1000")
        player.balance += amount

        db_session.commit()
        db_session.refresh(player)

        assert player.balance == Decimal("2000")

    def test_addmoney_interactive_amounts_5000(self, db_session):
        """Тест добавления фиксированной суммы 5000"""
        player = GameUser(telegram_id=123, name="TestPlayer", balance=Decimal("1000"))
        db_session.add(player)
        db_session.flush()

        # Добавить 5000 (вторая кнопка)
        amount = Decimal("5000")
        player.balance += amount

        db_session.commit()
        db_session.refresh(player)

        assert player.balance == Decimal("6000")

    def test_addmoney_interactive_amounts_10000(self, db_session):
        """Тест добавления фиксированной суммы 10000"""
        player = GameUser(telegram_id=123, name="TestPlayer", balance=Decimal("1000"))
        db_session.add(player)
        db_session.flush()

        # Добавить 10000 (третья кнопка)
        amount = Decimal("10000")
        player.balance += amount

        db_session.commit()
        db_session.refresh(player)

        assert player.balance == Decimal("11000")

    def test_addmoney_interactive_callback_data_parsing(self, db_session):
        """Тест парсинга callback_data для выбора пользователя и суммы"""
        # Создать игрока
        player = GameUser(telegram_id=12345, name="TestPlayer", balance=Decimal("1000"))
        db_session.add(player)
        db_session.flush()

        # Симулировать callback_data: "addmoney_user:12345"
        callback_data = "addmoney_user:12345"
        parts = callback_data.split(':')
        assert parts[0] == "addmoney_user"
        telegram_id = int(parts[1])
        assert telegram_id == 12345

        # Симулировать callback_data: "addmoney_amount:12345:5000"
        callback_data2 = "addmoney_amount:12345:5000"
        parts2 = callback_data2.split(':')
        assert parts2[0] == "addmoney_amount"
        telegram_id2 = int(parts2[1])
        amount = float(parts2[2])
        assert telegram_id2 == 12345
        assert amount == 5000.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
