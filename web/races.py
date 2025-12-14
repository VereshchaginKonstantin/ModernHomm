#!/usr/bin/env python3
"""
Модуль управления расами для веб-интерфейса
"""

import os
import io
import logging
import random
import requests
from datetime import datetime
from flask import Blueprint, render_template_string, request, jsonify, session, redirect, url_for, Response
from functools import wraps
from PIL import Image

from db.models import Base, GameUser, GameRace, RaceUnit, RaceUnitSkin, UnitLevel, UserRace, UserRaceUnit, Army, ArmyUnit
from db.repository import Database
from web.templates import HEADER_TEMPLATE, BASE_STYLE, FOOTER_TEMPLATE

logger = logging.getLogger(__name__)


# Placeholder sprite colors for different unit levels
LEVEL_COLORS = [
    (139, 69, 19),    # Level 1 - Brown (peasant)
    (34, 139, 34),    # Level 2 - Green (archer)
    (255, 215, 0),    # Level 3 - Gold (griffin)
    (192, 192, 192),  # Level 4 - Silver (swordsman)
    (255, 255, 255),  # Level 5 - White (monk)
    (70, 130, 180),   # Level 6 - Steel blue (cavalier)
    (255, 223, 0),    # Level 7 - Bright gold (angel)
]


def generate_placeholder_sprite(level: int, size: int = 64) -> bytes:
    """
    Generate a placeholder sprite image for a unit level.
    Creates a simple colored square with the level number.

    Args:
        level: Unit level (1-7)
        size: Image size in pixels

    Returns:
        PNG image data as bytes
    """
    # Get color for this level
    color = LEVEL_COLORS[min(level - 1, len(LEVEL_COLORS) - 1)]

    # Create image
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))

    # Draw a simple unit shape (circle with level indicator)
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(img)

    # Draw filled circle
    margin = size // 8
    draw.ellipse([margin, margin, size - margin, size - margin], fill=color, outline=(0, 0, 0))

    # Draw level number in center
    text = str(level)
    try:
        # Try to use a font if available
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size // 3)
    except Exception:
        font = ImageFont.load_default()

    # Get text bounding box
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center text
    x = (size - text_width) // 2
    y = (size - text_height) // 2 - margin // 2

    # Draw text with outline for visibility
    draw.text((x-1, y-1), text, fill=(0, 0, 0), font=font)
    draw.text((x+1, y-1), text, fill=(0, 0, 0), font=font)
    draw.text((x-1, y+1), text, fill=(0, 0, 0), font=font)
    draw.text((x+1, y+1), text, fill=(0, 0, 0), font=font)
    draw.text((x, y), text, fill=(255, 255, 255), font=font)

    # Save to bytes
    output = io.BytesIO()
    img.save(output, format='PNG')
    return output.getvalue()


def generate_animated_sprite_sheet(level: int, size: int = 64, frames: int = 4, columns: int = 4) -> bytes:
    """
    Generate an animated sprite sheet for a unit level.
    Creates a sprite sheet with multiple frames showing animation.

    Args:
        level: Unit level (1-7)
        size: Size of each frame in pixels
        frames: Number of animation frames
        columns: Number of columns in sprite sheet

    Returns:
        PNG image data as bytes (sprite sheet)
    """
    from PIL import ImageDraw, ImageFont

    # Get color for this level
    color = LEVEL_COLORS[min(level - 1, len(LEVEL_COLORS) - 1)]

    # Calculate sprite sheet dimensions
    rows = (frames + columns - 1) // columns
    sheet_width = size * columns
    sheet_height = size * rows

    # Create sprite sheet
    sheet = Image.new('RGBA', (sheet_width, sheet_height), (0, 0, 0, 0))

    for frame_idx in range(frames):
        # Calculate position in sheet
        col = frame_idx % columns
        row = frame_idx // columns
        offset_x = col * size
        offset_y = row * size

        # Create frame
        frame_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(frame_img)

        # Animate by slightly changing the circle size (breathing effect)
        margin = size // 8
        animation_offset = int((frame_idx % 4) * 2) - 3  # -3, -1, 1, 3 pixels

        draw.ellipse([
            margin - animation_offset,
            margin - animation_offset,
            size - margin + animation_offset,
            size - margin + animation_offset
        ], fill=color, outline=(0, 0, 0, 200), width=2)

        # Draw level number
        text = str(level)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size // 3)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (size - text_width) // 2
        y = (size - text_height) // 2 - margin // 2

        # Draw text with outline
        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
            draw.text((x + dx, y + dy), text, fill=(0, 0, 0), font=font)
        draw.text((x, y), text, fill=(255, 255, 255), font=font)

        # Paste frame onto sheet
        sheet.paste(frame_img, (offset_x, offset_y))

    # Save to bytes
    output = io.BytesIO()
    sheet.save(output, format='PNG')
    return output.getvalue()


def try_download_kenney_asset() -> tuple:
    """
    Try to download a random sprite from Kenney.nl free assets.
    Returns tuple of (image_data, mime_type) or (None, None) if failed.
    """
    # Kenney provides free game assets - we'll use their asset packs
    # These are direct download links to some of their free sprite sheets
    kenney_urls = [
        "https://kenney.nl/content/3-assets/5-platformer-art-pixel-redux/sample.png",
        "https://kenney.nl/content/3-assets/78-pixel-shmup/sample.png",
        "https://kenney.nl/content/3-assets/60-tiny-dungeon/sample.png",
    ]

    for url in random.sample(kenney_urls, len(kenney_urls)):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200 and response.content:
                return response.content, 'image/png'
        except Exception as e:
            logger.warning(f"Failed to download from {url}: {e}")
            continue

    return None, None


def create_default_skin_for_unit(race_unit, level: int) -> RaceUnitSkin:
    """
    Create a default skin with placeholder sprite for a race unit.
    Generates both static texture and animated sprite sheet.

    Args:
        race_unit: RaceUnit instance
        level: Unit level (1-7)

    Returns:
        RaceUnitSkin instance with placeholder image and sprite sheet
    """
    # Default unit type names for Godot asset paths (prototype assets)
    unit_type_names = [
        'peasant',    # Level 1
        'archer',     # Level 2
        'griffin',    # Level 3
        'swordsman',  # Level 4
        'monk',       # Level 5
        'cavalier',   # Level 6
        'angel',      # Level 7
    ]
    unit_type = unit_type_names[min(level - 1, len(unit_type_names) - 1)]

    # Generate placeholder sprite (static texture)
    image_data = generate_placeholder_sprite(level, size=64)

    # Generate animated sprite sheet (4 frames in 1 row)
    sprite_frames_data = generate_animated_sprite_sheet(level, size=64, frames=4, columns=4)

    # Create default Godot asset paths (prototype paths)
    godot_texture_path = f"res://assets/units/prototype/{unit_type}_level{level}.png"
    godot_sprite_path = f"res://scenes/units/prototype/{unit_type}_level{level}.tscn"

    # Create skin with all fields populated
    skin = RaceUnitSkin(
        race_unit_id=race_unit.id,
        name="Базовый скин",
        image_data=image_data,
        image_mime_type='image/png',
        description=f"Стандартный скин для юнита уровня {level}. Prototype Asset.",
        # Sprite display parameters
        sprite_scale_x=1.0,
        sprite_scale_y=1.0,
        sprite_offset_x=0,
        sprite_offset_y=0,
        sprite_rotation=0,
        # Animated sprite data
        sprite_frames_data=sprite_frames_data,
        sprite_frames_mime_type='image/png',
        sprite_frame_count=4,
        sprite_fps=8,
        sprite_columns=4,
        sprite_rows=1,
        # Godot asset paths
        godot_texture_path=godot_texture_path,
        godot_sprite_path=godot_sprite_path
    )

    return skin

