#!/usr/bin/env python3
"""
Blueprint для редактора боевых полей
"""

from flask import Blueprint, render_template_string, request, redirect, url_for, flash, session, Response, jsonify
from sqlalchemy.orm import Session
import os
from db.models import (
    Field, BattleFieldTemplate, BattleFieldObstacle, BattleFieldDecoration, DecorationType,
    ObstacleTemplate, DecorationTemplate
)
from db.repository import Database

# Database connection
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
db = Database(db_url)
from web.templates import HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE, get_web_version, get_bot_version
from functools import wraps

fields_bp = Blueprint('fields', __name__, url_prefix='/fields')


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


FIELDS_LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Редактор полей - ModernHomm</title>
    """ + BASE_STYLE + """
    <style>
        .field-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .field-info h3 {
            margin: 0 0 10px 0;
            color: #333;
        }
        .field-info p {
            margin: 5px 0;
            color: #666;
        }
        .field-size {
            display: inline-block;
            padding: 5px 12px;
            background: #3498db;
            color: white;
            border-radius: 4px;
            font-size: 14px;
        }
        .field-status {
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
        }
        .field-status.active {
            background: #27ae60;
            color: white;
        }
        .field-status.inactive {
            background: #95a5a6;
            color: white;
        }
        .create-btn {
            display: inline-block;
            padding: 15px 30px;
            background: #27ae60;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-size: 18px;
            margin-bottom: 20px;
        }
        .create-btn:hover {
            background: #219a52;
        }
        .field-actions {
            display: flex;
            gap: 10px;
        }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>🗺️ Редактор боевых полей</h1>

        <a href="{{ url_for('fields.create_field') }}" class="create-btn">+ Создать новое поле</a>

        {% if templates %}
        <h2>Созданные поля ({{ templates|length }})</h2>
        {% for template in templates %}
        <div class="field-card">
            <div class="field-info">
                <h3>{{ template.name }}</h3>
                <p>{{ template.description or 'Без описания' }}</p>
                <p>
                    <span class="field-size">{{ template.field_size.name }}</span>
                    <span class="field-status {{ 'active' if template.is_active else 'inactive' }}">
                        {{ 'Активно' if template.is_active else 'Неактивно' }}
                    </span>
                </p>
                <p style="font-size: 12px; color: #999;">
                    Препятствий: {{ template.obstacles|length }} |
                    Декораций: {{ template.decorations|length }}
                </p>
            </div>
            <div class="field-actions">
                <a href="{{ url_for('fields.edit_field', template_id=template.id) }}" class="btn btn-primary">✏️ Редактировать</a>
                <form action="{{ url_for('fields.toggle_field', template_id=template.id) }}" method="post" style="margin: 0;">
                    <button type="submit" class="btn {{ 'btn-secondary' if template.is_active else 'btn-success' }}">
                        {{ '⏸️ Деактивировать' if template.is_active else '▶️ Активировать' }}
                    </button>
                </form>
                <form action="{{ url_for('fields.delete_field', template_id=template.id) }}" method="post" style="margin: 0;" onsubmit="return confirm('Удалить поле {{ template.name }}?');">
                    <button type="submit" class="btn btn-danger">🗑️ Удалить</button>
                </form>
            </div>
        </div>
        {% endfor %}
        {% else %}
        <div class="alert alert-info" style="background: #e8f4fd; border: 1px solid #bee5eb; color: #0c5460; padding: 20px; border-radius: 8px;">
            <p>Поля ещё не созданы. Нажмите кнопку выше, чтобы создать первое поле.</p>
        </div>
        {% endif %}
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


