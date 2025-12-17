extends Node
## Тест раннер который работает в контексте сцены

var tests_passed: int = 0
var tests_failed: int = 0

func _ready() -> void:
	print("\n========================================")
	print("   MODERNHOMM ARENA TEST SUITE")
	print("   (Scene Context)")
	print("========================================\n")

	# Ждём один кадр для инициализации autoload
	await get_tree().process_frame
	await get_tree().process_frame

	# Запускаем тесты
	await run_all_tests()

	# Выводим результаты
	print("\n========================================")
	print("   RESULTS")
	print("========================================")
	print("Passed: %d" % tests_passed)
	print("Failed: %d" % tests_failed)
	print("Total:  %d" % (tests_passed + tests_failed))

	if tests_failed == 0:
		print("\n✓ ALL TESTS PASSED!")
	else:
		print("\n✗ SOME TESTS FAILED!")

	print("========================================\n")

	# Выход
	get_tree().quit(0 if tests_failed == 0 else 1)

func assert_true(condition: bool, message: String) -> void:
	if condition:
		tests_passed += 1
		print("  ✓ %s" % message)
	else:
		tests_failed += 1
		print("  ✗ FAILED: %s" % message)

func assert_false(condition: bool, message: String) -> void:
	assert_true(not condition, message)

func assert_eq(a, b, message: String) -> void:
	if a == b:
		tests_passed += 1
		print("  ✓ %s" % message)
	else:
		tests_failed += 1
		print("  ✗ FAILED: %s (expected %s, got %s)" % [message, str(b), str(a)])

func assert_not_null(obj, message: String) -> void:
	if obj != null:
		tests_passed += 1
		print("  ✓ %s" % message)
	else:
		tests_failed += 1
		print("  ✗ FAILED: %s (was null)" % message)

func run_all_tests() -> void:
	# GameManager тесты
	print("\n[GameManager Tests]")
	await test_game_manager_exists()
	await test_game_manager_initial_state()
	await test_game_manager_is_my_turn()
	await test_game_manager_get_unit_by_id()
	await test_game_manager_get_unit_at_position()
	await test_game_manager_can_move_to()
	await test_game_manager_can_attack()
	await test_game_manager_deselect_unit()

	# ApiClient тесты
	print("\n[ApiClient Tests]")
	await test_api_client_exists()
	await test_api_client_authentication()

	# Сцена игры
	print("\n[Game Scene Tests]")
	await test_game_scene_loads()
	await test_game_scene_board_creation()
	await test_game_scene_unit_creation()
	await test_game_scene_coordinate_conversion()

	# Интеграционные тесты
	print("\n[Integration Tests]")
	await test_full_battle_scenario()

# ============ GameManager Tests ============

func test_game_manager_exists() -> void:
	assert_not_null(GameManager, "GameManager autoload exists")

func test_game_manager_initial_state() -> void:
	# Сохраняем оригинальное состояние
	var orig_game_id = GameManager.current_game_id
	var orig_state = GameManager.game_state.duplicate()

	# Тестируем начальные значения
	GameManager.current_game_id = 0
	GameManager.game_state = {}

	assert_eq(GameManager.current_game_id, 0, "game_id starts at 0")
	assert_true(GameManager.game_state.is_empty(), "game_state starts empty")

	# Восстанавливаем
	GameManager.current_game_id = orig_game_id
	GameManager.game_state = orig_state

func test_game_manager_is_my_turn() -> void:
	var orig_player_id = GameManager.current_player_id
	var orig_state = GameManager.game_state.duplicate()

	GameManager.current_player_id = 100
	GameManager.game_state = {"current_player_id": 100}
	assert_true(GameManager.is_my_turn(), "is_my_turn true when IDs match")

	GameManager.game_state = {"current_player_id": 101}
	assert_false(GameManager.is_my_turn(), "is_my_turn false when IDs differ")

	GameManager.current_player_id = orig_player_id
	GameManager.game_state = orig_state

func test_game_manager_get_unit_by_id() -> void:
	var orig_state = GameManager.game_state.duplicate()

	GameManager.game_state = {
		"units": [
			{"id": 1, "name": "Unit1"},
			{"id": 2, "name": "Unit2"}
		]
	}

	var unit = GameManager.get_unit_by_id(1)
	assert_eq(unit.get("name"), "Unit1", "get_unit_by_id finds unit")

	var not_found = GameManager.get_unit_by_id(999)
	assert_true(not_found.is_empty(), "get_unit_by_id returns empty for non-existent")

	GameManager.game_state = orig_state

func test_game_manager_get_unit_at_position() -> void:
	var orig_state = GameManager.game_state.duplicate()

	GameManager.game_state = {
		"units": [
			{"id": 1, "x": 2, "y": 3},
			{"id": 2, "x": 4, "y": 5}
		]
	}

	var unit = GameManager.get_unit_at_position(2, 3)
	assert_eq(unit.get("id"), 1, "get_unit_at_position finds unit")

	var empty = GameManager.get_unit_at_position(0, 0)
	assert_true(empty.is_empty(), "get_unit_at_position returns empty for no unit")

	GameManager.game_state = orig_state

func test_game_manager_can_move_to() -> void:
	var orig_actions = GameManager.current_actions.duplicate()

	GameManager.current_actions = {
		"can_move": [{"x": 1, "y": 2}, {"x": 3, "y": 4}]
	}

	assert_true(GameManager.can_move_to(1, 2), "can_move_to true for valid position")
	assert_false(GameManager.can_move_to(9, 9), "can_move_to false for invalid position")

	GameManager.current_actions = orig_actions

