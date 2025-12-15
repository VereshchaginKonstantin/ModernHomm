#!/usr/bin/env python3
"""
Тесты для Godot Arena
"""

import os
import pytest


class TestGodotArenaBuild:
    """Тесты для сборки Godot Arena"""

    GODOT_ARENA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'godot-arena')
    BUILD_PATH = os.path.join(GODOT_ARENA_PATH, 'build')

    def test_godot_project_exists(self):
        """Проверка существования проекта Godot"""
        project_file = os.path.join(self.GODOT_ARENA_PATH, 'project.godot')
        assert os.path.exists(project_file), "project.godot должен существовать"

    def test_godot_project_config(self):
        """Проверка конфигурации проекта Godot"""
        project_file = os.path.join(self.GODOT_ARENA_PATH, 'project.godot')
        with open(project_file, 'r') as f:
            content = f.read()

        # Проверяем основные настройки
        assert 'config/name="ModernHomm Arena"' in content, "Имя проекта должно быть ModernHomm Arena"
        assert 'run/main_scene="res://scenes/main.tscn"' in content, "Главная сцена должна быть main.tscn"
        assert 'GameManager' in content, "GameManager должен быть в autoload"
        assert 'ApiClient' in content, "ApiClient должен быть в autoload"

    def test_scenes_exist(self):
        """Проверка существования сцен"""
        scenes_path = os.path.join(self.GODOT_ARENA_PATH, 'scenes')

        assert os.path.exists(os.path.join(scenes_path, 'main.tscn')), "main.tscn должна существовать"
        assert os.path.exists(os.path.join(scenes_path, 'game.tscn')), "game.tscn должна существовать"

    def test_scripts_exist(self):
        """Проверка существования скриптов"""
        scripts_path = os.path.join(self.GODOT_ARENA_PATH, 'scripts')
        autoload_path = os.path.join(scripts_path, 'autoload')

        assert os.path.exists(os.path.join(scripts_path, 'main.gd')), "main.gd должен существовать"
        assert os.path.exists(os.path.join(scripts_path, 'game.gd')), "game.gd должен существовать"
        assert os.path.exists(os.path.join(autoload_path, 'api_client.gd')), "api_client.gd должен существовать"
        assert os.path.exists(os.path.join(autoload_path, 'game_manager.gd')), "game_manager.gd должен существовать"

    def test_build_files_exist(self):
        """Проверка существования файлов сборки"""
        assert os.path.exists(os.path.join(self.BUILD_PATH, 'index.html')), "index.html должен существовать"
        assert os.path.exists(os.path.join(self.BUILD_PATH, 'index.js')), "index.js должен существовать"
        assert os.path.exists(os.path.join(self.BUILD_PATH, 'index.wasm')), "index.wasm должен существовать"
        assert os.path.exists(os.path.join(self.BUILD_PATH, 'index.pck')), "index.pck должен существовать"

    def test_build_html_valid(self):
        """Проверка валидности HTML файла сборки"""
        html_path = os.path.join(self.BUILD_PATH, 'index.html')
        with open(html_path, 'r') as f:
            content = f.read()

        # Проверяем основные элементы HTML
        assert '<!DOCTYPE html>' in content or '<html' in content, "Должен быть валидный HTML"
        assert 'canvas' in content.lower(), "Должен быть canvas элемент для WebGL"

    def test_wasm_file_size(self):
        """Проверка размера WASM файла"""
        wasm_path = os.path.join(self.BUILD_PATH, 'index.wasm')
        file_size = os.path.getsize(wasm_path)

        # WASM должен быть достаточно большим (минимум 1MB)
        assert file_size > 1_000_000, f"WASM файл слишком маленький: {file_size} bytes"

    def test_docker_files_exist(self):
        """Проверка файлов Docker"""
        assert os.path.exists(os.path.join(self.GODOT_ARENA_PATH, 'Dockerfile')), "Dockerfile должен существовать"
        assert os.path.exists(os.path.join(self.GODOT_ARENA_PATH, 'nginx.conf')), "nginx.conf должен существовать"

    def test_export_presets_exist(self):
        """Проверка файла экспорта"""
        export_presets = os.path.join(self.GODOT_ARENA_PATH, 'export_presets.cfg')
        assert os.path.exists(export_presets), "export_presets.cfg должен существовать"

        with open(export_presets, 'r') as f:
            content = f.read()

        assert 'platform="Web"' in content, "Должен быть настроен экспорт для Web"


