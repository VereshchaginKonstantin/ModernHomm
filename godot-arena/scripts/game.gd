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
# defer_button удалена - функционал не используется
@onready var surrender_button: Button = %SurrenderButton
@onready var log_list: VBoxContainer = %LogList
@onready var game_over_overlay: ColorRect = %GameOverOverlay
@onready var zoom_slider_node: HSlider = %ZoomSlider
@onready var zoom_value_label: Label = %ZoomValue
@onready var log_toggle_button: Button = %LogToggleButton
@onready var log_panel: PanelContainer = %LogPanel
@onready var close_log_button: Button = %CloseLogButton

# Базовые константы изометрического отображения (для 5x5)
const BASE_TILE_WIDTH: int = 96   # Базовая ширина тайла
const BASE_TILE_HEIGHT: int = 48  # Базовая высота тайла
const BASE_TILE_DEPTH: int = 24   # Базовая глубина тайла

# Динамические размеры тайлов (масштабируются для больших полей)
var TILE_WIDTH: int = 96
var TILE_HEIGHT: int = 48
var TILE_DEPTH: int = 24
var BOARD_OFFSET_X: int = 400  # Смещение поля по X (центрирование)
var BOARD_OFFSET_Y: int = 60   # Смещение поля по Y
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
	"selected": Color(0.945, 0.769, 0.059, 0.8),
	"hover": Color(0.6, 0.2, 0.8, 0.7)  # Фиолетовый для hover
}

# Кэш загруженных текстур юнитов
var unit_textures: Dictionary = {}
var texture_load_queue: Array = []
# Кэш для спрайт-листов: {sprite_url: {texture: Texture2D, params: {frame_count, fps, columns, rows}}}
var sprite_sheets: Dictionary = {}
# Отслеживание активных загрузок спрайтов чтобы не запускать повторные
var pending_sprite_loads: Dictionary = {}  # sprite_url -> true
# Отслеживание юнитов которым уже применили спрайт (для предотвращения повторных применений)
var units_with_sprites: Dictionary = {}  # unit_id -> sprite_url

# Состояние
var field_size: int = 5
var cells: Array[Control] = []
var unit_sprites: Dictionary = {}  # unit_id -> Control
var unit_positions: Dictionary = {}  # unit_id -> {x, y} - последние известные позиции
var active_tweens: Dictionary = {}  # unit_id -> Tween - активные анимации перемещения
var action_mode: String = ""  # "move" или "attack"
var board_initialized: bool = false  # Флаг что доска уже создана
var last_selected_unit_id: int = -1  # ID предыдущего выбранного юнита для управления анимацией
var last_log_count: int = 0  # Для отслеживания изменений в логах
var base_url: String = ""  # Кэшированный base URL для запросов
var is_game_over_displayed: bool = false  # Флаг что игра окончена и показан overlay

# Hover-подсветка для отладки
var hover_highlight: Polygon2D = null
var last_hover_cell: Vector2i = Vector2i(-1, -1)

# Константы анимации перемещения
const MOVE_DURATION: float = 1.0  # Длительность анимации перемещения в секундах

# Масштабирование (zoom)
const ZOOM_MIN: float = 0.5
const ZOOM_MAX: float = 3.0  # Увеличен до 300%
const ZOOM_STEP: float = 0.05  # Меньший шаг для плавности
var current_zoom: float = 1.0
var zoom_slider: HSlider = null
var ignore_slider_change: bool = false  # Флаг для игнорирования программных изменений слайдера

# Перетаскивание поля (pan)
var is_panning: bool = false
var pan_start_mouse: Vector2 = Vector2.ZERO
var pan_start_offset: Vector2 = Vector2.ZERO
var board_pan_offset: Vector2 = Vector2.ZERO  # Смещение поля от перетаскивания

func _js_log(msg: String) -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("console.log('[Game] " + msg.replace("'", "\\'").replace("\"", "\\\"") + "')")

func _ready() -> void:
	# Кэшируем base URL один раз
	if OS.has_feature("web"):
		base_url = JavaScriptBridge.eval("window.location.origin")
	else:
		base_url = "http://localhost"

	_js_log("Game scene _ready started, game_id=" + str(GameManager.current_game_id))
	RemoteLogger.info("Game scene _ready started", {
		"game_id": GameManager.current_game_id,
		"player_id": ApiClient.player_id,
		"auth_token_exists": ApiClient.auth_token != "",
		"authenticated": ApiClient.is_authenticated()
	})

	# Подключаем сигналы GameManager
	_js_log("Connecting signals...")
	GameManager.game_state_updated.connect(_on_game_state_updated)
	GameManager.unit_actions_received.connect(_on_unit_actions_received)
	GameManager.move_completed.connect(_on_move_completed)
	GameManager.game_over.connect(_on_game_over)
	GameManager.turn_changed.connect(_on_turn_changed)
	GameManager.error_occurred.connect(_on_error)

	# Подключаем кнопки
	_js_log("Connecting buttons...")
	move_button.pressed.connect(_on_move_pressed)
	attack_button.pressed.connect(_on_attack_pressed)
	skip_button.pressed.connect(_on_skip_pressed)
	# defer_button удалена
	surrender_button.pressed.connect(_on_surrender_pressed)
	game_over_overlay.get_node("VBox/BackButton").pressed.connect(_on_back_to_menu)

	# Подключаем слайдер масштабирования
	zoom_slider = zoom_slider_node
	# Сначала устанавливаем начальное значение с флагом игнорирования
	ignore_slider_change = true
	zoom_slider_node.value = current_zoom
	ignore_slider_change = false
	# Потом подключаем сигнал
	zoom_slider_node.value_changed.connect(_on_zoom_slider_changed)

	# Подключаем кнопки лога
	log_toggle_button.pressed.connect(_on_log_toggle_pressed)
	close_log_button.pressed.connect(_on_close_log_pressed)
	_js_log("Buttons connected")

	# Проверяем что game_id установлен
	if GameManager.current_game_id <= 0:
		_js_log("ERROR: No game_id set")
		RemoteLogger.error("No game_id set when entering game scene")
		hint_label.text = "Ошибка: игра не выбрана"
		return

	# Начинаем обновление состояния игры и запускаем polling только если авторизован
	_js_log("Checking authentication...")
	if ApiClient.is_authenticated():
		_js_log("Authenticated, starting game refresh")
		RemoteLogger.info("Starting game refresh", {"game_id": GameManager.current_game_id})
		hint_label.text = "Загрузка игры..."
		GameManager.refresh_game_state()
		GameManager.start_polling()
		_js_log("Game refresh and polling started")
	else:
		_js_log("ERROR: Not authenticated")
		RemoteLogger.error("Not authenticated when entering game scene")
		hint_label.text = "Ошибка: требуется авторизация"

	# Создаём hover-подсветку
	_create_hover_highlight()

## Создаёт фиолетовую подсветку для отображения ячейки под курсором
func _create_hover_highlight() -> void:
	hover_highlight = Polygon2D.new()
	_update_hover_highlight_shape()
	hover_highlight.color = COLORS.hover
	hover_highlight.z_index = 300  # Выше всего
	hover_highlight.visible = false
	board.add_child(hover_highlight)

## Обновляет форму hover подсветки при изменении размера тайлов
func _update_hover_highlight_shape() -> void:
	if hover_highlight == null:
		return
	hover_highlight.polygon = PackedVector2Array([
		Vector2(TILE_WIDTH / 2, 0),
		Vector2(TILE_WIDTH, TILE_HEIGHT / 2),
		Vector2(TILE_WIDTH / 2, TILE_HEIGHT),
		Vector2(0, TILE_HEIGHT / 2)
	])

