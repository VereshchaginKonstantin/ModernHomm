#!/usr/bin/env python3
"""
Blueprint для редактора элементов (препятствия и декорации)
"""

from flask import Blueprint, render_template_string, request, redirect, url_for, flash, session, Response
import os
import json
import base64
from db.models import ObstacleTemplate, DecorationTemplate, DecorationType
from db.repository import Database

# Database connection
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
db = Database(db_url)
from web.templates import HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE, get_web_version, get_bot_version
from functools import wraps

elements_bp = Blueprint('elements', __name__, url_prefix='/elements')


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


# Доступные размеры элементов
AVAILABLE_SIZES = [
    {'width': 1, 'height': 1, 'label': '1x1'},
    {'width': 2, 'height': 1, 'label': '2x1'},
    {'width': 1, 'height': 2, 'label': '1x2'},
    {'width': 2, 'height': 2, 'label': '2x2'},
    {'width': 3, 'height': 1, 'label': '3x1'},
    {'width': 1, 'height': 3, 'label': '1x3'},
    {'width': 3, 'height': 3, 'label': '3x3'},
    {'width': 4, 'height': 4, 'label': '4x4'},
]


ELEMENTS_LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Редактор элементов - ModernHomm</title>
    """ + BASE_STYLE + """
    <style>
        .tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        .tab {
            padding: 15px 30px;
            background: #ecf0f1;
            border: none;
            border-radius: 8px 8px 0 0;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.2s;
        }
        .tab:hover {
            background: #bdc3c7;
        }
        .tab.active {
            background: #3498db;
            color: white;
        }
        .elements-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 20px;
        }
        .element-card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }
        .element-card.inactive {
            opacity: 0.5;
        }
        .element-preview {
            width: 100%;
            height: 120px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f9f9f9;
            border-radius: 4px;
            margin-bottom: 10px;
            overflow: hidden;
        }
        .element-preview img {
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }
        .element-preview .no-sprite {
            color: #999;
            font-size: 48px;
        }
        .element-name {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .element-size {
            color: #666;
            font-size: 14px;
            margin-bottom: 10px;
        }
        .element-actions {
            display: flex;
            gap: 5px;
            justify-content: center;
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
        .section-title {
            margin: 30px 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #3498db;
        }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>🎨 Редактор элементов</h1>
        <p style="color: #666; margin-bottom: 20px;">
            Создавайте препятствия и декорации разных размеров для использования в редакторе полей.
        </p>

        <div class="tabs">
            <button class="tab active" onclick="showTab('obstacles')">🪨 Препятствия</button>
            <button class="tab" onclick="showTab('decorations')">🌲 Декорации</button>
        </div>

        <!-- Препятствия -->
        <div id="obstacles-tab">
            <a href="{{ url_for('elements.create_obstacle') }}" class="create-btn">+ Создать препятствие</a>

            {% if obstacle_templates %}
            <div class="elements-grid">
                {% for template in obstacle_templates %}
                <div class="element-card {{ 'inactive' if not template.is_active else '' }}">
                    <div class="element-preview">
                        {% if template.sprite_data %}
                        <img src="{{ url_for('elements.get_obstacle_template_sprite', template_id=template.id) }}" alt="{{ template.name }}">
                        {% else %}
                        <span class="no-sprite">🪨</span>
                        {% endif %}
                    </div>
                    <div class="element-name">{{ template.name }}</div>
                    <div class="element-size">{{ template.width }}x{{ template.height }} клеток</div>
                    <div class="element-actions">
                        <a href="{{ url_for('elements.edit_obstacle', template_id=template.id) }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;">✏️</a>
                        <form action="{{ url_for('elements.toggle_obstacle', template_id=template.id) }}" method="post" style="margin: 0;">
                            <button type="submit" class="btn {{ 'btn-secondary' if template.is_active else 'btn-success' }}" style="padding: 5px 10px; font-size: 12px;">
                                {{ '⏸️' if template.is_active else '▶️' }}
                            </button>
                        </form>
                        <form action="{{ url_for('elements.delete_obstacle', template_id=template.id) }}" method="post" style="margin: 0;" onsubmit="return confirm('Удалить {{ template.name }}?');">
                            <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;">🗑️</button>
                        </form>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="alert" style="background: #e8f4fd; padding: 20px; border-radius: 8px;">
                Препятствия ещё не созданы. Нажмите кнопку выше, чтобы создать первое.
            </div>
            {% endif %}
        </div>

        <!-- Декорации -->
        <div id="decorations-tab" style="display: none;">
            <a href="{{ url_for('elements.create_decoration') }}" class="create-btn">+ Создать декорацию</a>

            {% if decoration_templates %}
            <div class="elements-grid">
                {% for template in decoration_templates %}
                <div class="element-card {{ 'inactive' if not template.is_active else '' }}">
                    <div class="element-preview">
                        {% if template.sprite_data %}
                        <img src="{{ url_for('elements.get_decoration_template_sprite', template_id=template.id) }}" alt="{{ template.name }}">
                        {% else %}
                        <span class="no-sprite">{{ decoration_emojis.get(template.decoration_type.value, '⭐') }}</span>
                        {% endif %}
                    </div>
                    <div class="element-name">{{ template.name }}</div>
                    <div class="element-size">{{ template.width }}x{{ template.height }} клеток | {{ template.decoration_type.value }}</div>
                    <div class="element-actions">
                        <a href="{{ url_for('elements.edit_decoration', template_id=template.id) }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;">✏️</a>
                        <form action="{{ url_for('elements.toggle_decoration', template_id=template.id) }}" method="post" style="margin: 0;">
                            <button type="submit" class="btn {{ 'btn-secondary' if template.is_active else 'btn-success' }}" style="padding: 5px 10px; font-size: 12px;">
                                {{ '⏸️' if template.is_active else '▶️' }}
                            </button>
                        </form>
                        <form action="{{ url_for('elements.delete_decoration', template_id=template.id) }}" method="post" style="margin: 0;" onsubmit="return confirm('Удалить {{ template.name }}?');">
                            <button type="submit" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;">🗑️</button>
                        </form>
                    </div>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="alert" style="background: #e8f4fd; padding: 20px; border-radius: 8px;">
                Декорации ещё не созданы. Нажмите кнопку выше, чтобы создать первую.
            </div>
            {% endif %}
        </div>
    </div>

    <script>
        function showTab(tabName) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('[id$="-tab"]').forEach(t => t.style.display = 'none');

            event.target.classList.add('active');
            document.getElementById(tabName + '-tab').style.display = 'block';
        }
    </script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


ELEMENT_EDITOR_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ 'Редактирование' if template else 'Создание' }} {{ element_type_name }} - ModernHomm</title>
    """ + BASE_STYLE + """
    <style>
        .editor-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            max-width: 900px;
        }
        .form-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .preview-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .size-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-bottom: 20px;
        }
        .size-option {
            padding: 15px;
            border: 2px solid #ddd;
            border-radius: 8px;
            text-align: center;
            cursor: pointer;
            transition: all 0.2s;
        }
        .size-option:hover {
            border-color: #3498db;
            background: #f0f7fc;
        }
        .size-option.selected {
            border-color: #3498db;
            background: #e8f4fd;
        }
        .size-option .size-label {
            font-weight: bold;
            font-size: 18px;
        }
        .size-option .size-cells {
            font-size: 12px;
            color: #666;
        }
        .preview-grid {
            display: inline-grid;
            gap: 2px;
            background: #4a8c4a;
            padding: 10px;
            border-radius: 8px;
        }
        .preview-cell {
            width: 50px;
            height: 50px;
            background: #5a9c5a;
            border: 1px solid rgba(0,0,0,0.1);
        }
        .preview-cell.element {
            background: #808078;
        }
        .sprite-preview {
            margin-top: 20px;
            text-align: center;
        }
        .sprite-preview img {
            max-width: 200px;
            max-height: 200px;
            border: 2px solid #ddd;
            border-radius: 8px;
        }
        .decoration-types {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin-bottom: 20px;
        }
        .decoration-type-option {
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 8px;
            text-align: center;
            cursor: pointer;
        }
        .decoration-type-option:hover {
            border-color: #27ae60;
        }
        .decoration-type-option.selected {
            border-color: #27ae60;
            background: #e8f6ef;
        }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>{{ '✏️ Редактирование' if template else '➕ Создание' }} {{ element_type_name }}</h1>

        <form method="post" enctype="multipart/form-data" id="element-form">
            <div class="editor-container">
                <div class="form-section">
                    <div class="form-group">
                        <label>Название</label>
                        <input type="text" name="name" class="form-control" value="{{ template.name if template else '' }}" required>
                    </div>

                    {% if element_type == 'decoration' %}
                    <div class="form-group">
                        <label>Тип декорации</label>
                        <div class="decoration-types">
                            {% for dtype in decoration_types %}
                            <div class="decoration-type-option {{ 'selected' if template and template.decoration_type.value == dtype.value else ('selected' if not template and dtype.value == 'custom' else '') }}"
                                 data-type="{{ dtype.value }}" onclick="selectDecorationType(this)">
                                {{ decoration_emojis.get(dtype.value, '⭐') }} {{ dtype.value }}
                            </div>
                            {% endfor %}
                        </div>
                        <input type="hidden" name="decoration_type" id="decoration-type" value="{{ template.decoration_type.value if template else 'custom' }}">
                    </div>
                    {% endif %}

                    <div class="form-group">
                        <label>Размер (в клетках)</label>
                        <div class="size-grid">
                            {% for size in sizes %}
                            <div class="size-option {{ 'selected' if template and template.width == size.width and template.height == size.height else ('selected' if not template and size.width == 1 and size.height == 1 else '') }}"
                                 data-width="{{ size.width }}" data-height="{{ size.height }}" onclick="selectSize(this)">
                                <div class="size-label">{{ size.label }}</div>
                                <div class="size-cells">{{ size.width * size.height }} {{ 'клетка' if size.width * size.height == 1 else ('клетки' if size.width * size.height < 5 else 'клеток') }}</div>
                            </div>
                            {% endfor %}
                        </div>
                        <input type="hidden" name="width" id="element-width" value="{{ template.width if template else 1 }}">
                        <input type="hidden" name="height" id="element-height" value="{{ template.height if template else 1 }}">
                    </div>

                    <div class="form-group">
                        <label>Спрайт (изображение)</label>
                        <input type="file" name="sprite" id="sprite-input" accept="image/*" class="form-control">
                        <p style="font-size: 12px; color: #666; margin-top: 5px;">
                            Рекомендуемый размер: {{ 50 * (template.width if template else 1) }}x{{ 50 * (template.height if template else 1) }} пикселей
                        </p>
                    </div>

                    <input type="hidden" name="sprite_data" id="sprite-data" value="">
                </div>

                <div class="preview-section">
                    <h3>Предпросмотр</h3>
                    <p style="color: #666; font-size: 14px;">Как элемент будет выглядеть на поле:</p>

                    <div id="size-preview" style="margin: 20px 0;">
                        <div class="preview-grid" id="preview-grid" style="grid-template-columns: repeat(1, 50px);">
                            <div class="preview-cell element"></div>
                        </div>
                    </div>

                    <div class="sprite-preview" id="sprite-preview">
                        {% if template and template.sprite_data %}
                        <img src="{{ url_for('elements.get_' + element_type + '_template_sprite', template_id=template.id) }}" alt="Спрайт">
                        <p style="color: #666; font-size: 12px;">Текущий спрайт</p>
                        {% else %}
                        <p style="color: #999;">Спрайт не загружен</p>
                        {% endif %}
                    </div>
                </div>
            </div>

            <div style="margin-top: 20px; display: flex; gap: 10px;">
                <button type="submit" class="btn btn-success" style="padding: 15px 30px; font-size: 16px;">
                    💾 {{ 'Сохранить' if template else 'Создать' }}
                </button>
                <a href="{{ url_for('elements.elements_list') }}" class="btn btn-secondary" style="padding: 15px 30px; font-size: 16px;">
                    ❌ Отмена
                </a>
            </div>
        </form>
    </div>

    <script>
        function selectSize(element) {
            document.querySelectorAll('.size-option').forEach(el => el.classList.remove('selected'));
            element.classList.add('selected');

            const width = parseInt(element.dataset.width);
            const height = parseInt(element.dataset.height);

            document.getElementById('element-width').value = width;
            document.getElementById('element-height').value = height;

            updatePreview(width, height);
        }

        function selectDecorationType(element) {
            document.querySelectorAll('.decoration-type-option').forEach(el => el.classList.remove('selected'));
            element.classList.add('selected');
            document.getElementById('decoration-type').value = element.dataset.type;
        }

        function updatePreview(width, height) {
            const grid = document.getElementById('preview-grid');
            grid.style.gridTemplateColumns = `repeat(${width}, 50px)`;
            grid.innerHTML = '';

            for (let i = 0; i < width * height; i++) {
                const cell = document.createElement('div');
                cell.className = 'preview-cell element';
                grid.appendChild(cell);
            }
        }

        // Обработка загрузки спрайта
        document.getElementById('sprite-input').addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = function(event) {
                const dataUrl = event.target.result;
                document.getElementById('sprite-data').value = dataUrl;

                const preview = document.getElementById('sprite-preview');
                preview.innerHTML = `<img src="${dataUrl}" alt="Спрайт"><p style="color: #666; font-size: 12px;">Новый спрайт</p>`;
            };
            reader.readAsDataURL(file);
        });

        // Инициализация
        const initialWidth = parseInt(document.getElementById('element-width').value);
        const initialHeight = parseInt(document.getElementById('element-height').value);
        updatePreview(initialWidth, initialHeight);
    </script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