class TestGodotArenaScripts:
    """Тесты для скриптов Godot Arena"""

    GODOT_ARENA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'godot-arena')

    def test_api_client_endpoints(self):
        """Проверка API эндпоинтов в api_client.gd"""
        api_client_path = os.path.join(self.GODOT_ARENA_PATH, 'scripts', 'autoload', 'api_client.gd')
        with open(api_client_path, 'r') as f:
            content = f.read()

        # Проверяем наличие основных API методов
        assert 'get_players' in content, "Должен быть метод get_players"
        assert 'get_game_state' in content, "Должен быть метод get_game_state"
        assert 'create_game' in content, "Должен быть метод create_game"
        assert 'move_unit' in content, "Должен быть метод move_unit"
        assert 'attack_unit' in content, "Должен быть метод attack_unit"
        assert 'skip_unit' in content, "Должен быть метод skip_unit"

    def test_game_manager_signals(self):
        """Проверка сигналов в game_manager.gd"""
        game_manager_path = os.path.join(self.GODOT_ARENA_PATH, 'scripts', 'autoload', 'game_manager.gd')
        with open(game_manager_path, 'r') as f:
            content = f.read()

        # Проверяем наличие основных сигналов
        assert 'signal game_state_updated' in content, "Должен быть сигнал game_state_updated"
        assert 'signal game_over' in content, "Должен быть сигнал game_over"
        assert 'signal error_occurred' in content, "Должен быть сигнал error_occurred"

    def test_main_script_ui_elements(self):
        """Проверка UI элементов в main.gd"""
        main_path = os.path.join(self.GODOT_ARENA_PATH, 'scripts', 'main.gd')
        with open(main_path, 'r') as f:
            content = f.read()

        # Проверяем наличие основных UI элементов
        assert 'player_name_label' in content, "Должен быть player_name_label"
        assert 'opponent_select' in content, "Должен быть opponent_select"
        assert 'start_button' in content, "Должен быть start_button"
        assert 'pending_list' in content, "Должен быть pending_list для списка боев"

    def test_game_script_board_rendering(self):
        """Проверка рендеринга доски в game.gd"""
        game_path = os.path.join(self.GODOT_ARENA_PATH, 'scripts', 'game.gd')
        with open(game_path, 'r') as f:
            content = f.read()

        # Проверяем наличие методов рендеринга
        assert '_draw_board' in content, "Должен быть метод _draw_board"
        assert '_update_units' in content, "Должен быть метод _update_units"
        assert '_highlight_moves' in content, "Должен быть метод _highlight_moves"
        assert '_highlight_attacks' in content, "Должен быть метод _highlight_attacks"


class TestGodotArenaCORS:
    """Тесты CORS заголовков для Godot WebGL"""

    def test_nginx_cors_headers_for_godot_arena(self):
        """Проверка CORS заголовков для /godot-arena/ в nginx.conf"""
        import os
        nginx_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nginx', 'nginx.conf')
        with open(nginx_path, 'r') as f:
            content = f.read()

        # Проверяем заголовки для SharedArrayBuffer
        assert 'Cross-Origin-Opener-Policy' in content, "Должен быть заголовок Cross-Origin-Opener-Policy"
        assert 'Cross-Origin-Embedder-Policy' in content, "Должен быть заголовок Cross-Origin-Embedder-Policy"
        assert 'same-origin' in content, "Cross-Origin-Opener-Policy должен быть same-origin"
        assert 'require-corp' in content, "Cross-Origin-Embedder-Policy должен быть require-corp"

    def test_nginx_cors_resource_policy_for_api(self):
        """Проверка Cross-Origin-Resource-Policy для API запросов из Godot"""
        import os
        nginx_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nginx', 'nginx.conf')
        with open(nginx_path, 'r') as f:
            content = f.read()

        # Проверяем Cross-Origin-Resource-Policy для API (нужен для require-corp)
        assert 'Cross-Origin-Resource-Policy' in content, \
            "Должен быть заголовок Cross-Origin-Resource-Policy для API запросов из Godot WebGL"
        assert 'cross-origin' in content, \
            "Cross-Origin-Resource-Policy должен быть cross-origin для доступа из Godot арены"

    def test_godot_api_client_uses_correct_api_path(self):
        """Проверка корректного пути API в api_client.gd"""
        import os
        api_client_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                       'godot-arena', 'scripts', 'autoload', 'api_client.gd')
        with open(api_client_path, 'r') as f:
            content = f.read()

        # Проверяем что используется публичный API путь (без авторизации)
        assert '/arena/api/public' in content, "API путь должен быть /arena/api/public"
        # Проверяем что в веб-версии получаем origin из JavaScript
        assert 'window.location.origin' in content, "В веб-версии должен использоваться origin браузера"


class TestGodotArenaPublicAPI:
    """Тесты публичных API эндпоинтов для Godot"""

    def test_public_api_endpoints_exist_in_arena(self):
        """Проверка наличия публичных API эндпоинтов в arena.py"""
        import os
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        # Проверяем наличие публичных эндпоинтов
        assert '/api/public/players' in content, "Должен быть эндпоинт /api/public/players"
        assert '/api/public/games/' in content, "Должны быть эндпоинты /api/public/games/"
        assert 'api_public_players' in content, "Должна быть функция api_public_players"
        assert 'api_public_game_state' in content, "Должна быть функция api_public_game_state"
        assert 'api_public_move' in content, "Должна быть функция api_public_move"

    def test_public_api_no_login_required(self):
        """Проверка что публичные API используют JWT а не @login_required"""
        import os
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        # Проверяем что публичные API используют @token_required вместо @login_required
        assert '@token_required' in content, "Должен использоваться декоратор @token_required"
        # @login_required не должен использоваться в публичных эндпоинтах
        assert '@login_required' not in content, \
            "Публичные API эндпоинты не должны использовать @login_required"

    def test_pending_games_api_returns_player_armies(self):
        """Проверка что API pending games всегда возвращает player_armies для ожидающих игр"""
        import os
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        # Проверяем что player_armies добавляется для всех pending игр (не только с player1_army_id)
        assert "if is_pending:" in content, "Должна быть проверка is_pending для добавления player_armies"
        assert "result['player_armies'] = player_armies" in content, "player_armies должен добавляться в результат"