## Преобразует экранные координаты в координаты ячейки
func _screen_to_grid(screen_pos: Vector2) -> Vector2i:
	# Учитываем позицию board и масштаб
	var local_pos = screen_pos - board.global_position

	# Учитываем масштаб - делим на текущий зум
	local_pos = local_pos / current_zoom

	# Для изометрии центр тайла [0,0] находится в:
	# center_x = BOARD_OFFSET_X + TILE_WIDTH/2
	# center_y = BOARD_OFFSET_Y + TILE_HEIGHT/2

	# Смещаем координаты относительно центра тайла [0,0]
	var dx = local_pos.x - BOARD_OFFSET_X - TILE_WIDTH / 2.0
	var dy = local_pos.y - BOARD_OFFSET_Y - TILE_HEIGHT / 2.0

	# Обратное изометрическое преобразование:
	# Для изометрии 2:1 (ширина в 2 раза больше высоты)
	# screen_x = (grid_x - grid_y) * TILE_WIDTH / 2
	# screen_y = (grid_x + grid_y) * TILE_HEIGHT / 2
	#
	# Решаем систему:
	# grid_x - grid_y = 2 * dx / TILE_WIDTH
	# grid_x + grid_y = 2 * dy / TILE_HEIGHT
	#
	# grid_x = dx / TILE_WIDTH + dy / TILE_HEIGHT
	# grid_y = dy / TILE_HEIGHT - dx / TILE_WIDTH

	var fx = dx / (TILE_WIDTH / 2.0) + dy / (TILE_HEIGHT / 2.0)
	var fy = dy / (TILE_HEIGHT / 2.0) - dx / (TILE_WIDTH / 2.0)

	# Делим на 2 т.к. формула даёт удвоенные значения
	fx = fx / 2.0
	fy = fy / 2.0

	var grid_x = int(floor(fx + 0.5))  # округляем к ближайшему
	var grid_y = int(floor(fy + 0.5))

	return Vector2i(grid_x, grid_y)

## Обработка ввода для hover-подсветки, кликов и масштабирования
## Мониторинг и защита масштаба от внешнего сброса
func _process(_delta: float) -> void:
	# Проверяем не сбросился ли масштаб без нашего ведома
	if board != null and abs(board.scale.x - current_zoom) > 0.01:
		_js_log("SCALE MISMATCH DETECTED: board=%.2f, current_zoom=%.2f - RESTORING" % [board.scale.x, current_zoom])
		board.scale = Vector2(current_zoom, current_zoom)

func _input(event: InputEvent) -> void:
	if event is InputEventMouseMotion:
		if is_panning:
			# Перетаскивание поля правой кнопкой
			var delta = event.position - pan_start_mouse
			board_pan_offset = pan_start_offset + delta
			board.position = board_pan_offset
		else:
			_update_hover(event.position)
	elif event is InputEventMouseButton:
		if event.button_index == MOUSE_BUTTON_RIGHT:
			if event.pressed:
				# Начало перетаскивания
				is_panning = true
				pan_start_mouse = event.position
				pan_start_offset = board_pan_offset
			else:
				# Конец перетаскивания
				is_panning = false
		elif event.pressed:
			if event.button_index == MOUSE_BUTTON_LEFT:
				_handle_board_click(event.position)
			elif event.button_index == MOUSE_BUTTON_WHEEL_UP:
				_zoom_in()
			elif event.button_index == MOUSE_BUTTON_WHEEL_DOWN:
				_zoom_out()

## Увеличить масштаб
func _zoom_in() -> void:
	_set_zoom(current_zoom + ZOOM_STEP)

## Уменьшить масштаб
func _zoom_out() -> void:
	_set_zoom(current_zoom - ZOOM_STEP)

## Установить масштаб мгновенно
func _set_zoom(new_zoom: float) -> void:
	new_zoom = clampf(new_zoom, ZOOM_MIN, ZOOM_MAX)
	if abs(new_zoom - current_zoom) < 0.001:
		return

	# Защита от резких скачков масштаба (больше 0.5 за раз - подозрительно)
	if abs(new_zoom - current_zoom) > 0.5:
		_js_log("WARNING: Large zoom jump blocked: %.2f -> %.2f" % [current_zoom, new_zoom])
		return

	current_zoom = new_zoom
	board.scale = Vector2(current_zoom, current_zoom)

	# Обновляем слайдер если есть (с флагом чтобы не вызвать рекурсию)
	if zoom_slider != null and not zoom_slider.is_queued_for_deletion():
		ignore_slider_change = true
		zoom_slider.value = current_zoom
		ignore_slider_change = false

	# Обновляем label с процентами
	if zoom_value_label != null and not zoom_value_label.is_queued_for_deletion():
		zoom_value_label.text = "%d%%" % int(current_zoom * 100)

## Обновляет pivot_offset доски для центрирования при масштабировании
func _update_board_pivot() -> void:
	# Вычисляем центр изометрического поля
	# Центр поля в изометрии находится примерно в середине по обеим осям
	var center_grid_x = field_size / 2.0
	var center_grid_y = field_size / 2.0

	# Преобразуем в экранные координаты
	var center_iso_x = (center_grid_x - center_grid_y) * (TILE_WIDTH / 2) + BOARD_OFFSET_X + TILE_WIDTH / 2
	var center_iso_y = (center_grid_x + center_grid_y) * (TILE_HEIGHT / 2) + BOARD_OFFSET_Y + TILE_HEIGHT / 2

	board.pivot_offset = Vector2(center_iso_x, center_iso_y)

## Обработчик изменения слайдера масштабирования
func _on_zoom_slider_changed(value: float) -> void:
	# Игнорируем программные изменения слайдера
	if ignore_slider_change:
		_js_log("Slider change IGNORED (flag): %.2f" % value)
		return
	# Игнорируем изменения меньше ZOOM_STEP/2 (для защиты от шума)
	if abs(value - current_zoom) < ZOOM_STEP / 2:
		return
	_js_log("Slider changed by USER to: %.2f (current_zoom=%.2f)" % [value, current_zoom])
	_set_zoom(value)

func _update_hover(mouse_pos: Vector2) -> void:
	if hover_highlight == null:
		return

	var grid_pos = _screen_to_grid(mouse_pos)

	# Проверяем что ячейка в пределах поля
	if grid_pos.x < 0 or grid_pos.x >= field_size or grid_pos.y < 0 or grid_pos.y >= field_size:
		if hover_highlight.visible:
			hover_highlight.visible = false
			last_hover_cell = Vector2i(-1, -1)
		return

	# Если ячейка изменилась - обновляем
	if grid_pos != last_hover_cell:
		last_hover_cell = grid_pos

		# Позиционируем подсветку
		var iso_x = BOARD_OFFSET_X + (grid_pos.x - grid_pos.y) * TILE_WIDTH / 2
		var iso_y = BOARD_OFFSET_Y + (grid_pos.x + grid_pos.y) * TILE_HEIGHT / 2
		hover_highlight.position = Vector2(iso_x, iso_y)
		hover_highlight.visible = true

		# Логируем что под мышкой
		var info = "Cell [%d,%d]" % [grid_pos.x, grid_pos.y]

		# Проверяем есть ли юнит на этой клетке
		var unit = GameManager.get_unit_at_position(grid_pos.x, grid_pos.y)
		if not unit.is_empty():
			info += " | Unit: id=%d, name=%s" % [unit.get("id", 0), unit.get("name", "?")]

		# Проверяем это подсветка перемещения или атаки
		if GameManager.can_move_to(grid_pos.x, grid_pos.y):
			info += " | CAN_MOVE"
		if not unit.is_empty() and GameManager.can_attack(unit.get("id", 0)):
			info += " | CAN_ATTACK"

		_js_log("HOVER: " + info)

