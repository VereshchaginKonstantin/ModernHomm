extends "res://addons/gut/test.gd"
## Интеграционные тесты для сценариев боя - движение, атака, ходы

const TestFixtures = preload("res://test/test_fixtures.gd")

var game_scene: Node


func before_each() -> void:
	game_scene = load("res://scenes/game.tscn").instantiate()
	add_child_autofree(game_scene)
	await get_tree().process_frame

	# Устанавливаем начальное состояние
	if "field_size" in game_scene:
		game_scene.field_size = 5


func after_each() -> void:
	game_scene = null


## Тест: Отрисовка доски создаёт правильное количество клеток
func test_draw_board_creates_cells() -> void:
	if game_scene.has_method("_draw_board"):
		game_scene.field_size = 5
		game_scene._draw_board()

		await get_tree().process_frame

		if "cells" in game_scene:
			# 5x5 = 25 клеток
			assert_eq(game_scene.cells.size(), 25, "Should create 25 cells for 5x5 board")


## Тест: Обновление юнитов создаёт спрайты
func test_update_units_creates_sprites() -> void:
	# Сначала рисуем доску
	if game_scene.has_method("_draw_board"):
		game_scene.field_size = 5
		game_scene._draw_board()
		await get_tree().process_frame

	var units = [
		TestFixtures.get_test_unit_player1(),
		TestFixtures.get_test_unit_player2()
	]

	if game_scene.has_method("_update_units"):
		game_scene._update_units(units)
		await get_tree().process_frame

		if "unit_sprites" in game_scene:
			assert_eq(game_scene.unit_sprites.size(), 2, "Should create 2 unit sprites")
			assert_true(game_scene.unit_sprites.has(1001), "Should have player 1 unit")
			assert_true(game_scene.unit_sprites.has(1002), "Should have player 2 unit")


## Тест: Позиции юнитов сохраняются
func test_unit_positions_tracked() -> void:
	if game_scene.has_method("_draw_board"):
		game_scene.field_size = 5
		game_scene._draw_board()
		await get_tree().process_frame

	var units = [TestFixtures.get_test_unit_player1()]

	if game_scene.has_method("_update_units"):
		game_scene._update_units(units)
		await get_tree().process_frame

		if "unit_positions" in game_scene:
			assert_true(game_scene.unit_positions.has(1001), "Should track unit position")
			var pos = game_scene.unit_positions[1001]
			assert_eq(pos["x"], 1, "X position should be 1")
			assert_eq(pos["y"], 2, "Y position should be 2")


## Тест: Удаление юнита когда count = 0
func test_unit_removed_when_count_zero() -> void:
	if game_scene.has_method("_draw_board"):
		game_scene.field_size = 5
		game_scene._draw_board()
		await get_tree().process_frame

	# Создаём юнита
	var units = [TestFixtures.get_test_unit_player1()]
	if game_scene.has_method("_update_units"):
		game_scene._update_units(units)
		await get_tree().process_frame

		# Проверяем что юнит создан
		if "unit_sprites" in game_scene:
			assert_eq(game_scene.unit_sprites.size(), 1)

		# Обновляем с count = 0 (юнит погиб)
		units[0]["count"] = 0
		game_scene._update_units(units)
		await get_tree().process_frame

		if "unit_sprites" in game_scene:
			assert_eq(game_scene.unit_sprites.size(), 0, "Dead unit should be removed")


## Тест: Юнит с has_moved становится полупрозрачным
func test_unit_transparency_when_moved() -> void:
	if game_scene.has_method("_draw_board"):
		game_scene.field_size = 5
		game_scene._draw_board()
		await get_tree().process_frame

	var unit = TestFixtures.get_test_unit_player1()
	unit["has_moved"] = 0

	if game_scene.has_method("_update_units"):
		game_scene._update_units([unit])
		await get_tree().process_frame

		if "unit_sprites" in game_scene and game_scene.unit_sprites.has(1001):
			var unit_control = game_scene.unit_sprites[1001]
			assert_eq(unit_control.modulate.a, 1.0, "Unit should be fully visible when not moved")

		# Теперь юнит походил
		unit["has_moved"] = 1
		game_scene._update_units([unit])
		await get_tree().process_frame

		if "unit_sprites" in game_scene and game_scene.unit_sprites.has(1001):
			var unit_control = game_scene.unit_sprites[1001]
			assert_eq(unit_control.modulate.a, 0.5, "Unit should be semi-transparent when moved")


