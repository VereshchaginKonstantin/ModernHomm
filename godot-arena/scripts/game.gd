extends Control
## Основная игровая сцена - изометрическое поле битвы

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

# Константы изометрического отображения
const TILE_WIDTH: int = 64   # Ширина тайла (горизонтально)
const TILE_HEIGHT: int = 32  # Высота тайла (вертикально - половина ширины для изометрии)
const TILE_DEPTH: int = 16   # Глубина тайла (высота "кубика")
const BOARD_OFFSET_X: int = 300  # Смещение поля по X (центрирование)
const BOARD_OFFSET_Y: int = 50   # Смещение поля по Y
const COLORS = {
	"light_tile": Color(0.941, 0.851, 0.710),
	"dark_tile": Color(0.710, 0.533, 0.388),
	"tile_side_light": Color(0.75, 0.65, 0.55),
	"tile_side_dark": Color(0.55, 0.45, 0.35),
	"obstacle": Color(0.333, 0.333, 0.333),
	"obstacle_side": Color(0.2, 0.2, 0.2),
	"player1": Color(0.906, 0.298, 0.235),
	"player1_dark": Color(0.7, 0.2, 0.15),
	"player2": Color(0.180, 0.800, 0.443),
	"player2_dark": Color(0.1, 0.6, 0.3),
	"move_highlight": Color(0.153, 0.682, 0.376, 0.6),
	"attack_highlight": Color(0.906, 0.298, 0.235, 0.6),
	"selected": Color(0.945, 0.769, 0.059, 0.8)
}

# Кэш загруженных текстур юнитов
var unit_textures: Dictionary = {}
var texture_load_queue: Array = []

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

## Преобразование координат сетки в изометрические экранные координаты
func grid_to_iso(grid_x: int, grid_y: int) -> Vector2:
	var iso_x = (grid_x - grid_y) * (TILE_WIDTH / 2) + BOARD_OFFSET_X
	var iso_y = (grid_x + grid_y) * (TILE_HEIGHT / 2) + BOARD_OFFSET_Y
	return Vector2(iso_x, iso_y)

## Создание изометрического тайла (ромб с боковыми гранями)
func _create_iso_tile(grid_x: int, grid_y: int, is_obstacle: bool = false) -> Control:
	var container = Control.new()
	var iso_pos = grid_to_iso(grid_x, grid_y)
	container.position = iso_pos
	container.size = Vector2(TILE_WIDTH, TILE_HEIGHT + TILE_DEPTH)
	container.z_index = grid_x + grid_y  # Для правильного z-order

	# Определяем цвета
	var top_color: Color
	var side_color: Color
	if is_obstacle:
		top_color = COLORS.obstacle
		side_color = COLORS.obstacle_side
	elif (grid_x + grid_y) % 2 == 0:
		top_color = COLORS.light_tile
		side_color = COLORS.tile_side_light
	else:
		top_color = COLORS.dark_tile
		side_color = COLORS.tile_side_dark

	# Рисуем тайл через Polygon2D
	# Верхняя грань (ромб)
	var top_face = Polygon2D.new()
	top_face.polygon = PackedVector2Array([
		Vector2(TILE_WIDTH / 2, 0),           # Верх
		Vector2(TILE_WIDTH, TILE_HEIGHT / 2), # Право
		Vector2(TILE_WIDTH / 2, TILE_HEIGHT), # Низ
		Vector2(0, TILE_HEIGHT / 2)           # Лево
	])
	top_face.color = top_color
	container.add_child(top_face)

	# Левая боковая грань
	var left_side = Polygon2D.new()
	left_side.polygon = PackedVector2Array([
		Vector2(0, TILE_HEIGHT / 2),
		Vector2(TILE_WIDTH / 2, TILE_HEIGHT),
		Vector2(TILE_WIDTH / 2, TILE_HEIGHT + TILE_DEPTH),
		Vector2(0, TILE_HEIGHT / 2 + TILE_DEPTH)
	])
	left_side.color = side_color.darkened(0.2)
	container.add_child(left_side)

	# Правая боковая грань
	var right_side = Polygon2D.new()
	right_side.polygon = PackedVector2Array([
		Vector2(TILE_WIDTH / 2, TILE_HEIGHT),
		Vector2(TILE_WIDTH, TILE_HEIGHT / 2),
		Vector2(TILE_WIDTH, TILE_HEIGHT / 2 + TILE_DEPTH),
		Vector2(TILE_WIDTH / 2, TILE_HEIGHT + TILE_DEPTH)
	])
	right_side.color = side_color
	container.add_child(right_side)

	# Невидимая область для кликов (поверх всего тайла)
	var click_area = Control.new()
	click_area.size = Vector2(TILE_WIDTH, TILE_HEIGHT + TILE_DEPTH)
	click_area.mouse_filter = Control.MOUSE_FILTER_STOP
	click_area.gui_input.connect(_on_cell_clicked.bind(grid_x, grid_y))
	container.add_child(click_area)

	return container

