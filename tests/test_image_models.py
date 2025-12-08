#!/usr/bin/env python3
"""
Интеграционные тесты для моделей изображений и сеттингов
"""

import pytest
from decimal import Decimal
from db.image_models import Setting, UnitImage
from db.models import Unit


class TestSettingModel:
    """Тесты для модели Setting"""

    def test_create_setting(self, db):
        """Тест: создание сеттинга"""
        with db.get_session() as session:
            setting = Setting(
                name="Тестовый сеттинг",
                description="Описание тестового сеттинга",
                is_tournament=True,
                unlock_cost=Decimal('100.00'),
                subscription_only=False
            )
            session.add(setting)
            session.commit()

            # Проверяем, что сеттинг создан
            assert setting.id is not None
            assert setting.name == "Тестовый сеттинг"
            assert setting.is_tournament is True
            assert setting.unlock_cost == Decimal('100.00')

    def test_setting_with_images_relationship(self, db):
        """Тест: связь сеттинга с изображениями"""
        with db.get_session() as session:
            # Создаем сеттинг
            setting = Setting(
                name="Сеттинг с изображениями",
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
                coin_cost=Decimal('10.00'),
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
                name="Сеттинг для удаления",
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
                coin_cost=Decimal('0'),
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
                name="Сеттинг для изображения",
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
                is_flying=True,
                is_kamikaze=False,
                min_damage=50,
                max_damage=100,
                min_defense=20,
                max_defense=40,
                image_data=image_data,
                setting_id=setting_id,
                coin_cost=Decimal('25.50'),
                subscription_only=True
            )
            session.add(unit_image)
            session.commit()

            # Проверяем, что изображение создано
            assert unit_image.id is not None
            assert unit_image.is_flying is True
            assert unit_image.min_damage == 50
            assert unit_image.coin_cost == Decimal('25.50')
            assert unit_image.subscription_only is True

    def test_unit_image_applicability_flying(self, db):
        """Тест: применимость изображения к летающим юнитам"""
        with db.get_session() as session:
            # Создаем сеттинг и изображение для летающих юнитов
            setting = Setting(name="Test", is_tournament=False, unlock_cost=Decimal('0'), subscription_only=False)
            session.add(setting)
            session.commit()

            image_data = b'test'
            flying_image = UnitImage(
                is_flying=True,  # Только для летающих
                image_data=image_data,
                setting_id=setting.id,
                coin_cost=Decimal('0'),
                subscription_only=False
            )
            session.add(flying_image)
            session.commit()

            # Создаем летающий и нелетающий юниты
            flying_unit = Unit(
                name="Дракон",
                icon="🐉",
                price=Decimal('500'),
                damage=50,
                defense=30,
                health=200,
                range=1,
                speed=3,
                luck=Decimal('0.1'),
                crit_chance=Decimal('0.2'),
                dodge_chance=Decimal('0.1'),
                is_flying=1,
                is_kamikaze=0
            )

            ground_unit = Unit(
                name="Мечник",
                icon="⚔️",
                price=Decimal('100'),
                damage=20,
                defense=10,
                health=100,
                range=1,
                speed=1,
                luck=Decimal('0.05'),
                crit_chance=Decimal('0.1'),
                dodge_chance=Decimal('0.05'),
                is_flying=0,
                is_kamikaze=0
            )

            # Проверяем применимость
            assert flying_image.is_applicable_to_unit(flying_unit) is True
            assert flying_image.is_applicable_to_unit(ground_unit) is False

    def test_unit_image_applicability_damage_range(self, db):
        """Тест: применимость изображения по диапазону урона"""
        with db.get_session() as session:
            # Создаем сеттинг и изображение с диапазоном урона
            setting = Setting(name="Test", is_tournament=False, unlock_cost=Decimal('0'), subscription_only=False)
            session.add(setting)
            session.commit()

            image_data = b'test'
            damage_image = UnitImage(
                min_damage=20,
                max_damage=50,
                image_data=image_data,
                setting_id=setting.id,
                coin_cost=Decimal('0'),
                subscription_only=False
            )
            session.add(damage_image)
            session.commit()

            # Создаем юнитов с разным уроном
            weak_unit = Unit(
                name="Слабый", icon="🗡", price=Decimal('50'),
                damage=10, defense=5, health=50, range=1, speed=1,
                luck=Decimal('0'), crit_chance=Decimal('0'), dodge_chance=Decimal('0'),
                is_flying=0, is_kamikaze=0
            )

            medium_unit = Unit(
                name="Средний", icon="⚔️", price=Decimal('100'),
                damage=30, defense=10, health=100, range=1, speed=1,
                luck=Decimal('0'), crit_chance=Decimal('0'), dodge_chance=Decimal('0'),
                is_flying=0, is_kamikaze=0
            )

            strong_unit = Unit(
                name="Сильный", icon="🗡", price=Decimal('200'),
                damage=60, defense=20, health=150, range=1, speed=1,
                luck=Decimal('0'), crit_chance=Decimal('0'), dodge_chance=Decimal('0'),
                is_flying=0, is_kamikaze=0
            )

            # Проверяем применимость
            assert damage_image.is_applicable_to_unit(weak_unit) is False  # урон < min_damage
            assert damage_image.is_applicable_to_unit(medium_unit) is True  # урон в диапазоне
            assert damage_image.is_applicable_to_unit(strong_unit) is False  # урон > max_damage

    def test_unit_image_applicability_defense_range(self, db):
        """Тест: применимость изображения по диапазону защиты"""
        with db.get_session() as session:
            # Создаем сеттинг и изображение с диапазоном защиты
            setting = Setting(name="Test", is_tournament=False, unlock_cost=Decimal('0'), subscription_only=False)
            session.add(setting)
            session.commit()

            image_data = b'test'
            defense_image = UnitImage(
                min_defense=10,
                max_defense=30,
                image_data=image_data,
                setting_id=setting.id,
                coin_cost=Decimal('0'),
                subscription_only=False
            )
            session.add(defense_image)
            session.commit()

            # Создаем юнитов с разной защитой
            low_def_unit = Unit(
                name="Низкая защита", icon="🛡", price=Decimal('50'),
                damage=20, defense=5, health=80, range=1, speed=1,
                luck=Decimal('0'), crit_chance=Decimal('0'), dodge_chance=Decimal('0'),
                is_flying=0, is_kamikaze=0
            )

            mid_def_unit = Unit(
                name="Средняя защита", icon="🛡", price=Decimal('100'),
                damage=20, defense=20, health=120, range=1, speed=1,
                luck=Decimal('0'), crit_chance=Decimal('0'), dodge_chance=Decimal('0'),
                is_flying=0, is_kamikaze=0
            )

            high_def_unit = Unit(
                name="Высокая защита", icon="🛡", price=Decimal('200'),
                damage=20, defense=40, health=200, range=1, speed=1,
                luck=Decimal('0'), crit_chance=Decimal('0'), dodge_chance=Decimal('0'),
                is_flying=0, is_kamikaze=0
            )

            # Проверяем применимость
            assert defense_image.is_applicable_to_unit(low_def_unit) is False  # защита < min_defense
            assert defense_image.is_applicable_to_unit(mid_def_unit) is True  # защита в диапазоне
            assert defense_image.is_applicable_to_unit(high_def_unit) is False  # защита > max_defense

    def test_unit_image_applicability_kamikaze(self, db):
        """Тест: применимость изображения к камикадзе"""
        with db.get_session() as session:
            # Создаем сеттинг и изображение для камикадзе
            setting = Setting(name="Test", is_tournament=False, unlock_cost=Decimal('0'), subscription_only=False)
            session.add(setting)
            session.commit()

            image_data = b'test'
            kamikaze_image = UnitImage(
                is_kamikaze=True,  # Только для камикадзе
                image_data=image_data,
                setting_id=setting.id,
                coin_cost=Decimal('0'),
                subscription_only=False
            )
            session.add(kamikaze_image)
            session.commit()

            # Создаем камикадзе и обычного юнита
            kamikaze_unit = Unit(
                name="Камикадзе", icon="💣", price=Decimal('150'),
                damage=100, defense=5, health=50, range=1, speed=2,
                luck=Decimal('0'), crit_chance=Decimal('0'), dodge_chance=Decimal('0'),
                is_flying=0, is_kamikaze=1
            )

            normal_unit = Unit(
                name="Обычный", icon="⚔️", price=Decimal('100'),
                damage=30, defense=15, health=100, range=1, speed=1,
                luck=Decimal('0'), crit_chance=Decimal('0'), dodge_chance=Decimal('0'),
                is_flying=0, is_kamikaze=0
            )

            # Проверяем применимость
            assert kamikaze_image.is_applicable_to_unit(kamikaze_unit) is True
            assert kamikaze_image.is_applicable_to_unit(normal_unit) is False

    def test_unit_image_applicability_all_params(self, db):
        """Тест: применимость изображения со всеми параметрами"""
        with db.get_session() as session:
            # Создаем сеттинг и изображение со всеми параметрами
            setting = Setting(name="Test", is_tournament=False, unlock_cost=Decimal('0'), subscription_only=False)
            session.add(setting)
            session.commit()

            image_data = b'test'
            specific_image = UnitImage(
                is_flying=True,
                is_kamikaze=False,
                min_damage=40,
                max_damage=60,
                min_defense=15,
                max_defense=25,
                image_data=image_data,
                setting_id=setting.id,
                coin_cost=Decimal('50.00'),
                subscription_only=True
            )
            session.add(specific_image)
            session.commit()

            # Создаем подходящий юнит
            matching_unit = Unit(
                name="Подходящий дракон", icon="🐉", price=Decimal('400'),
                damage=50, defense=20, health=180, range=2, speed=3,
                luck=Decimal('0.1'), crit_chance=Decimal('0.15'), dodge_chance=Decimal('0.1'),
                is_flying=1, is_kamikaze=0
            )

            # Создаем не подходящий юнит (не летающий)
            non_matching_unit = Unit(
                name="Не подходящий рыцарь", icon="🛡", price=Decimal('300'),
                damage=50, defense=20, health=150, range=1, speed=2,
                luck=Decimal('0.1'), crit_chance=Decimal('0.1'), dodge_chance=Decimal('0.05'),
                is_flying=0, is_kamikaze=0
            )

            # Проверяем применимость
            assert specific_image.is_applicable_to_unit(matching_unit) is True
            assert specific_image.is_applicable_to_unit(non_matching_unit) is False

    def test_unit_image_applicability_none_params(self, db):
        """Тест: изображение с None параметрами применимо к любым юнитам"""
        with db.get_session() as session:
            # Создаем сеттинг и изображение без ограничений
            setting = Setting(name="Test", is_tournament=False, unlock_cost=Decimal('0'), subscription_only=False)
            session.add(setting)
            session.commit()

            image_data = b'test'
            universal_image = UnitImage(
                # Все параметры None - применимо к любым юнитам
                image_data=image_data,
                setting_id=setting.id,
                coin_cost=Decimal('0'),
                subscription_only=False
            )
            session.add(universal_image)
            session.commit()

            # Создаем разные юниты
            flying_unit = Unit(
                name="Дракон", icon="🐉", price=Decimal('500'),
                damage=60, defense=30, health=200, range=2, speed=3,
                luck=Decimal('0.1'), crit_chance=Decimal('0.2'), dodge_chance=Decimal('0.1'),
                is_flying=1, is_kamikaze=0
            )

            kamikaze_unit = Unit(
                name="Камикадзе", icon="💣", price=Decimal('150'),
                damage=100, defense=5, health=50, range=1, speed=2,
                luck=Decimal('0'), crit_chance=Decimal('0'), dodge_chance=Decimal('0.5'),
                is_flying=0, is_kamikaze=1
            )

            normal_unit = Unit(
                name="Мечник", icon="⚔️", price=Decimal('100'),
                damage=25, defense=12, health=100, range=1, speed=1,
                luck=Decimal('0.05'), crit_chance=Decimal('0.1'), dodge_chance=Decimal('0.05'),
                is_flying=0, is_kamikaze=0
            )

            # Проверяем применимость - должно подходить ко всем
            assert universal_image.is_applicable_to_unit(flying_unit) is True
            assert universal_image.is_applicable_to_unit(kamikaze_unit) is True
            assert universal_image.is_applicable_to_unit(normal_unit) is True


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