FIELD_EDITOR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ 'Редактирование' if template else 'Создание' }} поля - ModernHomm</title>
    """ + BASE_STYLE + """
    <style>
        .editor-container {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 20px;
        }
        .sidebar {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .field-preview {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-height: 500px;
            overflow: hidden;
            position: relative;
        }
        .field-viewport {
            width: 100%;
            height: 600px;
            overflow: hidden;
            position: relative;
            cursor: grab;
        }
        .field-viewport:active {
            cursor: grabbing;
        }
        .field-viewport.panning {
            cursor: grabbing;
        }
        .grid-container {
            position: absolute;
            background: #4a8c4a;
            border-radius: 8px;
            transform-origin: top left;
        }
        .grid-wrapper {
            position: relative;
            display: inline-block;
        }
        .grid {
            display: grid;
            overflow: hidden;
            gap: 2px;
            background: rgba(0,0,0,0.2);
            padding: 2px;
            position: relative;
            z-index: 10;
        }
        .cell {
            width: 50px;
            height: 50px;
            background: #5a9c5a;
            border: 1px solid rgba(0,0,0,0.1);
            box-sizing: border-box;
            cursor: pointer;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: background 0.2s;
        }
        .cell:hover {
            background: #6aac6a;
        }
        .cell.obstacle {
            background: #808078;
        }
        .cell.obstacle.has-sprite {
            background: transparent;
            overflow: visible;
        }
        .cell.obstacle.has-sprite.sprite-origin {
            /* Спрайт выходит за пределы ячейки на соседние */
            overflow: visible;
            z-index: 10;
        }
        .cell img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }
        .cell img.multi-cell-sprite {
            max-width: none;
            max-height: none;
            object-fit: cover;
            pointer-events: none;
        }
        .decoration-zone {
            position: absolute;
            width: 50px;
            height: 50px;
            background: rgba(139, 69, 19, 0.3);
            border: 1px solid rgba(139, 69, 19, 0.3);
            box-sizing: border-box;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
        }
        .decoration-zone:hover {
            background: rgba(139, 69, 19, 0.5);
        }
        .decoration-zone.has-decoration {
            background: rgba(34, 139, 34, 0.3);
            border-color: rgba(34, 139, 34, 0.5);
        }
        .cell.selected, .decoration-zone.selected {
            outline: 3px solid #3498db;
            outline-offset: -3px;
            box-shadow: 0 0 10px rgba(52, 152, 219, 0.5);
        }
        .tool-panel {
            margin-bottom: 20px;
        }
        .tool-panel h3 {
            margin: 0 0 10px 0;
        }
        .tool-btn {
            display: block;
            width: 100%;
            padding: 12px;
            margin-bottom: 8px;
            border: 2px solid #ddd;
            background: white;
            cursor: pointer;
            border-radius: 4px;
            text-align: left;
            transition: all 0.2s;
        }
        .tool-btn:hover {
            border-color: #3498db;
        }
        .tool-btn.active {
            border-color: #3498db;
            background: #e8f4fd;
        }
        .decoration-types {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            margin-top: 10px;
        }
        .decoration-type {
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
            text-align: center;
            cursor: pointer;
        }
        .decoration-type:hover {
            background: #f0f0f0;
        }
        .decoration-type.active {
            border-color: #27ae60;
            background: #e8f6ef;
        }
        .element-templates {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 10px 0;
        }
        .element-template {
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 8px;
            border: 2px solid #ddd;
            border-radius: 8px;
            cursor: pointer;
            min-width: 60px;
            transition: all 0.2s;
        }
        .element-template:hover {
            border-color: #3498db;
            background: #f0f7fc;
        }
        .element-template.active {
            border-color: #27ae60;
            background: #e8f6ef;
        }
        .element-template .template-icon {
            font-size: 24px;
        }
        .element-template .template-icon-img {
            width: 40px;
            height: 40px;
            object-fit: contain;
        }
        .element-template .template-name {
            font-size: 10px;
            margin-top: 4px;
            text-align: center;
            max-width: 60px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .element-template .template-size {
            font-size: 9px;
            color: #999;
        }
        .decoration-type-group {
            display: flex;
            gap: 5px;
            margin-bottom: 8px;
            width: 100%;
        }
        .decoration-type-group .decoration-type {
            padding: 8px;
            font-size: 18px;
        }
        .sprite-upload {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #ddd;
        }
        .legend {
            margin-top: 20px;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 4px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }
        .legend-color {
            width: 30px;
            height: 30px;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>{{ '✏️ Редактирование поля' if template else '🗺️ Создание нового поля' }}</h1>

        <form method="post" enctype="multipart/form-data" id="field-form">
            <div class="editor-container">
                <div class="sidebar">
                    <div class="form-group">
                        <label>Название поля</label>
                        <input type="text" name="name" class="form-control" value="{{ template.name if template else '' }}" required>
                    </div>

                    <div class="form-group">
                        <label>Описание</label>
                        <textarea name="description" class="form-control" rows="3">{{ template.description if template else '' }}</textarea>
                    </div>

                    <div class="form-group">
                        <label>Размер поля</label>
                        <select name="field_size_id" class="form-control" id="field-size-select" {{ 'disabled' if template else '' }}>
                            {% for field_size in field_sizes %}
                            <option value="{{ field_size.id }}" {{ 'selected' if template and template.field_size_id == field_size.id else '' }}>
                                {{ field_size.name }} ({{ field_size.width }}x{{ field_size.height }})
                            </option>
                            {% endfor %}
                        </select>
                        {% if template %}
                        <input type="hidden" name="field_size_id" value="{{ template.field_size_id }}">
                        {% endif %}
                    </div>

                    <div class="tool-panel">
                        <h3>Инструменты</h3>
                        <button type="button" class="tool-btn active" data-tool="select">
                            🖱️ Выделение
                        </button>
                        <button type="button" class="tool-btn" data-tool="obstacle">
                            🪨 Препятствие
                        </button>
                        <button type="button" class="tool-btn" data-tool="decoration">
                            🌲 Декорация
                        </button>
                        <button type="button" class="tool-btn" data-tool="erase">
                            🧹 Очистка
                        </button>
                    </div>

                    <!-- Панель выбора шаблона препятствия -->
                    <div id="obstacle-panel" style="display: none;">
                        <h4>Выберите препятствие</h4>
                        <div class="element-templates" id="obstacle-templates">
                            <div class="element-template active" data-template="default" data-width="1" data-height="1">
                                <span class="template-icon">🪨</span>
                                <span class="template-name">1x1</span>
                            </div>
                            {% for tmpl in obstacle_templates %}
                            <div class="element-template" data-template="{{ tmpl.id }}" data-width="{{ tmpl.width }}" data-height="{{ tmpl.height }}">
                                {% if tmpl.sprite_data %}
                                <img src="{{ url_for('elements.get_obstacle_template_sprite', template_id=tmpl.id) }}" class="template-icon-img">
                                {% else %}
                                <span class="template-icon">🪨</span>
                                {% endif %}
                                <span class="template-name">{{ tmpl.name }}</span>
                                <span class="template-size">{{ tmpl.width }}x{{ tmpl.height }}</span>
                            </div>
                            {% endfor %}
                        </div>
                        <a href="{{ url_for('elements.elements_list') }}" style="font-size: 12px; color: #3498db;">+ Создать новый шаблон</a>
                    </div>

                    <!-- Панель выбора типа декорации -->
                    <div id="decoration-panel" style="display: none;">
                        <h4>Выберите декорацию</h4>
                        <div class="element-templates" id="decoration-templates">
                            <!-- Базовые типы декораций -->
                            <div class="decoration-type-group">
                                <div class="decoration-type active" data-type="tree" data-width="1" data-height="1">🌲</div>
                                <div class="decoration-type" data-type="river" data-width="1" data-height="1">🌊</div>
                                <div class="decoration-type" data-type="rock" data-width="1" data-height="1">🪨</div>
                                <div class="decoration-type" data-type="bush" data-width="1" data-height="1">🌿</div>
                                <div class="decoration-type" data-type="flower" data-width="1" data-height="1">🌸</div>
                                <div class="decoration-type" data-type="custom" data-width="1" data-height="1">⭐</div>
                            </div>
                            <!-- Шаблоны декораций -->
                            {% for tmpl in decoration_templates %}
                            <div class="element-template" data-template="{{ tmpl.id }}" data-type="{{ tmpl.decoration_type.value }}" data-width="{{ tmpl.width }}" data-height="{{ tmpl.height }}">
                                {% if tmpl.sprite_data %}
                                <img src="{{ url_for('elements.get_decoration_template_sprite', template_id=tmpl.id) }}" class="template-icon-img">
                                {% else %}
                                <span class="template-icon">{{ decoration_emojis.get(tmpl.decoration_type.value, '⭐') }}</span>
                                {% endif %}
                                <span class="template-name">{{ tmpl.name }}</span>
                                <span class="template-size">{{ tmpl.width }}x{{ tmpl.height }}</span>
                            </div>
                            {% endfor %}
                        </div>
                        <a href="{{ url_for('elements.elements_list') }}" style="font-size: 12px; color: #3498db;">+ Создать новый шаблон</a>
                    </div>

                    <div class="sprite-upload" id="sprite-upload">
                        <h4>📷 Загрузить спрайт</h4>
                        <p id="sprite-hint" style="font-size: 12px; color: #666; margin-bottom: 10px;">
                            Нажмите на препятствие или декорацию инструментом "Выделение", чтобы загрузить картинку
                        </p>
                        <div id="sprite-upload-controls" style="display: none;">
                            <p style="font-size: 14px; color: #333; margin-bottom: 10px;">
                                <strong>Выбрано:</strong> <span id="selected-cell-info"></span>
                            </p>
                            <input type="file" id="sprite-file" accept="image/*" style="margin-bottom: 10px;">
                            <button type="button" id="clear-sprite-btn" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;">
                                🗑️ Удалить спрайт
                            </button>
                        </div>
                    </div>

                    <div class="legend">
                        <h4 style="margin: 0 0 10px 0;">Легенда</h4>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #5a9c5a;"></div>
                            <span>Трава (проходимо)</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: #808078;"></div>
                            <span>Препятствие</span>
                        </div>
                        <div class="legend-item">
                            <div class="legend-color" style="background: rgba(139, 69, 19, 0.3); border: 1px dashed rgba(139, 69, 19, 0.5);"></div>
                            <span>Зона декораций</span>
                        </div>
                    </div>
                </div>

                <div class="field-preview">
                    <p style="font-size: 12px; color: #666; margin: 0 0 10px 0;">
                        💡 Зажмите правую кнопку мыши для перемещения поля
                    </p>
                    <div class="field-viewport" id="field-viewport">
                        <div class="grid-container" id="grid-container">
                            <div class="grid-wrapper" id="grid-wrapper">
                                <div class="grid" id="field-grid" style="grid-template-columns: repeat({{ template.field_size.width if template else 5 }}, 50px);">
                                    <!-- Ячейки генерируются JavaScript -->
                                </div>
                                <!-- Зоны декораций генерируются JavaScript -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Скрытые поля для данных -->
            <input type="hidden" name="obstacles_data" id="obstacles-data" value="{{ obstacles_json }}">
            <input type="hidden" name="decorations_data" id="decorations-data" value="{{ decorations_json }}">

            <div style="margin-top: 20px; display: flex; gap: 10px;">
                <button type="submit" class="btn btn-success" style="padding: 15px 30px; font-size: 16px;">
                    💾 {{ 'Сохранить изменения' if template else 'Создать поле' }}
                </button>
                <a href="{{ url_for('fields.fields_list') }}" class="btn btn-secondary" style="padding: 15px 30px; font-size: 16px;">
                    ❌ Отмена
                </a>
            </div>
        </form>
    </div>

    <script>
        const fieldSizes = {{ field_sizes_json|safe }};
        const initialObstacles = {{ obstacles_json|safe if obstacles_json else '[]' }};
        const initialDecorations = {{ decorations_json|safe if decorations_json else '[]' }};

        let currentTool = 'select';
        let currentDecorationType = 'tree';
        let obstacles = [...initialObstacles];
        let decorations = [...initialDecorations];
        let selectedCell = null;

        // Переменные для размеров элементов
        let currentObstacleWidth = 1;
        let currentObstacleHeight = 1;
        let currentObstacleTemplateId = null;
        let currentDecorationWidth = 1;
        let currentDecorationHeight = 1;
        let currentDecorationTemplateId = null;

        // Переменные для панорамирования
        let isPanning = false;
        let panStartX = 0;
        let panStartY = 0;
        let panOffsetX = 0;
        let panOffsetY = 0;

        // Инициализация
        document.addEventListener('DOMContentLoaded', function() {
            initGrid();
            initTools();
            initDecorationTypes();
            initObstacleTemplates();
            initSpriteUpload();
            initFieldSizeChange();
            initPanning();
        });

        function initGrid() {
            const sizeSelect = document.getElementById('field-size-select');
            const sizeId = parseInt(sizeSelect.value);
            const size = fieldSizes.find(s => s.id === sizeId);
            if (!size) return;

            renderGrid(size.width, size.height);
        }

        function renderGrid(width, height) {
            const grid = document.getElementById('field-grid');
            const wrapper = document.getElementById('grid-wrapper');
            const container = document.getElementById('grid-container');

            grid.style.gridTemplateColumns = `repeat(${width}, 50px)`;
            grid.innerHTML = '';

            // Удаляем старые зоны декораций
            wrapper.querySelectorAll('.decoration-zone').forEach(el => el.remove());

            // Создаём ячейки поля
            for (let y = 0; y < height; y++) {
                for (let x = 0; x < width; x++) {
                    const cell = document.createElement('div');
                    cell.className = 'cell';
                    cell.dataset.x = x;
                    cell.dataset.y = y;
                    cell.addEventListener('click', () => handleCellClick(x, y, cell));
                    grid.appendChild(cell);
                }
            }

            // Рендерим существующие препятствия
            obstacles.forEach(obstacle => renderObstacleCells(obstacle));

            // Создаём зоны декораций вокруг поля (5 клеток с каждого края)
            const cellSize = 52; // 50px + 2px gap
            const decorationRange = 5; // 5 клеток с каждого края поля

            // Рассчитываем размеры
            const fieldWidthPx = width * cellSize;
            const fieldHeightPx = height * cellSize;
            const totalWidth = fieldWidthPx + 2 * decorationRange * cellSize;
            const totalHeight = fieldHeightPx + 2 * decorationRange * cellSize;

            // Устанавливаем размер wrapper и padding для grid
            wrapper.style.width = totalWidth + 'px';
            wrapper.style.height = totalHeight + 'px';

            // Позиционируем grid в центре wrapper
            grid.style.position = 'absolute';
            grid.style.left = (decorationRange * cellSize) + 'px';
            grid.style.top = (decorationRange * cellSize) + 'px';

            // Создаём зоны декораций только вокруг поля (5 клеток с каждого края)
            for (let dy = -decorationRange; dy < height + decorationRange; dy++) {
                for (let dx = -decorationRange; dx < width + decorationRange; dx++) {
                    // Пропускаем ячейки внутри игрового поля
                    if (dx >= 0 && dx < width && dy >= 0 && dy < height) {
                        continue;
                    }
                    createDecorationZone(wrapper, dx, dy, width, height, cellSize, decorationRange);
                }
            }
        }

        function createDecorationZone(wrapper, x, y, fieldWidth, fieldHeight, cellSize, decorationRange) {
            const zone = document.createElement('div');
            zone.className = 'decoration-zone';
            zone.dataset.x = x;
            zone.dataset.y = y;

            // Позиционирование: (x + decorationRange) даёт позицию от 0
            const offsetX = (x + decorationRange) * cellSize;
            const offsetY = (y + decorationRange) * cellSize;
            zone.style.position = 'absolute';
            zone.style.left = offsetX + 'px';
            zone.style.top = offsetY + 'px';

            // Проверяем, есть ли декорация
            const decoration = decorations.find(d => d.x === x && d.y === y);
            if (decoration) {
                zone.classList.add('has-decoration');
                if (decoration.sprite) {
                    zone.innerHTML = `<img src="${decoration.sprite}" style="max-width: 100%; max-height: 100%;">`;
                } else {
                    zone.textContent = getDecorationEmoji(decoration.type);
                }
            }

            zone.addEventListener('click', () => handleDecorationClick(x, y, zone));
            wrapper.appendChild(zone);
        }

        function getDecorationEmoji(type) {
            const emojis = {
                'tree': '🌲',
                'river': '🌊',
                'rock': '🪨',
                'bush': '🌿',
                'flower': '🌸',
                'custom': '⭐'
            };
            return emojis[type] || '❓';
        }

        function handleCellClick(x, y, cell) {
            if (currentTool === 'obstacle') {
                const existingIndex = obstacles.findIndex(o => o.x === x && o.y === y);
                if (existingIndex >= 0) {
                    // Удаляем препятствие и очищаем все занятые клетки
                    const obs = obstacles[existingIndex];
                    clearObstacleCells(obs);
                    obstacles.splice(existingIndex, 1);
                } else {
                    // Добавляем препятствие с размерами
                    const newObstacle = {
                        x, y,
                        width: currentObstacleWidth,
                        height: currentObstacleHeight,
                        templateId: currentObstacleTemplateId,
                        sprite: null
                    };
                    obstacles.push(newObstacle);
                    renderObstacleCells(newObstacle);
                }
                updateObstaclesData();
            } else if (currentTool === 'erase') {
                // Ищем препятствие которое занимает эту клетку
                const obstacleIndex = obstacles.findIndex(o => {
                    const w = o.width || 1;
                    const h = o.height || 1;
                    return x >= o.x && x < o.x + w && y >= o.y && y < o.y + h;
                });
                if (obstacleIndex >= 0) {
                    const obs = obstacles[obstacleIndex];
                    clearObstacleCells(obs);
                    obstacles.splice(obstacleIndex, 1);
                    updateObstaclesData();
                }
            } else if (currentTool === 'select') {
                // Ищем препятствие которое занимает эту клетку
                const obstacleIndex = obstacles.findIndex(o => {
                    const w = o.width || 1;
                    const h = o.height || 1;
                    return x >= o.x && x < o.x + w && y >= o.y && y < o.y + h;
                });
                if (obstacleIndex >= 0) {
                    selectCellForSprite('obstacle', obstacles[obstacleIndex].x, obstacles[obstacleIndex].y, cell, obstacles[obstacleIndex]);
                }
            }
        }

        function renderObstacleCells(obstacle) {
            const w = obstacle.width || 1;
            const h = obstacle.height || 1;
            const cellSize = 50;
            const gap = 2;
            // Размер спрайта с учётом gap между ячейками
            const spriteWidth = w * cellSize + (w - 1) * gap;
            const spriteHeight = h * cellSize + (h - 1) * gap;

            for (let dy = 0; dy < h; dy++) {
                for (let dx = 0; dx < w; dx++) {
                    const cell = document.querySelector(`.cell[data-x="${obstacle.x + dx}"][data-y="${obstacle.y + dy}"]`);
                    if (cell) {
                        cell.classList.add('obstacle');
                        // Только первая клетка показывает спрайт
                        if (dx === 0 && dy === 0) {
                            const hasSprite = obstacle.sprite || obstacle.templateId;
                            if (hasSprite) {
                                cell.classList.add('has-sprite', 'sprite-origin');
                                let spriteUrl = obstacle.sprite;
                                if (!spriteUrl && obstacle.templateId) {
                                    spriteUrl = `/elements/api/obstacles/${obstacle.templateId}/sprite`;
                                }
                                cell.innerHTML = `<img src="${spriteUrl}" class="multi-cell-sprite" style="width: ${spriteWidth}px; height: ${spriteHeight}px; position: absolute; left: 0; top: 0; z-index: 5; clip-path: inset(0 0 0 0);" onerror="this.parentElement.textContent='🪨'; this.parentElement.classList.remove('has-sprite', 'sprite-origin');">`;
                            } else {
                                cell.textContent = '🪨';
                            }
                        } else {
                            // Остальные ячейки делаем прозрачными если есть спрайт
                            if (obstacle.sprite || obstacle.templateId) {
                                cell.classList.add('has-sprite');
                            }
                        }
                    }
                }
            }
        }

        function clearObstacleCells(obstacle) {
            const w = obstacle.width || 1;
            const h = obstacle.height || 1;
            for (let dy = 0; dy < h; dy++) {
                for (let dx = 0; dx < w; dx++) {
                    const cell = document.querySelector(`.cell[data-x="${obstacle.x + dx}"][data-y="${obstacle.y + dy}"]`);
                    if (cell) {
                        cell.classList.remove('obstacle', 'has-sprite', 'sprite-origin');
                        cell.textContent = '';
                        cell.innerHTML = '';
                    }
                }
            }
        }

        function handleDecorationClick(x, y, zone) {
            if (currentTool === 'decoration') {
                const existingIndex = decorations.findIndex(d => d.x === x && d.y === y);
                if (existingIndex >= 0) {
                    // Удаляем декорацию
                    decorations.splice(existingIndex, 1);
                    zone.classList.remove('has-decoration');
                    zone.textContent = '';
                    zone.querySelectorAll('img').forEach(img => img.remove());
                } else {
                    // Добавляем декорацию с размерами
                    const newDecoration = {
                        x, y,
                        type: currentDecorationType,
                        width: currentDecorationWidth,
                        height: currentDecorationHeight,
                        templateId: currentDecorationTemplateId,
                        sprite: null
                    };
                    decorations.push(newDecoration);
                    zone.classList.add('has-decoration');
                    zone.textContent = getDecorationEmoji(currentDecorationType);
                }
                updateDecorationsData();
            } else if (currentTool === 'erase') {
                const existingIndex = decorations.findIndex(d => d.x === x && d.y === y);
                if (existingIndex >= 0) {
                    decorations.splice(existingIndex, 1);
                    zone.classList.remove('has-decoration');
                    zone.textContent = '';
                    zone.querySelectorAll('img').forEach(img => img.remove());
                    updateDecorationsData();
                }
            } else if (currentTool === 'select') {
                // Проверяем, есть ли декорация на этой клетке
                const decorationIndex = decorations.findIndex(d => d.x === x && d.y === y);
                if (decorationIndex >= 0) {
                    selectCellForSprite('decoration', x, y, zone, decorations[decorationIndex]);
                }
            }
        }

        function selectCellForSprite(type, x, y, element, data) {
            selectedCell = { type, x, y, element, data };

            // Показываем контролы загрузки
            document.getElementById('sprite-upload-controls').style.display = 'block';
            document.getElementById('sprite-hint').style.display = 'none';

            // Обновляем информацию о выбранной ячейке
            const info = type === 'obstacle'
                ? `Препятствие (${x}, ${y})`
                : `Декорация "${getDecorationEmoji(data.type)}" (${x}, ${y})`;
            document.getElementById('selected-cell-info').textContent = info;

            // Подсвечиваем выбранную ячейку
            document.querySelectorAll('.cell.selected, .decoration-zone.selected').forEach(el => {
                el.classList.remove('selected');
            });
            element.classList.add('selected');
        }

        function initTools() {
            document.querySelectorAll('.tool-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    currentTool = this.dataset.tool;

                    // Показываем соответствующие панели
                    const obstaclePanel = document.getElementById('obstacle-panel');
                    const decorationPanel = document.getElementById('decoration-panel');
                    obstaclePanel.style.display = currentTool === 'obstacle' ? 'block' : 'none';
                    decorationPanel.style.display = currentTool === 'decoration' ? 'block' : 'none';

                    // Сбрасываем выбранную ячейку при смене инструмента
                    if (currentTool !== 'select') {
                        document.getElementById('sprite-upload-controls').style.display = 'none';
                        document.getElementById('sprite-hint').style.display = 'block';
                        document.querySelectorAll('.cell.selected, .decoration-zone.selected').forEach(el => {
                            el.classList.remove('selected');
                        });
                        selectedCell = null;
                    }
                });
            });
        }

        function initDecorationTypes() {
            // Базовые типы декораций
            document.querySelectorAll('.decoration-type').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.decoration-type').forEach(b => b.classList.remove('active'));
                    document.querySelectorAll('#decoration-templates .element-template').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    currentDecorationType = this.dataset.type;
                    currentDecorationWidth = parseInt(this.dataset.width) || 1;
                    currentDecorationHeight = parseInt(this.dataset.height) || 1;
                    currentDecorationTemplateId = null;
                });
            });

            // Шаблоны декораций
            document.querySelectorAll('#decoration-templates .element-template').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('.decoration-type').forEach(b => b.classList.remove('active'));
                    document.querySelectorAll('#decoration-templates .element-template').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    currentDecorationType = this.dataset.type;
                    currentDecorationWidth = parseInt(this.dataset.width) || 1;
                    currentDecorationHeight = parseInt(this.dataset.height) || 1;
                    currentDecorationTemplateId = this.dataset.template;
                });
            });
        }

        function initObstacleTemplates() {
            document.querySelectorAll('#obstacle-templates .element-template').forEach(btn => {
                btn.addEventListener('click', function() {
                    document.querySelectorAll('#obstacle-templates .element-template').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                    currentObstacleWidth = parseInt(this.dataset.width) || 1;
                    currentObstacleHeight = parseInt(this.dataset.height) || 1;
                    currentObstacleTemplateId = this.dataset.template === 'default' ? null : this.dataset.template;
                });
            });
        }

        function initSpriteUpload() {
            const fileInput = document.getElementById('sprite-file');
            fileInput.addEventListener('change', function(e) {
                if (!selectedCell || !e.target.files[0]) return;

                const file = e.target.files[0];
                const reader = new FileReader();

                reader.onload = function(event) {
                    const dataUrl = event.target.result;

                    if (selectedCell.type === 'obstacle') {
                        const obstacleIndex = obstacles.findIndex(o => o.x === selectedCell.x && o.y === selectedCell.y);
                        if (obstacleIndex >= 0) {
                            obstacles[obstacleIndex].sprite = dataUrl;
                            selectedCell.element.textContent = '';
                            selectedCell.element.innerHTML = `<img src="${dataUrl}">`;
                            updateObstaclesData();
                        }
                    } else if (selectedCell.type === 'decoration') {
                        const decorationIndex = decorations.findIndex(d => d.x === selectedCell.x && d.y === selectedCell.y);
                        if (decorationIndex >= 0) {
                            decorations[decorationIndex].sprite = dataUrl;
                            selectedCell.element.innerHTML = `<img src="${dataUrl}" style="max-width: 100%; max-height: 100%;">`;
                            updateDecorationsData();
                        }
                    }
                };

                reader.readAsDataURL(file);
            });

            // Обработчик кнопки удаления спрайта
            const clearBtn = document.getElementById('clear-sprite-btn');
            clearBtn.addEventListener('click', function() {
                if (!selectedCell) return;

                if (selectedCell.type === 'obstacle') {
                    const obstacleIndex = obstacles.findIndex(o => o.x === selectedCell.x && o.y === selectedCell.y);
                    if (obstacleIndex >= 0) {
                        obstacles[obstacleIndex].sprite = null;
                        selectedCell.element.innerHTML = '';
                        selectedCell.element.textContent = '🪨';
                        updateObstaclesData();
                    }
                } else if (selectedCell.type === 'decoration') {
                    const decorationIndex = decorations.findIndex(d => d.x === selectedCell.x && d.y === selectedCell.y);
                    if (decorationIndex >= 0) {
                        decorations[decorationIndex].sprite = null;
                        selectedCell.element.innerHTML = '';
                        selectedCell.element.textContent = getDecorationEmoji(decorations[decorationIndex].type);
                        updateDecorationsData();
                    }
                }

                // Очищаем поле выбора файла
                document.getElementById('sprite-file').value = '';
            });
        }

        function initFieldSizeChange() {
            const sizeSelect = document.getElementById('field-size-select');
            sizeSelect.addEventListener('change', function() {
                obstacles = [];
                decorations = [];
                // Сбрасываем панорамирование при смене размера
                panOffsetX = 0;
                panOffsetY = 0;
                initGrid();
                updateObstaclesData();
                updateDecorationsData();
            });
        }

        function initPanning() {
            const viewport = document.getElementById('field-viewport');
            const container = document.getElementById('grid-container');

            // Предотвращаем контекстное меню при правом клике
            viewport.addEventListener('contextmenu', function(e) {
                e.preventDefault();
            });

            // Начало панорамирования при зажатии правой кнопки
            viewport.addEventListener('mousedown', function(e) {
                if (e.button === 2) { // Правая кнопка мыши
                    e.preventDefault();
                    isPanning = true;
                    panStartX = e.clientX - panOffsetX;
                    panStartY = e.clientY - panOffsetY;
                    viewport.classList.add('panning');
                }
            });

            // Перемещение при панорамировании
            document.addEventListener('mousemove', function(e) {
                if (!isPanning) return;

                panOffsetX = e.clientX - panStartX;
                panOffsetY = e.clientY - panStartY;

                container.style.left = panOffsetX + 'px';
                container.style.top = panOffsetY + 'px';
            });

            // Конец панорамирования
            document.addEventListener('mouseup', function(e) {
                if (e.button === 2 && isPanning) {
                    isPanning = false;
                    viewport.classList.remove('panning');
                }
            });

            // Также останавливаем панорамирование если мышь покинула окно
            document.addEventListener('mouseleave', function() {
                if (isPanning) {
                    isPanning = false;
                    viewport.classList.remove('panning');
                }
            });

            // Центрируем поле при инициализации
            centerField();
        }

        function centerField() {
            const viewport = document.getElementById('field-viewport');
            const container = document.getElementById('grid-container');

            // Даём время на рендеринг
            setTimeout(function() {
                const viewportRect = viewport.getBoundingClientRect();
                const containerRect = container.getBoundingClientRect();

                // Центрируем по горизонтали и вертикали
                panOffsetX = (viewportRect.width - containerRect.width) / 2;
                panOffsetY = (viewportRect.height - containerRect.height) / 2;

                // Ограничиваем, чтобы не уходило слишком далеко
                panOffsetX = Math.min(50, panOffsetX);
                panOffsetY = Math.min(50, panOffsetY);

                container.style.left = panOffsetX + 'px';
                container.style.top = panOffsetY + 'px';
            }, 100);
        }

        function updateObstaclesData() {
            document.getElementById('obstacles-data').value = JSON.stringify(obstacles);
        }

        function updateDecorationsData() {
            document.getElementById('decorations-data').value = JSON.stringify(decorations);
        }
    </script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