class TestArenaIndexRoute:
    """Тесты маршрута arena.index"""

    def test_arena_index_route_exists(self):
        """Проверка наличия маршрута arena.index в arena.py"""
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        assert "@arena_bp.route('/')" in content, "Должен быть маршрут arena.index (/)"
        assert "def index():" in content, "Должна быть функция index"
        assert "redirect('/godot-arena/')" in content, "Должен быть редирект на /godot-arena/"


class TestGodotArenaIntegration:
    """Интеграционные тесты для Godot Arena"""

    def test_arena_api_module_name(self):
        """Проверка что модуль arena.py содержит API для Godot"""
        arena_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_py_path, 'r') as f:
            content = f.read()

        assert 'Godot Arena API' in content or 'Godot клиента' in content, "Модуль должен быть для Godot Arena"
        assert 'api/public' in content, "Должны быть публичные API эндпоинты"

    def test_docker_compose_service(self):
        """Проверка сервиса в docker-compose.yml"""
        docker_compose_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'docker-compose.yml')
        with open(docker_compose_path, 'r') as f:
            content = f.read()

        assert 'godot-arena' in content, "Должен быть сервис godot-arena"

    def test_nginx_config_route(self):
        """Проверка роута в nginx.conf"""
        nginx_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'nginx', 'nginx.conf')
        with open(nginx_path, 'r') as f:
            content = f.read()

        assert 'godot-arena' in content, "Должен быть роут для godot-arena"
        assert 'godot_arena' in content, "Должен быть upstream godot_arena"


class TestGodotArenaSurrender:
    """Тесты функциональности сдачи в Godot Arena"""

    GODOT_ARENA_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'godot-arena')

    def test_surrender_endpoint_exists(self):
        """Проверка наличия эндпоинта сдачи в arena.py"""
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        assert '/api/public/games/<int:game_id>/surrender' in content, \
            "Должен быть эндпоинт /api/public/games/<game_id>/surrender"
        assert 'api_public_surrender' in content, "Должна быть функция api_public_surrender"

    def test_surrender_api_client_method(self):
        """Проверка наличия метода surrender в api_client.gd"""
        api_client_path = os.path.join(self.GODOT_ARENA_PATH, 'scripts', 'autoload', 'api_client.gd')
        with open(api_client_path, 'r') as f:
            content = f.read()

        assert 'surrender_game' in content, "Должен быть метод surrender_game"
        assert '/surrender' in content, "Метод должен вызывать эндпоинт /surrender"

    def test_surrender_game_manager_method(self):
        """Проверка наличия метода surrender в game_manager.gd"""
        game_manager_path = os.path.join(self.GODOT_ARENA_PATH, 'scripts', 'autoload', 'game_manager.gd')
        with open(game_manager_path, 'r') as f:
            content = f.read()

        assert 'surrender_game' in content, "Должен быть метод surrender_game"
        assert 'ApiClient.surrender_game' in content, "Должен вызываться ApiClient.surrender_game"

    def test_surrender_button_handler(self):
        """Проверка обработчика кнопки сдачи в game.gd"""
        game_path = os.path.join(self.GODOT_ARENA_PATH, 'scripts', 'game.gd')
        with open(game_path, 'r') as f:
            content = f.read()

        assert 'surrender_button' in content, "Должна быть кнопка surrender_button"
        assert '_on_surrender_pressed' in content, "Должен быть обработчик _on_surrender_pressed"
        assert 'GameManager.surrender_game()' in content, "Обработчик должен вызывать GameManager.surrender_game()"

    def test_surrender_handles_waiting_games(self):
        """Проверка что surrender обрабатывает ожидающие игры (отмена вызова)"""
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        assert 'GameStatus.WAITING' in content, "Должна быть проверка на WAITING статус"
        assert 'game_deleted' in content, "Для отмены вызова должен возвращаться game_deleted"

    def test_surrender_sets_winner(self):
        """Проверка что surrender устанавливает победителя"""
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        # Находим функцию surrender
        if 'api_public_surrender' in content:
            # Ищем строки после определения функции
            assert 'winner_id' in content, "Должен устанавливаться winner_id"
            assert 'GameStatus.COMPLETED' in content, "Должен устанавливаться статус COMPLETED"

    def test_surrender_creates_log_entry(self):
        """Проверка что surrender создаёт запись в логе"""
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        assert "event_type='surrender'" in content, "Должна создаваться запись в логе с типом surrender"
        assert 'сдался' in content, "Сообщение лога должно содержать 'сдался'"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
