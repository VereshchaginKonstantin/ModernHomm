#!/usr/bin/env python3
"""
Админка Flask для управления картинками юнитов
"""

import os
import json
from flask import Flask, render_template_string, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from db import Database
from db.models import Unit

# Создать Flask приложение
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'
app.config['UPLOAD_FOLDER'] = 'static/unit_images'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB max file size

# Инициализировать базу данных
config_path = 'config.json'
try:
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
except FileNotFoundError:
    print(f"Файл конфигурации {config_path} не найден!")
    exit(1)

db_url = os.getenv('DATABASE_URL', config.get('database', {}).get('url'))
db = Database(db_url)

# HTML шаблон для админки
ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Админка - Управление картинками юнитов</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .units-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .unit-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .unit-card h2 {
            margin-top: 0;
            color: #444;
            font-size: 20px;
        }
        .unit-info {
            margin: 10px 0;
            color: #666;
            font-size: 14px;
        }
        .unit-image {
            width: 150px;
            height: 150px;
            object-fit: contain;
            border: 2px solid #ddd;
            border-radius: 4px;
            margin: 10px 0;
            background-color: #f9f9f9;
        }
        .no-image {
            width: 150px;
            height: 150px;
            display: flex;
            align-items: center;
            justify-content: center;
            background-color: #eee;
            border: 2px dashed #ccc;
            border-radius: 4px;
            margin: 10px 0;
            color: #999;
            font-size: 14px;
        }
        .upload-form {
            margin-top: 15px;
        }
        .file-input {
            margin: 10px 0;
        }
        .btn {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
        }
        .btn:hover {
            background-color: #45a049;
        }
        .btn-danger {
            background-color: #f44336;
        }
        .btn-danger:hover {
            background-color: #da190b;
        }
        .alert {
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .alert-success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .alert-error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .stats {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }
        .stats-item {
            display: inline-block;
            margin: 0 20px;
        }
        .stats-number {
            font-size: 32px;
            font-weight: bold;
            color: #4CAF50;
        }
        .stats-label {
            font-size: 14px;
            color: #666;
        }
    </style>
</head>
<body>
    <h1>Админка - Управление картинками юнитов</h1>

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
</body>
</html>
"""


@app.route('/')
def index():
    """Главная страница админки"""
    units = db.session.query(Unit).all()

    # Проверить наличие файлов для каждого юнита
    for unit in units:
        unit.has_image = unit.image_path and os.path.exists(unit.image_path)

    # Подсчитать статистику
    stats = {
        'total': len(units),
        'with_images': sum(1 for u in units if u.has_image),
        'without_images': sum(1 for u in units if not u.has_image)
    }

    return render_template_string(ADMIN_TEMPLATE, units=units, stats=stats)


@app.route('/upload/<int:unit_id>', methods=['POST'])
def upload_image(unit_id):
    """Загрузка картинки для юнита"""
    if 'image' not in request.files:
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))

    file = request.files['image']
    if file.filename == '':
        flash('Файл не выбран', 'error')
        return redirect(url_for('index'))

    if file:
        # Получить юнит
        unit = db.session.query(Unit).filter_by(id=unit_id).first()
        if not unit:
            flash('Юнит не найден', 'error')
            return redirect(url_for('index'))

        # Создать безопасное имя файла
        filename = secure_filename(f"unit_{unit_id}_{file.filename}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Сохранить файл
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)

        # Обновить путь в базе данных
        unit.image_path = filepath
        db.session.commit()

        flash(f'Картинка для {unit.name} успешно загружена!', 'success')

    return redirect(url_for('index'))


@app.route('/delete/<int:unit_id>', methods=['POST'])
def delete_image(unit_id):
    """Удаление картинки юнита"""
    unit = db.session.query(Unit).filter_by(id=unit_id).first()
    if not unit:
        flash('Юнит не найден', 'error')
        return redirect(url_for('index'))

    if unit.image_path and os.path.exists(unit.image_path):
        # Удалить файл
        os.remove(unit.image_path)
        flash(f'Картинка для {unit.name} удалена', 'success')

    # Очистить путь в базе данных
    unit.image_path = None
    db.session.commit()

    return redirect(url_for('index'))


if __name__ == '__main__':
    print("Запуск админки на http://localhost:5000")
    print("Используйте Ctrl+C для остановки")
    app.run(host='0.0.0.0', port=5000, debug=True)