@fields_bp.route('/')
@login_required
def fields_list():
    """Список всех шаблонов полей"""
    with db.get_session() as db_session:
        templates = db_session.query(BattleFieldTemplate).order_by(BattleFieldTemplate.created_at.desc()).all()
        user_balance = get_user_balance(db_session, session.get('user_id'))

        return render_template_string(
            FIELDS_LIST_TEMPLATE,
            templates=templates,
            active_page='fields',
            user_balance=user_balance,
            web_version=get_web_version(),
            bot_version=get_bot_version()
        )


@fields_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create_field():
    """Создание нового поля"""
    import json
    import base64

    with db.get_session() as db_session:
        field_sizes = db_session.query(Field).order_by(Field.width).all()
        field_sizes_json = json.dumps([{'id': f.id, 'name': f.name, 'width': f.width, 'height': f.height} for f in field_sizes])

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            field_size_id = int(request.form.get('field_size_id', 1))
            obstacles_data = request.form.get('obstacles_data', '[]')
            decorations_data = request.form.get('decorations_data', '[]')

            if not name:
                flash('Название поля обязательно', 'error')
            else:
                # Создаём шаблон поля
                template = BattleFieldTemplate(
                    name=name,
                    description=description if description else None,
                    field_size_id=field_size_id,
                    is_active=True
                )
                db_session.add(template)
                db_session.flush()

                # Добавляем препятствия
                try:
                    obstacles = json.loads(obstacles_data)
                    for obs in obstacles:
                        sprite_data = None
                        sprite_mime = None
                        if obs.get('sprite') and obs['sprite'].startswith('data:'):
                            # Парсим data URL
                            header, data = obs['sprite'].split(',', 1)
                            sprite_mime = header.split(':')[1].split(';')[0]
                            sprite_data = base64.b64decode(data)

                        obstacle = BattleFieldObstacle(
                            template_id=template.id,
                            position_x=obs['x'],
                            position_y=obs['y'],
                            width=obs.get('width', 1),
                            height=obs.get('height', 1),
                            obstacle_template_id=int(obs['templateId']) if obs.get('templateId') else None,
                            sprite_data=sprite_data,
                            sprite_mime_type=sprite_mime
                        )
                        db_session.add(obstacle)
                except json.JSONDecodeError:
                    pass

                # Добавляем декорации
                try:
                    decorations = json.loads(decorations_data)
                    for dec in decorations:
                        sprite_data = None
                        sprite_mime = None
                        if dec.get('sprite') and dec['sprite'].startswith('data:'):
                            header, data = dec['sprite'].split(',', 1)
                            sprite_mime = header.split(':')[1].split(';')[0]
                            sprite_data = base64.b64decode(data)

                        decoration = BattleFieldDecoration(
                            template_id=template.id,
                            decoration_type=DecorationType(dec.get('type', 'tree')),
                            position_x=dec['x'],
                            position_y=dec['y'],
                            width=dec.get('width', 1),
                            height=dec.get('height', 1),
                            decoration_template_id=int(dec['templateId']) if dec.get('templateId') else None,
                            sprite_data=sprite_data,
                            sprite_mime_type=sprite_mime
                        )
                        db_session.add(decoration)
                except json.JSONDecodeError:
                    pass

                db_session.commit()
                flash(f'Поле "{name}" успешно создано!', 'success')
                return redirect(url_for('fields.fields_list'))

        user_balance = get_user_balance(db_session, session.get('user_id'))

        # Загружаем шаблоны элементов
        obstacle_templates = db_session.query(ObstacleTemplate).filter_by(is_active=True).all()
        decoration_templates = db_session.query(DecorationTemplate).filter_by(is_active=True).all()

        decoration_emojis = {
            'tree': '🌲', 'river': '🌊', 'rock': '🪨',
            'bush': '🌿', 'flower': '🌸', 'custom': '⭐'
        }

        return render_template_string(
            FIELD_EDITOR_TEMPLATE,
            template=None,
            field_sizes=field_sizes,
            field_sizes_json=field_sizes_json,
            obstacles_json='[]',
            decorations_json='[]',
            obstacle_templates=obstacle_templates,
            decoration_templates=decoration_templates,
            decoration_emojis=decoration_emojis,
            active_page='fields',
            user_balance=user_balance,
            web_version=get_web_version(),
            bot_version=get_bot_version()
        )