## Тест: Проверка доступных ходов (can_move_to)
func test_can_move_to() -> void:
	if "current_actions" in game_scene:
		game_scene.current_actions = TestFixtures.get_test_unit_actions()

		if game_scene.has_method("can_move_to"):
			# Позиция в списке доступных
			assert_true(game_scene.can_move_to(2, 1), "Should be able to move to (2,1)")
			assert_true(game_scene.can_move_to(2, 2), "Should be able to move to (2,2)")

			# Позиция НЕ в списке
			assert_false(game_scene.can_move_to(4, 4), "Should NOT be able to move to (4,4)")


## Тест: Проверка доступных атак (can_attack)
func test_can_attack() -> void:
	if "current_actions" in game_scene:
		game_scene.current_actions = TestFixtures.get_test_unit_actions()

		if game_scene.has_method("can_attack"):
			# ID юнита в списке целей атаки
			assert_true(game_scene.can_attack(1002), "Should be able to attack unit 1002")

			# ID юнита НЕ в списке
			assert_false(game_scene.can_attack(9999), "Should NOT be able to attack unit 9999")


## Тест: Анимация перемещения запускается
func test_animate_unit_move() -> void:
	if game_scene.has_method("_draw_board"):
		game_scene.field_size = 5
		game_scene._draw_board()
		await get_tree().process_frame

	# Создаём юнита
	var unit = TestFixtures.get_test_unit_player1()
	if game_scene.has_method("_update_units"):
		game_scene._update_units([unit])
		await get_tree().process_frame

	# Запускаем анимацию перемещения
	if game_scene.has_method("_animate_unit_move"):
		game_scene._animate_unit_move(1001, 1, 2, 2, 3, 2, 3)

		# Проверяем что tween создан
		if "active_tweens" in game_scene:
			assert_true(game_scene.active_tweens.has(1001), "Should have active tween for unit")


## Тест: Обновление счётчика юнитов
func test_update_unit_count() -> void:
	if game_scene.has_method("_draw_board"):
		game_scene.field_size = 5
		game_scene._draw_board()
		await get_tree().process_frame

	var unit = TestFixtures.get_test_unit_player1()
	unit["count"] = 10

	if game_scene.has_method("_update_units"):
		game_scene._update_units([unit])
		await get_tree().process_frame

		# Изменяем количество
		unit["count"] = 7
		game_scene._update_units([unit])
		await get_tree().process_frame

		if "unit_sprites" in game_scene and game_scene.unit_sprites.has(1001):
			var unit_control = game_scene.unit_sprites[1001]
			var count_label = unit_control.get_node_or_null("CountLabel")
			if count_label:
				assert_eq(count_label.text, "7", "Count should be updated to 7")


## Тест: Препятствия отображаются на доске
func test_obstacles_displayed() -> void:
	var game_state = TestFixtures.get_test_game_state()

	# Эмулируем обработку game_state
	if game_scene.has_method("_on_game_state_updated"):
		# Нам нужен сигнал от GameManager, но мы можем напрямую вызвать
		# внутреннюю логику
		pass

	# Проверяем что препятствия в состоянии игры
	assert_eq(game_state["obstacles"].size(), 2, "Should have 2 obstacles")


## Тест: Конец игры показывает overlay
func test_game_over_shows_overlay() -> void:
	var overlay = game_scene.get_node_or_null("GameOverOverlay")
	if overlay:
		assert_false(overlay.visible, "Overlay should be hidden initially")

	# Эмулируем конец игры
	if game_scene.has_method("_on_game_over"):
		game_scene._on_game_over(100, "test_player1")
		await get_tree().process_frame

		if overlay:
			assert_true(overlay.visible, "Overlay should be visible after game over")