func _draw_board() -> void:
	# Очищаем старые клетки
	for cell in cells:
		cell.queue_free()
	cells.clear()

	# Вычисляем размер доски для изометрии
	var board_width = (field_size * 2) * (TILE_WIDTH / 2) + BOARD_OFFSET_X
	var board_height = (field_size * 2) * (TILE_HEIGHT / 2) + TILE_DEPTH + BOARD_OFFSET_Y + 100
	board.custom_minimum_size = Vector2(board_width, board_height)

	# Собираем препятствия в словарь для быстрого доступа
	var obstacles_set = {}
	for obstacle in GameManager.game_state.get("obstacles", []):
		var key = "%d_%d" % [obstacle.get("x", 0), obstacle.get("y", 0)]
		obstacles_set[key] = true

	# Рисуем клетки в правильном порядке (от дальних к ближним для z-order)
	for y in range(field_size):
		for x in range(field_size):
			var key = "%d_%d" % [x, y]
			var is_obstacle = obstacles_set.has(key)
			var cell = _create_iso_tile(x, y, is_obstacle)
			board.add_child(cell)
			cells.append(cell)

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

		# Загружаем текстуру юнита если есть путь к изображению
		var image_path = unit.get("unit_type", {}).get("image_path", "")
		if image_path != "" and not unit_textures.has(image_path):
			_load_unit_texture(image_path, unit.get("id"))

## Загрузка текстуры юнита через HTTP
func _load_unit_texture(image_path: String, unit_id: int) -> void:
	# Формируем URL для загрузки изображения
	var url = ""
	if OS.has_feature("web"):
		url = JavaScriptBridge.eval("window.location.origin") + "/" + image_path
	else:
		url = "http://localhost/" + image_path

	# Создаём HTTPRequest для загрузки текстуры
	var http = HTTPRequest.new()
	http.use_threads = false  # WebGL совместимость
	add_child(http)
	http.request_completed.connect(_on_texture_loaded.bind(image_path, unit_id, http))
	http.request(url)

func _on_texture_loaded(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray, image_path: String, unit_id: int, http_node: HTTPRequest) -> void:
	http_node.queue_free()

	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		return

	# Создаём текстуру из загруженных данных
	var image = Image.new()
	var error = image.load_jpg_from_buffer(body)
	if error != OK:
		error = image.load_png_from_buffer(body)
	if error != OK:
		return

	var texture = ImageTexture.create_from_image(image)
	unit_textures[image_path] = texture

	# Обновляем спрайт юнита если он всё ещё существует
	if unit_sprites.has(unit_id):
		var unit_control = unit_sprites[unit_id]
		var texture_rect = unit_control.get_node_or_null("UnitTexture")
		if texture_rect:
			texture_rect.texture = texture

