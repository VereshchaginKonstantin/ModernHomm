extends Control
## Основная игровая сцена

# UI элементы
@onready var board: Control = %Board
@onready var turn_indicator: Label = %TurnIndicator
@onready var hint_label: Label = %HintLabel
@onready var player1_panel: PanelContainer = %Player1Panel
@onready var player2_panel: PanelContainer = %Player2Panel
@onready var move_button: Button = %MoveButton
@onready var attack_button: Button = %AttackButton
@onready var skip_button: Button = %SkipButton
@onready var defer_button: Button = %DeferButton
@onready var surrender_button: Button = %SurrenderButton
@onready var log_list: VBoxContainer = %LogList
@onready var game_over_overlay: ColorRect = %GameOverOverlay

# Константы отображения
const CELL_SIZE: int = 70
const BOARD_PADDING: int = 10
const COLORS = {
	"light_tile": Color(0.941, 0.851, 0.710),
	"dark_tile": Color(0.710, 0.533, 0.388),
	"obstacle": Color(0.333, 0.333, 0.333),
	"player1": Color(0.906, 0.298, 0.235),
	"player2": Color(0.180, 0.800, 0.443),
	"move_highlight": Color(0.153, 0.682, 0.376, 0.5),
	"attack_highlight": Color(0.906, 0.298, 0.235, 0.5),
	"selected": Color(0.945, 0.769, 0.059, 0.7)
}

# Состояние
var field_size: int = 5
var cells: Array[Control] = []
var unit_sprites: Dictionary = {}  # unit_id -> Control
var action_mode: String = ""  # "move" или "attack"

func _ready() -> void:
	# Подключаем сигналы GameManager
	GameManager.game_state_updated.connect(_on_game_state_updated)
	GameManager.unit_actions_received.connect(_on_unit_actions_received)
	GameManager.move_completed.connect(_on_move_completed)
	GameManager.game_over.connect(_on_game_over)
	GameManager.turn_changed.connect(_on_turn_changed)
	GameManager.error_occurred.connect(_on_error)

	# Подключаем кнопки
	move_button.pressed.connect(_on_move_pressed)
	attack_button.pressed.connect(_on_attack_pressed)
	skip_button.pressed.connect(_on_skip_pressed)
	defer_button.pressed.connect(_on_defer_pressed)
	surrender_button.pressed.connect(_on_surrender_pressed)
	game_over_overlay.get_node("VBox/BackButton").pressed.connect(_on_back_to_menu)

	# Начинаем обновление состояния игры
	GameManager.refresh_game_state()

func _on_game_state_updated(state: Dictionary) -> void:
	# Обновляем размер поля
	var field_name = state.get("field", {}).get("name", "5x5")
	field_size = int(field_name.split("x")[0])

	# Перерисовываем доску
	_draw_board()

	# Обновляем юнитов
	_update_units(state.get("units", []))

	# Обновляем UI
	_update_turn_indicator(state)
	_update_player_panels(state)
	_update_log(state.get("logs", []))

	# Обновляем кнопки
	_update_action_buttons()

func _draw_board() -> void:
	# Очищаем старые клетки
	for cell in cells:
		cell.queue_free()
	cells.clear()

	# Обновляем размер доски
	var board_size = field_size * CELL_SIZE + BOARD_PADDING * 2
	board.custom_minimum_size = Vector2(board_size, board_size)

	# Рисуем клетки
	for y in range(field_size):
		for x in range(field_size):
			var cell = ColorRect.new()
			cell.size = Vector2(CELL_SIZE - 2, CELL_SIZE - 2)
			cell.position = Vector2(
				BOARD_PADDING + x * CELL_SIZE + 1,
				BOARD_PADDING + y * CELL_SIZE + 1
			)

			# Чередование цветов
			if (x + y) % 2 == 0:
				cell.color = COLORS.light_tile
			else:
				cell.color = COLORS.dark_tile

			# Обработка клика
			cell.mouse_filter = Control.MOUSE_FILTER_STOP
			cell.gui_input.connect(_on_cell_clicked.bind(x, y))

			board.add_child(cell)
			cells.append(cell)

	# Рисуем препятствия
	for obstacle in GameManager.game_state.get("obstacles", []):
		var ox = obstacle.get("x", 0)
		var oy = obstacle.get("y", 0)
		var idx = oy * field_size + ox
		if idx < cells.size():
			cells[idx].color = COLORS.obstacle