# Blueprint для рас
races_bp = Blueprint('races', __name__, url_prefix='/admin/races')

# Получаем подключение к БД
db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5434/telegram_bot')
db = Database(db_url)


def admin_required(f):
    """Декоратор для проверки авторизации админа"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ==================== Шаблоны ====================

RACES_LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Расы - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .races-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; margin-top: 20px; }
        .race-card { background: #2a2a2a; border-radius: 10px; padding: 20px; }
        .race-card h3 { margin: 0 0 10px 0; color: #ffd700; }
        .race-card .description { color: #aaa; font-size: 14px; margin-bottom: 15px; }
        .race-card .badge { display: inline-block; padding: 3px 8px; border-radius: 5px; font-size: 12px; margin-right: 5px; }
        .badge-free { background: #2ecc71; color: white; }
        .badge-paid { background: #e74c3c; color: white; }
        .btn { display: inline-block; padding: 8px 15px; border-radius: 5px; text-decoration: none; margin-right: 5px; }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-sm { padding: 5px 10px; font-size: 12px; }
        .add-btn { margin-bottom: 20px; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>🏰 Управление расами</h1>

        <a href="{{ url_for('races.create_race') }}" class="btn btn-success add-btn">➕ Создать расу</a>

        <div class="races-grid">
            {% for race in races %}
            <div class="race-card">
                <h3>{{ race.name }}</h3>
                <p class="description">{{ race.description or 'Нет описания' }}</p>
                <div>
                    {% if race.is_free %}
                    <span class="badge badge-free">Бесплатная</span>
                    {% else %}
                    <span class="badge badge-paid">Платная</span>
                    {% endif %}
                    <span class="badge" style="background: #9b59b6;">{{ race.race_units|length }}/7 юнитов</span>
                </div>
                <div style="margin-top: 15px;">
                    <a href="{{ url_for('races.edit_race', race_id=race.id) }}" class="btn btn-primary btn-sm">✏️ Редактировать</a>
                    <button onclick="deleteRace({{ race.id }})" class="btn btn-danger btn-sm">🗑️ Удалить</button>
                </div>
            </div>
            {% else %}
            <p style="color: #aaa;">Расы не найдены. Создайте первую расу!</p>
            {% endfor %}
        </div>
    </div>

    <script>
    function deleteRace(raceId) {
        if (confirm('Вы уверены, что хотите удалить эту расу?')) {
            fetch('/admin/races/' + raceId + '/delete', {
                method: 'POST'
            }).then(response => response.json())
              .then(data => {
                  if (data.success) {
                      location.reload();
                  } else {
                      alert('Ошибка: ' + data.message);
                  }
              });
        }
    }
    </script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""

CREATE_RACE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Создать расу - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .form-group textarea { min-height: 100px; }
        .checkbox-group { display: flex; align-items: center; gap: 10px; }
        .checkbox-group input[type="checkbox"] { width: 20px; height: 20px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>➕ Создать расу</h1>

        <form method="POST" action="{{ url_for('races.create_race') }}">
            <div class="form-group">
                <label>Название</label>
                <input type="text" name="name" required placeholder="Название расы">
            </div>

            <div class="form-group">
                <label>Описание</label>
                <textarea name="description" placeholder="Описание расы (необязательно)"></textarea>
            </div>

            <div class="form-group checkbox-group">
                <input type="checkbox" name="is_free" id="is_free">
                <label for="is_free" style="margin-bottom: 0;">Бесплатная раса</label>
            </div>

            <button type="submit" class="btn btn-success">Создать</button>
            <a href="{{ url_for('races.races_list') }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""

EDIT_RACE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Редактировать расу - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 20px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .form-group textarea { min-height: 100px; }
        .checkbox-group { display: flex; align-items: center; gap: 10px; }
        .checkbox-group input[type="checkbox"] { width: 20px; height: 20px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
        .btn-primary { background: #3498db; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .units-section { margin-top: 30px; padding-top: 20px; border-top: 1px solid #444; }
        .units-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin-top: 15px; }
        .unit-card { background: #333; border-radius: 8px; padding: 15px; }
        .unit-card h4 { margin: 0 0 10px 0; color: #ffd700; }
        .unit-card .level { color: #3498db; font-size: 12px; }
        .unit-card .stats { font-size: 12px; color: #aaa; margin-top: 10px; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>✏️ Редактировать расу: {{ race.name }}</h1>

        <form method="POST" action="{{ url_for('races.edit_race', race_id=race.id) }}">
            <div class="form-group">
                <label>Название</label>
                <input type="text" name="name" required value="{{ race.name }}">
            </div>

            <div class="form-group">
                <label>Описание</label>
                <textarea name="description">{{ race.description or '' }}</textarea>
            </div>

            <div class="form-group checkbox-group">
                <input type="checkbox" name="is_free" id="is_free" {% if race.is_free %}checked{% endif %}>
                <label for="is_free" style="margin-bottom: 0;">Бесплатная раса</label>
            </div>

            <button type="submit" class="btn btn-success">💾 Сохранить</button>
            <a href="{{ url_for('races.races_list') }}" class="btn btn-secondary">Назад</a>
        </form>

        <div class="units-section">
            <h2>⚔️ Юниты расы (7 уровней)</h2>

            <div class="units-grid">
                {% for level in range(1, 8) %}
                {% set unit = units_by_level.get(level) %}
                <div class="unit-card">
                    <span class="level">Уровень {{ level }}</span>
                    {% if unit %}
                    <h4>{{ unit.unit_level.icon if unit.unit_level else '🎮' }} {{ unit.name }}</h4>
                    <div class="stats">
                        {% if unit.is_flying %}🦅 Летающий{% endif %}
                        {% if unit.is_kamikaze %}💥 Камикадзе{% endif %}
                        <br>🎨 Скинов: {{ unit.skins|length }}
                    </div>
                    <div style="margin-top: 10px;">
                        <a href="{{ url_for('races.edit_race_unit', race_id=race.id, unit_id=unit.id) }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;">✏️ Юнит</a>
                        <a href="{{ url_for('races.unit_skins', race_id=race.id, unit_id=unit.id) }}" class="btn btn-success" style="padding: 5px 10px; font-size: 12px;">🎨 Скины уровня</a>
                    </div>
                    {% else %}
                    <h4 style="color: #666;">Не задан</h4>
                    {% endif %}
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""

EDIT_UNIT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Редактировать Юнит расы - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .form-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
        .checkbox-group { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; }
        .checkbox-group input[type="checkbox"] { width: 20px; height: 20px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
        .level-info { background: #444; padding: 10px; border-radius: 5px; color: #aaa; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>✏️ Редактировать Юнит расы: {{ race.name }}</h1>

        <form method="POST">
            <div class="form-group">
                <label>Название</label>
                <input type="text" name="name" required value="{{ unit.name }}">
            </div>

            <div class="form-group">
                <label>Уровень юнита</label>
                <div class="level-info">
                    {% if unit.unit_level %}
                    {{ unit.unit_level.icon }} Уровень {{ unit.unit_level.level }} (престиж {{ unit.unit_level.prestige_min }} - {{ unit.unit_level.prestige_max }})
                    {% else %}
                    Не задан
                    {% endif %}
                </div>
                <small style="color: #666;">Уровень юнита фиксируется при создании расы и не может быть изменён</small>
            </div>

            <div class="checkbox-group">
                <input type="checkbox" name="is_flying" id="is_flying" {% if unit.is_flying %}checked{% endif %}>
                <label for="is_flying" style="margin-bottom: 0;">🦅 Летающий юнит</label>
            </div>

            <div class="checkbox-group">
                <input type="checkbox" name="is_kamikaze" id="is_kamikaze" {% if unit.is_kamikaze %}checked{% endif %}>
                <label for="is_kamikaze" style="margin-bottom: 0;">💥 Камикадзе</label>
            </div>

            <button type="submit" class="btn btn-success">💾 Сохранить</button>
            <a href="{{ url_for('races.edit_race', race_id=race.id) }}" class="btn btn-secondary">Назад</a>
        </form>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""

UNIT_SKINS_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Скины уровня расы - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .skins-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-top: 20px; }
        .skin-card { background: #333; border-radius: 8px; padding: 15px; text-align: center; }
        .skin-card img { max-width: 100%; max-height: 150px; margin: 10px 0; border-radius: 5px; }
        .skin-card .no-image { width: 100%; height: 100px; background: #444; display: flex; align-items: center; justify-content: center; color: #666; border-radius: 5px; margin: 10px 0; }
        .btn { padding: 8px 15px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin: 5px; }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>🎨 Скины уровня расы: {{ unit.unit_level.icon if unit.unit_level else '🎮' }} {{ unit.name }} (ур. {{ unit.unit_level.level if unit.unit_level else '?' }})</h1>
        <p style="color: #aaa;">Раса: {{ race.name }}</p>

        <a href="{{ url_for('races.add_unit_skin', race_id=race.id, unit_id=unit.id) }}" class="btn btn-success">➕ Добавить скин уровня расы</a>
        <a href="{{ url_for('races.edit_race', race_id=race.id) }}" class="btn btn-secondary">← Назад к расе</a>

        <div class="skins-grid">
            {% for skin in skins %}
            <div class="skin-card">
                <h4>{{ skin.name }}</h4>
                {% if skin.image_data %}
                <img src="{{ url_for('races.skin_image', skin_id=skin.id) }}" alt="Скин">
                {% else %}
                <div class="no-image">Нет изображения</div>
                {% endif %}
                <p style="font-size: 12px; color: #aaa;">{{ skin.description or 'Без описания' }}</p>
                <div>
                    <a href="{{ url_for('races.edit_unit_skin', race_id=race.id, unit_id=unit.id, skin_id=skin.id) }}" class="btn btn-primary" style="padding: 5px 10px; font-size: 12px;">✏️</a>
                    <button onclick="deleteSkin({{ skin.id }})" class="btn btn-danger" style="padding: 5px 10px; font-size: 12px;">🗑️</button>
                </div>
            </div>
            {% else %}
            <p style="color: #aaa;">Нет скинов уровня расы. Добавьте первый!</p>
            {% endfor %}
        </div>
    </div>

    <script>
    function deleteSkin(skinId) {
        if (confirm('Удалить этот скин?')) {
            fetch('/admin/races/skin/' + skinId + '/delete', {
                method: 'POST'
            }).then(response => response.json())
              .then(data => {
                  if (data.success) {
                      location.reload();
                  } else {
                      alert('Ошибка: ' + data.message);
                  }
              });
        }
    }
    </script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


# ==================== Маршруты ====================

@races_bp.route('/')
@admin_required
def races_list():
    """Список рас"""
    with db.get_session() as session_db:
        races = session_db.query(GameRace).all()
        return render_template_string(RACES_LIST_TEMPLATE, races=races)


@races_bp.route('/create', methods=['GET', 'POST'])
@admin_required
def create_race():
    """Создать новую расу"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        is_free = request.form.get('is_free') == 'on'

        with db.get_session() as session_db:
            race = GameRace(
                name=name,
                description=description,
                is_free=is_free
            )
            session_db.add(race)
            session_db.flush()  # Получаем ID расы

            # Получаем справочник уровней юнитов
            unit_levels = session_db.query(UnitLevel).order_by(UnitLevel.level).all()
            unit_levels_by_level = {ul.level: ul for ul in unit_levels}

            # Автоматически создаём 7 юнитов (по одному на каждый уровень)
            # Дефолтные характеристики юнитов по уровням (прототипные значения)
            default_units = [
                # Level 1 - Крестьянин (слабый, дешёвый)
                {
                    'name': 'Крестьянин', 'is_flying': False, 'is_kamikaze': False,
                    'attack': 2, 'defense': 1, 'min_damage': 1, 'max_damage': 2,
                    'health': 3, 'speed': 4, 'initiative': 8, 'range': 1,
                    'luck': 0.0, 'crit_chance': 0.02, 'dodge_chance': 0.05, 'counterattack_chance': 0.1,
                    'regeneration_health': 0, 'poison_damage': 0, 'poison_turns': 0, 'poison_immunity': False
                },
                # Level 2 - Лучник (дальнобойный)
                {
                    'name': 'Лучник', 'is_flying': False, 'is_kamikaze': False,
                    'attack': 5, 'defense': 3, 'min_damage': 2, 'max_damage': 4,
                    'health': 8, 'speed': 4, 'initiative': 9, 'range': 6,
                    'luck': 0.05, 'crit_chance': 0.05, 'dodge_chance': 0.08, 'counterattack_chance': 0.0,
                    'regeneration_health': 0, 'poison_damage': 0, 'poison_turns': 0, 'poison_immunity': False
                },
                # Level 3 - Грифон (летающий)
                {
                    'name': 'Грифон', 'is_flying': True, 'is_kamikaze': False,
                    'attack': 8, 'defense': 6, 'min_damage': 3, 'max_damage': 6,
                    'health': 25, 'speed': 6, 'initiative': 12, 'range': 1,
                    'luck': 0.1, 'crit_chance': 0.08, 'dodge_chance': 0.1, 'counterattack_chance': 0.5,
                    'regeneration_health': 0, 'poison_damage': 0, 'poison_turns': 0, 'poison_immunity': False
                },
                # Level 4 - Мечник (танк)
                {
                    'name': 'Мечник', 'is_flying': False, 'is_kamikaze': False,
                    'attack': 10, 'defense': 12, 'min_damage': 4, 'max_damage': 8,
                    'health': 40, 'speed': 4, 'initiative': 10, 'range': 1,
                    'luck': 0.05, 'crit_chance': 0.05, 'dodge_chance': 0.05, 'counterattack_chance': 0.3,
                    'regeneration_health': 0, 'poison_damage': 0, 'poison_turns': 0, 'poison_immunity': False
                },
                # Level 5 - Монах (регенерация, хилер)
                {
                    'name': 'Монах', 'is_flying': False, 'is_kamikaze': False,
                    'attack': 12, 'defense': 8, 'min_damage': 5, 'max_damage': 10,
                    'health': 35, 'speed': 5, 'initiative': 11, 'range': 1,
                    'luck': 0.15, 'crit_chance': 0.1, 'dodge_chance': 0.08, 'counterattack_chance': 0.2,
                    'regeneration_health': 5, 'poison_damage': 0, 'poison_turns': 0, 'poison_immunity': True
                },
                # Level 6 - Всадник (быстрый, мощный)
                {
                    'name': 'Всадник', 'is_flying': False, 'is_kamikaze': False,
                    'attack': 15, 'defense': 14, 'min_damage': 8, 'max_damage': 15,
                    'health': 80, 'speed': 7, 'initiative': 14, 'range': 1,
                    'luck': 0.1, 'crit_chance': 0.12, 'dodge_chance': 0.1, 'counterattack_chance': 0.4,
                    'regeneration_health': 0, 'poison_damage': 0, 'poison_turns': 0, 'poison_immunity': False
                },
                # Level 7 - Ангел (топ юнит, летающий, регенерация)
                {
                    'name': 'Ангел', 'is_flying': True, 'is_kamikaze': False,
                    'attack': 25, 'defense': 25, 'min_damage': 15, 'max_damage': 30,
                    'health': 200, 'speed': 10, 'initiative': 18, 'range': 1,
                    'luck': 0.2, 'crit_chance': 0.15, 'dodge_chance': 0.15, 'counterattack_chance': 0.5,
                    'regeneration_health': 10, 'poison_damage': 0, 'poison_turns': 0, 'poison_immunity': True
                },
            ]

            for level in range(1, 8):
                unit_level = unit_levels_by_level.get(level)
                unit_data = default_units[level - 1]
                unit = RaceUnit(
                    race_id=race.id,
                    unit_level_id=unit_level.id if unit_level else None,
                    name=unit_data['name'],
                    is_flying=unit_data['is_flying'],
                    is_kamikaze=unit_data['is_kamikaze'],
                    attack=unit_data['attack'],
                    defense=unit_data['defense'],
                    min_damage=unit_data['min_damage'],
                    max_damage=unit_data['max_damage'],
                    health=unit_data['health'],
                    speed=unit_data['speed'],
                    initiative=unit_data['initiative'],
                    range=unit_data['range'],
                    luck=unit_data['luck'],
                    crit_chance=unit_data['crit_chance'],
                    dodge_chance=unit_data['dodge_chance'],
                    counterattack_chance=unit_data['counterattack_chance'],
                    regeneration_health=unit_data['regeneration_health'],
                    poison_damage=unit_data['poison_damage'],
                    poison_turns=unit_data['poison_turns'],
                    poison_immunity=unit_data['poison_immunity']
                )
                session_db.add(unit)
                session_db.flush()  # Получаем ID юнита для создания скина

                # Создаём дефолтный скин для каждого юнита
                default_skin = create_default_skin_for_unit(unit, level)
                session_db.add(default_skin)

            session_db.commit()
            return redirect(url_for('races.edit_race', race_id=race.id))

    return render_template_string(CREATE_RACE_TEMPLATE)