DECORATION_EMOJIS = {
    'tree': '🌲',
    'river': '🌊',
    'rock': '🪨',
    'bush': '🌿',
    'flower': '🌸',
    'custom': '⭐'
}


@elements_bp.route('/')
@admin_required
def elements_list():
    """Список всех шаблонов элементов"""
    with db.get_session() as db_session:
        obstacle_templates = db_session.query(ObstacleTemplate).order_by(ObstacleTemplate.created_at.desc()).all()
        decoration_templates = db_session.query(DecorationTemplate).order_by(DecorationTemplate.created_at.desc()).all()
        user_balance = get_user_balance(db_session, session.get('user_id'))

        return render_template_string(
            ELEMENTS_LIST_TEMPLATE,
            obstacle_templates=obstacle_templates,
            decoration_templates=decoration_templates,
            decoration_emojis=DECORATION_EMOJIS,
            active_page='elements',
            user_balance=user_balance,
            web_version=get_web_version(),
            bot_version=get_bot_version()
        )


@elements_bp.route('/obstacles/create', methods=['GET', 'POST'])
@admin_required
def create_obstacle():
    """Создание нового шаблона препятствия"""
    with db.get_session() as db_session:
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            width = int(request.form.get('width', 1))
            height = int(request.form.get('height', 1))
            sprite_data_url = request.form.get('sprite_data', '')

            if not name:
                flash('Название обязательно', 'error')
            else:
                sprite_data = None
                sprite_mime = None
                if sprite_data_url and sprite_data_url.startswith('data:'):
                    header, data = sprite_data_url.split(',', 1)
                    sprite_mime = header.split(':')[1].split(';')[0]
                    sprite_data = base64.b64decode(data)

                template = ObstacleTemplate(
                    name=name,
                    width=width,
                    height=height,
                    sprite_data=sprite_data,
                    sprite_mime_type=sprite_mime,
                    is_active=True
                )
                db_session.add(template)
                db_session.commit()
                flash(f'Препятствие "{name}" создано!', 'success')
                return redirect(url_for('elements.elements_list'))

        user_balance = get_user_balance(db_session, session.get('user_id'))

        return render_template_string(
            ELEMENT_EDITOR_TEMPLATE,
            template=None,
            element_type='obstacle',
            element_type_name='препятствия',
            sizes=AVAILABLE_SIZES,
            decoration_types=[],
            decoration_emojis=DECORATION_EMOJIS,
            active_page='elements',
            user_balance=user_balance,
            web_version=get_web_version(),
            bot_version=get_bot_version()
        )


