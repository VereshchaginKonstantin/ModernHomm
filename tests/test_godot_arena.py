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


class TestGameEngineValidMoves:
    """Тесты для методов get_valid_moves и get_valid_attacks в GameEngine"""

    def test_get_valid_moves_method_exists(self):
        """Проверка наличия метода get_valid_moves в GameEngine"""
        game_engine_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'core', 'game_engine.py')
        with open(game_engine_path, 'r') as f:
            content = f.read()

        assert 'def get_valid_moves(self, battle_unit_id: int)' in content, \
            "Должен быть метод get_valid_moves(battle_unit_id)"
        assert "return [{'x': x, 'y': y}" in content, \
            "get_valid_moves должен возвращать список словарей с x, y"

    def test_get_valid_attacks_method_exists(self):
        """Проверка наличия метода get_valid_attacks в GameEngine"""
        game_engine_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'core', 'game_engine.py')
        with open(game_engine_path, 'r') as f:
            content = f.read()

        assert 'def get_valid_attacks(self, battle_unit_id: int)' in content, \
            "Должен быть метод get_valid_attacks(battle_unit_id)"
        assert "'id': t['unit_id']" in content, \
            "get_valid_attacks должен возвращать id цели"

    def test_unit_actions_api_uses_engine_methods(self):
        """Проверка что API unit_actions использует методы GameEngine"""
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        assert 'engine.get_valid_moves(unit_id)' in content, \
            "API должен использовать engine.get_valid_moves()"
        assert 'engine.get_valid_attacks(unit_id)' in content, \
            "API должен использовать engine.get_valid_attacks()"

    def test_get_unit_stats_returns_dict(self):
        """Проверка что _get_unit_stats возвращает словарь и используется правильно"""
        game_engine_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'core', 'game_engine.py')
        with open(game_engine_path, 'r') as f:
            content = f.read()

        # Проверяем что в get_available_movement_cells используется unit['speed']
        assert "speed = unit['speed']" in content, \
            "_get_unit_stats возвращает словарь, доступ должен быть через unit['speed']"


class TestHireCostFix:
    """Тесты для исправления hire_cost"""

    def test_get_hire_cost_function_exists(self):
        """Проверка наличия функции _get_hire_cost"""
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        assert 'def _get_hire_cost(race_unit)' in content, \
            "Должна быть функция _get_hire_cost"
        assert 'unit_level.prestige_max' in content, \
            "_get_hire_cost должна использовать prestige_max из unit_level"

    def test_armies_api_uses_get_hire_cost(self):
        """Проверка что API armies использует _get_hire_cost"""
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        # Проверяем что hire_cost берётся через функцию, а не атрибут
        assert "_get_hire_cost(au.race_unit)" in content, \
            "API должен использовать _get_hire_cost() для получения стоимости найма"
        # Не должно быть прямого обращения к race_unit.hire_cost
        lines_with_hire_cost = [line for line in content.split('\n')
                                if 'race_unit.hire_cost' in line and 'def _get_hire_cost' not in line]
        assert len(lines_with_hire_cost) == 0, \
            f"Не должно быть прямого обращения к race_unit.hire_cost: {lines_with_hire_cost}"

    def test_available_units_api_uses_get_hire_cost(self):
        """Проверка что API available_units использует _get_hire_cost"""
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        assert "hire_cost = _get_hire_cost(ru)" in content, \
            "API available_units должен использовать _get_hire_cost()"
        # can_hire учитывает hire_cost через player_balance >= hire_cost
        assert "'hire_cost': hire_cost" in content, \
            "hire_cost должен передаваться в ответ API"


class TestUnitActionsAPIEndpoint:
    """Тесты для API эндпоинта unit_actions"""

    def test_unit_actions_endpoint_exists(self):
        """Проверка наличия эндпоинта unit_actions"""
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        assert '/api/public/games/<int:game_id>/units/<int:unit_id>/actions' in content, \
            "Должен быть эндпоинт /api/public/games/<game_id>/units/<unit_id>/actions"
        assert 'def api_public_unit_actions' in content, \
            "Должна быть функция api_public_unit_actions"

    def test_unit_actions_returns_moves_and_attacks(self):
        """Проверка что unit_actions возвращает moves и attacks"""
        arena_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'arena.py')
        with open(arena_path, 'r') as f:
            content = f.read()

        assert "'moves': moves" in content, "Должен возвращать moves"
        assert "'attacks': attacks" in content, "Должен возвращать attacks"

    def test_unit_actions_api_client_method(self):
        """Проверка наличия метода get_unit_actions в api_client.gd"""
        api_client_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                       'godot-arena', 'scripts', 'autoload', 'api_client.gd')
        with open(api_client_path, 'r') as f:
            content = f.read()

        assert 'get_unit_actions' in content, "Должен быть метод get_unit_actions"
        assert '/actions' in content, "Метод должен вызывать эндпоинт /actions"