## Обработка клика по игровому полю (глобальная, использует правильные координаты)
func _handle_board_click(mouse_pos: Vector2) -> void:
	var grid_pos = _screen_to_grid(mouse_pos)

	# Проверяем что ячейка в пределах поля
	if grid_pos.x < 0 or grid_pos.x >= field_size or grid_pos.y < 0 or grid_pos.y >= field_size:
		return

	_js_log("CLICK: Cell [%d,%d], action_mode=%s" % [grid_pos.x, grid_pos.y, action_mode])

	# Если не в режиме действия - проверяем выбор юнита
	if action_mode == "":
		var unit = GameManager.get_unit_at_position(grid_pos.x, grid_pos.y)
		if not unit.is_empty() and unit.get("player_id") == GameManager.current_player_id:
			_js_log("Selecting unit at [%d,%d]" % [grid_pos.x, grid_pos.y])
			GameManager.select_unit(unit)
		return

	# В режиме движения
	if action_mode == "move":
		if GameManager.can_move_to(grid_pos.x, grid_pos.y):
			_js_log("Moving to [%d,%d]" % [grid_pos.x, grid_pos.y])

			# Запускаем локальную анимацию
			var unit_id = int(GameManager.selected_unit.get("id", 0))
			if unit_id > 0 and unit_sprites.has(unit_id):
				var old_pos = unit_positions.get(unit_id, {})
				if not old_pos.is_empty():
					_animate_unit_move(unit_id, old_pos["x"], old_pos["y"], grid_pos.x, grid_pos.y, grid_pos.x, grid_pos.y)

			GameManager.move_selected_unit(grid_pos.x, grid_pos.y)
			_clear_highlights()
			action_mode = ""
			return

	# Проверяем атаку (в режимах move и attack)
	if action_mode in ["move", "attack"]:
		var target = GameManager.get_unit_at_position(grid_pos.x, grid_pos.y)
		if not target.is_empty() and GameManager.can_attack(target.get("id", 0)):
			_js_log("Attacking unit at [%d,%d]" % [grid_pos.x, grid_pos.y])
			GameManager.attack_with_selected_unit(target.get("id", 0))
			_clear_highlights()
			action_mode = ""
			return

func _on_game_state_updated(state: Dictionary) -> void:
	# Если игра окончена и overlay показан - не обновляем ничего
	if is_game_over_displayed:
		return

	# Проверяем что state валидный
	if state.is_empty():
		_js_log("ERROR: Empty state")
		RemoteLogger.error("Empty game state received")
		hint_label.text = "Ошибка: пустое состояние игры"
		return

	# Обновляем размер поля
	var field_data = state.get("field", {})
	var field_name = field_data.get("name", "5x5")
	if field_name == "" or field_name == null:
		field_name = "5x5"
	var new_field_size = int(field_name.split("x")[0])
	if new_field_size <= 0:
		new_field_size = 5

	# Перерисовываем доску только если размер поля изменился или доска ещё не инициализирована
	# Используем флаг board_initialized вместо cells.is_empty() чтобы избежать
	# повторной перерисовки из-за queue_free() который очищает cells асинхронно
	var need_redraw = new_field_size != field_size or not board_initialized
	_js_log("State update: field_size=%d, new_size=%d, initialized=%s, need_redraw=%s, scale=%.2f" % [field_size, new_field_size, str(board_initialized), str(need_redraw), board.scale.x])
	if need_redraw:
		_js_log("Drawing board: " + field_name)
		field_size = new_field_size
		_draw_board()
		board_initialized = true

	# Обновляем юнитов
	_update_units(state.get("units", []))

	# Обновляем UI
	_update_turn_indicator(state)
	_update_player_panels(state)
	_update_log(state.get("logs", []))

	# Обновляем кнопки
	_update_action_buttons()

	# Обновляем hint_label только если нет активного выбора юнита
	# (чтобы не сбрасывать состояние при polling)
	if GameManager.selected_unit.is_empty():
		# Останавливаем анимацию предыдущего выбранного юнита если был
		if last_selected_unit_id > 0:
			_set_unit_animation(last_selected_unit_id, false)
			last_selected_unit_id = -1
		if GameManager.is_my_turn():
			hint_label.text = "Ваш ход! Выберите юнита для действия."
		else:
			hint_label.text = "Ход противника. Ожидайте..."
	else:
		# Если юнит выбран, перерисовываем подсветку
		if action_mode == "move":
			_highlight_moves()
			if GameManager.current_actions.get("can_attack", []).size() > 0:
				_highlight_attacks_additional()

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

func _calculate_tile_size() -> void:
	# Масштабируем тайлы в зависимости от размера поля
	# Для 5x5 - базовый размер, для больших полей - уменьшаем
	var scale_factor: float = 1.0
	if field_size == 7:
		scale_factor = 0.75  # 75% для 7x7
	elif field_size >= 10:
		scale_factor = 0.55  # 55% для 10x10 и больше

	TILE_WIDTH = int(BASE_TILE_WIDTH * scale_factor)
	TILE_HEIGHT = int(BASE_TILE_HEIGHT * scale_factor)
	TILE_DEPTH = int(BASE_TILE_DEPTH * scale_factor)

	# Пересчитываем смещения для центрирования
	# Ширина изометрического поля: field_size * TILE_WIDTH
	# Высота изометрического поля: field_size * TILE_HEIGHT + TILE_DEPTH
	var iso_width = field_size * TILE_WIDTH
	var iso_height = field_size * TILE_HEIGHT + TILE_DEPTH

	# Центрируем по горизонтали (оставляем место для боковой панели 300px)
	var available_width = 800  # Примерная ширина области для доски
	BOARD_OFFSET_X = maxi(60, (available_width - iso_width) / 2 + iso_width / 2)
	BOARD_OFFSET_Y = 40