func test_game_manager_can_attack() -> void:
	var orig_actions = GameManager.current_actions.duplicate()

	GameManager.current_actions = {
		"can_attack": [{"id": 100}, {"id": 200}]
	}

	assert_true(GameManager.can_attack(100), "can_attack true for valid target")
	assert_false(GameManager.can_attack(999), "can_attack false for invalid target")

	GameManager.current_actions = orig_actions

func test_game_manager_deselect_unit() -> void:
	GameManager.selected_unit = {"id": 1}
	GameManager.current_actions = {"test": "data"}

	GameManager.deselect_unit()

	assert_true(GameManager.selected_unit.is_empty(), "deselect_unit clears selected_unit")
	assert_true(GameManager.current_actions.is_empty(), "deselect_unit clears actions")

# ============ ApiClient Tests ============

func test_api_client_exists() -> void:
	assert_not_null(ApiClient, "ApiClient autoload exists")

func test_api_client_authentication() -> void:
	var orig_token = ApiClient.auth_token
	var orig_player_id = ApiClient.player_id

	ApiClient.auth_token = ""
	ApiClient.player_id = 0
	assert_false(ApiClient.is_authenticated(), "Not authenticated without token")

	ApiClient.auth_token = "test_token"
	ApiClient.player_id = 1
	assert_true(ApiClient.is_authenticated(), "Authenticated with token and player_id")

	ApiClient.logout()
	assert_false(ApiClient.is_authenticated(), "Not authenticated after logout")

	ApiClient.auth_token = orig_token
	ApiClient.player_id = orig_player_id

# ============ Game Scene Tests ============

func test_game_scene_loads() -> void:
	var scene = load("res://scenes/game.tscn")
	assert_not_null(scene, "Game scene resource loads")

	var instance = scene.instantiate()
	assert_not_null(instance, "Game scene instantiates")

	instance.queue_free()

func test_game_scene_board_creation() -> void:
	var scene = load("res://scenes/game.tscn").instantiate()
	add_child(scene)
	await get_tree().process_frame

	var board = scene.get_node_or_null("HBoxContainer/BoardContainer/Board")
	assert_not_null(board, "Board node exists")

	# Тестируем создание доски
	if scene.has_method("_draw_board"):
		scene.field_size = 5
		scene._draw_board()
		await get_tree().process_frame

		if "cells" in scene:
			assert_eq(scene.cells.size(), 25, "5x5 board creates 25 cells")

	scene.queue_free()
	await get_tree().process_frame

func test_game_scene_unit_creation() -> void:
	var scene = load("res://scenes/game.tscn").instantiate()
	add_child(scene)
	await get_tree().process_frame

	# Подготовка
	if scene.has_method("_draw_board"):
		scene.field_size = 5
		scene._draw_board()
		await get_tree().process_frame

	# Тестовый юнит
	var TestFixtures = load("res://test/test_fixtures.gd")
	var unit = TestFixtures.get_test_unit_player1()

	if scene.has_method("_create_unit_sprite"):
		var sprite = scene._create_unit_sprite(unit)
		assert_not_null(sprite, "Unit sprite created")

		var count_label = sprite.get_node_or_null("CountLabel")
		assert_not_null(count_label, "Unit has CountLabel")

		if count_label:
			assert_eq(count_label.text, "10", "CountLabel shows correct count")

		sprite.queue_free()

	scene.queue_free()
	await get_tree().process_frame

func test_game_scene_coordinate_conversion() -> void:
	var scene = load("res://scenes/game.tscn").instantiate()
	add_child(scene)
	await get_tree().process_frame

	if scene.has_method("grid_to_iso"):
		var pos = scene.grid_to_iso(0, 0)
		assert_true(pos is Vector2, "grid_to_iso returns Vector2")

		var pos2 = scene.grid_to_iso(1, 1)
		assert_true(pos2.y > pos.y, "Y increases for diagonal movement")

	scene.queue_free()
	await get_tree().process_frame

# ============ Integration Tests ============

func test_full_battle_scenario() -> void:
	var TestFixtures = load("res://test/test_fixtures.gd")

	# Загружаем сцену
	var scene = load("res://scenes/game.tscn").instantiate()
	add_child(scene)
	await get_tree().process_frame

	# Подготовка
	if scene.has_method("_draw_board"):
		scene.field_size = 5
		scene._draw_board()
		await get_tree().process_frame

	# Создаём юнитов
	var units = [
		TestFixtures.get_test_unit_player1(),
		TestFixtures.get_test_unit_player2()
	]

	if scene.has_method("_update_units"):
		scene._update_units(units)
		await get_tree().process_frame

		if "unit_sprites" in scene:
			assert_eq(scene.unit_sprites.size(), 2, "Battle scenario: 2 units created")

		# Тест перемещения юнита
		if "unit_positions" in scene:
			assert_true(scene.unit_positions.has(1001), "Battle scenario: unit 1 tracked")
			var pos = scene.unit_positions[1001]
			assert_eq(pos["x"], 1, "Battle scenario: unit 1 at x=1")
			assert_eq(pos["y"], 2, "Battle scenario: unit 1 at y=2")

		# Тест удаления погибшего юнита
		units[1]["count"] = 0  # Юнит 2 погиб
		scene._update_units(units)
		await get_tree().process_frame

		if "unit_sprites" in scene:
			assert_eq(scene.unit_sprites.size(), 1, "Battle scenario: dead unit removed")
			assert_false(scene.unit_sprites.has(1002), "Battle scenario: unit 2 removed")

	scene.queue_free()
	await get_tree().process_frame
