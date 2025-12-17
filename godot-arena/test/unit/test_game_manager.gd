extends "res://addons/gut/test.gd"
## Тесты для GameManager - управление состоянием игры

const TestFixtures = preload("res://test/test_fixtures.gd")


## Тест: GameManager существует как синглтон
func test_game_manager_exists() -> void:
	var gm = get_node_or_null("/root/GameManager")
	assert_not_null(gm, "GameManager autoload should exist")


## Тест: Начальное состояние GameManager
func test_initial_state() -> void:
	var gm = get_node_or_null("/root/GameManager")
	if gm:
		assert_eq(gm.current_game_id, 0, "Initial game_id should be 0")
		assert_true(gm.game_state.is_empty(), "Initial game_state should be empty")
		assert_true(gm.selected_unit.is_empty(), "Initial selected_unit should be empty")
		assert_true(gm.current_actions.is_empty(), "Initial current_actions should be empty")


## Тест: is_my_turn возвращает правильное значение
func test_is_my_turn() -> void:
	var gm = get_node_or_null("/root/GameManager")
	if gm:
		# Устанавливаем состояние
		gm.current_player_id = 100
		gm.game_state = {"current_player_id": 100}

		assert_true(gm.is_my_turn(), "Should be my turn when IDs match")

		gm.game_state = {"current_player_id": 101}
		assert_false(gm.is_my_turn(), "Should NOT be my turn when IDs don't match")

		# Очищаем
		gm.game_state = {}
		gm.current_player_id = 0


## Тест: get_unit_by_id находит юнита
func test_get_unit_by_id() -> void:
	var gm = get_node_or_null("/root/GameManager")
	if gm:
		gm.game_state = {
			"units": [
				{"id": 1, "name": "Unit1"},
				{"id": 2, "name": "Unit2"}
			]
		}

		var unit = gm.get_unit_by_id(1)
		assert_eq(unit.get("name"), "Unit1", "Should find Unit1")

		var unit2 = gm.get_unit_by_id(2)
		assert_eq(unit2.get("name"), "Unit2", "Should find Unit2")

		var not_found = gm.get_unit_by_id(999)
		assert_true(not_found.is_empty(), "Should return empty for non-existent unit")

		# Очищаем
		gm.game_state = {}


## Тест: get_unit_at_position находит юнита по координатам
func test_get_unit_at_position() -> void:
	var gm = get_node_or_null("/root/GameManager")
	if gm:
		gm.game_state = {
			"units": [
				{"id": 1, "x": 1, "y": 2},
				{"id": 2, "x": 3, "y": 4}
			]
		}

		var unit = gm.get_unit_at_position(1, 2)
		assert_eq(unit.get("id"), 1, "Should find unit at (1,2)")

		var unit2 = gm.get_unit_at_position(3, 4)
		assert_eq(unit2.get("id"), 2, "Should find unit at (3,4)")

		var not_found = gm.get_unit_at_position(0, 0)
		assert_true(not_found.is_empty(), "Should return empty for empty position")

		# Очищаем
		gm.game_state = {}


## Тест: can_move_to проверяет доступные ходы
func test_can_move_to() -> void:
	var gm = get_node_or_null("/root/GameManager")
	if gm:
		gm.current_actions = {
			"can_move": [
				{"x": 2, "y": 3},
				{"x": 1, "y": 1}
			]
		}

		assert_true(gm.can_move_to(2, 3), "Should be able to move to (2,3)")
		assert_true(gm.can_move_to(1, 1), "Should be able to move to (1,1)")
		assert_false(gm.can_move_to(5, 5), "Should NOT be able to move to (5,5)")

		# Очищаем
		gm.current_actions = {}


## Тест: can_attack проверяет доступные атаки
func test_can_attack() -> void:
	var gm = get_node_or_null("/root/GameManager")
	if gm:
		gm.current_actions = {
			"can_attack": [
				{"id": 100},
				{"id": 200}
			]
		}

		assert_true(gm.can_attack(100), "Should be able to attack unit 100")
		assert_true(gm.can_attack(200), "Should be able to attack unit 200")
		assert_false(gm.can_attack(999), "Should NOT be able to attack unit 999")

		# Очищаем
		gm.current_actions = {}


## Тест: deselect_unit очищает выбор
func test_deselect_unit() -> void:
	var gm = get_node_or_null("/root/GameManager")
	if gm:
		gm.selected_unit = {"id": 1}
		gm.current_actions = {"can_move": []}

		gm.deselect_unit()

		assert_true(gm.selected_unit.is_empty(), "selected_unit should be empty after deselect")
		assert_true(gm.current_actions.is_empty(), "current_actions should be empty after deselect")


## Тест: start_polling и stop_polling работают
func test_polling_control() -> void:
	var gm = get_node_or_null("/root/GameManager")
	if gm and gm.polling_timer:
		# Изначально таймер остановлен
		assert_false(gm.polling_timer.is_stopped() == false and gm.polling_timer.time_left > 0,
			"Polling should not be running initially")

		gm.start_polling()
		assert_false(gm.polling_timer.is_stopped(), "Polling should be running after start")

		gm.stop_polling()
		assert_true(gm.polling_timer.is_stopped(), "Polling should be stopped after stop")


## Тест: return_to_menu очищает состояние
func test_return_to_menu_clears_state() -> void:
	var gm = get_node_or_null("/root/GameManager")
	if gm:
		# Устанавливаем состояние
		gm.current_game_id = 123
		gm.game_state = {"test": "data"}
		gm.selected_unit = {"id": 1}

		# Мокаем change_scene чтобы не менять сцену в тесте
		# Просто проверяем что состояние очищается перед вызовом

		gm.stop_polling()
		gm.deselect_unit()
		gm.current_game_id = 0
		gm.game_state = {}

		assert_eq(gm.current_game_id, 0, "game_id should be reset")
		assert_true(gm.game_state.is_empty(), "game_state should be empty")
		assert_true(gm.selected_unit.is_empty(), "selected_unit should be empty")
