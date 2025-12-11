#!/usr/bin/env python3
"""
Простой тест для проверки функциональности поиска сообщений
"""

from db import Database

def test_search_messages():
    """Тест поиска сообщений по username"""
    print("🔍 Тестирование функции поиска сообщений...")

    # Создаем тестовую базу данных в памяти
    db = Database("sqlite:///:memory:")
    db.create_tables()

    # Добавляем тестовых пользователей
    print("\n1. Добавление тестовых пользователей...")
    user1 = db.save_user(telegram_id=12345, username="testuser")
    user2 = db.save_user(telegram_id=67890, username="another")
    print(f"   ✓ Добавлены пользователи: @testuser, @another")

    # Добавляем тестовые сообщения
    print("\n2. Добавление тестовых сообщений...")
    for i in range(25):
        db.save_message(telegram_user_id=12345, message_text=f"Сообщение {i+1} от testuser", username="testuser")

    for i in range(5):
        db.save_message(telegram_user_id=67890, message_text=f"Сообщение {i+1} от another", username="another")

    print(f"   ✓ Добавлено 25 сообщений от @testuser")
    print(f"   ✓ Добавлено 5 сообщений от @another")

    # Тест 1: Поиск первых 10 сообщений
    print("\n3. Тест поиска первых 10 сообщений от @testuser...")
    messages, total_count = db.search_messages_by_username("testuser", offset=0, limit=10)
    assert len(messages) == 10, f"Ожидалось 10 сообщений, получено {len(messages)}"
    assert total_count == 25, f"Ожидалось всего 25 сообщений, получено {total_count}"
    print(f"   ✓ Найдено {len(messages)} сообщений из {total_count}")

    # Тест 2: Поиск следующих 10 сообщений
    print("\n4. Тест поиска сообщений 11-20 от @testuser...")
    messages, total_count = db.search_messages_by_username("testuser", offset=10, limit=10)
    assert len(messages) == 10, f"Ожидалось 10 сообщений, получено {len(messages)}"
    print(f"   ✓ Найдено {len(messages)} сообщений")

    # Тест 3: Поиск последних сообщений
    print("\n5. Тест поиска последних сообщений (21-25) от @testuser...")
    messages, total_count = db.search_messages_by_username("testuser", offset=20, limit=10)
    assert len(messages) == 5, f"Ожидалось 5 сообщений, получено {len(messages)}"
    print(f"   ✓ Найдено {len(messages)} сообщений")

    # Тест 4: Поиск с @ в начале username
    print("\n6. Тест поиска с @ в начале username...")
    messages, total_count = db.search_messages_by_username("@testuser", offset=0, limit=10)
    assert total_count == 25, f"Ожидалось всего 25 сообщений, получено {total_count}"
    print(f"   ✓ Найдено {total_count} сообщений при поиске с @")

    # Тест 5: Поиск несуществующего пользователя
    print("\n7. Тест поиска несуществующего пользователя...")
    messages, total_count = db.search_messages_by_username("nonexistent", offset=0, limit=10)
    assert len(messages) == 0, f"Ожидалось 0 сообщений, получено {len(messages)}"
    assert total_count == 0, f"Ожидалось всего 0 сообщений, получено {total_count}"
    print(f"   ✓ Правильно вернуло 0 сообщений")

    # Тест 6: Поиск другого пользователя
    print("\n8. Тест поиска сообщений от @another...")
    messages, total_count = db.search_messages_by_username("another", offset=0, limit=10)
    assert len(messages) == 5, f"Ожидалось 5 сообщений, получено {len(messages)}"
    assert total_count == 5, f"Ожидалось всего 5 сообщений, получено {total_count}"
    print(f"   ✓ Найдено {len(messages)} сообщений из {total_count}")

    print("\n✅ Все тесты пройдены успешно!")

if __name__ == "__main__":
    test_search_messages()