func _draw_board() -> void:
	# Очищаем старые клетки
	for cell in cells:
		cell.queue_free()
	cells.clear()

	# Пересчитываем размеры тайлов для текущего поля
	_calculate_tile_size()

	# Обновляем форму hover подсветки
	_update_hover_highlight_shape()

	# Вычисляем размер доски для изометрии
	var board_width = (field_size * 2) * (TILE_WIDTH / 2) + BOARD_OFFSET_X
	var board_height = (field_size * 2) * (TILE_HEIGHT / 2) + TILE_DEPTH + BOARD_OFFSET_Y + 100
	board.custom_minimum_size = Vector2(board_width, board_height)

	# Обновляем pivot для центрирования при масштабировании
	_update_board_pivot()

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
	# Собираем ID юнитов из нового состояния
	# ВАЖНО: приводим ID к int для консистентности (JSON может вернуть float)
	var new_unit_ids: Dictionary = {}
	for unit in units:
		if unit.get("count", 0) > 0:
			var uid = int(unit.get("id", 0))
			new_unit_ids[uid] = unit

	# Удаляем юнитов, которых больше нет (погибших)
	var units_to_remove: Array = []
	for unit_id in unit_sprites.keys():
		if not new_unit_ids.has(unit_id):
			units_to_remove.append(unit_id)

	for unit_id in units_to_remove:
		# Останавливаем активную анимацию если есть
		if active_tweens.has(unit_id) and is_instance_valid(active_tweens[unit_id]):
			active_tweens[unit_id].kill()
			active_tweens.erase(unit_id)
		if unit_sprites.has(unit_id):
			unit_sprites[unit_id].queue_free()
			unit_sprites.erase(unit_id)
			unit_positions.erase(unit_id)
			units_with_sprites.erase(unit_id)

	# Обновляем или создаём юнитов
	for unit in units:
		if unit.get("count", 0) <= 0:
			continue

		# ВАЖНО: приводим к int для консистентности
		var unit_id: int = int(unit.get("id", 0))
		var new_x: int = int(unit.get("x", 0))
		var new_y: int = int(unit.get("y", 0))

		if unit_sprites.has(unit_id):
			# Юнит уже существует - проверяем нужно ли перемещение
			var old_pos = unit_positions.get(unit_id, {})
			if old_pos.is_empty():
				# Нет старой позиции - просто запоминаем текущую
				unit_positions[unit_id] = {"x": new_x, "y": new_y}
			else:
				# Проверяем что нет активной анимации и позиция изменилась
				var is_animating = active_tweens.has(unit_id) and is_instance_valid(active_tweens[unit_id]) and active_tweens[unit_id].is_running()
				var pos_changed = old_pos["x"] != new_x or old_pos["y"] != new_y

				if pos_changed:
					RemoteLogger.info("Unit position changed", {
						"unit_id": unit_id,
						"old_x": old_pos["x"], "old_y": old_pos["y"],
						"new_x": new_x, "new_y": new_y,
						"is_animating": is_animating
					})

				if not is_animating and pos_changed:
					# Позиция изменилась - плавно перемещаем
					_animate_unit_move(unit_id, old_pos["x"], old_pos["y"], new_x, new_y, new_x, new_y)

			# Обновляем счётчик юнитов
			_update_unit_count(unit_id, unit.get("count", 0))

			# Обновляем has_moved (полупрозрачность)
			_update_unit_moved_state(unit_id, unit.get("has_moved", 0) == 1)

			# Проверяем есть ли текстура у юнита, если нет - пробуем загрузить
			_ensure_unit_has_texture(unit_id, unit)
		else:
			# Новый юнит - создаём
			var unit_type = unit.get("unit_type", {})
			var sprite_url = unit_type.get("sprite_url", "")
			var sprite_params = unit_type.get("sprite_params", null)
			var image_url = unit_type.get("image_url", "")

			RemoteLogger.info("Creating new unit sprite", {
				"unit_id": unit_id,
				"x": new_x,
				"y": new_y,
				"sprite_url": sprite_url if sprite_url else "none",
				"image_url": image_url if image_url else "none",
				"unit_type_name": unit_type.get("name", "unknown")
			})

			var unit_control = _create_unit_sprite(unit)
			board.add_child(unit_control)
			unit_sprites[unit_id] = unit_control
			unit_positions[unit_id] = {"x": new_x, "y": new_y}

			if sprite_url != "" and sprite_url != null:
				if sprite_sheets.has(sprite_url):
					# Спрайт уже в кэше - сразу применяем
					_apply_animated_sprite(unit_id, sprite_url)
				else:
					# Загружаем спрайт
					_load_sprite_sheet(sprite_url, sprite_params, unit_id)
			elif image_url != "" and image_url != null:
				if unit_textures.has(image_url):
					# Текстура уже в кэше - сразу применяем
					_apply_cached_texture(unit_id, image_url)
				else:
					_load_unit_texture(image_url, unit_id)

## Плавное перемещение юнита с анимацией
## target_x, target_y - целевые координаты для обновления unit_positions после анимации
func _animate_unit_move(unit_id: int, from_x: int, from_y: int, to_x: int, to_y: int, target_x: int = -1, target_y: int = -1) -> void:
	RemoteLogger.info("Starting unit animation", {
		"unit_id": unit_id,
		"from": "%d,%d" % [from_x, from_y],
		"to": "%d,%d" % [to_x, to_y],
		"duration": MOVE_DURATION
	})

	if not unit_sprites.has(unit_id):
		RemoteLogger.error("Unit sprite not found for animation", {"unit_id": unit_id})
		return

	var unit_control = unit_sprites[unit_id]
	if not is_instance_valid(unit_control):
		RemoteLogger.error("Unit control invalid", {"unit_id": unit_id})
		return

	# Останавливаем предыдущую анимацию для этого юнита если есть
	if active_tweens.has(unit_id) and is_instance_valid(active_tweens[unit_id]):
		active_tweens[unit_id].kill()

	# Вычисляем позиции в изометрических координатах
	var vertical_offset = _get_unit_vertical_offset()
	var from_pos = grid_to_iso(from_x, from_y) + Vector2(0, -vertical_offset)
	var to_pos = grid_to_iso(to_x, to_y) + Vector2(0, -vertical_offset)

	# Обновляем z_index для правильной отрисовки во время движения
	unit_control.z_index = to_x + to_y + 100

	# Создаём Tween для плавной анимации
	var tween = create_tween()
	tween.set_ease(Tween.EASE_IN_OUT)
	tween.set_trans(Tween.TRANS_QUAD)
	tween.tween_property(unit_control, "position", to_pos, MOVE_DURATION)

	# Сохраняем ссылку на активный Tween
	active_tweens[unit_id] = tween

	# Обновляем позицию после завершения анимации
	var final_x = target_x if target_x >= 0 else to_x
	var final_y = target_y if target_y >= 0 else to_y
	tween.finished.connect(func():
		RemoteLogger.debug("Animation finished", {"unit_id": unit_id, "final_pos": "%d,%d" % [final_x, final_y]})
		unit_positions[unit_id] = {"x": final_x, "y": final_y}
		active_tweens.erase(unit_id)
	)

## Обновляет счётчик юнитов в существующем спрайте
func _update_unit_count(unit_id: int, count: int) -> void:
	if not unit_sprites.has(unit_id):
		return

	var unit_control = unit_sprites[unit_id]
	var count_label = unit_control.get_node_or_null("CountLabel")
	if count_label and count_label is Label:
		count_label.text = str(count)

## Обновляет состояние "уже походил" (полупрозрачность)
func _update_unit_moved_state(unit_id: int, has_moved: bool) -> void:
	if not unit_sprites.has(unit_id):
		return

	var unit_control = unit_sprites[unit_id]
	# Меняем прозрачность всего контейнера
	unit_control.modulate.a = 0.5 if has_moved else 1.0

## Проверяет и загружает текстуру для юнита если она отсутствует
## Исправляет race condition когда спрайт загружается асинхронно
func _ensure_unit_has_texture(unit_id: int, unit: Dictionary) -> void:
	# Если спрайт уже был применён к этому юниту - пропускаем
	if units_with_sprites.has(unit_id):
		return

	if not unit_sprites.has(unit_id):
		return

	var unit_control = unit_sprites[unit_id]
	if not is_instance_valid(unit_control):
		return

	var texture_rect = unit_control.get_node_or_null("UnitTexture")
	var animated_sprite = unit_control.get_node_or_null("AnimatedSprite")

	# Проверяем есть ли текстура или анимированный спрайт
	var has_texture = (texture_rect != null and texture_rect.texture != null)
	var has_animated = (animated_sprite != null and animated_sprite.sprite_frames != null)

	if has_texture or has_animated:
		return  # Текстура уже есть

	# Текстуры нет - проверяем нужно ли загружать
	var unit_type = unit.get("unit_type", {})
	var sprite_url = unit_type.get("sprite_url", "")
	var sprite_params = unit_type.get("sprite_params", null)
	var image_url = unit_type.get("image_url", "")

	# Нормализуем пустые значения
	if sprite_url == null:
		sprite_url = ""
	if image_url == null:
		image_url = ""

	if sprite_url != "":
		if sprite_sheets.has(sprite_url):
			# Спрайт уже в кэше - применяем
			_apply_animated_sprite(unit_id, sprite_url)
		elif not pending_sprite_loads.has(sprite_url):
			# Загрузка ещё не запущена - запускаем
			RemoteLogger.debug("Loading sprite for unit (retry)", {"unit_id": unit_id, "sprite_url": sprite_url})
			_load_sprite_sheet(sprite_url, sprite_params, unit_id)
		# Иначе загрузка уже идёт - ничего не делаем
	elif image_url != "":
		if unit_textures.has(image_url):
			# Текстура уже в кэше - применяем
			_apply_cached_texture(unit_id, image_url)
		elif not pending_sprite_loads.has(image_url):
			RemoteLogger.debug("Loading texture for unit (retry)", {"unit_id": unit_id, "image_url": image_url})
			_load_unit_texture(image_url, unit_id)

