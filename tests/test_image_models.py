#!/usr/bin/env python3
"""
Интеграционные тесты для моделей изображений, сеттингов и уровней юнитов
"""

import pytest
import random
from decimal import Decimal
from db.image_models import Setting, UnitImage, UnitLevel


def get_unique_level_number():
    """Генерирует уникальный номер уровня для тестов"""
    return random.randint(1000, 99999)


class TestSettingModel:
    """Тесты для модели Setting"""

    def test_create_setting(self, db):
        """Тест: создание сеттинга"""
        with db.get_session() as session:
            setting = Setting(
                name="Тестовый сеттинг test_create_setting",
                description="Описание тестового сеттинга",
                is_tournament=True,
                unlock_cost=Decimal('100.00'),
                subscription_only=False
            )
            session.add(setting)
            session.commit()

            # Проверяем, что сеттинг создан
            assert setting.id is not None
            assert setting.name == "Тестовый сеттинг test_create_setting"
            assert setting.is_tournament is True
            assert setting.unlock_cost == Decimal('100.00')

    def test_setting_with_images_relationship(self, db):
        """Тест: связь сеттинга с изображениями"""
        with db.get_session() as session:
            # Создаем сеттинг
            setting = Setting(
                name="Сеттинг с изображениями test_setting_with_images",
                description="Тестовый сеттинг",
                is_tournament=False,
                unlock_cost=Decimal('50.00'),
                subscription_only=False
            )
            session.add(setting)
            session.commit()
            setting_id = setting.id

            # Создаем изображение, связанное с сеттингом
            image_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'  # Минимальные данные PNG
            unit_image = UnitImage(
                description="Тестовое изображение",
                image_data=image_data,
                setting_id=setting_id,
                subscription_only=False
            )
            session.add(unit_image)
            session.commit()

            # Проверяем связь
            setting = session.query(Setting).filter_by(id=setting_id).first()
            assert len(setting.images) == 1
            assert setting.images[0].description == "Тестовое изображение"

    def test_delete_setting_cascades_to_images(self, db):
        """Тест: удаление сеттинга каскадно удаляет изображения"""
        with db.get_session() as session:
            # Создаем сеттинг с изображением
            setting = Setting(
                name="Сеттинг для удаления test_delete_setting",
                is_tournament=False,
                unlock_cost=Decimal('0'),
                subscription_only=False
            )
            session.add(setting)
            session.commit()
            setting_id = setting.id

            image_data = b'test_image_data'
            unit_image = UnitImage(
                description="Изображение для удаления",
                image_data=image_data,
                setting_id=setting_id,
                subscription_only=False
            )
            session.add(unit_image)
            session.commit()
            image_id = unit_image.id

        # Удаляем сеттинг
        with db.get_session() as session:
            setting = session.query(Setting).filter_by(id=setting_id).first()
            session.delete(setting)
            session.commit()

        # Проверяем, что изображение тоже удалено
        with db.get_session() as session:
            deleted_image = session.query(UnitImage).filter_by(id=image_id).first()
            assert deleted_image is None


class TestUnitImageModel:
    """Тесты для модели UnitImage"""

    def test_create_unit_image(self, db):
        """Тест: создание изображения юнита"""
        with db.get_session() as session:
            # Создаем сеттинг
            setting = Setting(
                name="Сеттинг для изображения test_create_unit_image",
                is_tournament=False,
                unlock_cost=Decimal('0'),
                subscription_only=False
            )
            session.add(setting)
            session.commit()
            setting_id = setting.id

            # Создаем изображение
            image_data = b'\x89PNG\r\n\x1a\n'
            unit_image = UnitImage(
                description="Изображение дракона",
                image_data=image_data,
                setting_id=setting_id,
                subscription_only=True
            )
            session.add(unit_image)
            session.commit()

            # Проверяем, что изображение создано
            assert unit_image.id is not None
            assert unit_image.description == "Изображение дракона"
            assert unit_image.subscription_only is True

    def test_unit_image_with_level(self, db):
        """Тест: создание изображения юнита с уровнем"""
        with db.get_session() as session:
            # Создаем сеттинг
            setting = Setting(
                name="Сеттинг для изображения с уровнем test_image_with_level",
                is_tournament=False,
                unlock_cost=Decimal('0'),
                subscription_only=False
            )
            session.add(setting)
            session.commit()
            setting_id = setting.id

            # Используем существующий уровень 1 из миграции
            level = session.query(UnitLevel).filter_by(level=1).first()
            if not level:
                # Если уровня нет, создаем с уникальным номером
                level = UnitLevel(
                    level=81,
                    name="Тестовый уровень test_image_with_level",
                    description="Слабые юниты",
                    min_damage=1,
                    max_damage=5,
                    min_defense=1,
                    max_defense=3,
                    min_health=10,
                    max_health=30,
                    min_speed=1,
                    max_speed=2,
                    min_cost=Decimal('10'),
                    max_cost=Decimal('50')
                )
                session.add(level)
                session.commit()
            level_id = level.id
            level_name = level.name

            # Создаем изображение с уровнем
            image_data = b'\x89PNG\r\n\x1a\n'
            unit_image = UnitImage(
                description="Изображение юнита 1 уровня",
                image_data=image_data,
                setting_id=setting_id,
                unit_level_id=level_id,
                subscription_only=False
            )
            session.add(unit_image)
            session.commit()

            # Проверяем связь с уровнем
            assert unit_image.unit_level_id == level_id
            assert unit_image.unit_level.name == level_name


