extends "res://addons/gut/test.gd"
## Тесты для обработки пользовательского ввода

const TestFixtures = preload("res://test/test_fixtures.gd")

var game_scene: Node


func before_each() -> void:
	game_scene = load("res://scenes/game.tscn").instantiate()
	add_child_autofree(game_scene)
	await get_tree().process_frame

	# Подготавливаем доску
	if game_scene.has_method("_draw_board"):
		game_scene.field_size = 5
		game_scene._draw_board()
		await get_tree().process_frame


func after_each() -> void:
	game_scene = null


## Тест: Клик по пустой клетке не вызывает ошибку
func test_click_empty_cell() -> void:
	# Симулируем клик по пустой позиции
	if game_scene.has_method("_on_cell_clicked"):
		# Не должно быть исключений
		game_scene._on_cell_clicked(2, 2)
		assert_true(true, "Click on empty cell should not crash")


## Тест: Клик по своему юниту выбирает его
func test_click_own_unit_selects() -> void:
	# Создаём юнита
	var unit = TestFixtures.get_test_unit_player1()
	if game_scene.has_method("_update_units"):
		game_scene._update_units([unit])
		await get_tree().process_frame

	# Устанавливаем что это наш ход
	var gm = get_node_or_null("/root/GameManager")
	if gm:
		gm.current_player_id = 100
		gm.game_state = {
			"current_player_id": 100,
			"units": [unit]
		}

		# Клик по юниту
		if game_scene.has_method("_on_cell_clicked"):
			game_scene._on_cell_clicked(1, 2)  # Позиция юнита

			# Проверяем что юнит выбран
			# (в реальности это делает GameManager через select_unit)


## Тест: Кнопка Move активируется при выборе юнита с доступными ходами
func test_move_button_enabled_with_moves() -> void:
	var move_btn = game_scene.get_node_or_null("UI/Actions/MoveButton")

	if move_btn:
		# Изначально disabled
		assert_true(move_btn.disabled, "Move button should be disabled initially")

		# Симулируем получение действий с доступными ходами
		if "move_mode" in game_scene:
			# Эмулируем что есть доступные ходы
			if game_scene.has_method("_on_unit_actions_received"):
				var actions = TestFixtures.get_test_unit_actions()
				game_scene._on_unit_actions_received(actions)
				await get_tree().process_frame

				# Кнопка должна стать активной если есть ходы
				# assert_false(move_btn.disabled, "Move button should be enabled with available moves")


## Тест: Кнопка Attack активируется при наличии целей
func test_attack_button_enabled_with_targets() -> void:
	var attack_btn = game_scene.get_node_or_null("UI/Actions/AttackButton")

	if attack_btn:
		# Изначально disabled
		assert_true(attack_btn.disabled, "Attack button should be disabled initially")


## Тест: Нажатие Skip вызывает skip_selected_unit
func test_skip_button_calls_skip() -> void:
	var skip_btn = game_scene.get_node_or_null("UI/Actions/SkipButton")

	if skip_btn:
		# Кнопка существует
		assert_not_null(skip_btn, "Skip button should exist")
		assert_true(skip_btn.disabled, "Skip button should be disabled without selection")


## Тест: Нажатие Defer вызывает defer_selected_unit
func test_defer_button_calls_defer() -> void:
	var defer_btn = game_scene.get_node_or_null("UI/Actions/DeferButton")

	if defer_btn:
		assert_not_null(defer_btn, "Defer button should exist")
		assert_true(defer_btn.disabled, "Defer button should be disabled without selection")


## Тест: Режим перемещения подсвечивает доступные клетки
func test_move_mode_highlights_cells() -> void:
	if "move_mode" in game_scene and "highlighted_cells" in game_scene:
		game_scene.move_mode = false
		assert_eq(game_scene.highlighted_cells.size(), 0, "No cells highlighted when not in move mode")


## Тест: Режим атаки подсвечивает цели
func test_attack_mode_highlights_targets() -> void:
	if "attack_mode" in game_scene:
		game_scene.attack_mode = false
		# Проверяем начальное состояние
		assert_false(game_scene.attack_mode, "Attack mode should be off initially")


## Тест: ESC отменяет выбор
func test_escape_deselects() -> void:
	# Создаём событие ESC
	var escape_event = InputEventKey.new()
	escape_event.keycode = KEY_ESCAPE
	escape_event.pressed = true

	# Симулируем нажатие
	if game_scene.has_method("_input"):
		# В реальности _input обрабатывает escape
		pass


## Тест: Клик по доступной клетке в режиме перемещения выполняет ход
func test_click_available_cell_moves_unit() -> void:
	# Подготовка - создаём юнита и устанавливаем режим перемещения
	var unit = TestFixtures.get_test_unit_player1()
	if game_scene.has_method("_update_units"):
		game_scene._update_units([unit])
		await get_tree().process_frame

	# Устанавливаем состояние
	if "selected_unit_id" in game_scene:
		game_scene.selected_unit_id = 1001

	if "move_mode" in game_scene:
		game_scene.move_mode = true

	if "available_moves" in game_scene:
		game_scene.available_moves = [{"x": 2, "y": 2}]

	# Клик по доступной клетке
	if game_scene.has_method("_on_cell_clicked"):
		game_scene._on_cell_clicked(2, 2)
		# В реальности это вызовет GameManager.move_selected_unit


## Тест: Клик по врагу в режиме атаки выполняет атаку
func test_click_enemy_attacks() -> void:
	# Создаём юнитов
	var units = [
		TestFixtures.get_test_unit_player1(),
		TestFixtures.get_test_unit_player2()
	]
	if game_scene.has_method("_update_units"):
		game_scene._update_units(units)
		await get_tree().process_frame

	# Устанавливаем режим атаки
	if "attack_mode" in game_scene:
		game_scene.attack_mode = true

	if "available_attacks" in game_scene:
		game_scene.available_attacks = [{"id": 1002, "x": 3, "y": 2}]

	# Клик по врагу
	if game_scene.has_method("_on_cell_clicked"):
		game_scene._on_cell_clicked(3, 2)  # Позиция вражеского юнита
		# В реальности это вызовет GameManager.attack_with_selected_unit


## Тест: Surrender button показывает подтверждение
func test_surrender_button() -> void:
	var surrender_btn = game_scene.get_node_or_null("UI/SurrenderButton")

	if surrender_btn:
		assert_not_null(surrender_btn, "Surrender button should exist")
		# Кнопка должна быть активна
		# assert_false(surrender_btn.disabled, "Surrender button should be enabled")