## Применяет кэшированную текстуру к юниту
func _apply_cached_texture(unit_id: int, image_url: String) -> void:
	if not unit_sprites.has(unit_id) or not unit_textures.has(image_url):
		return
	var unit_control = unit_sprites[unit_id]
	var texture_rect = unit_control.get_node_or_null("UnitTexture")
	if texture_rect:
		texture_rect.texture = unit_textures[image_url]
		texture_rect.visible = true
		# Скрываем иконку
		var icon_label = unit_control.get_node_or_null("IconLabel")
		if icon_label:
			icon_label.visible = false
		# Помечаем что спрайт применён
		units_with_sprites[unit_id] = image_url

## Загрузка текстуры юнита через HTTP
func _load_unit_texture(image_url: String, unit_id: int) -> void:
	# Предотвращаем повторную загрузку той же текстуры
	if pending_sprite_loads.has(image_url):
		return
	pending_sprite_loads[image_url] = true

	var url = base_url + image_url

	var http = HTTPRequest.new()
	http.use_threads = false
	add_child(http)
	http.request_completed.connect(_on_texture_loaded.bind(image_url, unit_id, http))

	var headers: PackedStringArray = []
	if ApiClient.auth_token != "":
		headers.append("Authorization: Bearer " + ApiClient.auth_token)

	var err = http.request(url, headers)
	if err != OK:
		pending_sprite_loads.erase(image_url)
		http.queue_free()

func _on_texture_loaded(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray, image_path: String, unit_id: int, http_node: HTTPRequest) -> void:
	http_node.queue_free()
	# Убираем из pending после завершения загрузки
	pending_sprite_loads.erase(image_path)

	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200 or body.size() == 0:
		return

	var image = Image.new()
	var error = image.load_jpg_from_buffer(body)
	if error != OK:
		error = image.load_png_from_buffer(body)
	if error != OK:
		error = image.load_webp_from_buffer(body)
	if error != OK:
		return

	var texture = ImageTexture.create_from_image(image)
	unit_textures[image_path] = texture

	if unit_sprites.has(unit_id):
		var unit_control = unit_sprites[unit_id]
		var texture_rect = unit_control.get_node_or_null("UnitTexture")
		if texture_rect:
			texture_rect.texture = texture
			texture_rect.visible = true

## Загрузка спрайт-листа через HTTP
func _load_sprite_sheet(sprite_url: String, sprite_params: Variant, unit_id: int) -> void:
	# Предотвращаем повторную загрузку того же спрайта
	if pending_sprite_loads.has(sprite_url):
		return
	pending_sprite_loads[sprite_url] = true

	var url = base_url + sprite_url
	RemoteLogger.info("Loading sprite sheet", {"url": url, "unit_id": unit_id})

	var http = HTTPRequest.new()
	http.use_threads = false
	add_child(http)
	http.request_completed.connect(_on_sprite_sheet_loaded.bind(sprite_url, sprite_params, unit_id, http))

	var headers: PackedStringArray = []
	if ApiClient.auth_token != "":
		headers.append("Authorization: Bearer " + ApiClient.auth_token)

	var err = http.request(url, headers)
	if err != OK:
		RemoteLogger.error("Failed to start sprite request", {"url": url, "error": err})
		pending_sprite_loads.erase(sprite_url)  # Убираем из pending при ошибке
		http.queue_free()
	else:
		RemoteLogger.debug("Sprite request sent", {"url": url, "unit_id": unit_id})

func _on_sprite_sheet_loaded(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray, sprite_url: String, sprite_params: Variant, unit_id: int, http_node: HTTPRequest) -> void:
	RemoteLogger.info("Sprite callback received", {"sprite_url": sprite_url, "result": result, "response_code": response_code, "body_size": body.size()})
	http_node.queue_free()
	# Убираем из pending после завершения загрузки
	pending_sprite_loads.erase(sprite_url)

	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200 or body.size() == 0:
		RemoteLogger.error("Sprite load failed", {"sprite_url": sprite_url, "result": result, "response_code": response_code, "body_size": body.size()})
		return

	RemoteLogger.info("Sprite loaded successfully", {"sprite_url": sprite_url, "body_size": body.size()})

	# Создаём текстуру из спрайт-листа - определяем формат по сигнатуре файла
	var image = Image.new()
	var error = ERR_FILE_UNRECOGNIZED

	if body.size() >= 4:
		var header = body.slice(0, 4)
		# RIFF = WebP
		if header[0] == 0x52 and header[1] == 0x49 and header[2] == 0x46 and header[3] == 0x46:
			error = image.load_webp_from_buffer(body)
		# PNG signature
		elif header[0] == 0x89 and header[1] == 0x50 and header[2] == 0x4E and header[3] == 0x47:
			error = image.load_png_from_buffer(body)
		# JPEG signature
		elif header[0] == 0xFF and header[1] == 0xD8:
			error = image.load_jpg_from_buffer(body)

	# Fallback: пробуем все форматы
	if error != OK:
		error = image.load_png_from_buffer(body)
	if error != OK:
		error = image.load_jpg_from_buffer(body)
	if error != OK:
		error = image.load_webp_from_buffer(body)

	if error != OK:
		return

	var texture = ImageTexture.create_from_image(image)

	# Сохраняем в кэш с параметрами анимации
	sprite_sheets[sprite_url] = {
		"texture": texture,
		"params": sprite_params if sprite_params else {"frame_count": 1, "fps": 10, "columns": 1, "rows": 1}
	}

	# Обновляем юнита с анимированным спрайтом
	if unit_sprites.has(unit_id):
		RemoteLogger.info("Applying sprite to unit", {"unit_id": unit_id, "sprite_url": sprite_url})
		_apply_animated_sprite(unit_id, sprite_url)
	else:
		RemoteLogger.warning("Unit sprite not found after load", {"unit_id": unit_id})

## Применяет анимированный спрайт к юниту
func _apply_animated_sprite(unit_id: int, sprite_url: String) -> void:
	if not unit_sprites.has(unit_id) or not sprite_sheets.has(sprite_url):
		RemoteLogger.error("Cannot apply sprite - missing data", {"unit_id": unit_id, "has_sprite": unit_sprites.has(unit_id), "has_sheet": sprite_sheets.has(sprite_url)})
		return

	var unit_control = unit_sprites[unit_id]
	# Проверяем что узел всё ещё валиден (не удалён)
	if not is_instance_valid(unit_control) or unit_control.is_queued_for_deletion():
		RemoteLogger.error("Unit control invalid when applying sprite", {"unit_id": unit_id})
		return

	# Определяем является ли юнит противником для зеркалирования
	var is_opponent: bool = false
	for unit in GameManager.game_state.get("units", []):
		if int(unit.get("id", 0)) == unit_id:
			is_opponent = unit.get("player_id") != GameManager.game_state.get("player1_id")
			break

	RemoteLogger.debug("Applying animated sprite", {"unit_id": unit_id, "is_opponent": is_opponent})

	var sprite_data = sprite_sheets[sprite_url]
	var texture: Texture2D = sprite_data["texture"]
	var params: Dictionary = sprite_data["params"]

	# Удаляем старый TextureRect и иконку если есть
	var old_texture = unit_control.get_node_or_null("UnitTexture")
	if old_texture:
		old_texture.queue_free()

	# Скрываем Label с иконкой
	var icon_label = unit_control.get_node_or_null("IconLabel")
	if icon_label and icon_label is Label:
		icon_label.visible = false

	# Создаём AnimatedSprite2D
	var animated_sprite = AnimatedSprite2D.new()
	animated_sprite.name = "AnimatedSprite"

	# Создаём SpriteFrames для анимации
	var sprite_frames = SpriteFrames.new()
	sprite_frames.add_animation("idle")
	sprite_frames.set_animation_loop("idle", true)
	sprite_frames.set_animation_speed("idle", params.get("fps", 10))

	# Получаем параметры спрайт-листа с защитой от деления на ноль
	var frame_count: int = maxi(1, params.get("frame_count", 1))
	var columns: int = maxi(1, params.get("columns", 1))
	var rows: int = maxi(1, params.get("rows", 1))

	var tex_width = texture.get_width()
	var tex_height = texture.get_height()
	var frame_width = tex_width / columns
	var frame_height = tex_height / rows

	# Добавляем кадры анимации
	for i in range(frame_count):
		var col = i % columns
		var row = i / columns  # Integer division in GDScript 4.x

		var atlas_texture = AtlasTexture.new()
		atlas_texture.atlas = texture
		atlas_texture.region = Rect2(col * frame_width, row * frame_height, frame_width, frame_height)

		sprite_frames.add_frame("idle", atlas_texture)

	animated_sprite.sprite_frames = sprite_frames
	animated_sprite.animation = "idle"

	# Позиционирование и масштабирование (сохраняем пропорции, учитываем размер поля)
	var sprite_size = _get_unit_sprite_size()
	var tile_scale = float(TILE_WIDTH) / float(BASE_TILE_WIDTH)
	animated_sprite.position = Vector2(TILE_WIDTH / 2, int(36 * tile_scale))
	var scale_factor = float(sprite_size) / maxf(frame_width, frame_height)
	animated_sprite.scale = Vector2(scale_factor, scale_factor)
	# Зеркалим спрайт для противника
	animated_sprite.flip_h = is_opponent

	unit_control.add_child(animated_sprite)
	# Не запускаем анимацию - показываем первый кадр (анимация включается при выборе юнита)
	animated_sprite.stop()
	animated_sprite.frame = 0
	# Помечаем что спрайт применён
	units_with_sprites[unit_id] = sprite_url
	RemoteLogger.info("Animated sprite applied successfully", {"unit_id": unit_id, "frame_count": frame_count, "frame_size": "%dx%d" % [frame_width, frame_height]})