func _update_units(units: Array) -> void:
	# Удаляем старых юнитов
	for sprite in unit_sprites.values():
		sprite.queue_free()
	unit_sprites.clear()

	# Создаём новых юнитов
	for unit in units:
		if unit.get("count", 0) <= 0:
			continue

		var unit_control = _create_unit_sprite(unit)
		board.add_child(unit_control)
		unit_sprites[unit.get("id")] = unit_control

func _create_unit_sprite(unit: Dictionary) -> Control:
	var container = Control.new()
	container.size = Vector2(CELL_SIZE - 4, CELL_SIZE - 4)
	container.position = Vector2(
		BOARD_PADDING + unit.get("x", 0) * CELL_SIZE + 2,
		BOARD_PADDING + unit.get("y", 0) * CELL_SIZE + 2
	)

	# Фон юнита
	var bg = ColorRect.new()
	bg.size = container.size
	if unit.get("player_id") == GameManager.game_state.get("player1_id"):
		bg.color = COLORS.player1
	else:
		bg.color = COLORS.player2

	# Полупрозрачность для уже походивших
	if unit.get("has_moved", 0) == 1:
		bg.color.a = 0.5

	container.add_child(bg)

	# Иконка юнита
	var icon_label = Label.new()
	icon_label.text = unit.get("unit_type", {}).get("icon", "⚔️")
	icon_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	icon_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	icon_label.size = container.size
	icon_label.add_theme_font_size_override("font_size", 28)
	container.add_child(icon_label)

	# Количество юнитов
	var count_label = Label.new()
	count_label.text = str(unit.get("count", 0))
	count_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	count_label.vertical_alignment = VERTICAL_ALIGNMENT_BOTTOM
	count_label.size = container.size
	count_label.add_theme_font_size_override("font_size", 12)
	container.add_child(count_label)

	# Обработка клика
	bg.mouse_filter = Control.MOUSE_FILTER_STOP
	bg.gui_input.connect(_on_unit_clicked.bind(unit))

	# Выделение выбранного юнита
	if not GameManager.selected_unit.is_empty() and GameManager.selected_unit.get("id") == unit.get("id"):
		var selection = ColorRect.new()
		selection.size = container.size
		selection.color = COLORS.selected
		container.add_child(selection)

	return container

func _on_cell_clicked(event: InputEvent, x: int, y: int) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		if action_mode == "move" and GameManager.can_move_to(x, y):
			GameManager.move_selected_unit(x, y)
			_clear_highlights()
			action_mode = ""
		elif action_mode == "attack":
			var target = GameManager.get_unit_at_position(x, y)
			if not target.is_empty() and GameManager.can_attack(target.get("id")):
				GameManager.attack_with_selected_unit(target.get("id"))
				_clear_highlights()
				action_mode = ""

func _on_unit_clicked(event: InputEvent, unit: Dictionary) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		if action_mode == "attack" and GameManager.can_attack(unit.get("id")):
			GameManager.attack_with_selected_unit(unit.get("id"))
			_clear_highlights()
			action_mode = ""
		elif unit.get("player_id") == GameManager.current_player_id:
			GameManager.select_unit(unit)

func _on_unit_actions_received(actions: Dictionary) -> void:
	_update_action_buttons()
	hint_label.text = "Выбран юнит. Выберите действие."

func _on_move_pressed() -> void:
	action_mode = "move"
	_highlight_moves()
	hint_label.text = "Нажмите на зелёную клетку для перемещения"

func _on_attack_pressed() -> void:
	action_mode = "attack"
	_highlight_attacks()
	hint_label.text = "Нажмите на красную клетку для атаки"

func _on_skip_pressed() -> void:
	GameManager.skip_selected_unit()
	_clear_highlights()
	action_mode = ""

func _on_defer_pressed() -> void:
	GameManager.defer_selected_unit()
	_clear_highlights()
	action_mode = ""

func _on_surrender_pressed() -> void:
	# TODO: Реализовать сдачу
	GameManager.return_to_menu()

func _highlight_moves() -> void:
	_clear_highlights()
	for move in GameManager.current_actions.get("can_move", []):
		var x = move.get("x", 0)
		var y = move.get("y", 0)
		var idx = y * field_size + x
		if idx < cells.size():
			var highlight = ColorRect.new()
			highlight.size = cells[idx].size
			highlight.color = COLORS.move_highlight
			highlight.name = "Highlight"
			cells[idx].add_child(highlight)

func _highlight_attacks() -> void:
	_clear_highlights()
	for target in GameManager.current_actions.get("can_attack", []):
		var x = target.get("x", 0)
		var y = target.get("y", 0)
		var idx = y * field_size + x
		if idx < cells.size():
			var highlight = ColorRect.new()
			highlight.size = cells[idx].size
			highlight.color = COLORS.attack_highlight
			highlight.name = "Highlight"
			cells[idx].add_child(highlight)