class TestUnitLevelModel:
    """Тесты для модели UnitLevel"""

    def test_create_unit_level(self, db):
        """Тест: создание уровня юнита"""
        unique_level = get_unique_level_number()
        with db.get_session() as session:
            level = UnitLevel(
                level=unique_level,
                name=f"Тестовый уровень test_create_unit_level_{unique_level}",
                description="Описание тестового уровня",
                min_damage=10,
                max_damage=20,
                min_defense=5,
                max_defense=15,
                min_health=50,
                max_health=100,
                min_speed=2,
                max_speed=4,
                min_cost=Decimal('100'),
                max_cost=Decimal('200')
            )
            session.add(level)
            session.commit()

            # Проверяем, что уровень создан
            assert level.id is not None
            assert level.level == unique_level
            assert f"test_create_unit_level_{unique_level}" in level.name
            assert level.min_damage == 10
            assert level.max_damage == 20
            assert level.min_cost == Decimal('100')
            assert level.max_cost == Decimal('200')

    def test_unit_level_unique_constraint(self, db):
        """Тест: уникальность номера уровня"""
        from sqlalchemy.exc import IntegrityError
        unique_level = get_unique_level_number()

        with db.get_session() as session:
            level1 = UnitLevel(
                level=unique_level,
                name=f"Первый уровень {unique_level} test_unique",
                min_damage=1,
                max_damage=5,
                min_defense=1,
                max_defense=3,
                min_health=10,
                max_health=30,
                min_speed=1,
                max_speed=2,
                min_cost=Decimal('10'),
                max_cost=Decimal('50')
            )
            session.add(level1)
            session.commit()

        # Пытаемся создать уровень с тем же номером в отдельной сессии
        with pytest.raises(IntegrityError):
            with db.get_session() as session:
                level2 = UnitLevel(
                    level=unique_level,  # Тот же номер
                    name=f"Второй уровень {unique_level} test_unique",
                    min_damage=5,
                    max_damage=10,
                    min_defense=3,
                    max_defense=6,
                    min_health=30,
                    max_health=60,
                    min_speed=2,
                    max_speed=3,
                    min_cost=Decimal('50'),
                    max_cost=Decimal('100')
                )
                session.add(level2)
                session.flush()  # Вызываем flush чтобы получить IntegrityError

    def test_unit_level_images_relationship(self, db):
        """Тест: связь уровня с изображениями"""
        unique_level = get_unique_level_number()
        with db.get_session() as session:
            # Создаем сеттинг
            setting = Setting(
                name=f"Сеттинг для уровня test_level_images_rel_{unique_level}",
                is_tournament=False,
                unlock_cost=Decimal('0'),
                subscription_only=False
            )
            session.add(setting)
            session.commit()
            setting_id = setting.id

            # Создаем уровень
            level = UnitLevel(
                level=unique_level,
                name=f"Уровень с изображениями test_level_images_rel_{unique_level}",
                min_damage=1,
                max_damage=5,
                min_defense=1,
                max_defense=3,
                min_health=10,
                max_health=30,
                min_speed=1,
                max_speed=2,
                min_cost=Decimal('10'),
                max_cost=Decimal('50')
            )
            session.add(level)
            session.commit()
            level_id = level.id

            # Создаем изображения с этим уровнем
            image1 = UnitImage(
                description="Изображение 1",
                image_data=b'image1',
                setting_id=setting_id,
                unit_level_id=level_id,
                subscription_only=False
            )
            image2 = UnitImage(
                description="Изображение 2",
                image_data=b'image2',
                setting_id=setting_id,
                unit_level_id=level_id,
                subscription_only=False
            )
            session.add(image1)
            session.add(image2)
            session.commit()

            # Проверяем связь
            level = session.query(UnitLevel).filter_by(id=level_id).first()
            assert len(level.images) == 2

    def test_delete_level_sets_null_on_images(self, db):
        """Тест: удаление уровня устанавливает NULL в изображениях"""
        unique_level = get_unique_level_number()
        with db.get_session() as session:
            # Создаем сеттинг
            setting = Setting(
                name=f"Сеттинг для удаления уровня test_delete_level_{unique_level}",
                is_tournament=False,
                unlock_cost=Decimal('0'),
                subscription_only=False
            )
            session.add(setting)
            session.commit()
            setting_id = setting.id

            # Создаем уровень
            level = UnitLevel(
                level=unique_level,
                name=f"Уровень для удаления test_delete_level_{unique_level}",
                min_damage=1,
                max_damage=5,
                min_defense=1,
                max_defense=3,
                min_health=10,
                max_health=30,
                min_speed=1,
                max_speed=2,
                min_cost=Decimal('10'),
                max_cost=Decimal('50')
            )
            session.add(level)
            session.commit()
            level_id = level.id

            # Создаем изображение с этим уровнем
            image = UnitImage(
                description="Изображение с уровнем",
                image_data=b'image',
                setting_id=setting_id,
                unit_level_id=level_id,
                subscription_only=False
            )
            session.add(image)
            session.commit()
            image_id = image.id

        # Удаляем уровень
        with db.get_session() as session:
            level = session.query(UnitLevel).filter_by(id=level_id).first()
            session.delete(level)
            session.commit()

        # Проверяем, что изображение осталось, но unit_level_id стал NULL
        with db.get_session() as session:
            image = session.query(UnitImage).filter_by(id=image_id).first()
            assert image is not None
            assert image.unit_level_id is None


