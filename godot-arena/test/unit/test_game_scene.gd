extends "res://addons/gut/test.gd"
## Тесты для игровой сцены - проверка отображения доски и юнитов

const TestFixtures = preload("res://test/test_fixtures.gd")

var game_scene: Node
var game_script: GDScript


func before_all() -> void:
	# Загружаем скрипт игры для тестирования изолированных функций
	game_script = load("res://scripts/game.gd")


func before_each() -> void:
	# Создаём новый экземпляр сцены для каждого теста
	game_scene = load("res://scenes/game.tscn").instantiate()
	add_child_autofree(game_scene)
	# Ждём инициализации
	await get_tree().process_frame


func after_each() -> void:
	game_scene = null


## Тест: Сцена успешно загружается
func test_game_scene_loads() -> void:
	assert_not_null(game_scene, "Game scene should load")
	assert_true(game_scene is Control, "Game scene should be Control node")


## Тест: Основные UI элементы существуют
func test_ui_elements_exist() -> void:
	var board = game_scene.get_node_or_null("Board")
	assert_not_null(board, "Board node should exist")

	var hint_label = game_scene.get_node_or_null("UI/HintLabel")
	assert_not_null(hint_label, "HintLabel should exist")

	var turn_label = game_scene.get_node_or_null("UI/TurnLabel")
	assert_not_null(turn_label, "TurnLabel should exist")


## Тест: Кнопки действий существуют
func test_action_buttons_exist() -> void:
	var move_btn = game_scene.get_node_or_null("UI/Actions/MoveButton")
	var attack_btn = game_scene.get_node_or_null("UI/Actions/AttackButton")
	var skip_btn = game_scene.get_node_or_null("UI/Actions/SkipButton")
	var defer_btn = game_scene.get_node_or_null("UI/Actions/DeferButton")
	var surrender_btn = game_scene.get_node_or_null("UI/SurrenderButton")

	assert_not_null(move_btn, "Move button should exist")
	assert_not_null(attack_btn, "Attack button should exist")
	assert_not_null(skip_btn, "Skip button should exist")
	assert_not_null(defer_btn, "Defer button should exist")
	assert_not_null(surrender_btn, "Surrender button should exist")


## Тест: Конвертация grid -> iso координат
func test_grid_to_iso_conversion() -> void:
	# Функция grid_to_iso определена в game.gd
	# grid_to_iso(x, y) = Vector2((x - y) * TILE_WIDTH / 2 + offset, (x + y) * TILE_HEIGHT / 2 + offset)
	# Проверяем что функция возвращает Vector2

	# Для этого теста нам нужен доступ к методу, который мы проверим через сцену
	if game_scene.has_method("grid_to_iso"):
		var result = game_scene.grid_to_iso(0, 0)
		assert_true(result is Vector2, "grid_to_iso should return Vector2")

		var result2 = game_scene.grid_to_iso(1, 1)
		assert_true(result2.y > result.y, "Y should increase when both x and y increase")


## Тест: Конвертация iso -> grid координат
func test_iso_to_grid_conversion() -> void:
	if game_scene.has_method("iso_to_grid"):
		# Проверяем обратное преобразование
		var iso_pos = Vector2(400, 300)
		var grid_pos = game_scene.iso_to_grid(iso_pos)
		assert_true(grid_pos is Vector2, "iso_to_grid should return Vector2")


## Тест: Начальное состояние - кнопки disabled
func test_initial_buttons_state() -> void:
	var move_btn = game_scene.get_node_or_null("UI/Actions/MoveButton")
	var attack_btn = game_scene.get_node_or_null("UI/Actions/AttackButton")

	# В начале кнопки должны быть неактивны (нет выбранного юнита)
	if move_btn:
		assert_true(move_btn.disabled, "Move button should be disabled initially")
	if attack_btn:
		assert_true(attack_btn.disabled, "Attack button should be disabled initially")


## Тест: Размер поля по умолчанию
func test_default_field_size() -> void:
	# Проверяем что field_size инициализирован
	if "field_size" in game_scene:
		assert_eq(game_scene.field_size, 5, "Default field size should be 5")


## Тест: Словари для юнитов пусты изначально
func test_initial_empty_collections() -> void:
	if "unit_sprites" in game_scene:
		assert_eq(game_scene.unit_sprites.size(), 0, "unit_sprites should be empty initially")

	if "unit_positions" in game_scene:
		assert_eq(game_scene.unit_positions.size(), 0, "unit_positions should be empty initially")

	if "cells" in game_scene:
		assert_eq(game_scene.cells.size(), 0, "cells should be empty initially")


## Тест: Overlay для game over скрыт изначально
func test_game_over_overlay_hidden() -> void:
	var overlay = game_scene.get_node_or_null("GameOverOverlay")
	if overlay:
		assert_false(overlay.visible, "GameOverOverlay should be hidden initially")