@races_bp.route('/<int:race_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_race(race_id):
    """Редактировать расу"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        if not race:
            return redirect(url_for('races.races_list'))

        if request.method == 'POST':
            race.name = request.form.get('name')
            race.description = request.form.get('description')
            race.is_free = request.form.get('is_free') == 'on'
            session_db.commit()
            return redirect(url_for('races.edit_race', race_id=race_id))

        # Получаем юниты по уровням (уровень теперь берётся из связанного UnitLevel)
        units = session_db.query(RaceUnit).filter_by(race_id=race_id).all()
        units_by_level = {u.unit_level.level: u for u in units if u.unit_level}

        return render_template_string(EDIT_RACE_TEMPLATE, race=race, units_by_level=units_by_level)


@races_bp.route('/<int:race_id>/delete', methods=['POST'])
@admin_required
def delete_race(race_id):
    """Удалить расу"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        if race:
            session_db.delete(race)
            session_db.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Раса не найдена'})


@races_bp.route('/<int:race_id>/unit/<int:unit_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_race_unit(race_id, unit_id):
    """Редактировать юнит расы (уровень не изменяется после создания)"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        unit = session_db.query(RaceUnit).filter_by(id=unit_id, race_id=race_id).first()

        if not race or not unit:
            return redirect(url_for('races.races_list'))

        if request.method == 'POST':
            unit.name = request.form.get('name')
            unit.is_flying = request.form.get('is_flying') == 'on'
            unit.is_kamikaze = request.form.get('is_kamikaze') == 'on'
            # unit_level_id не меняется после создания расы
            session_db.commit()
            return redirect(url_for('races.edit_race', race_id=race_id))

        return render_template_string(EDIT_UNIT_TEMPLATE, race=race, unit=unit)


@races_bp.route('/<int:race_id>/unit/<int:unit_id>/skins')
@admin_required
def unit_skins(race_id, unit_id):
    """Скины юнита расы"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        unit = session_db.query(RaceUnit).filter_by(id=unit_id, race_id=race_id).first()

        if not race or not unit:
            return redirect(url_for('races.races_list'))

        skins = session_db.query(RaceUnitSkin).filter_by(race_unit_id=unit_id).all()

        return render_template_string(UNIT_SKINS_TEMPLATE, race=race, unit=unit, skins=skins)


ADD_SKIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Добавить скин уровня расы - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .form-group input[type="file"] { padding: 8px; }
        .form-group input[type="number"] { width: 120px; }
        .form-group textarea { min-height: 80px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
        .image-preview { max-width: 200px; max-height: 200px; margin-top: 10px; border: 2px solid #444; border-radius: 5px; }
        .form-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
        .section { background: #2a2a2a; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .section h3 { color: #3498db; margin-top: 0; margin-bottom: 15px; font-size: 16px; }
        .help-text { color: #888; font-size: 12px; margin-top: 5px; line-height: 1.4; }
        .info-box { background: #1a3a5c; border-left: 4px solid #3498db; padding: 12px 15px; margin-bottom: 20px; border-radius: 0 5px 5px 0; }
        .info-box h4 { color: #3498db; margin: 0 0 8px 0; font-size: 14px; }
        .info-box p { color: #aaa; margin: 0; font-size: 13px; line-height: 1.5; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>➕ Добавить скин уровня расы для: {{ unit.unit_level.icon if unit.unit_level else '🎮' }} {{ unit.name }}</h1>
        <p style="color: #aaa;">Раса: {{ race.name }} | Уровень: {{ unit.unit_level.level if unit.unit_level else '?' }}</p>

        <form method="POST" enctype="multipart/form-data">
            <div class="section">
                <h3>Основные данные</h3>
                <div class="form-group">
                    <label>Название скина</label>
                    <input type="text" name="name" required placeholder="Базовый скин">
                </div>

                <div class="form-group">
                    <label>Изображение скина (PNG, JPG до 5MB)</label>
                    <input type="file" name="image" accept="image/png,image/jpeg,image/gif,image/webp" onchange="previewImage(this)">
                    <img id="imagePreview" class="image-preview" style="display: none;">
                </div>

                <div class="form-group">
                    <label>Описание</label>
                    <textarea name="description" placeholder="Описание скина (необязательно)"></textarea>
                </div>
            </div>

            <div class="section">
                <h3>Параметры спрайта для Godot</h3>

                <div class="info-box">
                    <h4>Для чего нужны эти параметры?</h4>
                    <p>Эти настройки определяют, как изображение скина будет отображаться в игровом клиенте Godot.
                    <br>• <b>Масштаб</b> — размер спрайта относительно оригинала (1.0 = 100%)
                    <br>• <b>Смещение</b> — позиция спрайта относительно центра клетки (в пикселях)
                    <br>• <b>Поворот</b> — угол поворота спрайта (в градусах)
                    <br>Для анимированных юнитов загрузите спрайт-лист и укажите количество кадров.</p>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Масштаб X</label>
                        <input type="number" name="sprite_scale_x" value="1.0" step="0.1" min="0.1" max="10">
                        <p class="help-text">Масштаб по горизонтали (1.0 = оригинальный размер)</p>
                    </div>
                    <div class="form-group">
                        <label>Масштаб Y</label>
                        <input type="number" name="sprite_scale_y" value="1.0" step="0.1" min="0.1" max="10">
                        <p class="help-text">Масштаб по вертикали</p>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Смещение X (пиксели)</label>
                        <input type="number" name="sprite_offset_x" value="0">
                        <p class="help-text">Смещение от центра клетки по горизонтали</p>
                    </div>
                    <div class="form-group">
                        <label>Смещение Y (пиксели)</label>
                        <input type="number" name="sprite_offset_y" value="0">
                        <p class="help-text">Смещение от центра клетки по вертикали</p>
                    </div>
                </div>

                <div class="form-group">
                    <label>Поворот (градусы)</label>
                    <input type="number" name="sprite_rotation" value="0" step="1" min="-360" max="360" style="width: 120px;">
                    <p class="help-text">Угол поворота спрайта (0-360 градусов)</p>
                </div>
            </div>

            <div class="section">
                <h3>Анимированный спрайт (опционально)</h3>

                <div class="info-box">
                    <h4>Спрайт-листы для анимации</h4>
                    <p>Если вы загружаете спрайт-лист (изображение с несколькими кадрами анимации),
                    укажите количество кадров, колонок и строк в листе. Godot использует эти данные для
                    создания AnimatedSprite2D.</p>
                </div>

                <div class="form-group">
                    <label>Спрайт-лист анимации (PNG)</label>
                    <input type="file" name="sprite_frames" accept="image/png">
                    <p class="help-text">Загрузите спрайт-лист с кадрами анимации</p>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Количество кадров</label>
                        <input type="number" name="sprite_frame_count" value="1" min="1" max="100">
                    </div>
                    <div class="form-group">
                        <label>Скорость (FPS)</label>
                        <input type="number" name="sprite_fps" value="10" min="1" max="60">
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Колонок в спрайт-листе</label>
                        <input type="number" name="sprite_columns" value="1" min="1" max="20">
                    </div>
                    <div class="form-group">
                        <label>Строк в спрайт-листе</label>
                        <input type="number" name="sprite_rows" value="1" min="1" max="20">
                    </div>
                </div>
            </div>

            <div class="section">
                <h3>Пути в Godot проекте (опционально)</h3>
                <div class="form-group">
                    <label>Путь к текстуре в Godot</label>
                    <input type="text" name="godot_texture_path" placeholder="res://assets/units/knight.png">
                    <p class="help-text">Путь к файлу текстуры в проекте Godot</p>
                </div>
                <div class="form-group">
                    <label>Путь к спрайту в Godot</label>
                    <input type="text" name="godot_sprite_path" placeholder="res://scenes/units/knight.tscn">
                    <p class="help-text">Путь к сцене спрайта в проекте Godot</p>
                </div>
            </div>

            <button type="submit" class="btn btn-success">Создать</button>
            <a href="{{ url_for('races.unit_skins', race_id=race.id, unit_id=unit.id) }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
    <script>
    function previewImage(input) {
        if (input.files && input.files[0]) {
            var reader = new FileReader();
            reader.onload = function(e) {
                var preview = document.getElementById('imagePreview');
                preview.src = e.target.result;
                preview.style.display = 'block';
            }
            reader.readAsDataURL(input.files[0]);
        }
    }
    </script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


@races_bp.route('/<int:race_id>/unit/<int:unit_id>/skin/add', methods=['GET', 'POST'])
@admin_required
def add_unit_skin(race_id, unit_id):
    """Добавить скин юниту"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        unit = session_db.query(RaceUnit).filter_by(id=unit_id, race_id=race_id).first()

        if not race or not unit:
            return redirect(url_for('races.races_list'))

        if request.method == 'POST':
            # Обработка загруженного изображения
            image_data = None
            image_mime_type = None

            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    # Проверка размера (максимум 5MB)
                    file.seek(0, 2)  # Перейти в конец файла
                    size = file.tell()
                    file.seek(0)  # Вернуться в начало

                    if size <= 5 * 1024 * 1024:  # 5MB
                        image_data = file.read()
                        image_mime_type = file.content_type or 'image/png'

            # Обработка спрайт-листа
            sprite_frames_data = None
            sprite_frames_mime_type = None

            if 'sprite_frames' in request.files:
                file = request.files['sprite_frames']
                if file and file.filename:
                    file.seek(0, 2)
                    size = file.tell()
                    file.seek(0)

                    if size <= 10 * 1024 * 1024:  # 10MB для спрайт-листов
                        sprite_frames_data = file.read()
                        sprite_frames_mime_type = file.content_type or 'image/png'

            skin = RaceUnitSkin(
                race_unit_id=unit_id,
                name=request.form.get('name'),
                image_data=image_data,
                image_mime_type=image_mime_type,
                description=request.form.get('description') or None,
                # Параметры спрайта
                sprite_scale_x=float(request.form.get('sprite_scale_x', 1.0) or 1.0),
                sprite_scale_y=float(request.form.get('sprite_scale_y', 1.0) or 1.0),
                sprite_offset_x=int(request.form.get('sprite_offset_x', 0) or 0),
                sprite_offset_y=int(request.form.get('sprite_offset_y', 0) or 0),
                sprite_rotation=float(request.form.get('sprite_rotation', 0) or 0),
                # Анимация
                sprite_frames_data=sprite_frames_data,
                sprite_frames_mime_type=sprite_frames_mime_type,
                sprite_frame_count=int(request.form.get('sprite_frame_count', 1) or 1),
                sprite_fps=int(request.form.get('sprite_fps', 10) or 10),
                sprite_columns=int(request.form.get('sprite_columns', 1) or 1),
                sprite_rows=int(request.form.get('sprite_rows', 1) or 1),
                # Godot пути
                godot_texture_path=request.form.get('godot_texture_path') or None,
                godot_sprite_path=request.form.get('godot_sprite_path') or None
            )
            session_db.add(skin)
            session_db.commit()
            return redirect(url_for('races.unit_skins', race_id=race_id, unit_id=unit_id))

        return render_template_string(ADD_SKIN_TEMPLATE, race=race, unit=unit)


EDIT_SKIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Редактировать скин уровня расы - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input, .form-group textarea { width: 100%; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .form-group input[type="file"] { padding: 8px; }
        .form-group input[type="number"] { width: 120px; }
        .form-group textarea { min-height: 80px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .current-image { max-width: 200px; max-height: 200px; margin: 10px 0; border: 2px solid #444; border-radius: 5px; }
        .image-preview { max-width: 200px; max-height: 200px; margin-top: 10px; border: 2px solid #444; border-radius: 5px; }
        .form-row { display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; }
        .section { background: #2a2a2a; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .section h3 { color: #3498db; margin-top: 0; margin-bottom: 15px; font-size: 16px; }
        .help-text { color: #888; font-size: 12px; margin-top: 5px; line-height: 1.4; }
        .info-box { background: #1a3a5c; border-left: 4px solid #3498db; padding: 12px 15px; margin-bottom: 20px; border-radius: 0 5px 5px 0; }
        .info-box h4 { color: #3498db; margin: 0 0 8px 0; font-size: 14px; }
        .info-box p { color: #aaa; margin: 0; font-size: 13px; line-height: 1.5; }
        .status-box { background: #1a3a1a; border: 1px solid #2ecc71; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
        .status-box h3 { color: #2ecc71; margin: 0 0 10px 0; font-size: 16px; }
        .status-item { display: flex; align-items: center; margin: 8px 0; }
        .status-icon { margin-right: 10px; font-size: 18px; }
        .status-ok { color: #2ecc71; }
        .status-missing { color: #e74c3c; }
        .status-label { color: #aaa; min-width: 180px; }
        .status-value { color: #fff; word-break: break-all; }
        .status-value code { background: #333; padding: 2px 6px; border-radius: 3px; font-family: monospace; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>✏️ Редактировать скин уровня расы: {{ skin.name }}</h1>
        <p style="color: #aaa;">Юнит: {{ unit.unit_level.icon if unit.unit_level else '🎮' }} {{ unit.name }} | Раса: {{ race.name }}</p>

        <div class="status-box">
            <h3>📊 Статус загруженных ассетов</h3>
            <div class="status-item">
                <span class="status-icon {% if skin.image_data %}status-ok{% else %}status-missing{% endif %}">
                    {% if skin.image_data %}✅{% else %}❌{% endif %}
                </span>
                <span class="status-label">Текстура (статичная):</span>
                <span class="status-value">
                    {% if skin.image_data %}
                        Загружена ({{ (skin.image_data|length / 1024)|round(1) }} KB)
                    {% else %}
                        Не загружена
                    {% endif %}
                </span>
            </div>
            <div class="status-item">
                <span class="status-icon {% if skin.sprite_frames_data %}status-ok{% else %}status-missing{% endif %}">
                    {% if skin.sprite_frames_data %}✅{% else %}❌{% endif %}
                </span>
                <span class="status-label">Спрайт-лист (анимация):</span>
                <span class="status-value">
                    {% if skin.sprite_frames_data %}
                        Загружен ({{ (skin.sprite_frames_data|length / 1024)|round(1) }} KB, {{ skin.sprite_frame_count }} кадров, {{ skin.sprite_fps }} FPS)
                    {% else %}
                        Не загружен
                    {% endif %}
                </span>
            </div>
            <div class="status-item">
                <span class="status-icon {% if skin.godot_texture_path %}status-ok{% else %}status-missing{% endif %}">
                    {% if skin.godot_texture_path %}✅{% else %}❌{% endif %}
                </span>
                <span class="status-label">Путь к текстуре Godot:</span>
                <span class="status-value">
                    {% if skin.godot_texture_path %}
                        <code>{{ skin.godot_texture_path }}</code>
                    {% else %}
                        Не указан
                    {% endif %}
                </span>
            </div>
            <div class="status-item">
                <span class="status-icon {% if skin.godot_sprite_path %}status-ok{% else %}status-missing{% endif %}">
                    {% if skin.godot_sprite_path %}✅{% else %}❌{% endif %}
                </span>
                <span class="status-label">Путь к спрайту Godot:</span>
                <span class="status-value">
                    {% if skin.godot_sprite_path %}
                        <code>{{ skin.godot_sprite_path }}</code>
                    {% else %}
                        Не указан
                    {% endif %}
                </span>
            </div>
        </div>

        <form method="POST" enctype="multipart/form-data">
            <div class="section">
                <h3>Основные данные</h3>
                <div class="form-group">
                    <label>Название скина</label>
                    <input type="text" name="name" required value="{{ skin.name }}">
                </div>

                <div class="form-group">
                    <label>Текущее изображение</label>
                    {% if skin.image_data %}
                    <div>
                        <img src="{{ url_for('races.skin_image', skin_id=skin.id) }}" class="current-image" alt="Текущий скин">
                        <br>
                        <label style="color: #aaa;">
                            <input type="checkbox" name="delete_image"> Удалить текущее изображение
                        </label>
                    </div>
                    {% else %}
                    <p style="color: #666;">Изображение не загружено</p>
                    {% endif %}
                </div>

                <div class="form-group">
                    <label>Загрузить новое изображение (PNG, JPG до 5MB)</label>
                    <input type="file" name="image" accept="image/png,image/jpeg,image/gif,image/webp" onchange="previewImage(this)">
                    <img id="imagePreview" class="image-preview" style="display: none;">
                </div>

                <div class="form-group">
                    <label>Описание</label>
                    <textarea name="description">{{ skin.description or '' }}</textarea>
                </div>
            </div>

            <div class="section">
                <h3>Параметры спрайта для Godot</h3>

                <div class="info-box">
                    <h4>Для чего нужны эти параметры?</h4>
                    <p>Эти настройки определяют, как изображение скина будет отображаться в игровом клиенте Godot.
                    <br>• <b>Масштаб</b> — размер спрайта относительно оригинала (1.0 = 100%)
                    <br>• <b>Смещение</b> — позиция спрайта относительно центра клетки (в пикселях)
                    <br>• <b>Поворот</b> — угол поворота спрайта (в градусах)
                    <br>Для анимированных юнитов загрузите спрайт-лист и укажите количество кадров.</p>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Масштаб X</label>
                        <input type="number" name="sprite_scale_x" value="{{ skin.sprite_scale_x or 1.0 }}" step="0.1" min="0.1" max="10">
                        <p class="help-text">Масштаб по горизонтали (1.0 = оригинальный размер)</p>
                    </div>
                    <div class="form-group">
                        <label>Масштаб Y</label>
                        <input type="number" name="sprite_scale_y" value="{{ skin.sprite_scale_y or 1.0 }}" step="0.1" min="0.1" max="10">
                        <p class="help-text">Масштаб по вертикали</p>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Смещение X (пиксели)</label>
                        <input type="number" name="sprite_offset_x" value="{{ skin.sprite_offset_x or 0 }}">
                        <p class="help-text">Смещение от центра клетки по горизонтали</p>
                    </div>
                    <div class="form-group">
                        <label>Смещение Y (пиксели)</label>
                        <input type="number" name="sprite_offset_y" value="{{ skin.sprite_offset_y or 0 }}">
                        <p class="help-text">Смещение от центра клетки по вертикали</p>
                    </div>
                </div>

                <div class="form-group">
                    <label>Поворот (градусы)</label>
                    <input type="number" name="sprite_rotation" value="{{ skin.sprite_rotation or 0 }}" step="1" min="-360" max="360" style="width: 120px;">
                    <p class="help-text">Угол поворота спрайта (0-360 градусов)</p>
                </div>
            </div>

            <div class="section">
                <h3>Анимированный спрайт (опционально)</h3>

                <div class="info-box">
                    <h4>Спрайт-листы для анимации</h4>
                    <p>Если вы загружаете спрайт-лист (изображение с несколькими кадрами анимации),
                    укажите количество кадров, колонок и строк в листе. Godot использует эти данные для
                    создания AnimatedSprite2D.</p>
                </div>

                {% if skin.sprite_frames_data %}
                <div class="form-group">
                    <label>Текущий спрайт-лист</label>
                    <div>
                        <img src="{{ url_for('races.skin_sprite_frames', skin_id=skin.id) }}" class="current-image" alt="Спрайт-лист">
                        <br>
                        <label style="color: #aaa;">
                            <input type="checkbox" name="delete_sprite_frames"> Удалить спрайт-лист
                        </label>
                    </div>
                </div>
                {% endif %}

                <div class="form-group">
                    <label>{% if skin.sprite_frames_data %}Загрузить новый{% else %}Загрузить{% endif %} спрайт-лист анимации (PNG)</label>
                    <input type="file" name="sprite_frames" accept="image/png">
                    <p class="help-text">Загрузите спрайт-лист с кадрами анимации</p>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Количество кадров</label>
                        <input type="number" name="sprite_frame_count" value="{{ skin.sprite_frame_count or 1 }}" min="1" max="100">
                    </div>
                    <div class="form-group">
                        <label>Скорость (FPS)</label>
                        <input type="number" name="sprite_fps" value="{{ skin.sprite_fps or 10 }}" min="1" max="60">
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Колонок в спрайт-листе</label>
                        <input type="number" name="sprite_columns" value="{{ skin.sprite_columns or 1 }}" min="1" max="20">
                    </div>
                    <div class="form-group">
                        <label>Строк в спрайт-листе</label>
                        <input type="number" name="sprite_rows" value="{{ skin.sprite_rows or 1 }}" min="1" max="20">
                    </div>
                </div>
            </div>

            <div class="section">
                <h3>Пути в Godot проекте (опционально)</h3>
                <div class="form-group">
                    <label>Путь к текстуре в Godot</label>
                    <input type="text" name="godot_texture_path" value="{{ skin.godot_texture_path or '' }}" placeholder="res://assets/units/knight.png">
                    <p class="help-text">Путь к файлу текстуры в проекте Godot</p>
                </div>
                <div class="form-group">
                    <label>Путь к спрайту в Godot</label>
                    <input type="text" name="godot_sprite_path" value="{{ skin.godot_sprite_path or '' }}" placeholder="res://scenes/units/knight.tscn">
                    <p class="help-text">Путь к сцене спрайта в проекте Godot</p>
                </div>
            </div>

            <button type="submit" class="btn btn-success">💾 Сохранить</button>
            <a href="{{ url_for('races.unit_skins', race_id=race.id, unit_id=unit.id) }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
    <script>
    function previewImage(input) {
        if (input.files && input.files[0]) {
            var reader = new FileReader();
            reader.onload = function(e) {
                var preview = document.getElementById('imagePreview');
                preview.src = e.target.result;
                preview.style.display = 'block';
            }
            reader.readAsDataURL(input.files[0]);
        }
    }
    </script>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


@races_bp.route('/<int:race_id>/unit/<int:unit_id>/skin/<int:skin_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_unit_skin(race_id, unit_id, skin_id):
    """Редактировать скин юнита"""
    with db.get_session() as session_db:
        race = session_db.query(GameRace).filter_by(id=race_id).first()
        unit = session_db.query(RaceUnit).filter_by(id=unit_id, race_id=race_id).first()
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id, race_unit_id=unit_id).first()

        if not race or not unit or not skin:
            return redirect(url_for('races.races_list'))

        if request.method == 'POST':
            skin.name = request.form.get('name')
            skin.description = request.form.get('description') or None

            # Удаление изображения
            if request.form.get('delete_image') == 'on':
                skin.image_data = None
                skin.image_mime_type = None

            # Загрузка нового изображения
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename:
                    # Проверка размера (максимум 5MB)
                    file.seek(0, 2)
                    size = file.tell()
                    file.seek(0)

                    if size <= 5 * 1024 * 1024:  # 5MB
                        skin.image_data = file.read()
                        skin.image_mime_type = file.content_type or 'image/png'

            # Обновление параметров спрайта
            skin.sprite_scale_x = float(request.form.get('sprite_scale_x', 1.0) or 1.0)
            skin.sprite_scale_y = float(request.form.get('sprite_scale_y', 1.0) or 1.0)
            skin.sprite_offset_x = int(request.form.get('sprite_offset_x', 0) or 0)
            skin.sprite_offset_y = int(request.form.get('sprite_offset_y', 0) or 0)
            skin.sprite_rotation = float(request.form.get('sprite_rotation', 0) or 0)

            # Параметры анимации
            skin.sprite_frame_count = int(request.form.get('sprite_frame_count', 1) or 1)
            skin.sprite_fps = int(request.form.get('sprite_fps', 10) or 10)
            skin.sprite_columns = int(request.form.get('sprite_columns', 1) or 1)
            skin.sprite_rows = int(request.form.get('sprite_rows', 1) or 1)

            # Godot пути
            skin.godot_texture_path = request.form.get('godot_texture_path') or None
            skin.godot_sprite_path = request.form.get('godot_sprite_path') or None

            # Удаление спрайт-листа
            if request.form.get('delete_sprite_frames') == 'on':
                skin.sprite_frames_data = None
                skin.sprite_frames_mime_type = None

            # Загрузка спрайт-листа
            if 'sprite_frames' in request.files:
                file = request.files['sprite_frames']
                if file and file.filename:
                    file.seek(0, 2)
                    size = file.tell()
                    file.seek(0)

                    if size <= 10 * 1024 * 1024:  # 10MB
                        skin.sprite_frames_data = file.read()
                        skin.sprite_frames_mime_type = file.content_type or 'image/png'

            session_db.commit()
            return redirect(url_for('races.unit_skins', race_id=race_id, unit_id=unit_id))

        return render_template_string(EDIT_SKIN_TEMPLATE, race=race, unit=unit, skin=skin)


@races_bp.route('/skin/<int:skin_id>/delete', methods=['POST'])
@admin_required
def delete_skin(skin_id):
    """Удалить скин"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id).first()
        if skin:
            session_db.delete(skin)
            session_db.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Скин не найден'})


@races_bp.route('/skin/<int:skin_id>/image')
def skin_image(skin_id):
    """Отдача изображения скина из БД"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id).first()
        if skin and skin.image_data:
            return Response(
                skin.image_data,
                mimetype=skin.image_mime_type or 'image/png',
                headers={'Cache-Control': 'public, max-age=3600'}
            )
        # Возвращаем пустую картинку 1x1 PNG если изображение не найдено
        empty_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        return Response(empty_png, mimetype='image/png', status=404)


@races_bp.route('/skin/<int:skin_id>/sprite-frames')
def skin_sprite_frames(skin_id):
    """Отдача спрайт-листа скина из БД"""
    with db.get_session() as session_db:
        skin = session_db.query(RaceUnitSkin).filter_by(id=skin_id).first()
        if skin and skin.sprite_frames_data:
            return Response(
                skin.sprite_frames_data,
                mimetype=skin.sprite_frames_mime_type or 'image/png',
                headers={'Cache-Control': 'public, max-age=3600'}
            )
        # Возвращаем пустую картинку 1x1 PNG если изображение не найдено
        empty_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        return Response(empty_png, mimetype='image/png', status=404)


# ==================== Управление уровнями юнитов ====================

UNIT_LEVELS_LIST_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Уровни юнитов - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        body { background: #1a1a2e; color: #eee; }
        .content { padding: 20px; }
        h1 { color: #ffd700; }
        table { width: 100%; border-collapse: collapse; background: #222; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #444; }
        th { background: #333; color: #ffd700; }
        .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; text-decoration: none; display: inline-block; }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>📊 Уровни юнитов</h1>
        <p style="color: #aaa;">Справочник уровней юнитов с диапазонами престижа для найма</p>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Уровень</th>
                    <th>Иконка</th>
                    <th>Мин. престиж</th>
                    <th>Макс. престиж</th>
                    <th>Действия</th>
                </tr>
            </thead>
            <tbody>
                {% for level in levels %}
                <tr>
                    <td>{{ level.id }}</td>
                    <td>{{ level.level }}</td>
                    <td style="font-size: 24px;">{{ level.icon }}</td>
                    <td>{{ level.prestige_min }}</td>
                    <td>{{ level.prestige_max }}</td>
                    <td>
                        <a href="{{ url_for('races.edit_unit_level', level_id=level.id) }}" class="btn btn-primary">Редактировать</a>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <div style="margin-top: 20px;">
            <a href="{{ url_for('races.races_list') }}" class="btn btn-secondary">Назад к расам</a>
        </div>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""

EDIT_UNIT_LEVEL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Редактировать уровень юнита - Админ-панель</title>
    <meta charset="utf-8">
    """ + BASE_STYLE + """
    <style>
        body { background: #1a1a2e; color: #eee; }
        .content { padding: 20px; }
        h1 { color: #ffd700; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #ffd700; }
        .form-group input { width: 100%; max-width: 300px; padding: 10px; border: 1px solid #444; background: #2a2a2a; color: white; border-radius: 5px; }
        .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; text-decoration: none; display: inline-block; margin-right: 10px; }
        .btn-success { background: #2ecc71; color: white; }
        .btn-secondary { background: #666; color: white; }
    </style>
</head>
<body>
    """ + HEADER_TEMPLATE + """
    <div class="content">
        <h1>Редактировать уровень {{ level.level }}</h1>

        <form method="POST">
            <div class="form-group">
                <label>Уровень (1-7)</label>
                <input type="number" name="level" min="1" max="7" value="{{ level.level }}" required readonly>
            </div>

            <div class="form-group">
                <label>Иконка уровня</label>
                <input type="text" name="icon" value="{{ level.icon }}" required maxlength="10" style="font-size: 24px; width: 100px;">
                <small style="display: block; color: #aaa; margin-top: 5px;">Эмодзи для отображения юнитов этого уровня</small>
            </div>

            <div class="form-group">
                <label>Минимальный престиж</label>
                <input type="number" name="prestige_min" min="0" value="{{ level.prestige_min }}" required>
            </div>

            <div class="form-group">
                <label>Максимальный престиж</label>
                <input type="number" name="prestige_max" min="0" value="{{ level.prestige_max }}" required>
            </div>

            <button type="submit" class="btn btn-success">Сохранить</button>
            <a href="{{ url_for('races.unit_levels_list') }}" class="btn btn-secondary">Отмена</a>
        </form>
    </div>
    """ + FOOTER_TEMPLATE + """
</body>
</html>
"""


@races_bp.route('/unit-levels')
@admin_required
def unit_levels_list():
    """Список уровней юнитов"""
    with db.get_session() as session_db:
        levels = session_db.query(UnitLevel).order_by(UnitLevel.level).all()
        return render_template_string(UNIT_LEVELS_LIST_TEMPLATE, levels=levels, active_page='unit_levels')


@races_bp.route('/unit-levels/<int:level_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_unit_level(level_id):
    """Редактировать уровень юнита"""
    with db.get_session() as session_db:
        level = session_db.query(UnitLevel).filter_by(id=level_id).first()
        if not level:
            return redirect(url_for('races.unit_levels_list'))

        if request.method == 'POST':
            level.icon = request.form.get('icon', '🎮')
            level.prestige_min = int(request.form.get('prestige_min', 0))
            level.prestige_max = int(request.form.get('prestige_max', 100))
            session_db.commit()
            return redirect(url_for('races.unit_levels_list'))

        return render_template_string(EDIT_UNIT_LEVEL_TEMPLATE, level=level, active_page='unit_levels')
