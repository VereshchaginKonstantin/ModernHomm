#!/usr/bin/env python3
"""
Общие HTML-шаблоны для веб-интерфейса
"""

import os
from datetime import datetime


def get_web_version():
    """Получить версию веб-интерфейса из файла WEB_VERSION"""
    try:
        with open('WEB_VERSION', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"


def get_bot_version():
    """Получить версию бота из файла VERSION"""
    try:
        with open('VERSION', 'r', encoding='utf-8') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"


# HTML шаблоны для веб-интерфейса
HEADER_TEMPLATE = """
<nav class="navbar">
    <div class="nav-links">
        <a href="{{ url_for('index') }}" class="nav-link {{ 'active' if active_page == 'home' else '' }}">Список юнитов</a>
        <a href="{{ url_for('admin_images') }}" class="nav-link {{ 'active' if active_page == 'images' else '' }}">Картинки</a>
        <a href="{{ url_for('admin_units_list') }}" class="nav-link {{ 'active' if active_page == 'units' else '' }}">Управление</a>
        {% if session.username == 'okarien' %}
        <a href="{{ url_for('settings.settings_list') }}" class="nav-link {{ 'active' if active_page == 'settings' else '' }}">⚙️ Сеттинги</a>
        <a href="{{ url_for('images_manager.settings_list') }}" class="nav-link {{ 'active' if active_page == 'img_settings' else '' }}">Старые сеттинги</a>
        <a href="{{ url_for('images_manager.unit_images_list') }}" class="nav-link {{ 'active' if active_page == 'unit_images' else '' }}">Изображения</a>
        <a href="{{ url_for('images_manager.unit_levels_list') }}" class="nav-link {{ 'active' if active_page == 'unit_levels' else '' }}">Уровни</a>
        {% endif %}
        <a href="{{ url_for('arena.index') }}" class="nav-link {{ 'active' if active_page == 'arena' else '' }}">🏟️ Арена</a>
        <a href="{{ url_for('leaderboard') }}" class="nav-link {{ 'active' if active_page == 'leaderboard' else '' }}">Рейтинг</a>
        <a href="{{ url_for('help_page') }}" class="nav-link {{ 'active' if active_page == 'help' else '' }}">Справка</a>
        <a href="{{ url_for('export_units') }}" class="nav-link">Экспорт</a>
        <a href="{{ url_for('logout') }}" class="nav-link" style="margin-left: auto;">Выход ({{ session.username }})</a>
    </div>
</nav>
"""

BASE_STYLE = """
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 0;
            background-color: #f5f5f5;
        }
        .navbar {
            background-color: #2c3e50;
            padding: 15px 20px;
            margin-bottom: 30px;
        }
        .nav-links {
            display: flex;
            gap: 20px;
        }
        .nav-link {
            color: white;
            text-decoration: none;
            padding: 10px 20px;
            border-radius: 4px;
            transition: background-color 0.3s;
        }
        .nav-link:hover {
            background-color: #34495e;
        }
        .nav-link.active {
            background-color: #3498db;
        }
        .content {
            padding: 0 20px 20px 20px;
        }
        h1 {
            color: #333;
            text-align: center;
            margin: 20px 0;
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
        .form-group {
            margin-bottom: 15px;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #333;
        }
        .form-control {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            box-sizing: border-box;
        }
        .btn-primary {
            background-color: #3498db;
        }
        .btn-primary:hover {
            background-color: #2980b9;
        }
        .unit-params-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .unit-params-table th,
        .unit-params-table td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        .unit-params-table th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        .import-form {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        table {
            border-collapse: collapse;
            width: 100%;
            margin-top: 20px;
            background: white;
        }
        th, td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .btn-edit {
            background-color: #2196F3;
            color: white;
        }
        .btn-edit:hover {
            background-color: #0b7dda;
        }
        .btn-delete {
            background-color: #f44336;
            color: white;
        }
        .btn-delete:hover {
            background-color: #da190b;
        }
        .btn-view {
            background-color: #2196F3;
            color: white;
        }
        .btn-view:hover {
            background-color: #0b7dda;
        }
        .flash {
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
        }
        .thumbnail {
            width: 50px;
            height: 50px;
            object-fit: cover;
        }
        .section {
            border: 1px solid #ddd;
            padding: 15px;
            margin: 10px 0;
            background: #f9f9f9;
        }
        .section h3 {
            margin-top: 0;
        }
        input[type="text"], input[type="number"], textarea, select, input[type="file"] {
            width: 100%;
            max-width: 500px;
            padding: 8px;
            box-sizing: border-box;
        }
        textarea {
            height: 100px;
        }
        input[type="checkbox"] {
            margin-right: 5px;
        }
        .btn-secondary {
            background-color: #6c757d;
            color: white;
            text-decoration: none;
            display: inline-block;
        }
        .btn-secondary:hover {
            background-color: #5a6268;
        }
        .btn-success {
            background-color: #28a745;
            color: white;
        }
        .btn-success:hover {
            background-color: #218838;
        }
        /* Footer с версией */
        .version-footer {
            position: fixed;
            bottom: 10px;
            right: 15px;
            background: rgba(44, 62, 80, 0.9);
            color: #bdc3c7;
            padding: 8px 15px;
            border-radius: 6px;
            font-size: 11px;
            font-family: 'Courier New', monospace;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            z-index: 1000;
            line-height: 1.4;
        }
        .version-footer .version-label {
            color: #95a5a6;
            margin-right: 5px;
        }
        .version-footer .version-value {
            color: #3498db;
        }
        .version-footer .version-bot {
            color: #2ecc71;
        }
        .version-footer .version-divider {
            margin: 0 8px;
            color: #7f8c8d;
        }
    </style>
"""

FOOTER_TEMPLATE = """
<div class="version-footer">
    <span class="version-label">Web:</span>
    <span class="version-value">{{ web_version }}</span>
    <span class="version-divider">|</span>
    <span class="version-label">Bot:</span>
    <span class="version-bot">{{ bot_version }}</span>
</div>
"""