func _clear_highlights() -> void:
	for cell in cells:
		var highlight = cell.get_node_or_null("Highlight")
		if highlight:
			highlight.queue_free()

func _update_turn_indicator(state: Dictionary) -> void:
	if GameManager.is_my_turn():
		turn_indicator.text = "ВАШ ХОД!"
		turn_indicator.add_theme_color_override("font_color", Color.GREEN)
	else:
		turn_indicator.text = "Ход противника..."
		turn_indicator.add_theme_color_override("font_color", Color.RED)

func _update_player_panels(state: Dictionary) -> void:
	# Player 1
	var p1_name = player1_panel.get_node("VBox/Name")
	var p1_stats = player1_panel.get_node("VBox/Stats")
	p1_name.text = state.get("player1_name", "Игрок 1")

	var p1_units = 0
	for u in state.get("units", []):
		if u.get("player_id") == state.get("player1_id"):
			p1_units += u.get("count", 0)
	p1_stats.text = "Юнитов: %d" % p1_units

	# Player 2
	var p2_name = player2_panel.get_node("VBox/Name")
	var p2_stats = player2_panel.get_node("VBox/Stats")
	p2_name.text = state.get("player2_name", "Игрок 2")

	var p2_units = 0
	for u in state.get("units", []):
		if u.get("player_id") == state.get("player2_id"):
			p2_units += u.get("count", 0)
	p2_stats.text = "Юнитов: %d" % p2_units

	# Подсветка активного игрока
	if state.get("current_player_id") == state.get("player1_id"):
		player1_panel.modulate = Color(1.2, 1.2, 1.2)
		player2_panel.modulate = Color(0.7, 0.7, 0.7)
	else:
		player1_panel.modulate = Color(0.7, 0.7, 0.7)
		player2_panel.modulate = Color(1.2, 1.2, 1.2)

func _update_action_buttons() -> void:
	var has_unit = not GameManager.selected_unit.is_empty()
	var is_my_turn = GameManager.is_my_turn()

	var can_move = has_unit and is_my_turn and GameManager.current_actions.get("can_move", []).size() > 0
	var can_attack = has_unit and is_my_turn and GameManager.current_actions.get("can_attack", []).size() > 0

	move_button.disabled = not can_move
	attack_button.disabled = not can_attack
	skip_button.disabled = not (has_unit and is_my_turn)
	defer_button.disabled = not (has_unit and is_my_turn)

func _update_log(logs: Array) -> void:
	# Очищаем старые записи
	for child in log_list.get_children():
		child.queue_free()

	# Добавляем новые (последние 20)
	var recent_logs = logs.slice(max(0, logs.size() - 20), logs.size())
	recent_logs.reverse()

	for log_entry in recent_logs:
		var label = Label.new()
		label.text = log_entry.get("message", "")
		label.add_theme_font_size_override("font_size", 12)
		label.autowrap_mode = TextServer.AUTOWRAP_WORD

		# Цвет по типу события
		match log_entry.get("event_type", ""):
			"attack":
				label.add_theme_color_override("font_color", Color.RED)
			"move":
				label.add_theme_color_override("font_color", Color.CYAN)
			_:
				label.add_theme_color_override("font_color", Color.GRAY)

		log_list.add_child(label)

func _on_move_completed(result: Dictionary) -> void:
	if result.get("success"):
		hint_label.text = result.get("message", "Действие выполнено")
	else:
		hint_label.text = "Ошибка: " + result.get("message", "Неизвестная ошибка")

func _on_turn_changed(current_player_id: int) -> void:
	hint_label.text = "Ход сменился!"
	_update_action_buttons()

func _on_game_over(winner_id: int, winner_name: String) -> void:
	game_over_overlay.visible = true

	var title = game_over_overlay.get_node("VBox/Title")
	var message = game_over_overlay.get_node("VBox/Message")

	if winner_id == GameManager.current_player_id:
		title.text = "ПОБЕДА!"
		title.add_theme_color_override("font_color", Color.GOLD)
		message.text = "Поздравляем! Вы одержали победу!"
	else:
		title.text = "ПОРАЖЕНИЕ"
		title.add_theme_color_override("font_color", Color.RED)
		message.text = winner_name + " одержал победу."

func _on_error(error_message: String) -> void:
	hint_label.text = "Ошибка: " + error_message

func _on_back_to_menu() -> void:
	GameManager.return_to_menu()