@fields_bp.route('/<int:template_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_field(template_id):
    """Редактирование поля"""
    import json
    import base64

    with db.get_session() as db_session:
        template = db_session.query(BattleFieldTemplate).filter_by(id=template_id).first()
        if not template:
            flash('Поле не найдено', 'error')
            return redirect(url_for('fields.fields_list'))

        field_sizes = db_session.query(Field).order_by(Field.width).all()
        field_sizes_json = json.dumps([{'id': f.id, 'name': f.name, 'width': f.width, 'height': f.height} for f in field_sizes])

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            description = request.form.get('description', '').strip()
            obstacles_data = request.form.get('obstacles_data', '[]')
            decorations_data = request.form.get('decorations_data', '[]')

            if not name:
                flash('Название поля обязательно', 'error')
            else:
                template.name = name
                template.description = description if description else None

                # Удаляем старые препятствия и декорации
                db_session.query(BattleFieldObstacle).filter_by(template_id=template.id).delete()
                db_session.query(BattleFieldDecoration).filter_by(template_id=template.id).delete()

                # Добавляем препятствия
                try:
                    obstacles = json.loads(obstacles_data)
                    for obs in obstacles:
                        sprite_data = None
                        sprite_mime = None
                        if obs.get('sprite') and obs['sprite'].startswith('data:'):
                            header, data = obs['sprite'].split(',', 1)
                            sprite_mime = header.split(':')[1].split(';')[0]
                            sprite_data = base64.b64decode(data)

                        obstacle = BattleFieldObstacle(
                            template_id=template.id,
                            position_x=obs['x'],
                            position_y=obs['y'],
                            width=obs.get('width', 1),
                            height=obs.get('height', 1),
                            obstacle_template_id=int(obs['templateId']) if obs.get('templateId') else None,
                            sprite_data=sprite_data,
                            sprite_mime_type=sprite_mime
                        )
                        db_session.add(obstacle)
                except json.JSONDecodeError:
                    pass

                # Добавляем декорации
                try:
                    decorations = json.loads(decorations_data)
                    for dec in decorations:
                        sprite_data = None
                        sprite_mime = None
                        if dec.get('sprite') and dec['sprite'].startswith('data:'):
                            header, data = dec['sprite'].split(',', 1)
                            sprite_mime = header.split(':')[1].split(';')[0]
                            sprite_data = base64.b64decode(data)

                        decoration = BattleFieldDecoration(
                            template_id=template.id,
                            decoration_type=DecorationType(dec.get('type', 'tree')),
                            position_x=dec['x'],
                            position_y=dec['y'],
                            width=dec.get('width', 1),
                            height=dec.get('height', 1),
                            decoration_template_id=int(dec['templateId']) if dec.get('templateId') else None,
                            sprite_data=sprite_data,
                            sprite_mime_type=sprite_mime
                        )
                        db_session.add(decoration)
                except json.JSONDecodeError:
                    pass

                db_session.commit()
                flash(f'Поле "{name}" успешно обновлено!', 'success')
                return redirect(url_for('fields.fields_list'))

        # Формируем JSON данных для редактора
        obstacles_json = json.dumps([
            {
                'x': o.position_x,
                'y': o.position_y,
                'width': o.width or 1,
                'height': o.height or 1,
                'templateId': o.obstacle_template_id,
                'sprite': f"data:{o.sprite_mime_type};base64,{base64.b64encode(o.sprite_data).decode()}" if o.sprite_data else None
            }
            for o in template.obstacles
        ])

        decorations_json = json.dumps([
            {
                'x': d.position_x,
                'y': d.position_y,
                'type': d.decoration_type.value,
                'width': d.width or 1,
                'height': d.height or 1,
                'templateId': d.decoration_template_id,
                'sprite': f"data:{d.sprite_mime_type};base64,{base64.b64encode(d.sprite_data).decode()}" if d.sprite_data else None
            }
            for d in template.decorations
        ])

        user_balance = get_user_balance(db_session, session.get('user_id'))

        # Загружаем шаблоны элементов
        obstacle_templates = db_session.query(ObstacleTemplate).filter_by(is_active=True).all()
        decoration_templates = db_session.query(DecorationTemplate).filter_by(is_active=True).all()

        decoration_emojis = {
            'tree': '🌲', 'river': '🌊', 'rock': '🪨',
            'bush': '🌿', 'flower': '🌸', 'custom': '⭐'
        }

        return render_template_string(
            FIELD_EDITOR_TEMPLATE,
            template=template,
            field_sizes=field_sizes,
            field_sizes_json=field_sizes_json,
            obstacles_json=obstacles_json,
            decorations_json=decorations_json,
            obstacle_templates=obstacle_templates,
            decoration_templates=decoration_templates,
            decoration_emojis=decoration_emojis,
            active_page='fields',
            user_balance=user_balance,
            web_version=get_web_version(),
            bot_version=get_bot_version()
        )


@fields_bp.route('/<int:template_id>/toggle', methods=['POST'])
@admin_required
def toggle_field(template_id):
    """Переключение активности поля"""
    with db.get_session() as db_session:
        template = db_session.query(BattleFieldTemplate).filter_by(id=template_id).first()
        if template:
            template.is_active = not template.is_active
            db_session.commit()
            status = 'активировано' if template.is_active else 'деактивировано'
            flash(f'Поле "{template.name}" {status}', 'success')
        else:
            flash('Поле не найдено', 'error')

    return redirect(url_for('fields.fields_list'))


@fields_bp.route('/<int:template_id>/delete', methods=['POST'])
@admin_required
def delete_field(template_id):
    """Удаление поля"""
    with db.get_session() as db_session:
        template = db_session.query(BattleFieldTemplate).filter_by(id=template_id).first()
        if template:
            name = template.name
            db_session.delete(template)
            db_session.commit()
            flash(f'Поле "{name}" удалено', 'success')
        else:
            flash('Поле не найдено', 'error')

    return redirect(url_for('fields.fields_list'))


# API для получения спрайта препятствия
@fields_bp.route('/api/obstacle/<int:obstacle_id>/sprite')
def get_obstacle_sprite(obstacle_id):
    """Получить спрайт препятствия"""
    with db.get_session() as db_session:
        obstacle = db_session.query(BattleFieldObstacle).filter_by(id=obstacle_id).first()
        if obstacle and obstacle.sprite_data:
            return Response(
                obstacle.sprite_data,
                mimetype=obstacle.sprite_mime_type or 'image/png'
            )
    return '', 404


# API для получения спрайта декорации
@fields_bp.route('/api/decoration/<int:decoration_id>/sprite')
def get_decoration_sprite(decoration_id):
    """Получить спрайт декорации"""
    with db.get_session() as db_session:
        decoration = db_session.query(BattleFieldDecoration).filter_by(id=decoration_id).first()
        if decoration and decoration.sprite_data:
            return Response(
                decoration.sprite_data,
                mimetype=decoration.sprite_mime_type or 'image/png'
            )
    return '', 404