class TestUnitLevelParameterRanges:
    """Тесты для диапазонов параметров уровней юнитов"""

    def test_level_damage_range(self, db):
        """Тест: диапазон урона уровня"""
        unique_level = get_unique_level_number()
        with db.get_session() as session:
            level = UnitLevel(
                level=unique_level,
                name=f"Тест диапазона урона test_level_damage_range_{unique_level}",
                min_damage=10,
                max_damage=25,
                min_defense=5,
                max_defense=15,
                min_health=50,
                max_health=100,
                min_speed=2,
                max_speed=4,
                min_cost=Decimal('80'),
                max_cost=Decimal('150')
            )
            session.add(level)
            session.commit()

            # Проверяем диапазон
            assert level.min_damage == 10
            assert level.max_damage == 25
            assert level.min_damage < level.max_damage

    def test_level_defense_range(self, db):
        """Тест: диапазон защиты уровня"""
        unique_level = get_unique_level_number()
        with db.get_session() as session:
            level = UnitLevel(
                level=unique_level,
                name=f"Тест диапазона защиты test_level_defense_range_{unique_level}",
                min_damage=5,
                max_damage=15,
                min_defense=8,
                max_defense=20,
                min_health=40,
                max_health=80,
                min_speed=1,
                max_speed=3,
                min_cost=Decimal('60'),
                max_cost=Decimal('120')
            )
            session.add(level)
            session.commit()

            # Проверяем диапазон
            assert level.min_defense == 8
            assert level.max_defense == 20
            assert level.min_defense < level.max_defense

    def test_level_health_range(self, db):
        """Тест: диапазон здоровья уровня"""
        unique_level = get_unique_level_number()
        with db.get_session() as session:
            level = UnitLevel(
                level=unique_level,
                name=f"Тест диапазона здоровья test_level_health_range_{unique_level}",
                min_damage=5,
                max_damage=10,
                min_defense=3,
                max_defense=8,
                min_health=25,
                max_health=75,
                min_speed=1,
                max_speed=2,
                min_cost=Decimal('40'),
                max_cost=Decimal('90')
            )
            session.add(level)
            session.commit()

            # Проверяем диапазон
            assert level.min_health == 25
            assert level.max_health == 75
            assert level.min_health < level.max_health

    def test_level_speed_range(self, db):
        """Тест: диапазон скорости уровня"""
        unique_level = get_unique_level_number()
        with db.get_session() as session:
            level = UnitLevel(
                level=unique_level,
                name=f"Тест диапазона скорости test_level_speed_range_{unique_level}",
                min_damage=3,
                max_damage=8,
                min_defense=2,
                max_defense=6,
                min_health=20,
                max_health=50,
                min_speed=3,
                max_speed=6,
                min_cost=Decimal('30'),
                max_cost=Decimal('70')
            )
            session.add(level)
            session.commit()

            # Проверяем диапазон
            assert level.min_speed == 3
            assert level.max_speed == 6
            assert level.min_speed < level.max_speed

    def test_level_cost_range(self, db):
        """Тест: диапазон стоимости уровня"""
        unique_level = get_unique_level_number()
        with db.get_session() as session:
            level = UnitLevel(
                level=unique_level,
                name=f"Тест диапазона стоимости test_level_cost_range_{unique_level}",
                min_damage=2,
                max_damage=6,
                min_defense=1,
                max_defense=4,
                min_health=15,
                max_health=40,
                min_speed=1,
                max_speed=2,
                min_cost=Decimal('25.50'),
                max_cost=Decimal('65.75')
            )
            session.add(level)
            session.commit()

            # Проверяем диапазон
            assert level.min_cost == Decimal('25.50')
            assert level.max_cost == Decimal('65.75')
            assert level.min_cost < level.max_cost


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