@elements_bp.route('/obstacles/<int:template_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_obstacle(template_id):
    """Редактирование шаблона препятствия"""
    with db.get_session() as db_session:
        template = db_session.query(ObstacleTemplate).filter_by(id=template_id).first()
        if not template:
            flash('Шаблон не найден', 'error')
            return redirect(url_for('elements.elements_list'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            width = int(request.form.get('width', 1))
            height = int(request.form.get('height', 1))
            sprite_data_url = request.form.get('sprite_data', '')

            if not name:
                flash('Название обязательно', 'error')
            else:
                template.name = name
                template.width = width
                template.height = height

                if sprite_data_url and sprite_data_url.startswith('data:'):
                    header, data = sprite_data_url.split(',', 1)
                    template.sprite_mime_type = header.split(':')[1].split(';')[0]
                    template.sprite_data = base64.b64decode(data)

                db_session.commit()
                flash(f'Препятствие "{name}" обновлено!', 'success')
                return redirect(url_for('elements.elements_list'))

        user_balance = get_user_balance(db_session, session.get('user_id'))

        return render_template_string(
            ELEMENT_EDITOR_TEMPLATE,
            template=template,
            element_type='obstacle',
            element_type_name='препятствия',
            sizes=AVAILABLE_SIZES,
            decoration_types=[],
            decoration_emojis=DECORATION_EMOJIS,
            active_page='elements',
            user_balance=user_balance,
            web_version=get_web_version(),
            bot_version=get_bot_version()
        )


@elements_bp.route('/obstacles/<int:template_id>/toggle', methods=['POST'])
@admin_required
def toggle_obstacle(template_id):
    """Переключение активности препятствия"""
    with db.get_session() as db_session:
        template = db_session.query(ObstacleTemplate).filter_by(id=template_id).first()
        if template:
            template.is_active = not template.is_active
            db_session.commit()
            status = 'активировано' if template.is_active else 'деактивировано'
            flash(f'Препятствие "{template.name}" {status}', 'success')
    return redirect(url_for('elements.elements_list'))


@elements_bp.route('/obstacles/<int:template_id>/delete', methods=['POST'])
@admin_required
def delete_obstacle(template_id):
    """Удаление препятствия"""
    with db.get_session() as db_session:
        template = db_session.query(ObstacleTemplate).filter_by(id=template_id).first()
        if template:
            name = template.name
            db_session.delete(template)
            db_session.commit()
            flash(f'Препятствие "{name}" удалено', 'success')
    return redirect(url_for('elements.elements_list'))


@elements_bp.route('/decorations/create', methods=['GET', 'POST'])
@admin_required
def create_decoration():
    """Создание нового шаблона декорации"""
    with db.get_session() as db_session:
        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            decoration_type = request.form.get('decoration_type', 'custom')
            width = int(request.form.get('width', 1))
            height = int(request.form.get('height', 1))
            sprite_data_url = request.form.get('sprite_data', '')

            if not name:
                flash('Название обязательно', 'error')
            else:
                sprite_data = None
                sprite_mime = None
                if sprite_data_url and sprite_data_url.startswith('data:'):
                    header, data = sprite_data_url.split(',', 1)
                    sprite_mime = header.split(':')[1].split(';')[0]
                    sprite_data = base64.b64decode(data)

                template = DecorationTemplate(
                    name=name,
                    decoration_type=DecorationType(decoration_type),
                    width=width,
                    height=height,
                    sprite_data=sprite_data,
                    sprite_mime_type=sprite_mime,
                    is_active=True
                )
                db_session.add(template)
                db_session.commit()
                flash(f'Декорация "{name}" создана!', 'success')
                return redirect(url_for('elements.elements_list'))

        user_balance = get_user_balance(db_session, session.get('user_id'))

        return render_template_string(
            ELEMENT_EDITOR_TEMPLATE,
            template=None,
            element_type='decoration',
            element_type_name='декорации',
            sizes=AVAILABLE_SIZES,
            decoration_types=list(DecorationType),
            decoration_emojis=DECORATION_EMOJIS,
            active_page='elements',
            user_balance=user_balance,
            web_version=get_web_version(),
            bot_version=get_bot_version()
        )


@elements_bp.route('/decorations/<int:template_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_decoration(template_id):
    """Редактирование шаблона декорации"""
    with db.get_session() as db_session:
        template = db_session.query(DecorationTemplate).filter_by(id=template_id).first()
        if not template:
            flash('Шаблон не найден', 'error')
            return redirect(url_for('elements.elements_list'))

        if request.method == 'POST':
            name = request.form.get('name', '').strip()
            decoration_type = request.form.get('decoration_type', 'custom')
            width = int(request.form.get('width', 1))
            height = int(request.form.get('height', 1))
            sprite_data_url = request.form.get('sprite_data', '')

            if not name:
                flash('Название обязательно', 'error')
            else:
                template.name = name
                template.decoration_type = DecorationType(decoration_type)
                template.width = width
                template.height = height

                if sprite_data_url and sprite_data_url.startswith('data:'):
                    header, data = sprite_data_url.split(',', 1)
                    template.sprite_mime_type = header.split(':')[1].split(';')[0]
                    template.sprite_data = base64.b64decode(data)

                db_session.commit()
                flash(f'Декорация "{name}" обновлена!', 'success')
                return redirect(url_for('elements.elements_list'))

        user_balance = get_user_balance(db_session, session.get('user_id'))

        return render_template_string(
            ELEMENT_EDITOR_TEMPLATE,
            template=template,
            element_type='decoration',
            element_type_name='декорации',
            sizes=AVAILABLE_SIZES,
            decoration_types=list(DecorationType),
            decoration_emojis=DECORATION_EMOJIS,
            active_page='elements',
            user_balance=user_balance,
            web_version=get_web_version(),
            bot_version=get_bot_version()
        )


@elements_bp.route('/decorations/<int:template_id>/toggle', methods=['POST'])
@admin_required
def toggle_decoration(template_id):
    """Переключение активности декорации"""
    with db.get_session() as db_session:
        template = db_session.query(DecorationTemplate).filter_by(id=template_id).first()
        if template:
            template.is_active = not template.is_active
            db_session.commit()
            status = 'активирована' if template.is_active else 'деактивирована'
            flash(f'Декорация "{template.name}" {status}', 'success')
    return redirect(url_for('elements.elements_list'))


@elements_bp.route('/decorations/<int:template_id>/delete', methods=['POST'])
@admin_required
def delete_decoration(template_id):
    """Удаление декорации"""
    with db.get_session() as db_session:
        template = db_session.query(DecorationTemplate).filter_by(id=template_id).first()
        if template:
            name = template.name
            db_session.delete(template)
            db_session.commit()
            flash(f'Декорация "{name}" удалена', 'success')
    return redirect(url_for('elements.elements_list'))


# API для получения спрайтов
@elements_bp.route('/api/obstacles/<int:template_id>/sprite')
def get_obstacle_template_sprite(template_id):
    """Получить спрайт шаблона препятствия"""
    with db.get_session() as db_session:
        template = db_session.query(ObstacleTemplate).filter_by(id=template_id).first()
        if template and template.sprite_data:
            return Response(
                template.sprite_data,
                mimetype=template.sprite_mime_type or 'image/png'
            )
    return '', 404


@elements_bp.route('/api/decorations/<int:template_id>/sprite')
def get_decoration_template_sprite(template_id):
    """Получить спрайт шаблона декорации"""
    with db.get_session() as db_session:
        template = db_session.query(DecorationTemplate).filter_by(id=template_id).first()
        if template and template.sprite_data:
            return Response(
                template.sprite_data,
                mimetype=template.sprite_mime_type or 'image/png'
            )
    return '', 404


# API для получения списка шаблонов (для редактора полей)
@elements_bp.route('/api/obstacles')
def get_obstacle_templates_api():
    """Получить список активных шаблонов препятствий"""
    with db.get_session() as db_session:
        templates = db_session.query(ObstacleTemplate).filter_by(is_active=True).all()
        return {
            'templates': [
                {
                    'id': t.id,
                    'name': t.name,
                    'width': t.width,
                    'height': t.height,
                    'has_sprite': t.sprite_data is not None
                }
                for t in templates
            ]
        }


@elements_bp.route('/api/decorations')
def get_decoration_templates_api():
    """Получить список активных шаблонов декораций"""
    with db.get_session() as db_session:
        templates = db_session.query(DecorationTemplate).filter_by(is_active=True).all()
        return {
            'templates': [
                {
                    'id': t.id,
                    'name': t.name,
                    'type': t.decoration_type.value,
                    'width': t.width,
                    'height': t.height,
                    'has_sprite': t.sprite_data is not None
                }
                for t in templates
            ]
        }