## Создаёт анимированный спрайт в контейнере (используется при создании юнита)
func _create_animated_sprite_in_container(container: Control, sprite_url: String, flip_h: bool = false) -> void:
	if not sprite_sheets.has(sprite_url):
		return

	var sprite_data = sprite_sheets[sprite_url]
	var texture: Texture2D = sprite_data["texture"]
	var params: Dictionary = sprite_data["params"]

	var animated_sprite = AnimatedSprite2D.new()
	animated_sprite.name = "AnimatedSprite"

	var sprite_frames = SpriteFrames.new()
	sprite_frames.add_animation("idle")
	sprite_frames.set_animation_loop("idle", true)
	sprite_frames.set_animation_speed("idle", params.get("fps", 10))

	# Защита от деления на ноль
	var frame_count: int = maxi(1, params.get("frame_count", 1))
	var columns: int = maxi(1, params.get("columns", 1))
	var rows: int = maxi(1, params.get("rows", 1))

	var tex_width = texture.get_width()
	var tex_height = texture.get_height()
	var frame_width = tex_width / columns
	var frame_height = tex_height / rows

	for i in range(frame_count):
		var col = i % columns
		var row = i / columns  # Integer division in GDScript 4.x

		var atlas_texture = AtlasTexture.new()
		atlas_texture.atlas = texture
		atlas_texture.region = Rect2(col * frame_width, row * frame_height, frame_width, frame_height)
		sprite_frames.add_frame("idle", atlas_texture)

	animated_sprite.sprite_frames = sprite_frames
	animated_sprite.animation = "idle"
	# Масштабируем позицию и размер под текущий размер поля
	var sprite_size = _get_unit_sprite_size()
	var tile_scale = float(TILE_WIDTH) / float(BASE_TILE_WIDTH)
	animated_sprite.position = Vector2(TILE_WIDTH / 2, int(36 * tile_scale))
	var scale_factor = float(sprite_size) / maxf(frame_width, frame_height)
	animated_sprite.scale = Vector2(scale_factor, scale_factor)
	# Зеркалим спрайт для противника
	animated_sprite.flip_h = flip_h

	container.add_child(animated_sprite)
	# Не запускаем анимацию - показываем первый кадр
	animated_sprite.stop()
	animated_sprite.frame = 0

## Включает/выключает анимацию спрайта юнита
func _set_unit_animation(unit_id: int, playing: bool) -> void:
	if not unit_sprites.has(unit_id):
		return
	var unit_control = unit_sprites[unit_id]
	if not is_instance_valid(unit_control):
		return
	var animated_sprite = unit_control.get_node_or_null("AnimatedSprite")
	if animated_sprite and animated_sprite is AnimatedSprite2D:
		if playing:
			animated_sprite.play("idle")
		else:
			animated_sprite.stop()
			animated_sprite.frame = 0

## Возвращает масштабированный размер спрайта юнита
func _get_unit_sprite_size() -> int:
	# Базовый размер 72 для 5x5, масштабируем для больших полей
	var base_size: int = 72
	var scale = float(TILE_WIDTH) / float(BASE_TILE_WIDTH)
	return int(base_size * scale)

## Возвращает масштабированный размер шрифта для иконок
func _get_unit_font_size() -> int:
	var base_size: int = 48
	var scale = float(TILE_WIDTH) / float(BASE_TILE_WIDTH)
	return int(base_size * scale)

## Возвращает масштабированный радиус базы юнита
func _get_unit_base_radius() -> int:
	var base_radius: int = 36
	var scale = float(TILE_WIDTH) / float(BASE_TILE_WIDTH)
	return int(base_radius * scale)

## Возвращает масштабированное смещение юнита над тайлом
func _get_unit_vertical_offset() -> int:
	var base_offset: int = 30
	var scale = float(TILE_WIDTH) / float(BASE_TILE_WIDTH)
	return int(base_offset * scale)

