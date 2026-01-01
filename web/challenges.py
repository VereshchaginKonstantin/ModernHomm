#!/usr/bin/env python3
"""
Blueprint для управления челленджами (PvE сражения с AI)
"""

from flask import Blueprint, render_template_string, request, redirect, url_for, flash, session, Response, jsonify
import os
import json
import base64
from db.models import Challenge, ChallengeUnit, ChallengeCompletion, AIDifficulty, GameRace, RaceUnit, BattleFieldTemplate, Field
from db.repository import Database

# Database connection
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
db = Database(db_url)
from web.templates import HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE, get_web_version, get_bot_version
from functools import wraps

challenges_bp = Blueprint('challenges', __name__, url_prefix='/challenges')


def login_required(f):
    """Декоратор для проверки авторизации"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Декоратор для проверки прав администратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('user_id') not in [1, 4] and session.get('username') != 'okarien':
            flash('Доступ запрещен', 'error')
            return redirect(url_for('arena.index'))
        return f(*args, **kwargs)
    return decorated_function


def get_user_balance(db_session, user_id):
    """Получить баланс пользователя"""
    from db.models import GameUser
    user = db_session.query(GameUser).filter_by(id=user_id).first()
    if user:
        return {
            'coins': int(user.balance) if user.balance else 0,
            'glory': int(user.glory) if user.glory else 0,
            'crystals': int(user.crystals) if user.crystals else 0
        }
    return None


# Список сложностей AI
AI_DIFFICULTIES = [
    {'value': 'easy', 'label': 'Легкий', 'description': 'AI делает случайные ходы'},
    {'value': 'normal', 'label': 'Нормальный', 'description': 'AI использует базовую тактику'},
    {'value': 'hard', 'label': 'Сложный', 'description': 'AI использует продвинутую тактику'},
    {'value': 'nightmare', 'label': 'Кошмар', 'description': 'AI оптимально использует все возможности'},
]


CHALLENGES_LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Челленджи - ModernHomm</title>
    """ + BASE_STYLE + """
    <style>
        .challenges-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            padding: 20px;
        }
        .challenge-card {
            background: white;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .challenge-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0,0,0,0.15);
        }
        .challenge-card.inactive {
            opacity: 0.6;
            background: #f0f0f0;
        }
        .challenge-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 15px;
        }
        .challenge-sprite {
            width: 80px;
            height: 80px;
            border-radius: 10px;
            object-fit: cover;
            background: #ecf0f1;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 40px;
        }
        .challenge-title {
            font-size: 20px;
            font-weight: bold;
            margin: 0;
        }
        .challenge-difficulty {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 12px;
            font-weight: bold;
            margin-top: 5px;
        }
        .difficulty-easy { background: #27ae60; color: white; }
        .difficulty-normal { background: #3498db; color: white; }
        .difficulty-hard { background: #e67e22; color: white; }
        .difficulty-nightmare { background: #c0392b; color: white; }

        .challenge-description {
            color: #666;
            margin: 10px 0;
            font-size: 14px;
        }
        .challenge-rewards {
            display: flex;
            gap: 20px;
            margin: 15px 0;
            padding: 10px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .reward-item {
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .reward-icon { font-size: 18px; }
        .reward-value { font-weight: bold; }

        .challenge-units {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }
        .units-title {
            font-size: 14px;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .units-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .unit-badge {
            display: flex;
            align-items: center;
            gap: 5px;
            padding: 5px 10px;
            background: #ecf0f1;
            border-radius: 15px;
            font-size: 12px;
        }
        .unit-count {
            font-weight: bold;
            color: #3498db;
        }

        .challenge-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            text-decoration: none;
            font-size: 14px;
            display: inline-flex;
            align-items: center;
            gap: 5px;
        }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #27ae60; color: white; }
        .btn-warning { background: #f39c12; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn:hover { opacity: 0.9; }

        .add-challenge-btn {
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 16px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            text-decoration: none;
        }

        .stats-bar {
            display: flex;
            gap: 20px;
            padding: 15px 20px;
            background: #34495e;
            color: white;
            margin-bottom: 20px;
        }
        .stat-item {
            display: flex;
            align-items: center;
            gap: 8px;
        }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """

    <div class="stats-bar">
        <a href="{{ url_for('challenges.create_challenge') }}" class="btn btn-success add-challenge-btn">+ Создать челлендж</a>
        <div class="stat-item">
            <span>Всего челленджей:</span>
            <strong>{{ challenges|length }}</strong>
        </div>
        <div class="stat-item">
            <span>Активных:</span>
            <strong>{{ challenges|selectattr('is_active')|list|length }}</strong>
        </div>
    </div>

    <div class="challenges-grid">
        {% for challenge in challenges %}
        <div class="challenge-card {{ 'inactive' if not challenge.is_active else '' }}">
            <div class="challenge-header">
                {% if challenge.sprite_data %}
                <img src="{{ url_for('challenges.challenge_sprite', challenge_id=challenge.id) }}"
                     class="challenge-sprite" alt="{{ challenge.name }}">
                {% else %}
                <div class="challenge-sprite">⚔️</div>
                {% endif %}
                <div>
                    <h3 class="challenge-title">{{ challenge.name }}</h3>
                    <span class="challenge-difficulty difficulty-{{ challenge.ai_difficulty.value }}">
                        {{ {'easy': 'Легкий', 'normal': 'Нормальный', 'hard': 'Сложный', 'nightmare': 'Кошмар'}[challenge.ai_difficulty.value] }}
                    </span>
                </div>
            </div>

            {% if challenge.description %}
            <p class="challenge-description">{{ challenge.description }}</p>
            {% endif %}

            <div class="challenge-rewards">
                <div class="reward-item">
                    <span class="reward-icon">🪙</span>
                    <span class="reward-value">{{ challenge.reward_gold }}</span>
                    <span>золота</span>
                </div>
                <div class="reward-item">
                    <span class="reward-icon">💎</span>
                    <span class="reward-value">{{ challenge.reward_gems }}</span>
                    <span>кристаллов</span>
                </div>
            </div>

            <div class="challenge-units">
                <div class="units-title">Армия противника ({{ challenge.units|length }} стеков):</div>
                <div class="units-list">
                    {% for unit in challenge.units %}
                    <div class="unit-badge">
                        <span class="unit-count">{{ unit.count }}x</span>
                        <span>{{ unit.race_unit.name }}</span>
                    </div>
                    {% else %}
                    <span style="color: #999;">Армия не настроена</span>
                    {% endfor %}
                </div>
            </div>

            <div class="challenge-actions">
                <a href="{{ url_for('challenges.edit_challenge', challenge_id=challenge.id) }}" class="btn btn-primary">✏️ Редактировать</a>
                <a href="{{ url_for('challenges.toggle_challenge', challenge_id=challenge.id) }}"
                   class="btn {{ 'btn-warning' if challenge.is_active else 'btn-success' }}">
                    {{ '⏸️ Деактивировать' if challenge.is_active else '▶️ Активировать' }}
                </a>
                <form action="{{ url_for('challenges.delete_challenge', challenge_id=challenge.id) }}"
                      method="post" style="display:inline"
                      onsubmit="return confirm('Удалить челлендж {{ challenge.name }}?')">
                    <button type="submit" class="btn btn-danger">🗑️</button>
                </form>
            </div>
        </div>
        {% else %}
        <div style="grid-column: 1/-1; text-align: center; padding: 50px; color: #666;">
            <h2>Челленджи ещё не созданы</h2>
            <p>Нажмите кнопку "Создать челлендж" вверху страницы</p>
        </div>
        {% endfor %}
    </div>

    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