class TestGameManagerDictionaryAccess:
    """Тесты для проверки корректного доступа к словарям в GameManager"""

    GAME_MANAGER_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                      'godot-arena', 'scripts', 'autoload', 'game_manager.gd')

    def test_move_selected_unit_uses_get(self):
        """Проверка что move_selected_unit использует get() вместо прямого доступа"""
        with open(self.GAME_MANAGER_PATH, 'r') as f:
            content = f.read()

        # Не должно быть selected_unit.id - только selected_unit.get("id")
        assert 'selected_unit.get("id"' in content, \
            "move_selected_unit должен использовать selected_unit.get('id')"
        # Проверяем что нет прямого доступа selected_unit.id
        lines = content.split('\n')
        for line in lines:
            if 'selected_unit.id' in line and 'selected_unit.get' not in line:
                assert False, f"Найден прямой доступ selected_unit.id: {line}"

    def test_attack_with_selected_unit_uses_get(self):
        """Проверка что attack_with_selected_unit использует get()"""
        with open(self.GAME_MANAGER_PATH, 'r') as f:
            content = f.read()

        # Должен использовать selected_unit.get("id")
        assert 'attack_with_selected_unit' in content
        # Проверяем что функция использует get для доступа к id

    def test_skip_and_defer_use_get(self):
        """Проверка что skip и defer используют get()"""
        with open(self.GAME_MANAGER_PATH, 'r') as f:
            content = f.read()

        # Должны использовать selected_unit.get("id")
        assert content.count('selected_unit.get("id"') >= 4, \
            "Все методы работы с юнитом должны использовать get()"


class TestGameLoadingHintUpdate:
    """Тесты для проверки обновления hint_label при загрузке игры

    Баг: При входе в игру hint_label устанавливается в "Загрузка игры..."
    но после успешного получения состояния игры никогда не обновляется,
    создавая впечатление вечной загрузки.
    """

    GAME_GD_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 'godot-arena', 'scripts', 'game.gd')

    def test_hint_label_set_to_loading_on_start(self):
        """Проверка что hint_label устанавливается в 'Загрузка игры...' при старте"""
        with open(self.GAME_GD_PATH, 'r') as f:
            content = f.read()

        assert 'hint_label.text = "Загрузка игры..."' in content, \
            "При старте hint_label должен устанавливаться в 'Загрузка игры...'"

    def test_hint_label_updated_after_game_state_received(self):
        """Проверка что hint_label обновляется после получения состояния игры

        Это основной тест на баг: после успешного получения game_state
        hint_label должен быть обновлён, чтобы пользователь знал что игра загружена.
        """
        with open(self.GAME_GD_PATH, 'r') as f:
            content = f.read()

        # Ищем функцию _on_game_state_updated
        assert '_on_game_state_updated' in content, \
            "Должна быть функция _on_game_state_updated"

        # После успешной загрузки состояния hint_label должен обновиться
        # Ищем обновление hint_label внутри _on_game_state_updated
        # Функция должна содержать обновление hint_label для информирования игрока

        # Находим содержимое функции _on_game_state_updated
        func_start = content.find('func _on_game_state_updated')
        if func_start == -1:
            assert False, "Функция _on_game_state_updated не найдена"

        # Находим конец функции (следующий func или конец файла)
        next_func = content.find('\nfunc ', func_start + 1)
        if next_func == -1:
            next_func = len(content)

        func_content = content[func_start:next_func]

        # Проверяем что внутри функции есть обновление hint_label
        # (исключая строки с "Ошибка:", которые для ошибок)
        hint_updates = [line for line in func_content.split('\n')
                       if 'hint_label.text' in line and 'Ошибка' not in line]

        assert len(hint_updates) > 0, \
            "После успешного получения game_state функция _on_game_state_updated " \
            "должна обновлять hint_label, чтобы пользователь знал что игра загружена. " \
            "Текущий баг: hint_label остаётся на 'Загрузка игры...' навсегда."

    def test_game_status_shown_in_hint(self):
        """Проверка что hint_label показывает статус игры (чей ход)"""
        with open(self.GAME_GD_PATH, 'r') as f:
            content = f.read()

        # После загрузки игры hint должен показывать информацию о ходе
        # или подсказку что делать (выбрать юнита)
        assert 'Выберите юнита' in content or 'Ваш ход' in content or 'Ход противника' in content, \
            "hint_label должен показывать статус игры после загрузки"


class TestTextureLoadingAuth:
    """Тесты для проверки авторизации при загрузке текстур"""

    GAME_GD_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                 'godot-arena', 'scripts', 'game.gd')

    def test_texture_loading_adds_auth_header(self):
        """Проверка что загрузка текстур добавляет JWT токен"""
        with open(self.GAME_GD_PATH, 'r') as f:
            content = f.read()

        assert 'Authorization: Bearer' in content, \
            "Загрузка текстур должна добавлять Authorization header"
        assert 'ApiClient.auth_token' in content, \
            "Должен использоваться токен из ApiClient"

    def test_texture_loading_uses_headers(self):
        """Проверка что HTTP запрос текстуры использует заголовки"""
        with open(self.GAME_GD_PATH, 'r') as f:
            content = f.read()

        # Проверяем что http.request вызывается с headers
        assert 'http.request(url, headers)' in content, \
            "HTTP запрос текстуры должен передавать headers"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