func _create_unit_sprite(unit: Dictionary) -> Control:
	var container = Control.new()
	var grid_x = unit.get("x", 0)
	var grid_y = unit.get("y", 0)

	# Масштабированные размеры
	var sprite_size = _get_unit_sprite_size()
	var base_radius = _get_unit_base_radius()
	var vertical_offset = _get_unit_vertical_offset()

	# Позиция в изометрических координатах
	var iso_pos = grid_to_iso(grid_x, grid_y)
	container.position = iso_pos + Vector2(0, -vertical_offset)  # Поднимаем юнита над тайлом
	container.size = Vector2(TILE_WIDTH, TILE_WIDTH)  # Квадратный спрайт
	container.z_index = grid_x + grid_y + 100  # Юниты поверх тайлов

	# Определяем цвета игрока и нужно ли зеркалить спрайт
	var player_color: Color
	var player_dark: Color
	var is_opponent: bool = false
	if unit.get("player_id") == GameManager.game_state.get("player1_id"):
		player_color = COLORS.player1
		player_dark = COLORS.player1_dark
	else:
		player_color = COLORS.player2
		player_dark = COLORS.player2_dark
		is_opponent = true  # player2 - противник, зеркалим спрайты

	# Полупрозрачность для уже походивших
	if unit.get("has_moved", 0) == 1:
		player_color.a = 0.5
		player_dark.a = 0.5

	# Основа юнита - цветной круг/овал для обозначения принадлежности
	var base = Polygon2D.new()
	var base_points: PackedVector2Array = []
	for i in range(16):
		var angle = i * PI * 2 / 16
		base_points.append(Vector2(
			TILE_WIDTH / 2 + cos(angle) * base_radius,
			TILE_HEIGHT + sin(angle) * base_radius * 0.5 + int(12 * float(TILE_WIDTH) / float(BASE_TILE_WIDTH))
		))
	base.polygon = base_points
	base.color = player_dark
	container.add_child(base)

	# Рамка базы
	var base_outline = Polygon2D.new()
	var outline_points: PackedVector2Array = []
	var outline_radius = base_radius + 3
	for i in range(16):
		var angle = i * PI * 2 / 16
		outline_points.append(Vector2(
			TILE_WIDTH / 2 + cos(angle) * outline_radius,
			TILE_HEIGHT + sin(angle) * outline_radius * 0.5 + int(12 * float(TILE_WIDTH) / float(BASE_TILE_WIDTH))
		))
	base_outline.polygon = outline_points
	base_outline.color = player_color
	container.add_child(base_outline)
	# Перемещаем base поверх outline
	container.move_child(base, 1)

	# Изображение юнита: приоритет sprite_url > image_url > иконка
	var unit_type = unit.get("unit_type", {})
	var sprite_url = unit_type.get("sprite_url", "")
	var image_url = unit_type.get("image_url", "")

	# Приоритет 1: анимированный спрайт-лист (если уже загружен)
	if sprite_url != null and sprite_url != "" and sprite_sheets.has(sprite_url):
		_create_animated_sprite_in_container(container, sprite_url, is_opponent)
	# Приоритет 2: статическое изображение
	elif image_url != null and image_url != "" and unit_textures.has(image_url):
		var texture_rect = TextureRect.new()
		texture_rect.name = "UnitTexture"
		texture_rect.texture = unit_textures[image_url]
		texture_rect.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
		texture_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		texture_rect.size = Vector2(sprite_size, sprite_size)
		texture_rect.position = Vector2((TILE_WIDTH - sprite_size) / 2, 0)
		texture_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
		# Зеркалим текстуру для противника
		if is_opponent:
			texture_rect.flip_h = true
		container.add_child(texture_rect)
	else:
		# Fallback: иконка юнита (эмодзи)
		# Получаем иконку и заменяем эмодзи на ASCII
		var icon = unit_type.get("icon", "U")
		# Если иконка содержит Unicode символы выше ASCII, заменяем на "U"
		if icon == null or icon == "" or icon.length() > 2 or (icon.length() > 0 and icon.unicode_at(0) > 127):
			icon = "U"

		var icon_label = Label.new()
		icon_label.name = "IconLabel"
		icon_label.text = icon
		icon_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		icon_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		icon_label.size = Vector2(TILE_WIDTH, sprite_size)
		icon_label.position = Vector2(0, 0)
		icon_label.add_theme_font_size_override("font_size", _get_unit_font_size())
		icon_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
		container.add_child(icon_label)

		# Добавляем placeholder для текстуры (будет заполнен после загрузки)
		var texture_rect = TextureRect.new()
		texture_rect.name = "UnitTexture"
		texture_rect.size = Vector2(sprite_size, sprite_size)
		texture_rect.position = Vector2((TILE_WIDTH - sprite_size) / 2, 0)
		texture_rect.visible = false
		texture_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
		container.add_child(texture_rect)

	# Количество юнитов - бейдж в углу (масштабируем размер)
	var badge_scale = float(TILE_WIDTH) / float(BASE_TILE_WIDTH)
	var badge_width = int(28 * badge_scale)
	var badge_height = int(20 * badge_scale)

	var count_label = Label.new()
	count_label.name = "CountLabel"
	count_label.text = str(unit.get("count", 0))
	count_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	count_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	count_label.size = Vector2(badge_width, badge_height)
	count_label.position = Vector2(TILE_WIDTH - badge_width - 2, TILE_HEIGHT - 4)
	count_label.add_theme_font_size_override("font_size", int(14 * badge_scale))
	count_label.add_theme_color_override("font_color", Color.WHITE)
	# Добавляем чёрную обводку для читаемости
	count_label.add_theme_constant_override("outline_size", 2)
	count_label.add_theme_color_override("font_outline_color", Color.BLACK)
	count_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	container.add_child(count_label)

	# Кликабельная область
	var click_area = Control.new()
	click_area.name = "ClickArea"
	click_area.size = container.size
	click_area.mouse_filter = Control.MOUSE_FILTER_STOP
	click_area.gui_input.connect(_on_unit_clicked.bind(unit))
	container.add_child(click_area)

	# Выделение выбранного юнита
	if not GameManager.selected_unit.is_empty() and GameManager.selected_unit.get("id") == unit.get("id"):
		var selection = Polygon2D.new()
		var sel_points: PackedVector2Array = []
		var sel_radius = base_radius + int(8 * badge_scale)
		for i in range(16):
			var angle = i * PI * 2 / 16
			sel_points.append(Vector2(
				TILE_WIDTH / 2 + cos(angle) * sel_radius,
				TILE_HEIGHT + sin(angle) * sel_radius * 0.5 + int(12 * badge_scale)
			))
		selection.polygon = sel_points
		selection.color = COLORS.selected
		container.add_child(selection)
		container.move_child(selection, 0)  # Под остальными элементами

	return container

func _on_cell_clicked(event: InputEvent, x: int, y: int) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		RemoteLogger.debug("Cell clicked", {"x": x, "y": y, "action_mode": action_mode})

		# Проверяем перемещение
		var can_move = GameManager.can_move_to(x, y)
		RemoteLogger.debug("Can move check", {"can_move": can_move, "current_actions": str(GameManager.current_actions)})

		if action_mode == "move" and can_move:
			RemoteLogger.info("Moving unit", {"x": x, "y": y})
			GameManager.move_selected_unit(x, y)
			_clear_highlights()
			action_mode = ""
			return

		# Проверяем атаку (в режимах move и attack)
		if action_mode in ["move", "attack"]:
			var target = GameManager.get_unit_at_position(x, y)
			if not target.is_empty() and GameManager.can_attack(target.get("id")):
				GameManager.attack_with_selected_unit(target.get("id"))
				_clear_highlights()
				action_mode = ""

func _on_unit_clicked(event: InputEvent, unit: Dictionary) -> void:
	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		var unit_id = unit.get("id", -1)
		var unit_x = unit.get("x", -1)
		var unit_y = unit.get("y", -1)
		var selected_id = GameManager.selected_unit.get("id", -1)

		RemoteLogger.debug("Unit clicked", {
			"unit_id": unit_id,
			"unit_pos": str(unit_x) + "," + str(unit_y),
			"action_mode": action_mode,
			"selected_unit": selected_id
		})

		# Если юнит НЕ выбран - выбираем этого юнита (если наш)
		if GameManager.selected_unit.is_empty():
			if unit.get("player_id") == GameManager.current_player_id:
				GameManager.select_unit(unit)
			return

		# Юнит уже выбран - все клики обрабатываем как действия на клетку
		# Игнорируем клик на самого себя
		if selected_id == unit_id:
			RemoteLogger.debug("Clicked on selected unit, ignoring")
			return

		# Проверяем атаку по этой клетке
		if action_mode in ["move", "attack"] and GameManager.can_attack(unit_id):
			RemoteLogger.info("Attacking unit", {"target_id": unit_id})
			GameManager.attack_with_selected_unit(unit_id)
			_clear_highlights()
			action_mode = ""
			return

		# Проверяем перемещение на эту клетку
		if action_mode == "move" and GameManager.can_move_to(unit_x, unit_y):
			RemoteLogger.info("Moving to cell with unit", {"x": unit_x, "y": unit_y})
			# Запускаем локальную анимацию
			var moving_unit_id = int(GameManager.selected_unit.get("id", 0))
			if moving_unit_id > 0 and unit_sprites.has(moving_unit_id):
				var old_pos = unit_positions.get(moving_unit_id, {})
				if not old_pos.is_empty():
					_animate_unit_move(moving_unit_id, old_pos["x"], old_pos["y"], unit_x, unit_y, unit_x, unit_y)
			GameManager.move_selected_unit(unit_x, unit_y)
			_clear_highlights()
			action_mode = ""
			return

		# Клик не привёл к действию - игнорируем (не переключаем юнита)
		RemoteLogger.debug("Click on unit didn't result in action, ignoring")

