#!/usr/bin/env python3
"""
HTML шаблоны для веб-интерфейса управления юнитами
"""

from web.templates import HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE


# Шаблон главной страницы (управление картинками)
IMAGES_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Веб-интерфейс - Управление картинками юнитов</title>
""" + BASE_STYLE + """
</head>
<body>
""" + HEADER_TEMPLATE + """
    <div class="content">
        <h1>Управление картинками юнитов</h1>

    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <div class="stats">
        <div class="stats-item">
            <div class="stats-number">{{ stats.total }}</div>
            <div class="stats-label">Всего юнитов</div>
        </div>
        <div class="stats-item">
            <div class="stats-number">{{ stats.with_images }}</div>
            <div class="stats-label">С картинками</div>
        </div>
        <div class="stats-item">
            <div class="stats-number">{{ stats.without_images }}</div>
            <div class="stats-label">Без картинок</div>
        </div>
    </div>

    <div class="units-grid">
        {% for unit in units %}
        <div class="unit-card">
            <h2>{{ unit.icon }} {{ unit.name }}</h2>
            <div class="unit-info">
                <strong>Цена:</strong> {{ unit.price }} |
                <strong>Урон:</strong> {{ unit.damage }} |
                <strong>Защита:</strong> {{ unit.defense }}
            </div>
            <div class="unit-info">
                <strong>Здоровье:</strong> {{ unit.health }} |
                <strong>Дальность:</strong> {{ unit.range }} |
                <strong>Скорость:</strong> {{ unit.speed }}
            </div>

            {% if unit.image_path and unit.has_image %}
                <img src="/{{ unit.image_path }}" alt="{{ unit.name }}" class="unit-image">
                <form action="{{ url_for('delete_image', unit_id=unit.id) }}" method="POST" style="display: inline;">
                    <button type="submit" class="btn btn-danger" onclick="return confirm('Удалить картинку?')">Удалить картинку</button>
                </form>
            {% else %}
                <div class="no-image">Нет картинки</div>
            {% endif %}

            <form action="{{ url_for('upload_image', unit_id=unit.id) }}" method="POST" enctype="multipart/form-data" class="upload-form">
                <input type="file" name="image" accept="image/png,image/jpeg,image/jpg" class="file-input" required>
                <button type="submit" class="btn">Загрузить</button>
            </form>
        </div>
        {% endfor %}
    </div>
    </div>
    {{ footer_html|safe }}
</body>
</html>
"""

# Шаблон для главной страницы (полный список юнитов)
COMPREHENSIVE_UNITS_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Список юнитов</title>
""" + BASE_STYLE + """
</head>
<body>
""" + HEADER_TEMPLATE + """
    <div class="content">
        <h1>Полный список юнитов</h1>

        {% for unit in units %}
        <div style="background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
            <div style="display: flex; gap: 20px; align-items: start;">
                {% if unit.has_image %}
                <div style="flex-shrink: 0;">
                    <img src="{{ '/' + unit.image_path }}" alt="{{ unit.name }}" style="width: 150px; height: 150px; object-fit: cover; border-radius: 8px; border: 2px solid #ddd;">
                </div>
                {% endif %}

                <div style="flex-grow: 1;">
                    <h2 style="margin: 0 0 10px 0; color: #2c3e50;">{{ unit.icon }} {{ unit.name }}</h2>

                    {% if unit.description %}
                    <p style="color: #7f8c8d; font-style: italic; margin: 0 0 15px 0;">{{ unit.description }}</p>
                    {% endif %}

                    <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px;">
                        <div><strong>💰 Цена:</strong> {{ unit.price }}</div>
                        <div><strong>⚔️ Урон:</strong> {{ unit.damage }}</div>
                        <div><strong>🛡️ Защита:</strong> {{ unit.defense }}</div>
                        <div><strong>❤️ Здоровье:</strong> {{ unit.health }}</div>
                        <div><strong>🎯 Дальность:</strong> {{ unit.range }}</div>
                        <div><strong>⚡ Скорость:</strong> {{ unit.speed }}</div>
                        <div><strong>🍀 Удача:</strong> {{ "%.2f"|format(unit.luck|float * 100) }}%</div>
                        <div><strong>💥 Крит:</strong> {{ "%.2f"|format(unit.crit_chance|float * 100) }}%</div>
                        <div><strong>🏃 Уклонение:</strong> {{ "%.2f"|format(unit.dodge_chance|float * 100) }}%</div>
                        {% if unit.is_kamikaze %}
                        <div><strong>💣 Камикадзе:</strong> Да</div>
                        {% endif %}
                        {% if unit.is_flying %}
                        <div><strong>🦅 Летающий:</strong> Да</div>
                        {% endif %}
                        {% if unit.counterattack_chance > 0 %}
                        <div><strong>🔄 Контратака:</strong> {{ "%.2f"|format(unit.counterattack_chance|float * 100) }}%</div>
                        {% endif %}
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    {{ footer_html|safe }}
</body>
</html>
"""

