extends SceneTree
## Простой тест раннер без GUT плагина

var tests_passed: int = 0
var tests_failed: int = 0
var current_test: String = ""

func _init() -> void:
	print("\n========================================")
	print("   MODERNHOMM ARENA TEST SUITE")
	print("========================================\n")

	# Запускаем тесты
	run_all_tests()

	# Выводим результаты
	print("\n========================================")
	print("   RESULTS")
	print("========================================")
	print("Passed: %d" % tests_passed)
	print("Failed: %d" % tests_failed)
	print("Total:  %d" % (tests_passed + tests_failed))
	print("========================================\n")

	# Выход
	quit(0 if tests_failed == 0 else 1)

func run_all_tests() -> void:
	# Тесты GameManager
	print("\n[GameManager Tests]")
	test_game_manager_initial_state()
	test_game_manager_is_my_turn()
	test_game_manager_get_unit_by_id()
	test_game_manager_can_move_to()
	test_game_manager_can_attack()

	# Тесты конверсии координат
	print("\n[Coordinate Tests]")
	test_grid_to_iso_conversion()

	# Тесты фикстур
	print("\n[Fixtures Tests]")
	test_fixtures_game_state()
	test_fixtures_units()

func assert_true(condition: bool, message: String) -> void:
	if condition:
		tests_passed += 1
		print("  ✓ %s" % message)
	else:
		tests_failed += 1
		print("  ✗ FAILED: %s" % message)

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

# ============ GameManager Tests ============

func test_game_manager_initial_state() -> void:
	var gm = root.get_node_or_null("/root/GameManager")
	if gm:
		assert_eq(gm.current_game_id, 0, "Initial game_id is 0")
		assert_true(gm.game_state.is_empty(), "Initial game_state is empty")
		assert_true(gm.selected_unit.is_empty(), "Initial selected_unit is empty")
	else:
		tests_failed += 1
		print("  ✗ GameManager not found")

func test_game_manager_is_my_turn() -> void:
	var gm = root.get_node_or_null("/root/GameManager")
	if gm:
		gm.current_player_id = 100
		gm.game_state = {"current_player_id": 100}
		assert_true(gm.is_my_turn(), "is_my_turn returns true when IDs match")

		gm.game_state = {"current_player_id": 101}
		assert_true(not gm.is_my_turn(), "is_my_turn returns false when IDs don't match")

		# Cleanup
		gm.game_state = {}
		gm.current_player_id = 0

func test_game_manager_get_unit_by_id() -> void:
	var gm = root.get_node_or_null("/root/GameManager")
	if gm:
		gm.game_state = {
			"units": [
				{"id": 1, "name": "Unit1"},
				{"id": 2, "name": "Unit2"}
			]
		}

		var unit = gm.get_unit_by_id(1)
		assert_eq(unit.get("name"), "Unit1", "get_unit_by_id finds Unit1")

		var not_found = gm.get_unit_by_id(999)
		assert_true(not_found.is_empty(), "get_unit_by_id returns empty for non-existent")

		gm.game_state = {}

func test_game_manager_can_move_to() -> void:
	var gm = root.get_node_or_null("/root/GameManager")
	if gm:
		gm.current_actions = {
			"can_move": [
				{"x": 2, "y": 3},
				{"x": 1, "y": 1}
			]
		}

		assert_true(gm.can_move_to(2, 3), "can_move_to returns true for available position")
		assert_true(not gm.can_move_to(5, 5), "can_move_to returns false for unavailable position")

		gm.current_actions = {}

func test_game_manager_can_attack() -> void:
	var gm = root.get_node_or_null("/root/GameManager")
	if gm:
		gm.current_actions = {
			"can_attack": [
				{"id": 100},
				{"id": 200}
			]
		}

		assert_true(gm.can_attack(100), "can_attack returns true for available target")
		assert_true(not gm.can_attack(999), "can_attack returns false for unavailable target")

		gm.current_actions = {}

# ============ Coordinate Tests ============

func test_grid_to_iso_conversion() -> void:
	# Тестируем формулу конверсии
	# grid_to_iso(x, y) = Vector2((x - y) * TILE_WIDTH / 2 + offset, (x + y) * TILE_HEIGHT / 2 + offset)
	var TILE_WIDTH = 64
	var TILE_HEIGHT = 32

	# При x=0, y=0 результат должен быть в центре (с учётом offset)
	var pos_0_0 = Vector2((0 - 0) * TILE_WIDTH / 2, (0 + 0) * TILE_HEIGHT / 2)
	assert_eq(pos_0_0, Vector2(0, 0), "grid_to_iso(0,0) formula works")

	# При x=1, y=0
	var pos_1_0 = Vector2((1 - 0) * TILE_WIDTH / 2, (1 + 0) * TILE_HEIGHT / 2)
	assert_eq(pos_1_0, Vector2(32, 16), "grid_to_iso(1,0) formula works")

	# При x=0, y=1
	var pos_0_1 = Vector2((0 - 1) * TILE_WIDTH / 2, (0 + 1) * TILE_HEIGHT / 2)
	assert_eq(pos_0_1, Vector2(-32, 16), "grid_to_iso(0,1) formula works")

# ============ Fixtures Tests ============

func test_fixtures_game_state() -> void:
	var TestFixtures = load("res://test/test_fixtures.gd")

	var state = TestFixtures.get_test_game_state()
	assert_eq(state["game_id"], 999, "Fixture game_id is 999")
	assert_eq(state["status"], "in_progress", "Fixture status is in_progress")
	assert_eq(state["units"].size(), 2, "Fixture has 2 units")
	assert_eq(state["obstacles"].size(), 2, "Fixture has 2 obstacles")

func test_fixtures_units() -> void:
	var TestFixtures = load("res://test/test_fixtures.gd")

	var unit1 = TestFixtures.get_test_unit_player1()
	assert_eq(unit1["id"], 1001, "Unit1 ID is 1001")
	assert_eq(unit1["player_id"], 100, "Unit1 belongs to player 100")
	assert_eq(unit1["count"], 10, "Unit1 count is 10")

	var unit2 = TestFixtures.get_test_unit_player2()
	assert_eq(unit2["id"], 1002, "Unit2 ID is 1002")
	assert_eq(unit2["player_id"], 101, "Unit2 belongs to player 101")