func _on_unit_actions_received(actions: Dictionary) -> void:
	_update_action_buttons()

	# Управляем анимацией спрайтов: останавливаем старый, запускаем новый
	var current_unit_id = int(GameManager.selected_unit.get("id", -1))
	if current_unit_id != last_selected_unit_id:
		# Останавливаем анимацию предыдущего юнита
		if last_selected_unit_id > 0:
			_set_unit_animation(last_selected_unit_id, false)
		# Запускаем анимацию нового юнита
		if current_unit_id > 0:
			_set_unit_animation(current_unit_id, true)
		last_selected_unit_id = current_unit_id

	# Автоматически показываем доступные ходы при выборе юнита
	var can_move = actions.get("can_move", []).size() > 0
	var can_attack = actions.get("can_attack", []).size() > 0

	if can_move:
		action_mode = "move"
		_set_selected_unit_clickable(false)  # Отключаем клики на выбранном юните
		_highlight_moves()
		# Также подсвечиваем атаку если доступна
		if can_attack:
			_highlight_attacks_additional()
		hint_label.text = "Нажмите на зелёную клетку для перемещения или красную для атаки"
	elif can_attack:
		action_mode = "attack"
		_set_selected_unit_clickable(false)  # Отключаем клики на выбранном юните
		_highlight_attacks()
		hint_label.text = "Нажмите на красную клетку для атаки"
	else:
		hint_label.text = "Нет доступных действий. Пропустите ход."

	# Перерисовываем юнитов чтобы показать выделение
	_update_units(GameManager.game_state.get("units", []))

func _on_move_pressed() -> void:
	action_mode = "move"
	_set_selected_unit_clickable(false)
	_highlight_moves()
	hint_label.text = "Нажмите на зелёную клетку для перемещения"

func _on_attack_pressed() -> void:
	action_mode = "attack"
	_set_selected_unit_clickable(false)
	_highlight_attacks()
	hint_label.text = "Нажмите на красную клетку для атаки"

func _on_skip_pressed() -> void:
	GameManager.skip_selected_unit()
	_clear_highlights()
	_set_selected_unit_clickable(true)
	action_mode = ""

## Включает/отключает кликабельность спрайта выбранного юнита
## Когда юнит в режиме действия, его спрайт не должен перехватывать клики
func _set_selected_unit_clickable(clickable: bool) -> void:
	if GameManager.selected_unit.is_empty():
		return
	var unit_id = int(GameManager.selected_unit.get("id", 0))
	if unit_id <= 0 or not unit_sprites.has(unit_id):
		return
	var unit_control = unit_sprites[unit_id]
	if not is_instance_valid(unit_control):
		return

	# Находим ClickArea и переключаем его mouse_filter
	var click_area = unit_control.get_node_or_null("ClickArea")
	if click_area:
		click_area.mouse_filter = Control.MOUSE_FILTER_STOP if clickable else Control.MOUSE_FILTER_IGNORE

# defer удалена

func _on_surrender_pressed() -> void:
	# Сдаёмся и возвращаемся в меню
	# Ожидаем завершения запроса surrender перед переходом в меню
	# чтобы избежать race condition с HTTPRequest
	GameManager.surrender_game()
	await get_tree().create_timer(0.3).timeout
	GameManager.return_to_menu()

## Показать/скрыть панель лога
func _on_log_toggle_pressed() -> void:
	log_panel.visible = not log_panel.visible
	log_toggle_button.visible = not log_panel.visible

## Закрыть панель лога
func _on_close_log_pressed() -> void:
	log_panel.visible = false
	log_toggle_button.visible = true

## Создание изометрической подсветки для тайла (только визуальная, без обработки кликов)
func _create_iso_highlight(color: Color, grid_x: int, grid_y: int, highlight_type: String = "move") -> Polygon2D:
	var highlight = Polygon2D.new()
	highlight.name = "Highlight" if highlight_type == "move" else "AttackHighlight"
	highlight.polygon = PackedVector2Array([
		Vector2(TILE_WIDTH / 2, 0),
		Vector2(TILE_WIDTH, TILE_HEIGHT / 2),
		Vector2(TILE_WIDTH / 2, TILE_HEIGHT),
		Vector2(0, TILE_HEIGHT / 2)
	])
	highlight.color = color
	highlight.z_index = 50  # Поверх тайлов но под юнитами
	return highlight

func _highlight_moves() -> void:
	_clear_highlights()
	for move in GameManager.current_actions.get("can_move", []):
		var x = move.get("x", 0)
		var y = move.get("y", 0)
		var idx = y * field_size + x
		if idx < cells.size():
			var highlight = _create_iso_highlight(COLORS.move_highlight, x, y, "move")
			cells[idx].add_child(highlight)

func _highlight_attacks() -> void:
	_clear_highlights()
	for target in GameManager.current_actions.get("can_attack", []):
		var x = target.get("x", 0)
		var y = target.get("y", 0)
		var idx = y * field_size + x
		if idx < cells.size():
			var highlight = _create_iso_highlight(COLORS.attack_highlight, x, y, "attack")
			cells[idx].add_child(highlight)

## Подсветка атаки без очистки существующей подсветки (для комбинированного отображения)
func _highlight_attacks_additional() -> void:
	for target in GameManager.current_actions.get("can_attack", []):
		var x = target.get("x", 0)
		var y = target.get("y", 0)
		var idx = y * field_size + x
		if idx < cells.size():
			var highlight = _create_iso_highlight(COLORS.attack_highlight, x, y, "attack")
			cells[idx].add_child(highlight)

func _clear_highlights() -> void:
	# Включаем обратно клики на выбранном юните
	_set_selected_unit_clickable(true)

	for cell in cells:
		# Удаляем ВСЕ подсветки (могут быть дубликаты)
		# Используем free() вместо queue_free() для мгновенного удаления
		var to_remove = []
		for child in cell.get_children():
			if child.name == "Highlight" or child.name == "AttackHighlight":
				to_remove.append(child)
		for child in to_remove:
			child.free()

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
	# defer_button удалена

func _update_log(logs: Array) -> void:
	# Проверяем изменилось ли количество логов (оптимизация - не пересоздаём если не изменилось)
	if logs.size() == last_log_count:
		return
	last_log_count = logs.size()

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
	# Устанавливаем флаг чтобы предотвратить обновления
	is_game_over_displayed = true

	# Очищаем поле боя
	_clear_board()

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

## Очищает поле боя (удаляет все клетки и юнитов)
func _clear_board() -> void:
	# Сбрасываем флаг инициализации доски
	board_initialized = false

	# Останавливаем активные анимации сначала
	for unit_id in active_tweens.keys():
		if is_instance_valid(active_tweens[unit_id]):
			active_tweens[unit_id].kill()
	active_tweens.clear()

	# Удаляем hover подсветку (free для немедленного удаления)
	if hover_highlight != null and is_instance_valid(hover_highlight):
		hover_highlight.free()
		hover_highlight = null

	# Удаляем все клетки (free для немедленного удаления)
	for cell in cells:
		if is_instance_valid(cell):
			cell.free()
	cells.clear()

	# Удаляем все спрайты юнитов (free для немедленного удаления)
	for unit_id in unit_sprites.keys():
		if is_instance_valid(unit_sprites[unit_id]):
			unit_sprites[unit_id].free()
	unit_sprites.clear()
	unit_positions.clear()
	units_with_sprites.clear()

	# Удаляем все оставшиеся дочерние элементы board (free для немедленного удаления)
	for child in board.get_children():
		if is_instance_valid(child):
			child.free()

func _on_error(error_message: String) -> void:
	hint_label.text = "Ошибка: " + error_message

func _on_back_to_menu() -> void:
	# Сбрасываем флаг перед переходом в меню
	is_game_over_displayed = false
	GameManager.return_to_menu()
