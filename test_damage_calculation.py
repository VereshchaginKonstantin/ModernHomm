#!/usr/bin/env python3
"""
Тесты для обновленного алгоритма расчета урона
"""

import pytest
from unittest.mock import Mock, patch
from game_engine import GameEngine
from db.models import Unit, User, UserUnit


class TestDamageCalculation:
    """Тесты для алгоритма расчета урона"""

    @pytest.fixture
    def mock_session(self):
        """Мок сессии БД"""
        return Mock()

    @pytest.fixture
    def game_engine(self, mock_session):
        """Создать игровой движок"""
        return GameEngine(mock_session)

    @pytest.fixture
    def test_attacker_unit(self):
        """Создать юнит атакующего"""
        unit = Mock(spec=Unit)
        unit.id = 1
        unit.name = "Атакующий"
        unit.damage = 100
        unit.defense = 10
        unit.health = 200
        unit.speed = 5
        unit.range = 1
        unit.luck = 0.0
        unit.crit_chance = 0.0
        unit.dodge_chance = 0.0
        unit.is_kamikaze = 0
        unit.counterattack_chance = 0.0
        unit.effective_against_unit_id = None
        return unit

    @pytest.fixture
    def test_defender_unit(self):
        """Создать юнит защитника"""
        unit = Mock(spec=Unit)
        unit.id = 2
        unit.name = "Защитник"
        unit.damage = 50
        unit.defense = 20
        unit.health = 150
        unit.speed = 3
        unit.range = 1
        unit.luck = 0.0
        unit.crit_chance = 0.0
        unit.dodge_chance = 0.0
        unit.is_kamikaze = 0
        unit.counterattack_chance = 0.0
        unit.effective_against_unit_id = None
        return unit

    @pytest.fixture
    def mock_attacker(self, test_attacker_unit):
        """Создать мок атакующего BattleUnit"""
        attacker = Mock()
        user_unit = Mock(spec=UserUnit)
        user_unit.unit = test_attacker_unit
        user_unit.count = 10
        attacker.user_unit = user_unit
        attacker.position = 0
        attacker.total_count = 10
        attacker.current_health = test_attacker_unit.health
        attacker.remaining_hp = test_attacker_unit.health
        attacker.fatigue = 0
        attacker.morale = 100
        return attacker

    @pytest.fixture
    def mock_defender(self, test_defender_unit):
        """Создать мок защитника BattleUnit"""
        defender = Mock()
        user_unit = Mock(spec=UserUnit)
        user_unit.unit = test_defender_unit
        user_unit.count = 5
        defender.user_unit = user_unit
        defender.position = 1
        defender.total_count = 5
        defender.current_health = test_defender_unit.health
        defender.remaining_hp = test_defender_unit.health
        defender.fatigue = 0
        defender.morale = 100
        return defender

    @patch('game_engine.random')
    def test_damage_calculation_order(self, mock_random, game_engine, mock_attacker, mock_defender):
        """
        Тест что защита применяется после умножения урона на количество атакующих
        """
        # Фиксируем случайные значения
        mock_random.uniform.return_value = 1.0  # Нет вариативности урона
        mock_random.random.side_effect = [0.5, 0.5, 0.5]  # Нет уклонения, нет крита, нет удачи

        # Рассчитываем урон
        damage, is_crit, log = game_engine._calculate_damage(mock_attacker, mock_defender)

        # Проверяем порядок расчетов:
        # 1. Базовый урон: 100
        # 2. Урон * количество атакующих: 100 * 10 = 1000
        # 3. Защита * количество обороняющихся: 20 * 5 = 100
        # 4. Итоговый урон: max(10, 1000 - 100) = 900

        expected_damage = 900
        assert damage == expected_damage, f"Ожидаемый урон {expected_damage}, получено {damage}"

        # Проверяем что в логе есть информация о новом порядке расчетов
        assert "Количество атакующих: x10" in log
        assert "обороняющихся" in log

    @patch('game_engine.random')
    def test_damage_with_high_defense(self, mock_random, game_engine, mock_attacker, mock_defender):
        """
        Тест что минимальный урон составляет по 1 на каждого атакующего
        """
        # Фиксируем случайные значения
        mock_random.uniform.return_value = 1.0
        mock_random.random.side_effect = [0.5, 0.5, 0.5]

        # Увеличиваем защиту чтобы она превысила урон
        mock_defender.user_unit.unit.defense = 150

        damage, is_crit, log = game_engine._calculate_damage(mock_attacker, mock_defender)

        # Минимальный урон: количество атакующих (10)
        # Расчет: 100 * 10 = 1000, защита 150 * 5 = 750
        # 1000 - 750 = 250, что больше 10, поэтому урон = 250
        expected_min_damage = 250
        assert damage == expected_min_damage, f"Ожидаемый минимальный урон {expected_min_damage}, получено {damage}"

    @patch('game_engine.random')
    def test_damage_with_massive_defense(self, mock_random, game_engine, mock_attacker, mock_defender):
        """
        Тест что при огромной защите урон минимум равен количеству атакующих
        """
        # Фиксируем случайные значения
        mock_random.uniform.return_value = 1.0
        mock_random.random.side_effect = [0.5, 0.5, 0.5]

        # Огромная защита
        mock_defender.user_unit.unit.defense = 500

        damage, is_crit, log = game_engine._calculate_damage(mock_attacker, mock_defender)

        # Расчет: 100 * 10 = 1000, защита 500 * 5 = 2500
        # 1000 - 2500 = -1500, но минимум = 10 атакующих
        expected_min_damage = 10
        assert damage == expected_min_damage, f"Минимальный урон должен быть {expected_min_damage}, получено {damage}"

    @patch('game_engine.random')
    def test_defense_scales_with_defenders(self, mock_random, game_engine, mock_attacker, mock_defender):
        """
        Тест что защита масштабируется с количеством обороняющихся
        """
        # Фиксируем случайные значения
        mock_random.uniform.return_value = 1.0
        mock_random.random.side_effect = [0.5, 0.5, 0.5]

        # Сначала с 5 защитниками
        mock_defender.total_count = 5
        damage_5_defenders, _, _ = game_engine._calculate_damage(mock_attacker, mock_defender)

        # Затем с 10 защитниками
        mock_random.uniform.return_value = 1.0
        mock_random.random.side_effect = [0.5, 0.5, 0.5]
        mock_defender.total_count = 10
        damage_10_defenders, _, _ = game_engine._calculate_damage(mock_attacker, mock_defender)

        # С 5 защитниками: 100 * 10 - 20 * 5 = 1000 - 100 = 900
        # С 10 защитниками: 100 * 10 - 20 * 10 = 1000 - 200 = 800
        assert damage_5_defenders == 900
        assert damage_10_defenders == 800
        assert damage_10_defenders < damage_5_defenders, "Больше защитников должно давать меньший урон"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