CHALLENGE_FORM_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ 'Редактирование' if challenge else 'Создание' }} челленджа - ModernHomm</title>
    """ + BASE_STYLE + """
    <style>
        .form-container {
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        .form-card {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .form-title {
            font-size: 24px;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid #3498db;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #2c3e50;
        }
        .form-group input, .form-group select, .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 6px;
            font-size: 14px;
        }
        .form-group textarea {
            min-height: 100px;
            resize: vertical;
        }
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }
        .form-row-3 {
            display: grid;
            grid-template-columns: 1fr 1fr 1fr;
            gap: 20px;
        }

        .sprite-preview {
            width: 150px;
            height: 150px;
            border: 2px dashed #ddd;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 10px;
            background: #f8f9fa;
        }
        .sprite-preview img {
            max-width: 100%;
            max-height: 100%;
            border-radius: 8px;
        }

        .army-section {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #eee;
        }
        .army-title {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .race-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        .race-tab {
            padding: 10px 20px;
            background: #ecf0f1;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }
        .race-tab:hover { background: #bdc3c7; }
        .race-tab.active { background: #3498db; color: white; }

        .units-grid {
            display: none;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 15px;
        }
        .units-grid.active { display: grid; }

        .unit-card {
            background: #f8f9fa;
            border: 2px solid #ddd;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            transition: all 0.2s;
        }
        .unit-card.selected {
            border-color: #3498db;
            background: #e8f4fc;
        }
        .unit-name {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .unit-level {
            font-size: 12px;
            color: #666;
            margin-bottom: 10px;
        }
        .unit-count-input {
            width: 80px;
            padding: 8px;
            text-align: center;
            border: 1px solid #ddd;
            border-radius: 6px;
        }

        .selected-units {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .selected-units-title {
            font-weight: bold;
            margin-bottom: 10px;
        }
        .selected-unit-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            background: white;
            border-radius: 6px;
            margin-bottom: 5px;
        }
        .selected-unit-info {
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .remove-unit {
            background: #e74c3c;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 4px 8px;
            cursor: pointer;
        }

        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .btn-primary { background: #3498db; color: white; }
        .btn-secondary { background: #95a5a6; color: white; }
        .btn-success { background: #27ae60; color: white; }
        .btn:hover { opacity: 0.9; }

        .form-actions {
            display: flex;
            gap: 15px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #eee;
        }

        .difficulty-option {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s;
        }
        .difficulty-option:hover { border-color: #3498db; }
        .difficulty-option.selected { border-color: #3498db; background: #e8f4fc; }
        .difficulty-options {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """

    <div class="form-container">
        <div class="form-card">
            <h2 class="form-title">{{ 'Редактирование челленджа' if challenge else 'Создание нового челленджа' }}</h2>

            <form method="post" enctype="multipart/form-data" id="challenge-form">
                <div class="form-group">
                    <label>Название челленджа *</label>
                    <input type="text" name="name" value="{{ challenge.name if challenge else '' }}" required>
                </div>

                <div class="form-group">
                    <label>Описание</label>
                    <textarea name="description">{{ challenge.description if challenge else '' }}</textarea>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Награда в золоте 🪙</label>
                        <input type="number" name="reward_gold" value="{{ challenge.reward_gold if challenge else 100 }}" min="0">
                    </div>
                    <div class="form-group">
                        <label>Награда в кристаллах 💎</label>
                        <input type="number" name="reward_gems" value="{{ challenge.reward_gems if challenge else 10 }}" min="0">
                    </div>
                </div>

                <div class="form-group">
                    <label>Сложность AI</label>
                    <div class="difficulty-options">
                        {% for diff in difficulties %}
                        <label class="difficulty-option {{ 'selected' if challenge and challenge.ai_difficulty.value == diff.value else ('selected' if not challenge and diff.value == 'normal' else '') }}">
                            <input type="radio" name="ai_difficulty" value="{{ diff.value }}"
                                   {{ 'checked' if challenge and challenge.ai_difficulty.value == diff.value else ('checked' if not challenge and diff.value == 'normal' else '') }}
                                   style="display:none;">
                            <div>
                                <strong>{{ diff.label }}</strong>
                                <div style="font-size:12px; color:#666;">{{ diff.description }}</div>
                            </div>
                        </label>
                        {% endfor %}
                    </div>
                </div>

                <div class="form-row-3">
                    <div class="form-group">
                        <label>Порядок сортировки</label>
                        <input type="number" name="sort_order" value="{{ challenge.sort_order if challenge else 0 }}">
                    </div>
                    <div class="form-group">
                        <label>Спрайт</label>
                        <input type="file" name="sprite" accept="image/*">
                        <div class="sprite-preview">
                            {% if challenge and challenge.sprite_data %}
                            <img src="{{ url_for('challenges.challenge_sprite', challenge_id=challenge.id) }}" alt="Спрайт">
                            {% else %}
                            <span style="color:#999;">Нет спрайта</span>
                            {% endif %}
                        </div>
                    </div>
                    <div class="form-group">
                        <label>Статус</label>
                        <select name="is_active">
                            <option value="1" {{ 'selected' if not challenge or challenge.is_active else '' }}>Активен</option>
                            <option value="0" {{ 'selected' if challenge and not challenge.is_active else '' }}>Неактивен</option>
                        </select>
                    </div>
                </div>

                <!-- Секция предустановленных полей -->
                <div class="army-section">
                    <div class="army-title">
                        <span>🗺️</span>
                        <span>Предустановленные шаблоны полей (опционально)</span>
                    </div>
                    <p style="color:#666; font-size:13px; margin-bottom:15px;">
                        Если выбран шаблон - он будет использоваться для челленджа вместо случайного.
                        Шаблон выбирается в зависимости от размера поля (определяется автоматически по размеру армий).
                    </p>
                    <div class="form-row-3">
                        <div class="form-group">
                            <label>Шаблон для поля 5x5</label>
                            <select name="field_template_5x5_id">
                                <option value="">-- Случайный --</option>
                                {% for template in field_templates_5x5 %}
                                <option value="{{ template.id }}" {{ 'selected' if challenge and challenge.field_template_5x5_id == template.id else '' }}>
                                    {{ template.name }}
                                </option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Шаблон для поля 7x7</label>
                            <select name="field_template_7x7_id">
                                <option value="">-- Случайный --</option>
                                {% for template in field_templates_7x7 %}
                                <option value="{{ template.id }}" {{ 'selected' if challenge and challenge.field_template_7x7_id == template.id else '' }}>
                                    {{ template.name }}
                                </option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Шаблон для поля 10x10</label>
                            <select name="field_template_10x10_id">
                                <option value="">-- Случайный --</option>
                                {% for template in field_templates_10x10 %}
                                <option value="{{ template.id }}" {{ 'selected' if challenge and challenge.field_template_10x10_id == template.id else '' }}>
                                    {{ template.name }}
                                </option>
                                {% endfor %}
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Секция армии AI -->
                <div class="army-section">
                    <div class="army-title">
                        <span>⚔️</span>
                        <span>Армия противника (AI)</span>
                    </div>

                    <!-- Табы рас -->
                    <div class="race-tabs">
                        {% for race in races %}
                        <button type="button" class="race-tab {{ 'active' if loop.first else '' }}"
                                data-race-id="{{ race.id }}">
                            {{ race.name }}
                        </button>
                        {% endfor %}
                    </div>

                    <!-- Юниты по расам -->
                    {% for race in races %}
                    <div class="units-grid {{ 'active' if loop.first else '' }}" data-race-id="{{ race.id }}">
                        {% for unit in race.race_units %}
                        <div class="unit-card" data-unit-id="{{ unit.id }}">
                            <div class="unit-name">{{ unit.name }}</div>
                            <div class="unit-level">Ур. {{ unit.unit_level.level if unit.unit_level else '?' }}</div>
                            <input type="number" class="unit-count-input"
                                   name="unit_{{ unit.id }}"
                                   value="{{ (selected_units.get(unit.id, 0) if selected_units else 0) }}"
                                   min="0" max="9999"
                                   placeholder="0">
                        </div>
                        {% endfor %}
                    </div>
                    {% endfor %}

                    <!-- Список выбранных юнитов -->
                    <div class="selected-units" id="selected-units">
                        <div class="selected-units-title">Выбранные юниты:</div>
                        <div id="selected-units-list">
                            {% if challenge and challenge.units %}
                                {% for cu in challenge.units %}
                                <div class="selected-unit-item" data-unit-id="{{ cu.race_unit_id }}">
                                    <div class="selected-unit-info">
                                        <span class="unit-count">{{ cu.count }}x</span>
                                        <span>{{ cu.race_unit.name }}</span>
                                        <span style="color:#999;">({{ cu.race_unit.race.name }})</span>
                                    </div>
                                </div>
                                {% endfor %}
                            {% else %}
                            <div style="color:#999; padding:10px;">Юниты не выбраны</div>
                            {% endif %}
                        </div>
                    </div>
                </div>

                <div class="form-actions">
                    <button type="submit" class="btn btn-success">
                        💾 {{ 'Сохранить' if challenge else 'Создать' }}
                    </button>
                    <a href="{{ url_for('challenges.challenges_list') }}" class="btn btn-secondary">
                        ← Назад к списку
                    </a>
                </div>
            </form>
        </div>
    </div>

    <script>
        // Переключение табов рас
        document.querySelectorAll('.race-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.race-tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.units-grid').forEach(g => g.classList.remove('active'));

                tab.classList.add('active');
                document.querySelector(`.units-grid[data-race-id="${tab.dataset.raceId}"]`).classList.add('active');
            });
        });

        // Обновление списка выбранных юнитов
        function updateSelectedUnits() {
            const list = document.getElementById('selected-units-list');
            list.innerHTML = '';
            let hasUnits = false;

            document.querySelectorAll('.unit-count-input').forEach(input => {
                const count = parseInt(input.value) || 0;
                if (count > 0) {
                    hasUnits = true;
                    const card = input.closest('.unit-card');
                    const name = card.querySelector('.unit-name').textContent;
                    const raceName = document.querySelector(`.race-tab.active`)?.textContent || '';

                    const item = document.createElement('div');
                    item.className = 'selected-unit-item';
                    item.innerHTML = `
                        <div class="selected-unit-info">
                            <span class="unit-count">${count}x</span>
                            <span>${name}</span>
                            <span style="color:#999;">(${raceName})</span>
                        </div>
                    `;
                    list.appendChild(item);

                    card.classList.add('selected');
                } else {
                    const card = input.closest('.unit-card');
                    card.classList.remove('selected');
                }
            });

            if (!hasUnits) {
                list.innerHTML = '<div style="color:#999; padding:10px;">Юниты не выбраны</div>';
            }
        }

        // Слушаем изменения в инпутах
        document.querySelectorAll('.unit-count-input').forEach(input => {
            input.addEventListener('change', updateSelectedUnits);
            input.addEventListener('input', updateSelectedUnits);
        });

        // Выбор сложности
        document.querySelectorAll('.difficulty-option').forEach(option => {
            option.addEventListener('click', () => {
                document.querySelectorAll('.difficulty-option').forEach(o => o.classList.remove('selected'));
                option.classList.add('selected');
            });
        });

        // Инициализация выбранных юнитов
        updateSelectedUnits();
    </script>

    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


@challenges_bp.route('/')
@admin_required
def challenges_list():
    """Список всех челленджей"""
    with db.get_session() as session:
        challenges = session.query(Challenge).order_by(Challenge.sort_order, Challenge.id).all()

        return render_template_string(
            CHALLENGES_LIST_TEMPLATE,
            challenges=challenges,
            active_page='challenges'
        )


@challenges_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create_challenge():
    """Создание нового челленджа"""
    with db.get_session() as session:
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            if not name:
                flash('Название челленджа обязательно', 'error')
                return redirect(url_for('challenges.create_challenge'))

            # Обрабатываем предустановленные шаблоны полей
            ft_5x5 = request.form.get('field_template_5x5_id', '').strip()
            ft_7x7 = request.form.get('field_template_7x7_id', '').strip()
            ft_10x10 = request.form.get('field_template_10x10_id', '').strip()

            # Создаём челлендж
            challenge = Challenge(
                name=name,
                description=request.form.get('description', '').strip() or None,
                reward_gold=int(request.form.get('reward_gold', 0)),
                reward_gems=int(request.form.get('reward_gems', 0)),
                ai_difficulty=AIDifficulty(request.form.get('ai_difficulty', 'normal')),
                is_active=request.form.get('is_active') == '1',
                sort_order=int(request.form.get('sort_order', 0)),
                field_template_5x5_id=int(ft_5x5) if ft_5x5 else None,
                field_template_7x7_id=int(ft_7x7) if ft_7x7 else None,
                field_template_10x10_id=int(ft_10x10) if ft_10x10 else None
            )

            # Обрабатываем спрайт
            sprite = request.files.get('sprite')
            if sprite and sprite.filename:
                challenge.sprite_data = sprite.read()
                challenge.sprite_mime_type = sprite.content_type

            session.add(challenge)
            session.flush()  # Получаем ID

            # Добавляем юнитов
            for key, value in request.form.items():
                if key.startswith('unit_'):
                    unit_id = int(key.replace('unit_', ''))
                    count = int(value) if value else 0
                    if count > 0:
                        cu = ChallengeUnit(
                            challenge_id=challenge.id,
                            race_unit_id=unit_id,
                            count=count
                        )
                        session.add(cu)

            session.commit()
            flash(f'Челлендж "{name}" создан', 'success')
            return redirect(url_for('challenges.challenges_list'))

        # GET - показать форму
        races = session.query(GameRace).order_by(GameRace.name).all()

        # Получаем шаблоны полей для каждого размера
        field_5x5 = session.query(Field).filter_by(width=5, height=5).first()
        field_7x7 = session.query(Field).filter_by(width=7, height=7).first()
        field_10x10 = session.query(Field).filter_by(width=10, height=10).first()

        field_templates_5x5 = session.query(BattleFieldTemplate).filter(
            BattleFieldTemplate.field_size_id == field_5x5.id,
            BattleFieldTemplate.is_active == True
        ).order_by(BattleFieldTemplate.name).all() if field_5x5 else []

        field_templates_7x7 = session.query(BattleFieldTemplate).filter(
            BattleFieldTemplate.field_size_id == field_7x7.id,
            BattleFieldTemplate.is_active == True
        ).order_by(BattleFieldTemplate.name).all() if field_7x7 else []

        field_templates_10x10 = session.query(BattleFieldTemplate).filter(
            BattleFieldTemplate.field_size_id == field_10x10.id,
            BattleFieldTemplate.is_active == True
        ).order_by(BattleFieldTemplate.name).all() if field_10x10 else []

        return render_template_string(
            CHALLENGE_FORM_TEMPLATE,
            challenge=None,
            races=races,
            selected_units={},
            difficulties=AI_DIFFICULTIES,
            field_templates_5x5=field_templates_5x5,
            field_templates_7x7=field_templates_7x7,
            field_templates_10x10=field_templates_10x10,
            active_page='challenges'
        )


@challenges_bp.route('/<int:challenge_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_challenge(challenge_id):
    """Редактирование челленджа"""
    with db.get_session() as session:
        challenge = session.query(Challenge).filter_by(id=challenge_id).first()
        if not challenge:
            flash('Челлендж не найден', 'error')
            return redirect(url_for('challenges.challenges_list'))

        if request.method == 'POST':
            challenge.name = request.form.get('name', '').strip()
            challenge.description = request.form.get('description', '').strip() or None
            challenge.reward_gold = int(request.form.get('reward_gold', 0))
            challenge.reward_gems = int(request.form.get('reward_gems', 0))
            challenge.ai_difficulty = AIDifficulty(request.form.get('ai_difficulty', 'normal'))
            challenge.is_active = request.form.get('is_active') == '1'
            challenge.sort_order = int(request.form.get('sort_order', 0))

            # Обрабатываем предустановленные шаблоны полей
            ft_5x5 = request.form.get('field_template_5x5_id', '').strip()
            ft_7x7 = request.form.get('field_template_7x7_id', '').strip()
            ft_10x10 = request.form.get('field_template_10x10_id', '').strip()
            challenge.field_template_5x5_id = int(ft_5x5) if ft_5x5 else None
            challenge.field_template_7x7_id = int(ft_7x7) if ft_7x7 else None
            challenge.field_template_10x10_id = int(ft_10x10) if ft_10x10 else None

            # Обрабатываем спрайт
            sprite = request.files.get('sprite')
            if sprite and sprite.filename:
                challenge.sprite_data = sprite.read()
                challenge.sprite_mime_type = sprite.content_type

            # Удаляем старых юнитов и добавляем новых
            session.query(ChallengeUnit).filter_by(challenge_id=challenge.id).delete()

            for key, value in request.form.items():
                if key.startswith('unit_'):
                    unit_id = int(key.replace('unit_', ''))
                    count = int(value) if value else 0
                    if count > 0:
                        cu = ChallengeUnit(
                            challenge_id=challenge.id,
                            race_unit_id=unit_id,
                            count=count
                        )
                        session.add(cu)

            session.commit()
            flash(f'Челлендж "{challenge.name}" обновлён', 'success')
            return redirect(url_for('challenges.challenges_list'))

        # GET - показать форму
        races = session.query(GameRace).order_by(GameRace.name).all()

        # Собираем выбранных юнитов
        selected_units = {cu.race_unit_id: cu.count for cu in challenge.units}

        # Получаем шаблоны полей для каждого размера
        field_5x5 = session.query(Field).filter_by(width=5, height=5).first()
        field_7x7 = session.query(Field).filter_by(width=7, height=7).first()
        field_10x10 = session.query(Field).filter_by(width=10, height=10).first()

        field_templates_5x5 = session.query(BattleFieldTemplate).filter(
            BattleFieldTemplate.field_size_id == field_5x5.id,
            BattleFieldTemplate.is_active == True
        ).order_by(BattleFieldTemplate.name).all() if field_5x5 else []

        field_templates_7x7 = session.query(BattleFieldTemplate).filter(
            BattleFieldTemplate.field_size_id == field_7x7.id,
            BattleFieldTemplate.is_active == True
        ).order_by(BattleFieldTemplate.name).all() if field_7x7 else []

        field_templates_10x10 = session.query(BattleFieldTemplate).filter(
            BattleFieldTemplate.field_size_id == field_10x10.id,
            BattleFieldTemplate.is_active == True
        ).order_by(BattleFieldTemplate.name).all() if field_10x10 else []

        return render_template_string(
            CHALLENGE_FORM_TEMPLATE,
            challenge=challenge,
            races=races,
            selected_units=selected_units,
            difficulties=AI_DIFFICULTIES,
            field_templates_5x5=field_templates_5x5,
            field_templates_7x7=field_templates_7x7,
            field_templates_10x10=field_templates_10x10,
            active_page='challenges'
        )


@challenges_bp.route('/<int:challenge_id>/toggle')
@admin_required
def toggle_challenge(challenge_id):
    """Переключение статуса активности челленджа"""
    with db.get_session() as session:
        challenge = session.query(Challenge).filter_by(id=challenge_id).first()
        if challenge:
            challenge.is_active = not challenge.is_active
            session.commit()
            status = 'активирован' if challenge.is_active else 'деактивирован'
            flash(f'Челлендж "{challenge.name}" {status}', 'success')
    return redirect(url_for('challenges.challenges_list'))


@challenges_bp.route('/<int:challenge_id>/delete', methods=['POST'])
@admin_required
def delete_challenge(challenge_id):
    """Удаление челленджа"""
    with db.get_session() as session:
        challenge = session.query(Challenge).filter_by(id=challenge_id).first()
        if challenge:
            name = challenge.name
            session.delete(challenge)
            session.commit()
            flash(f'Челлендж "{name}" удалён', 'success')
    return redirect(url_for('challenges.challenges_list'))


@challenges_bp.route('/<int:challenge_id>/sprite')
def challenge_sprite(challenge_id):
    """Возвращает спрайт челленджа"""
    with db.get_session() as session:
        challenge = session.query(Challenge).filter_by(id=challenge_id).first()
        if challenge and challenge.sprite_data:
            return Response(
                challenge.sprite_data,
                mimetype=challenge.sprite_mime_type or 'image/png'
            )
    # Возвращаем пустой пиксель если нет спрайта
    return Response(
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82',
        mimetype='image/png'
    )


# API endpoints для Godot Arena
@challenges_bp.route('/api/list')
def api_list_challenges():
    """API: Список активных челленджей для Godot"""
    with db.get_session() as session:
        challenges = session.query(Challenge).filter_by(is_active=True).order_by(Challenge.sort_order, Challenge.id).all()

        result = []
        for c in challenges:
            result.append({
                'id': c.id,
                'name': c.name,
                'description': c.description,
                'reward_gold': c.reward_gold,
                'reward_gems': c.reward_gems,
                'ai_difficulty': c.ai_difficulty.value,
                'sprite_url': url_for('challenges.challenge_sprite', challenge_id=c.id, _external=True) if c.sprite_data else None,
                'units_count': len(c.units),
                'total_units': sum(u.count for u in c.units)
            })

        return jsonify(result)


@challenges_bp.route('/api/<int:challenge_id>')
def api_get_challenge(challenge_id):
    """API: Получить детали челленджа"""
    with db.get_session() as session:
        challenge = session.query(Challenge).filter_by(id=challenge_id, is_active=True).first()
        if not challenge:
            return jsonify({'error': 'Challenge not found'}), 404

        units = []
        for cu in challenge.units:
            units.append({
                'race_unit_id': cu.race_unit_id,
                'count': cu.count,
                'name': cu.race_unit.name,
                'race_name': cu.race_unit.race.name if cu.race_unit.race else None,
                'level': cu.race_unit.unit_level.level if cu.race_unit.unit_level else None
            })

        return jsonify({
            'id': challenge.id,
            'name': challenge.name,
            'description': challenge.description,
            'reward_gold': challenge.reward_gold,
            'reward_gems': challenge.reward_gems,
            'ai_difficulty': challenge.ai_difficulty.value,
            'sprite_url': url_for('challenges.challenge_sprite', challenge_id=challenge.id, _external=True) if challenge.sprite_data else None,
            'units': units
        })