# Шаблон для управления юнитами
UNITS_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Управление юнитами</title>
""" + BASE_STYLE + """
</head>
<body>
""" + HEADER_TEMPLATE + """
    <div class="content">
        <h1>Управление юнитами</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div style="margin-bottom: 20px;">
            <a href="{{ url_for('admin_create_unit') }}" class="btn btn-primary">Создать нового юнита</a>
            <a href="{{ url_for('import_page') }}" class="btn btn-primary" style="margin-left: 10px;">Импортировать юнитов</a>
        </div>

        <table class="unit-params-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Иконка</th>
                    <th>Название</th>
                    <th>Цена</th>
                    <th>Урон</th>
                    <th>Защита</th>
                    <th>Здоровье</th>
                    <th>Дальность</th>
                    <th>Скорость</th>
                    <th>Удача</th>
                    <th>Крит %</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                {% for unit in units %}
                <tr>
                    <td>{{ unit.id }}</td>
                    <td>{{ unit.icon }}</td>
                    <td>{{ unit.name }}</td>
                    <td>{{ unit.price }}</td>
                    <td>{{ unit.damage }}</td>
                    <td>{{ unit.defense }}</td>
                    <td>{{ unit.health }}</td>
                    <td>{{ unit.range }}</td>
                    <td>{{ unit.speed }}</td>
                    <td>{{ "%.2f"|format(unit.luck|float) }}</td>
                    <td>{{ "%.2f"|format(unit.crit_chance|float * 100) }}%</td>
                    <td>
                        <a href="{{ url_for('admin_edit_unit', unit_id=unit.id) }}" class="btn" style="background-color: #3498db; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px; font-size: 12px;">Редактировать</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    {{ footer_html|safe }}
