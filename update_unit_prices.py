#!/usr/bin/env python3
"""
Скрипт для обновления стоимости существующих юнитов в базе данных
согласно формуле: Урон + Защита + Здоровье + 100*Дальность + 50*Скорость + 100*Удача + 100*Крит
"""

import os
import json
from decimal import Decimal
from db import Database
from db.models import Unit


def calculate_unit_price(damage: int, defense: int, health: int, unit_range: int, speed: int, luck: float, crit_chance: float) -> Decimal:
    """
    Автоматический расчет стоимости юнита по формуле:
    Урон + Защита + Здоровье + 100*Дальность + 50*Скорость + 100*Удача + 100*Крит
    """
    price = (
        damage +
        defense +
        health +
        100 * unit_range +
        50 * speed +
        100 * luck +
        100 * crit_chance
    )
    return Decimal(str(round(price, 2)))


def update_all_unit_prices():
    """Обновить стоимость всех существующих юнитов"""
    # Инициализировать базу данных
    config_path = 'config.json'
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Файл конфигурации {config_path} не найден!")
        return

    db_url = os.getenv('DATABASE_URL', config.get('database', {}).get('url'))
    db = Database(db_url)

    with db.get_session() as session:
        units = session.query(Unit).all()

        if not units:
            print("Юниты не найдены в базе данных")
            return

        print(f"Найдено юнитов: {len(units)}")
        print("\nОбновление стоимости юнитов...")
        print("-" * 80)

        for unit in units:
            old_price = unit.price
            new_price = calculate_unit_price(
                damage=unit.damage,
                defense=unit.defense,
                health=unit.health,
                unit_range=unit.range,
                speed=unit.speed,
                luck=float(unit.luck),
                crit_chance=float(unit.crit_chance)
            )

            unit.price = new_price

            print(f"Юнит: {unit.name:<15} | Старая цена: {old_price:>8} | Новая цена: {new_price:>8}")

        session.flush()
        print("-" * 80)
        print(f"Успешно обновлено юнитов: {len(units)}")


if __name__ == '__main__':
    update_all_unit_prices()
