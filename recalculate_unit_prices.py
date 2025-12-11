#!/usr/bin/env python3
"""
Скрипт для пересчета стоимостей всех юнитов с новой формулой
"""

import os
import json
from decimal import Decimal
from db.models import Unit
from db import Database
from web.app import calculate_unit_price


def main():
    # Загрузить конфигурацию
    with open('config.json', 'r') as f:
        config = json.load(f)

    # Подключиться к базе данных
    db_url = os.getenv('DATABASE_URL', config.get('database', {}).get('url'))
    db = Database(db_url)

    print("Пересчитываю стоимости всех юнитов...")
    print("-" * 80)

    with db.get_session() as session:
        units = session.query(Unit).all()

        for unit in units:
            # Рассчитать новую стоимость
            old_price = unit.price
            new_price = calculate_unit_price(
                unit.damage,
                unit.defense,
                unit.health,
                unit.range,
                unit.speed,
                float(unit.luck),
                float(unit.crit_chance),
                float(unit.dodge_chance),
                unit.is_kamikaze,
                float(unit.counterattack_chance)
            )

            # Обновить стоимость
            unit.price = new_price

            print(f"ID {unit.id}: {unit.name}")
            print(f"  Старая цена: {old_price}")
            print(f"  Новая цена:  {new_price}")
            print(f"  Изменение:   {new_price - old_price} ({((new_price - old_price) / old_price * 100) if old_price != 0 else 0:.2f}%)")
            print()

        # Сохранить изменения
        session.commit()
        print("-" * 80)
        print(f"✅ Обновлено {len(units)} юнитов")


if __name__ == '__main__':
    main()