</body>
</html>
"""

# Шаблон для создания/редактирования юнита
UNIT_FORM_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ 'Редактирование' if unit else 'Создание' }} юнита</title>
""" + BASE_STYLE + """
</head>
<body>
""" + HEADER_TEMPLATE + """
    <div class="content">
        <h1>{{ 'Редактирование' if unit else 'Создание' }} юнита</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div style="background: white; padding: 30px; border-radius: 8px; max-width: 600px; margin: 0 auto;">
            <form method="POST" style="margin: 0;">
                <div class="form-group">
                    <label>Название юнита *</label>
                    <input type="text" name="name" class="form-control" value="{{ unit.name if unit else '' }}" required>
                </div>

                <div class="form-group">
                    <label>Иконка (эмодзи) *</label>
                    <input type="text" name="icon" class="form-control" value="{{ unit.icon if unit else '🎮' }}" required maxlength="10">
                </div>

                <div class="form-group">
                    <label>Описание</label>
                    <textarea name="description" class="form-control" rows="3" maxlength="1000" placeholder="Описание юнита...">{{ unit.description if unit and unit.description else '' }}</textarea>
                    <small class="form-text text-muted">Описание юнита (до 1000 символов)</small>
                </div>

                <div class="form-group">
                    <label>Цена (автоматически рассчитывается)</label>
                    <input type="text" class="form-control" value="{{ unit.price if unit else 'Рассчитается автоматически' }}" readonly disabled style="background-color: #e9ecef; cursor: not-allowed;">
                    <small class="form-text text-muted">Формула: (Урон + Защита + Здоровье + 2×Дальность×(Урон + Защита) + Скорость×(Урон + Защита) + 2×Удача×Урон + 2×Крит×Урон + 10×Уклонение×(Урон + Защита) + 10×Контратака×Урон). Для камикадзе: Урон/5 и Уклонение/50</small>
                </div>

                <div class="form-group">
                    <label>Урон *</label>
                    <input type="number" name="damage" class="form-control" value="{{ unit.damage if unit else '10' }}" min="1" required>
                </div>

                <div class="form-group">
                    <label>Защита *</label>
                    <input type="number" name="defense" class="form-control" value="{{ unit.defense if unit else '0' }}" min="0" required>
                </div>

                <div class="form-group">
                    <label>Здоровье (HP) *</label>
                    <input type="number" name="health" class="form-control" value="{{ unit.health if unit else '100' }}" min="1" required>
                </div>

                <div class="form-group">
                    <label>Дальность атаки *</label>
                    <input type="number" name="range" class="form-control" value="{{ unit.range if unit else '1' }}" min="1" required>
                </div>

                <div class="form-group">
                    <label>Скорость (клеток за ход) *</label>
                    <input type="number" name="speed" class="form-control" value="{{ unit.speed if unit else '1' }}" min="1" required>
                </div>

                <div class="form-group">
                    <label>Удача (0-1, например 0.1 = 10%) *</label>
                    <input type="number" name="luck" class="form-control" value="{{ unit.luck if unit else '0' }}" step="0.01" min="0" max="1" required>
                </div>

                <div class="form-group">
                    <label>Шанс критического удара (0-1, например 0.15 = 15%) *</label>
                    <input type="number" name="crit_chance" class="form-control" value="{{ unit.crit_chance if unit else '0' }}" step="0.01" min="0" max="1" required>
                </div>

                <div class="form-group">
                    <label>Шанс уклонения (0-0.9, например 0.2 = 20%, максимум 90%) *</label>
                    <input type="number" name="dodge_chance" class="form-control" value="{{ unit.dodge_chance if unit else '0' }}" step="0.01" min="0" max="0.9" required>
                    <small class="form-text text-muted">Вероятность полностью избежать урона от атаки (максимум 90%)</small>
                </div>

                <div class="form-group form-check">
                    <input type="checkbox" name="is_kamikaze" class="form-check-input" id="is_kamikaze" value="1" {{ 'checked' if unit and unit.is_kamikaze else '' }}>
                    <label class="form-check-label" for="is_kamikaze">
                        💣 Камикадзе (урон за 1 юнита, -1 юнит после атаки)
                    </label>
                </div>

                <div class="form-group form-check">
                    <input type="checkbox" name="is_flying" class="form-check-input" id="is_flying" value="1" {{ 'checked' if unit and unit.is_flying else '' }}>
                    <label class="form-check-label" for="is_flying">
                        🦅 Летающий (может перемещаться через препятствия)
                    </label>
                </div>

                <div class="form-group">
                    <label>Доля контратаки (0-1, например 0.5 = 50%) *</label>
                    <input type="number" name="counterattack_chance" class="form-control" value="{{ unit.counterattack_chance if unit else '0' }}" step="0.01" min="0" max="1" required>
                    <small class="form-text text-muted">При получении урона наносит ответный урон с этим коэффициентом</small>
                </div>

                <div style="margin-top: 20px;">
                    <button type="submit" class="btn btn-primary">Сохранить</button>
                    <a href="{{ url_for('admin_units_list') }}" class="btn" style="background-color: #95a5a6; color: white; text-decoration: none; margin-left: 10px;">Отмена</a>
                </div>
            </form>
        </div>
    </div>
    {{ footer_html|safe }}
</body>
</html>
"""