func _create_unit_sprite(unit: Dictionary) -> Control:
	var container = Control.new()
	var grid_x = unit.get("x", 0)
	var grid_y = unit.get("y", 0)

	# Позиция в изометрических координатах
	var iso_pos = grid_to_iso(grid_x, grid_y)
	container.position = iso_pos + Vector2(0, -20)  # Поднимаем юнита над тайлом
	container.size = Vector2(TILE_WIDTH, TILE_WIDTH)  # Квадратный спрайт
	container.z_index = grid_x + grid_y + 100  # Юниты поверх тайлов

	# Определяем цвета игрока
	var player_color: Color
	var player_dark: Color
	if unit.get("player_id") == GameManager.game_state.get("player1_id"):
		player_color = COLORS.player1
		player_dark = COLORS.player1_dark
	else:
		player_color = COLORS.player2
		player_dark = COLORS.player2_dark

	# Полупрозрачность для уже походивших
	if unit.get("has_moved", 0) == 1:
		player_color.a = 0.5
		player_dark.a = 0.5

	# Основа юнита - цветной круг/овал для обозначения принадлежности
	var base = Polygon2D.new()
	var base_points: PackedVector2Array = []
	var base_radius = 24
	for i in range(16):
		var angle = i * PI * 2 / 16
		base_points.append(Vector2(
			TILE_WIDTH / 2 + cos(angle) * base_radius,
			TILE_HEIGHT + sin(angle) * base_radius * 0.5 + 8
		))
	base.polygon = base_points
	base.color = player_dark
	container.add_child(base)

	# Рамка базы
	var base_outline = Polygon2D.new()
	var outline_points: PackedVector2Array = []
	var outline_radius = base_radius + 2
	for i in range(16):
		var angle = i * PI * 2 / 16
		outline_points.append(Vector2(
			TILE_WIDTH / 2 + cos(angle) * outline_radius,
			TILE_HEIGHT + sin(angle) * outline_radius * 0.5 + 8
		))
	base_outline.polygon = outline_points
	base_outline.color = player_color
	container.add_child(base_outline)
	# Перемещаем base поверх outline
	container.move_child(base, 1)

	# Изображение юнита (если загружено) или иконка
	var image_path = unit.get("unit_type", {}).get("image_path", "")
	if unit_textures.has(image_path):
		var texture_rect = TextureRect.new()
		texture_rect.name = "UnitTexture"
		texture_rect.texture = unit_textures[image_path]
		texture_rect.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
		texture_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		texture_rect.size = Vector2(48, 48)
		texture_rect.position = Vector2((TILE_WIDTH - 48) / 2, 0)
		container.add_child(texture_rect)
	else:
		# Иконка юнита (эмодзи) как fallback
		var icon_label = Label.new()
		icon_label.text = unit.get("unit_type", {}).get("icon", "⚔️")
		icon_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		icon_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		icon_label.size = Vector2(TILE_WIDTH, 48)
		icon_label.position = Vector2(0, 0)
		icon_label.add_theme_font_size_override("font_size", 32)
		container.add_child(icon_label)

		# Добавляем placeholder для текстуры (будет заполнен после загрузки)
		var texture_rect = TextureRect.new()
		texture_rect.name = "UnitTexture"
		texture_rect.size = Vector2(48, 48)
		texture_rect.position = Vector2((TILE_WIDTH - 48) / 2, 0)
		texture_rect.visible = false
		container.add_child(texture_rect)

	# Количество юнитов - бейдж в углу
	var count_bg = ColorRect.new()
	count_bg.size = Vector2(22, 16)
	count_bg.position = Vector2(TILE_WIDTH - 24, TILE_HEIGHT - 4)
	count_bg.color = Color(0, 0, 0, 0.8)
	container.add_child(count_bg)

	var count_label = Label.new()
	count_label.text = str(unit.get("count", 0))
	count_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	count_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	count_label.size = Vector2(22, 16)
	count_label.position = Vector2(TILE_WIDTH - 24, TILE_HEIGHT - 4)
	count_label.add_theme_font_size_override("font_size", 11)
	count_label.add_theme_color_override("font_color", Color.WHITE)
	container.add_child(count_label)

	# Кликабельная область
	var click_area = Control.new()
	click_area.size = container.size
	click_area.mouse_filter = Control.MOUSE_FILTER_STOP
	click_area.gui_input.connect(_on_unit_clicked.bind(unit))
	container.add_child(click_area)

	# Выделение выбранного юнита
	if not GameManager.selected_unit.is_empty() and GameManager.selected_unit.get("id") == unit.get("id"):
		var selection = Polygon2D.new()
		var sel_points: PackedVector2Array = []
		var sel_radius = base_radius + 6
		for i in range(16):
			var angle = i * PI * 2 / 16
			sel_points.append(Vector2(
				TILE_WIDTH / 2 + cos(angle) * sel_radius,
				TILE_HEIGHT + sin(angle) * sel_radius * 0.5 + 8
			))
		selection.polygon = sel_points
		selection.color = COLORS.selected
		container.add_child(selection)
		container.move_child(selection, 0)  # Под остальными элементами

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

## Создание изометрической подсветки для тайла
func _create_iso_highlight(color: Color) -> Polygon2D:
	var highlight = Polygon2D.new()
	highlight.name = "Highlight"
	highlight.polygon = PackedVector2Array([
		Vector2(TILE_WIDTH / 2, 0),
		Vector2(TILE_WIDTH, TILE_HEIGHT / 2),
		Vector2(TILE_WIDTH / 2, TILE_HEIGHT),
		Vector2(0, TILE_HEIGHT / 2)
	])
	highlight.color = color
	return highlight

func _highlight_moves() -> void:
	_clear_highlights()
	for move in GameManager.current_actions.get("can_move", []):
		var x = move.get("x", 0)
		var y = move.get("y", 0)
		var idx = y * field_size + x
		if idx < cells.size():
			var highlight = _create_iso_highlight(COLORS.move_highlight)
			cells[idx].add_child(highlight)

func _highlight_attacks() -> void:
	_clear_highlights()
	for target in GameManager.current_actions.get("can_attack", []):
		var x = target.get("x", 0)
		var y = target.get("y", 0)
		var idx = y * field_size + x
		if idx < cells.size():
			var highlight = _create_iso_highlight(COLORS.attack_highlight)
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