# Шаблон страницы рейтинга
LEADERBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Рейтинг игроков - Веб-интерфейс</title>
    """ + BASE_STYLE + """
    <style>
        .leaderboard-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .leaderboard-table th,
        .leaderboard-table td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .leaderboard-table th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        .leaderboard-table tr:hover {
            background-color: #f5f5f5;
        }
        .rank-gold { color: #FFD700; font-weight: bold; }
        .rank-silver { color: #C0C0C0; font-weight: bold; }
        .rank-bronze { color: #CD7F32; font-weight: bold; }
        .pagination {
            margin-top: 20px;
            display: flex;
            justify-content: center;
            gap: 10px;
        }
        .pagination a {
            padding: 8px 12px;
            background-color: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 4px;
        }
        .pagination a.active {
            background-color: #2980b9;
        }
        .pagination a:hover {
            background-color: #2980b9;
        }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """

    <div class="container">
        <h1>🏆 Рейтинг игроков</h1>

        <table class="leaderboard-table">
            <thead>
                <tr>
                    <th>#</th>
                    <th>Игрок</th>
                    <th>🏆 Побед</th>
                    <th>💔 Поражений</th>
                    <th>📊 Винрейт</th>
                    <th>💰 Баланс</th>
                    <th>⚔️ Армия</th>
                </tr>
            </thead>
            <tbody>
                {% for player in players %}
                <tr>
                    <td class="{% if player.rank == 1 %}rank-gold{% elif player.rank == 2 %}rank-silver{% elif player.rank == 3 %}rank-bronze{% endif %}">
                        {{ player.rank }}
                    </td>
                    <td>{{ player.username }}</td>
                    <td>{{ player.wins }}</td>
                    <td>{{ player.losses }}</td>
                    <td>{{ "%.1f"|format(player.win_rate) }}%</td>
                    <td>{{ "%.2f"|format(player.balance) }}</td>
                    <td>{{ "%.2f"|format(player.army_value) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <!-- Пагинация -->
        {% if total_pages > 1 %}
        <div class="pagination">
            {% if page > 1 %}
            <a href="{{ url_for('leaderboard', page=page-1) }}">← Назад</a>
            {% endif %}

            <span style="padding: 8px 12px;">Страница {{ page }} из {{ total_pages }}</span>

            {% if page < total_pages %}
            <a href="{{ url_for('leaderboard', page=page+1) }}">Вперед →</a>
            {% endif %}
        </div>
        {% endif %}
    </div>
    {{ footer_html|safe }}
</body>
</html>
"""

# Шаблон страницы справки
HELP_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Справка по параметрам юнитов</title>
""" + BASE_STYLE + """
</head>
<body>
""" + HEADER_TEMPLATE + """
    <div class="content">
        <h1>Справка по параметрам юнитов</h1>

        <div style="background: white; padding: 30px; border-radius: 8px;">
            <h2>Базовые параметры</h2>
            <table class="unit-params-table">
                <tr>
                    <th style="width: 200px;">Параметр</th>
                    <th>Описание</th>
                    <th style="width: 300px;">Как используется в формулах</th>
                </tr>
                <tr>
                    <td><strong>Цена</strong></td>
                    <td>Стоимость покупки одного юнита</td>
                    <td>Используется при покупке юнитов и расчете награды за убитых врагов</td>
                </tr>
                <tr>
                    <td><strong>Урон (Damage)</strong></td>
                    <td>Базовый урон юнита при атаке</td>
                    <td><code>Урон = damage × (0.9-1.1) × (1 - усталость×0.3) × (1 + мораль×0.2)</code></td>
                </tr>
                <tr>
                    <td><strong>Защита (Defense)</strong></td>
                    <td>Уменьшает входящий урон</td>
                    <td><code>Финальный_урон = max(1, Урон - defense)</code></td>
                </tr>
                <tr>
                    <td><strong>Здоровье (Health)</strong></td>
                    <td>Количество очков жизни каждого юнита</td>
                    <td>При получении урона >= health юнит погибает</td>
                </tr>
                <tr>
                    <td><strong>Дальность (Range)</strong></td>
                    <td>Максимальная дистанция атаки (манхэттенское расстояние)</td>
                    <td><code>Можно_атаковать = |x1-x2| + |y1-y2| ≤ range</code></td>
                </tr>
                <tr>
                    <td><strong>Скорость (Speed)</strong></td>
                    <td>Количество клеток, на которое может переместиться юнит за ход</td>
                    <td>Используется в алгоритме BFS для поиска доступных клеток</td>
                </tr>
                <tr>
                    <td><strong>Удача (Luck)</strong></td>
                    <td>Вероятность нанести максимальный урон (0-1, где 0.1 = 10%)</td>
                    <td><code>if random() < luck: Урон = Урон × 1.5</code></td>
                </tr>
                <tr>
                    <td><strong>Шанс крита (Crit Chance)</strong></td>
                    <td>Вероятность критического удара (0-1, где 0.15 = 15%)</td>
                    <td><code>Шанс = crit_chance + мораль×0.2 - усталость×0.2<br>if random() < Шанс: Урон = Урон × 2</code></td>
                </tr>
            </table>

            <h2 style="margin-top: 40px;">Динамические параметры (во время боя)</h2>
            <table class="unit-params-table">
                <tr>
                    <th style="width: 200px;">Параметр</th>
                    <th>Описание</th>
                    <th style="width: 300px;">Влияние на бой</th>
                </tr>
                <tr>
                    <td><strong>Мораль</strong></td>
                    <td>Повышается при успешных атаках (0-100%)</td>
                    <td>
                        • Увеличивает урон до +20%<br>
                        • Увеличивает шанс крита до +20%<br>
                        • +10 при успешной атаке
                    </td>
                </tr>
                <tr>
                    <td><strong>Усталость</strong></td>
                    <td>Повышается при неудачах (0-100%)</td>
                    <td>
                        • Снижает урон до -30%<br>
                        • Снижает шанс крита до -20%<br>
                        • +10 при неудачной атаке<br>
                        • -5 при успешной атаке
                    </td>
                </tr>
            </table>

            <h2 style="margin-top: 40px;">Формула расчета стоимости юнита</h2>
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <p><strong>Для обычных юнитов:</strong></p>
                <div style="background-color: white; padding: 15px; border-radius: 4px; margin: 10px 0; font-family: monospace;">
                    <code>Цена = Урон + Защита + Здоровье + 100×Дальность + 100×Скорость + 1000×Удача + 1000×Крит + 5000×Уклонение + 1000×Контратака</code>
                </div>
                <p><strong>Для камикадзе:</strong></p>
                <div style="background-color: white; padding: 15px; border-radius: 4px; margin: 10px 0; font-family: monospace;">
                    <code>Цена = (Урон/5) + Защита + Здоровье + 100×Дальность + 100×Скорость + 1000×Удача + 1000×Крит + 100×Уклонение + 1000×Контратака</code>
                </div>
                <p style="color: #666; margin-top: 15px;"><em>Примечание: Для камикадзе урон учитывается с коэффициентом 1/5, а уклонение с коэффициентом 1/50 (5000/50=100), так как эти юниты жертвуют собой после атаки.</em></p>
            </div>

            <h2 style="margin-top: 40px;">Полная формула расчета урона</h2>
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; font-family: monospace;">
                <p><strong>1.</strong> Базовый урон со случайностью: <code>base = damage × random(0.9, 1.1)</code></p>
                <p><strong>2.</strong> Модификатор усталости: <code>fatigue_mod = 1 - (усталость / 100) × 0.3</code></p>
                <p><strong>3.</strong> Модификатор морали: <code>morale_mod = мораль / 100</code></p>
                <p><strong>4.</strong> Урон с модификаторами: <code>dmg = base × fatigue_mod × morale_mod</code></p>
                <p><strong>5.</strong> Проверка эффективности: <code>if эффективен: dmg = dmg × 1.5</code></p>
                <p><strong>6.</strong> Проверка критического удара: <code>crit_chance_final = crit_chance + (мораль/100)×0.2 - (усталость/100)×0.2</code></p>
                <p><strong>7.</strong> Если крит: <code>dmg = dmg × 2</code></p>
                <p><strong>8.</strong> Проверка удачи: <code>if random() < luck: dmg = dmg × 1.5</code></p>
                <p><strong>9.</strong> Умножение на количество атакующих: <code>dmg_multiplied = dmg × кол-во_атакующих</code></p>
                <p><strong>10.</strong> Расчет задетых юнитов: <code>задетые_юниты = 1 + floor(0.5 × (dmg_multiplied - здоровье) / здоровье)</code></p>
                <p><strong>11.</strong> Применение защиты: <code>defense_reduction = defense × |задетые_юниты|</code></p>
                <p><strong>12.</strong> Итоговый урон: <code>total_dmg = dmg_multiplied - defense_reduction</code></p>
            </div>

            <h2 style="margin-top: 40px;">Награда за победу</h2>
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px;">
                <p><strong>При завершении игры победитель получает награду:</strong></p>
                <div style="background-color: white; padding: 15px; border-radius: 4px; margin: 10px 0; font-family: monospace;">
                    <code>Награда = (Стоимость убитых юнитов противника) × 0.9</code>
                </div>
                <p><strong>Чистая прибыль рассчитывается как:</strong></p>
                <div style="background-color: white; padding: 15px; border-radius: 4px; margin: 10px 0; font-family: monospace;">
                    <code>Чистая прибыль = Награда - Стоимость потерянных своих юнитов</code>
                </div>
                <p style="color: #666; margin-top: 15px;"><em>Примечание: Учитываются все убитые юниты обеих сторон. Победитель получает 90% от стоимости убитых юнитов противника, но теряет стоимость своих погибших юнитов.</em></p>
            </div>
        </div>
    </div>
    {{ footer_html|safe }}
</body>
</html>
"""

# Шаблон страницы импорта
IMPORT_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Импорт юнитов</title>
""" + BASE_STYLE + """
</head>
<body>
""" + HEADER_TEMPLATE + """
    <div class="content">
        <h1>Импорт юнитов</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }}">{{ message }}</div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <div class="import-form">
            <h2>Загрузить архив с юнитами</h2>
            <p style="color: #666; margin-bottom: 20px;">
                <strong>Внимание!</strong> Импорт заменит все существующие юниты на юниты из архива.
                Убедитесь, что вы сделали экспорт текущих юнитов перед импортом.
            </p>
            <form method="POST" enctype="multipart/form-data">
                <div class="form-group">
                    <label>Выберите ZIP-архив с юнитами</label>
                    <input type="file" name="archive" class="form-control" accept=".zip" required>
                </div>
                <div style="margin-top: 20px;">
                    <button type="submit" class="btn btn-danger" onclick="return confirm('Вы уверены? Это заменит всех существующих юнитов!')">Импортировать</button>
                    <a href="{{ url_for('admin_units_list') }}" class="btn" style="background-color: #95a5a6; color: white; text-decoration: none; margin-left: 10px;">Отмена</a>
                </div>
            </form>
        </div>
    </div>
    {{ footer_html|safe }}
</body>
</html>
"""

# Шаблон страницы логина
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Вход в веб-интерфейс</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
        }
        .login-container {
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            width: 100%;
            max-width: 400px;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            color: #555;
            font-weight: bold;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }
        input[type="text"]:focus,
        input[type="password"]:focus {
            outline: none;
            border-color: #3498db;
        }
        button {
            width: 100%;
            padding: 12px;
            background-color: #3498db;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover {
            background-color: #2980b9;
        }
        .flash-messages {
            margin-bottom: 20px;
        }
        .flash {
            padding: 10px;
            border-radius: 4px;
            margin-bottom: 10px;
        }
        .flash.error {
            background-color: #e74c3c;
            color: white;
        }
        .flash.success {
            background-color: #2ecc71;
            color: white;
        }
        .info {
            text-align: center;
            margin-top: 20px;
            color: #7f8c8d;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>🔐 Вход в веб-интерфейс</h1>

        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                <div class="flash-messages">
                    {% for category, message in messages %}
                        <div class="flash {{ category }}">{{ message }}</div>
                    {% endfor %}
                </div>
            {% endif %}
        {% endwith %}

        <form method="POST">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" required autofocus>
            </div>

            <div class="form-group">
                <label for="password">Пароль:</label>
                <input type="password" id="password" name="password" required>
            </div>

            <button type="submit">Войти</button>
        </form>

        <div class="info">
            Установите пароль через команду /password в боте
        </div>
    </div>
</body>
</html>
"""
