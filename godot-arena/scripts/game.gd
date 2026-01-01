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
	# Травяное поле (поляна)
	"grass_base": Color(0.298, 0.600, 0.298),      # Базовый зелёный RGB(76, 153, 76)
	"grass_light": Color(0.361, 0.678, 0.361),    # Светлый оттенок RGB(92, 173, 92)
	"grass_dark": Color(0.235, 0.522, 0.235),     # Тёмный оттенок RGB(60, 133, 60)
	"grid_line": Color(0.157, 0.314, 0.157, 0.4), # Линии сетки (полупрозрачные)

	# Камни (препятствия)
	"rock_top": Color(0.502, 0.502, 0.471),       # Верх камня RGB(128, 128, 120)
	"rock_side": Color(0.376, 0.376, 0.353),      # Бок камня RGB(96, 96, 90)
	"rock_shadow": Color(0.251, 0.251, 0.235),    # Тень камня

	# Деревья по границам
	"tree_trunk": Color(0.396, 0.263, 0.129),     # Ствол RGB(101, 67, 33)
	"tree_leaves": Color(0.133, 0.545, 0.133),    # Крона RGB(34, 139, 34)
	"tree_leaves_dark": Color(0.098, 0.420, 0.098), # Тёмная крона

	# Цвета игроков
	"player1": Color(0.906, 0.298, 0.235),
	"player1_dark": Color(0.7, 0.2, 0.15),
	"player2": Color(0.180, 0.800, 0.443),
	"player2_dark": Color(0.1, 0.6, 0.3),

	# Подсветка действий
	"move_highlight": Color(0.6, 0.3, 0.9, 0.6),  # Фиолетовый для возможных ходов
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
# Кэш текстур для декораций и препятствий (загруженные спрайты)
var decoration_textures: Dictionary = {}  # sprite_url -> Texture2D
# Контейнеры для декораций и препятствий со спрайтами
var decoration_sprites: Array[Control] = []
var obstacle_sprite_containers: Array[Control] = []

# Состояние
var field_size: int = 5
var cells: Array[Control] = []
var cells_by_coords: Dictionary = {}  # "x_y" -> Control - для быстрого доступа по координатам
var unit_sprites: Dictionary = {}  # unit_id -> Control
var unit_positions: Dictionary = {}  # unit_id -> {x, y} - последние известные позиции
var active_tweens: Dictionary = {}  # unit_id -> Tween - активные анимации перемещения
var action_mode: String = ""  # "move" или "attack"
var board_initialized: bool = false  # Флаг что доска уже создана
var obstacle_sprites: Dictionary = {}  # "x_y" -> Control - спрайты препятствий
var obstacle_textures: Dictionary = {}  # sprite_url -> Texture2D - кэш текстур препятствий
var last_selected_unit_id: int = -1  # ID предыдущего выбранного юнита для управления анимацией
var last_log_count: int = 0  # Для отслеживания изменений в логах
var base_url: String = ""  # Кэшированный base URL для запросов
var is_game_over_displayed: bool = false  # Флаг что игра окончена и показан overlay
# Координаты границ с учётом декораций (вычисляются в _calculate_tile_size)
var board_min_x: int = 0
var board_max_x: int = 4
var board_min_y: int = 0
var board_max_y: int = 4

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
	GameManager.game_draw.connect(_on_game_draw)
	GameManager.draw_warning.connect(_on_draw_warning)
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

	# Проверяем есть ли юнит на этой клетке
	var clicked_unit = GameManager.get_unit_at_position(grid_pos.x, grid_pos.y)

	# Если не в режиме действия - проверяем выбор юнита
	if action_mode == "":
		if not clicked_unit.is_empty() and clicked_unit.get("player_id") == GameManager.current_player_id:
			_js_log("Selecting unit at [%d,%d]" % [grid_pos.x, grid_pos.y])
			GameManager.select_unit(clicked_unit)
		return

	# Если кликнули на своего юнита (не выбранного) - переключаемся на него
	if not clicked_unit.is_empty() and clicked_unit.get("player_id") == GameManager.current_player_id:
		var selected_id = GameManager.selected_unit.get("id", -1)
		if clicked_unit.get("id", -1) != selected_id:
			_js_log("Switching to unit at [%d,%d]" % [grid_pos.x, grid_pos.y])
			_clear_highlights()
			action_mode = ""
			GameManager.select_unit(clicked_unit)
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

	# Проверяем это челлендж или PvP (на основе данных от сервера)
	if state.has("is_challenge"):
		GameManager.is_challenge_game = state.get("is_challenge", false)

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
			# Если это челлендж и не наш ход - запрашиваем ход AI
			if GameManager.is_challenge_game and not state.get("is_game_over", false):
				_request_ai_turn()
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
func _create_iso_tile(grid_x: int, grid_y: int, is_obstacle: bool = false, is_game_cell: bool = true) -> Control:
	var container = Control.new()
	var iso_pos = grid_to_iso(grid_x, grid_y)
	container.position = iso_pos
	container.size = Vector2(TILE_WIDTH, TILE_HEIGHT + TILE_DEPTH)
	container.z_index = grid_x + grid_y  # Для правильного z-order

	# Случайная вариация оттенка травы для естественности
	var rng = RandomNumberGenerator.new()
	rng.seed = hash(str(grid_x) + "_" + str(grid_y))  # Детерминированный seed
	var shade_variation = rng.randf_range(-0.05, 0.05)
	var grass_color = COLORS.grass_base

	# Для декоративных ячеек (за пределами игрового поля) делаем цвет темнее
	if not is_game_cell:
		grass_color = grass_color.darkened(0.15)

	grass_color = grass_color.lightened(shade_variation) if shade_variation > 0 else grass_color.darkened(-shade_variation)

	# Рисуем травяную ячейку (плоский ромб)
	var top_face = Polygon2D.new()
	top_face.polygon = PackedVector2Array([
		Vector2(TILE_WIDTH / 2, 0),           # Верх
		Vector2(TILE_WIDTH, TILE_HEIGHT / 2), # Право
		Vector2(TILE_WIDTH / 2, TILE_HEIGHT), # Низ
		Vector2(0, TILE_HEIGHT / 2)           # Лево
	])
	top_face.color = grass_color
	container.add_child(top_face)

	# Тонкие линии-контуры для разделения ячеек (только для игровых клеток)
	if is_game_cell:
		var line_width = 1.0
		var grid_line = Line2D.new()
		grid_line.points = PackedVector2Array([
			Vector2(TILE_WIDTH / 2, 0),
			Vector2(TILE_WIDTH, TILE_HEIGHT / 2),
			Vector2(TILE_WIDTH / 2, TILE_HEIGHT),
			Vector2(0, TILE_HEIGHT / 2),
			Vector2(TILE_WIDTH / 2, 0)  # Замыкаем контур
		])
		grid_line.width = line_width
		grid_line.default_color = COLORS.grid_line
		container.add_child(grid_line)

	# Если это препятствие - рисуем камень поверх травы
	if is_obstacle:
		_add_rock_to_tile(container)

	# Невидимая область для кликов (только для игровых клеток)
	if is_game_cell:
		var click_area = Control.new()
		click_area.size = Vector2(TILE_WIDTH, TILE_HEIGHT + TILE_DEPTH)
		click_area.mouse_filter = Control.MOUSE_FILTER_STOP
		click_area.gui_input.connect(_on_cell_clicked.bind(grid_x, grid_y))
		container.add_child(click_area)

	return container

## Добавляет камень на ячейку (для препятствий)
func _add_rock_to_tile(container: Control) -> void:
	# Основной камень (овальная форма)
	var rock_main = Polygon2D.new()
	var cx = TILE_WIDTH / 2
	var cy = TILE_HEIGHT / 2
	var rx = TILE_WIDTH * 0.35  # Радиус по X
	var ry = TILE_HEIGHT * 0.4  # Радиус по Y

	# Создаём овальную форму камня
	var rock_points: PackedVector2Array = []
	for i in range(8):
		var angle = i * PI * 2 / 8
		var px = cx + cos(angle) * rx
		var py = cy + sin(angle) * ry * 0.7
		rock_points.append(Vector2(px, py))
	rock_main.polygon = rock_points
	rock_main.color = COLORS.rock_top
	container.add_child(rock_main)

	# Тень камня (смещённая вниз)
	var shadow = Polygon2D.new()
	var shadow_points: PackedVector2Array = []
	for i in range(8):
		var angle = i * PI * 2 / 8
		var px = cx + cos(angle) * rx * 0.9
		var py = cy + sin(angle) * ry * 0.6 + TILE_HEIGHT * 0.15
		shadow_points.append(Vector2(px, py))
	shadow.polygon = shadow_points
	shadow.color = COLORS.rock_shadow
	shadow.z_index = -1  # Под основным камнем
	container.add_child(shadow)

	# Блик на камне (маленький светлый овал)
	var highlight = Polygon2D.new()
	var hl_points: PackedVector2Array = []
	var hl_cx = cx - rx * 0.3
	var hl_cy = cy - ry * 0.2
	var hl_rx = rx * 0.25
	var hl_ry = ry * 0.2
	for i in range(6):
		var angle = i * PI * 2 / 6
		var px = hl_cx + cos(angle) * hl_rx
		var py = hl_cy + sin(angle) * hl_ry
		hl_points.append(Vector2(px, py))
	highlight.polygon = hl_points
	highlight.color = COLORS.rock_top.lightened(0.3)
	container.add_child(highlight)

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

	# Находим минимальные и максимальные координаты декораций
	board_min_x = 0
	board_max_x = field_size - 1
	board_min_y = 0
	board_max_y = field_size - 1
	var decorations = GameManager.game_state.get("decorations", [])
	var has_template_decorations = not decorations.is_empty()

	_js_log("_calculate_tile_size: decorations count=" + str(decorations.size()))
	for dec in decorations:
		# Явное приведение к int (JSON может вернуть float)
		var dec_x: int = int(dec.get("x", 0))
		var dec_y: int = int(dec.get("y", 0))
		var dec_width: int = int(dec.get("width", 1))
		var dec_height: int = int(dec.get("height", 1))
		_js_log("  Decoration at (%d, %d) size %dx%d" % [dec_x, dec_y, dec_width, dec_height])
		# Учитываем все клетки которые занимает декорация
		board_min_x = mini(board_min_x, dec_x)
		board_max_x = maxi(board_max_x, dec_x + dec_width - 1)
		board_min_y = mini(board_min_y, dec_y)
		board_max_y = maxi(board_max_y, dec_y + dec_height - 1)

	# Деревья по границам только если нет декораций из шаблона
	if not has_template_decorations:
		board_min_x = mini(board_min_x, -2)
		board_max_x = maxi(board_max_x, field_size + 1)
		board_min_y = mini(board_min_y, -2)
		board_max_y = maxi(board_max_y, field_size + 1)

	# Всегда расширяем границы до decoration_margin для правильного расчёта смещений
	# (это гарантирует что все декоративные клетки будут видны)
	var decoration_margin = 5
	board_min_x = mini(board_min_x, -decoration_margin)
	board_max_x = maxi(board_max_x, field_size - 1 + decoration_margin)
	board_min_y = mini(board_min_y, -decoration_margin)
	board_max_y = maxi(board_max_y, field_size - 1 + decoration_margin)

	# Вычисляем необходимое смещение чтобы все декорации помещались
	# Для изометрии: iso_x = (x - y) * TILE_WIDTH/2 + OFFSET_X
	# Минимальный iso_x при min_x, max_y: (min_x - max_y) * TILE_WIDTH/2 + OFFSET_X >= 0
	# Значит OFFSET_X >= -(min_x - max_y) * TILE_WIDTH/2 = (max_y - min_x) * TILE_WIDTH/2
	var min_offset_x = (board_max_y - board_min_x) * (TILE_WIDTH / 2) + 50  # +50 для запаса

	# Центрируем по горизонтали (оставляем место для боковой панели 300px)
	var available_width = 800  # Примерная ширина области для доски
	var iso_width = field_size * TILE_WIDTH
	var calculated_offset = (available_width - iso_width) / 2 + iso_width / 2

	BOARD_OFFSET_X = maxi(min_offset_x, calculated_offset)

	# Для изометрии: iso_y = (x + y) * TILE_HEIGHT/2 + OFFSET_Y
	# Минимальный iso_y при min_x, min_y: (min_x + min_y) * TILE_HEIGHT/2 + OFFSET_Y >= 0
	# Значит OFFSET_Y >= -(min_x + min_y) * TILE_HEIGHT/2
	var min_offset_y = -(board_min_x + board_min_y) * (TILE_HEIGHT / 2) + 50  # +50 для запаса
	BOARD_OFFSET_Y = maxi(min_offset_y, 40)  # Минимум 40px сверху

	var expected_cells = (board_max_x - board_min_x + 1) * (board_max_y - board_min_y + 1)
	_js_log("_calculate_tile_size: field=%d, board bounds x=[%d,%d] y=[%d,%d], expected_cells=%d, TILE_WIDTH=%d, OFFSET_X=%d, OFFSET_Y=%d" % [field_size, board_min_x, board_max_x, board_min_y, board_max_y, expected_cells, TILE_WIDTH, BOARD_OFFSET_X, BOARD_OFFSET_Y])

func _draw_board() -> void:
	# Очищаем старые клетки
	for cell in cells:
		cell.queue_free()
	cells.clear()
	cells_by_coords.clear()

	# Очищаем старые декорации и препятствия со спрайтами
	for dec in decoration_sprites:
		if is_instance_valid(dec):
			dec.queue_free()
	decoration_sprites.clear()
	for obs in obstacle_sprite_containers:
		if is_instance_valid(obs):
			obs.queue_free()
	obstacle_sprite_containers.clear()

	# Пересчитываем размеры тайлов для текущего поля
	_calculate_tile_size()

	# Обновляем форму hover подсветки
	_update_hover_highlight_shape()

	# Вычисляем размер доски для изометрии с учётом всех декораций
	# Ширина: от минимального iso_x до максимального iso_x
	var total_x_span = board_max_x - board_min_x + 1
	var total_y_span = board_max_y - board_min_y + 1
	# Изометрическая ширина: (total_x + total_y) * TILE_WIDTH / 2 + запас
	var board_width = (total_x_span + total_y_span) * (TILE_WIDTH / 2) + BOARD_OFFSET_X + TILE_WIDTH
	# Изометрическая высота: (total_x + total_y) * TILE_HEIGHT / 2 + глубина + запас
	var board_height = (total_x_span + total_y_span) * (TILE_HEIGHT / 2) + TILE_DEPTH + BOARD_OFFSET_Y + 200
	board.custom_minimum_size = Vector2(board_width, board_height)
	# Принудительно устанавливаем размер доски
	board.size = Vector2(board_width, board_height)
	_js_log("_draw_board: board_size=%dx%d, custom_min=%s" % [int(board_width), int(board_height), str(board.custom_minimum_size)])

	# Обновляем pivot для центрирования при масштабировании
	_update_board_pivot()

	# Проверяем есть ли декорации из шаблона
	var decorations = GameManager.game_state.get("decorations", [])
	var has_template_decorations = not decorations.is_empty()

	# Собираем препятствия в словарь для быстрого доступа
	# Учитываем многоклеточные препятствия: помечаем все занятые клетки
	var obstacles_set = {}  # key -> obstacle data (для origin) или true (для занятых клеток)
	var obstacles_list = GameManager.game_state.get("obstacles", [])
	_js_log("_draw_board: obstacles count=" + str(obstacles_list.size()))
	for obstacle in obstacles_list:
		# Явное приведение к int (JSON может вернуть float)
		var ox: int = int(obstacle.get("x", 0))
		var oy: int = int(obstacle.get("y", 0))
		var ow: int = int(obstacle.get("width", 1))
		var oh: int = int(obstacle.get("height", 1))
		var sprite_url = obstacle.get("sprite_url", "")
		_js_log("  Obstacle: pos=(%d,%d), size=%dx%d, sprite=%s" % [ox, oy, ow, oh, sprite_url])
		var origin_key = "%d_%d" % [ox, oy]
		obstacles_set[origin_key] = obstacle  # Сохраняем данные препятствия для origin
		# Помечаем остальные занятые клетки
		for dx in range(ow):
			for dy in range(oh):
				if dx == 0 and dy == 0:
					continue  # origin уже добавлен
				var key = "%d_%d" % [ox + dx, oy + dy]
				obstacles_set[key] = true  # Просто пометка что клетка занята

	# Границы отрисовки уже вычислены в _calculate_tile_size() и включают decoration_margin
	var draw_min_x = board_min_x
	var draw_max_x = board_max_x
	var draw_min_y = board_min_y
	var draw_max_y = board_max_y

	var total_cells_to_draw = (draw_max_x - draw_min_x + 1) * (draw_max_y - draw_min_y + 1)
	_js_log("Drawing cells from (%d,%d) to (%d,%d), game field 0-%d, total cells: %d" % [draw_min_x, draw_min_y, draw_max_x, draw_max_y, field_size - 1, total_cells_to_draw])

	var cells_created = 0
	# Рисуем клетки в правильном порядке (от дальних к ближним для z-order)
	for y in range(draw_min_y, draw_max_y + 1):
		for x in range(draw_min_x, draw_max_x + 1):
			cells_created += 1
			var key = "%d_%d" % [x, y]
			var obstacle_data = obstacles_set.get(key, null)

			# Проверяем находится ли клетка в игровом поле
			var is_game_cell = x >= 0 and x < field_size and y >= 0 and y < field_size

			# Если это origin препятствия (Dictionary) или занятая клетка (true)
			var is_obstacle = obstacle_data != null
			# Рисуем простой камень только если нет спрайта или это не origin
			var draw_simple_rock = false
			if is_obstacle:
				if obstacle_data is Dictionary:
					# Это origin - проверяем есть ли спрайт
					if not obstacle_data.has("sprite_url") or obstacle_data.get("sprite_url", "") == "":
						draw_simple_rock = true
					# else: спрайт будет отрисован отдельно
				else:
					# Это не origin а часть большого препятствия - не рисуем камень
					draw_simple_rock = false

			var cell = _create_iso_tile(x, y, draw_simple_rock, is_game_cell)
			board.add_child(cell)
			cells.append(cell)
			# Логируем позиции угловых клеток
			if (x == draw_min_x and y == draw_min_y) or (x == draw_min_x and y == draw_max_y) or (x == draw_max_x and y == draw_min_y) or (x == draw_max_x and y == draw_max_y):
				var iso_pos = grid_to_iso(x, y)
				_js_log("Corner cell (%d,%d) at iso pos (%d,%d)" % [x, y, int(iso_pos.x), int(iso_pos.y)])
			# Сохраняем в словарь для быстрого доступа (только игровые клетки)
			if is_game_cell:
				var cell_key = "%d_%d" % [x, y]
				cells_by_coords[cell_key] = cell

	_js_log("Created %d cells, cells array size: %d" % [cells_created, cells.size()])
	var scroll_container = board.get_parent()
	_js_log("Board actual size: %s, ScrollContainer size: %s, type: %s" % [str(board.size), str(scroll_container.size), scroll_container.get_class()])

	# Рисуем деревья по границам только если нет декораций из шаблона
	# (шаблоны сами определяют оформление границ)
	if not has_template_decorations:
		_draw_border_trees()

	# Рисуем декорации ПОСЛЕ ячеек чтобы они гарантированно были поверх
	_draw_decorations()

	# Рисуем препятствия со спрайтами поверх клеток
	_draw_obstacle_sprites()

## Рисует деревья по границам поляны
func _draw_border_trees() -> void:
	var tree_size = TILE_WIDTH * 0.8  # Размер дерева

	# Рисуем деревья вокруг поля
	# Верхняя граница (от -1 до field_size)
	for i in range(-1, field_size + 1):
		_create_tree(-1, i, tree_size)
		_create_tree(field_size, i, tree_size)

	# Левая и правая границы
	for i in range(0, field_size):
		_create_tree(i, -1, tree_size)
		_create_tree(i, field_size, tree_size)

## Создаёт одно дерево в изометрической позиции
func _create_tree(grid_x: int, grid_y: int, size: float) -> void:
	var container = Control.new()
	var iso_pos = grid_to_iso(grid_x, grid_y)
	container.position = iso_pos
	container.z_index = 1000 + grid_x + grid_y  # Деревья поверх всего

	var trunk_width = size * 0.15
	var trunk_height = size * 0.4
	var crown_radius = size * 0.4

	# Ствол дерева (прямоугольник)
	var trunk = Polygon2D.new()
	var trunk_x = TILE_WIDTH / 2 - trunk_width / 2
	var trunk_y = TILE_HEIGHT / 2 - trunk_height
	trunk.polygon = PackedVector2Array([
		Vector2(trunk_x, trunk_y + trunk_height),
		Vector2(trunk_x + trunk_width, trunk_y + trunk_height),
		Vector2(trunk_x + trunk_width, trunk_y),
		Vector2(trunk_x, trunk_y)
	])
	trunk.color = COLORS.tree_trunk
	container.add_child(trunk)

	# Крона дерева (несколько кругов/треугольников для объёма)
	var crown_y = trunk_y - crown_radius * 0.5

	# Задняя часть кроны (тёмная)
	var crown_back = Polygon2D.new()
	var back_points: PackedVector2Array = []
	for i in range(12):
		var angle = i * PI * 2 / 12
		var px = TILE_WIDTH / 2 + cos(angle) * crown_radius
		var py = crown_y + sin(angle) * crown_radius * 0.6
		back_points.append(Vector2(px, py))
	crown_back.polygon = back_points
	crown_back.color = COLORS.tree_leaves_dark
	container.add_child(crown_back)

	# Передняя часть кроны (светлая, смещена немного)
	var crown_front = Polygon2D.new()
	var front_points: PackedVector2Array = []
	for i in range(10):
		var angle = i * PI * 2 / 10
		var px = TILE_WIDTH / 2 + cos(angle) * crown_radius * 0.85
		var py = crown_y - crown_radius * 0.15 + sin(angle) * crown_radius * 0.55
		front_points.append(Vector2(px, py))
	crown_front.polygon = front_points
	crown_front.color = COLORS.tree_leaves
	container.add_child(crown_front)

	board.add_child(container)

## Рисует декорации вокруг и на поле
func _draw_decorations() -> void:
	var decorations = GameManager.game_state.get("decorations", [])
	_js_log("_draw_decorations: count=" + str(decorations.size()))
	if decorations.is_empty():
		return

	for dec in decorations:
		# Явное приведение к int (JSON может вернуть float)
		var dec_x: int = int(dec.get("x", 0))
		var dec_y: int = int(dec.get("y", 0))
		var dec_width: int = int(dec.get("width", 1))
		var dec_height: int = int(dec.get("height", 1))
		var dec_type = dec.get("type", "tree")
		var z_index_val: int = int(dec.get("z_index", 0))
		var sprite_url = dec.get("sprite_url", "")

		_js_log("  Decoration: type=" + str(dec_type) + ", pos=(" + str(dec_x) + "," + str(dec_y) + "), sprite=" + str(sprite_url))

		# Позиция декорации в изометрических координатах
		var iso_pos = grid_to_iso(dec_x, dec_y)

		var container = Control.new()
		container.position = iso_pos
		# Размер контейнера зависит от размера декорации
		var dec_pixel_width = dec_width * TILE_WIDTH
		var dec_pixel_height = dec_height * TILE_HEIGHT + TILE_DEPTH
		container.size = Vector2(dec_pixel_width, dec_pixel_height)
		# Z-index для декораций: поверх травы но под юнитами
		# Декорации всегда рисуются над клетками (клетки имеют z_index = x + y)
		# Добавляем 10 чтобы декорации были выше всех клеток
		container.z_index = 10 + dec_x + dec_y + z_index_val

		# Если есть спрайт - загружаем и отображаем
		if sprite_url != "" and sprite_url != null:
			_create_decoration_with_sprite(container, sprite_url, dec_width, dec_height)
		else:
			# Рисуем дефолтную декорацию по типу
			_draw_default_decoration(container, dec_type, dec_width, dec_height)

		board.add_child(container)
		decoration_sprites.append(container)

## Создаёт декорацию со спрайтом
func _create_decoration_with_sprite(container: Control, sprite_url: String, width: int, height: int) -> void:
	# Если текстура уже в кэше - применяем сразу
	if decoration_textures.has(sprite_url):
		var texture_rect = TextureRect.new()
		texture_rect.texture = decoration_textures[sprite_url]
		texture_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		texture_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		texture_rect.size = Vector2(width * TILE_WIDTH, height * TILE_HEIGHT + TILE_DEPTH)
		texture_rect.position = Vector2(0, -TILE_DEPTH)
		container.add_child(texture_rect)
	else:
		# Загружаем текстуру
		_load_decoration_texture(sprite_url, container, width, height)

## Рисует дефолтную декорацию (заглушка если нет спрайта)
func _draw_default_decoration(container: Control, dec_type: String, width: int, height: int) -> void:
	# Простые заглушки для разных типов декораций
	match dec_type:
		"tree":
			_draw_simple_tree(container, width * TILE_WIDTH * 0.6)
		"rock":
			_draw_simple_rock_decoration(container, width * TILE_WIDTH * 0.4)
		"bush":
			_draw_simple_bush(container, width * TILE_WIDTH * 0.5)
		"flower":
			_draw_simple_flower(container, width * TILE_WIDTH * 0.7)
		_:
			# Для неизвестных типов рисуем цветок
			_draw_simple_flower(container, width * TILE_WIDTH * 0.5)

## Рисует простое дерево для декорации
func _draw_simple_tree(container: Control, size: float) -> void:
	var trunk_width = size * 0.15
	var trunk_height = size * 0.4
	var crown_radius = size * 0.35

	# Ствол
	var trunk = Polygon2D.new()
	var trunk_x = TILE_WIDTH / 2 - trunk_width / 2
	var trunk_y = TILE_HEIGHT / 2 - trunk_height
	trunk.polygon = PackedVector2Array([
		Vector2(trunk_x, trunk_y + trunk_height),
		Vector2(trunk_x + trunk_width, trunk_y + trunk_height),
		Vector2(trunk_x + trunk_width, trunk_y),
		Vector2(trunk_x, trunk_y)
	])
	trunk.color = COLORS.tree_trunk
	container.add_child(trunk)

	# Крона
	var crown = Polygon2D.new()
	var crown_points: PackedVector2Array = []
	var crown_y = trunk_y - crown_radius * 0.3
	for i in range(10):
		var angle = i * PI * 2 / 10
		crown_points.append(Vector2(
			TILE_WIDTH / 2 + cos(angle) * crown_radius,
			crown_y + sin(angle) * crown_radius * 0.6
		))
	crown.polygon = crown_points
	crown.color = COLORS.tree_leaves
	container.add_child(crown)

## Рисует простой камень для декорации
func _draw_simple_rock_decoration(container: Control, size: float) -> void:
	var rock = Polygon2D.new()
	var rock_points: PackedVector2Array = []
	for i in range(8):
		var angle = i * PI * 2 / 8
		rock_points.append(Vector2(
			TILE_WIDTH / 2 + cos(angle) * size,
			TILE_HEIGHT / 2 + sin(angle) * size * 0.5
		))
	rock.polygon = rock_points
	rock.color = COLORS.rock_top
	container.add_child(rock)

## Рисует простой куст для декорации
func _draw_simple_bush(container: Control, size: float) -> void:
	var bush = Polygon2D.new()
	var bush_points: PackedVector2Array = []
	for i in range(12):
		var angle = i * PI * 2 / 12
		var radius_mod = 1.0 + 0.2 * sin(angle * 3)  # Волнистый край
		bush_points.append(Vector2(
			TILE_WIDTH / 2 + cos(angle) * size * radius_mod,
			TILE_HEIGHT / 2 + sin(angle) * size * 0.5 * radius_mod
		))
	bush.polygon = bush_points
	bush.color = COLORS.tree_leaves_dark
	container.add_child(bush)

## Рисует простой цветок для декорации
func _draw_simple_flower(container: Control, size: float) -> void:
	var center_x = TILE_WIDTH / 2
	var center_y = TILE_HEIGHT / 2

	# Стебель
	var stem = Polygon2D.new()
	var stem_width = size * 0.08
	var stem_height = size * 0.5
	stem.polygon = PackedVector2Array([
		Vector2(center_x - stem_width / 2, center_y),
		Vector2(center_x + stem_width / 2, center_y),
		Vector2(center_x + stem_width / 2, center_y - stem_height),
		Vector2(center_x - stem_width / 2, center_y - stem_height)
	])
	stem.color = Color(0.2, 0.6, 0.2)  # Зелёный стебель
	container.add_child(stem)

	# Лепестки (5 штук)
	var petal_size = size * 0.2
	var flower_center_y = center_y - stem_height
	for i in range(5):
		var petal = Polygon2D.new()
		var angle = i * PI * 2 / 5 - PI / 2  # Начинаем сверху
		var petal_points: PackedVector2Array = []
		# Овальный лепесток
		for j in range(8):
			var petal_angle = j * PI * 2 / 8
			var px = cos(petal_angle) * petal_size * 0.5
			var py = sin(petal_angle) * petal_size
			# Смещаем лепесток от центра
			var offset_x = cos(angle) * petal_size * 0.7
			var offset_y = sin(angle) * petal_size * 0.5
			petal_points.append(Vector2(
				center_x + offset_x + px * cos(angle) - py * sin(angle),
				flower_center_y + offset_y + px * sin(angle) + py * cos(angle)
			))
		petal.polygon = petal_points
		petal.color = Color(1.0, 0.4, 0.6)  # Розовый лепесток
		container.add_child(petal)

	# Центр цветка
	var center = Polygon2D.new()
	var center_points: PackedVector2Array = []
	for i in range(8):
		var angle = i * PI * 2 / 8
		center_points.append(Vector2(
			center_x + cos(angle) * petal_size * 0.3,
			flower_center_y + sin(angle) * petal_size * 0.2
		))
	center.polygon = center_points
	center.color = Color(1.0, 0.9, 0.2)  # Жёлтый центр
	container.add_child(center)

## Рисует препятствия со спрайтами
func _draw_obstacle_sprites() -> void:
	var obstacles = GameManager.game_state.get("obstacles", [])

	for obstacle in obstacles:
		var sprite_url = obstacle.get("sprite_url", "")
		if sprite_url == "" or sprite_url == null:
			continue  # Нет спрайта - уже отрисован простой камень

		var ox = obstacle.get("x", 0)
		var oy = obstacle.get("y", 0)
		var ow = obstacle.get("width", 1)
		var oh = obstacle.get("height", 1)

		# Для изометрии препятствие начинается в (ox, oy) и растёт вправо-вниз
		# Позиция контейнера в верхней точке ромба (ox, oy)
		var iso_pos = grid_to_iso(ox, oy)

		_js_log("Obstacle sprite: grid(%d,%d) size=%dx%d, iso_pos=(%d,%d)" % [ox, oy, ow, oh, int(iso_pos.x), int(iso_pos.y)])

		var container = Control.new()
		container.position = iso_pos

		# Z-index: препятствия над клетками но под юнитами
		# Используем правый нижний угол для z-order
		container.z_index = ox + oy + ow + oh + 50

		# Загружаем спрайт
		if decoration_textures.has(sprite_url):
			_apply_obstacle_sprite(container, sprite_url, ow, oh)
		else:
			_load_obstacle_sprite(sprite_url, container, ow, oh)

		board.add_child(container)
		obstacle_sprite_containers.append(container)

## Применяет текстуру препятствия к контейнеру
## width, height - размер препятствия в grid клетках
## container.position - изометрическая позиция верхнего левого угла (grid origin)
func _apply_obstacle_sprite(container: Control, sprite_url: String, width: int, height: int) -> void:
	if not decoration_textures.has(sprite_url):
		return

	var texture = decoration_textures[sprite_url]
	var texture_rect = TextureRect.new()
	texture_rect.texture = texture
	texture_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	# Используем STRETCH_KEEP_ASPECT чтобы спрайт вписывался в область
	# сохраняя пропорции и не вылезая за границы
	texture_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED

	# Для препятствия WxH клеток изометрический ромб имеет:
	# Ширина: (W + H) * TILE_WIDTH / 2  (от левой до правой вершины)
	# Высота: (W + H) * TILE_HEIGHT / 2 (от верхней до нижней вершины)
	#
	# Относительно container (grid_to_iso(ox, oy)):
	# - Верхняя вершина: (TILE_WIDTH/2, 0)
	# - Левая вершина: (-(H-1) * TILE_WIDTH/2, (H-1) * TILE_HEIGHT/2)
	# - Правая вершина: (TILE_WIDTH + (W-1) * TILE_WIDTH/2, (W-1) * TILE_HEIGHT/2)
	# - Нижняя вершина: (TILE_WIDTH/2 + (W-H) * TILE_WIDTH/4, (W+H-1) * TILE_HEIGHT/2)

	var rhombus_width = (width + height) * TILE_WIDTH / 2.0
	var rhombus_height = (width + height) * TILE_HEIGHT / 2.0

	# Получаем размеры оригинальной текстуры
	var tex_width = float(texture.get_width())
	var tex_height = float(texture.get_height())

	# Вычисляем масштаб чтобы спрайт вписался в ромб не выходя за границы
	var scale_x = rhombus_width / tex_width
	var scale_y = rhombus_height / tex_height
	# Берём меньший масштаб чтобы спрайт не вылезал за границы ромба
	var scale_factor = minf(scale_x, scale_y)

	var sprite_width = tex_width * scale_factor
	var sprite_height = tex_height * scale_factor

	texture_rect.size = Vector2(sprite_width, sprite_height)

	# Центрируем спрайт относительно центра изометрического ромба
	# Центр ромба относительно container:
	# center_x = TILE_WIDTH/2 + (W-1-H+1) * TILE_WIDTH/4 = TILE_WIDTH/2 + (W-H) * TILE_WIDTH/4
	# center_y = (W + H - 1) * TILE_HEIGHT / 4
	# Но для квадратного препятствия (W=H): center_x = TILE_WIDTH/2, center_y = (2W-1) * TILE_HEIGHT/4

	var rhombus_center_x = TILE_WIDTH / 2.0 + (width - height) * TILE_WIDTH / 4.0
	var rhombus_center_y = (width + height - 1) * TILE_HEIGHT / 4.0

	var offset_x = rhombus_center_x - sprite_width / 2.0
	var offset_y = rhombus_center_y - sprite_height / 2.0

	texture_rect.position = Vector2(offset_x, offset_y)

	_js_log("Obstacle sprite applied: tex=(%d,%d), rhombus=(%d,%d), sprite=(%d,%d), offset=(%d,%d)" % [
		int(tex_width), int(tex_height),
		int(rhombus_width), int(rhombus_height),
		int(sprite_width), int(sprite_height),
		int(offset_x), int(offset_y)
	])
	container.add_child(texture_rect)

## Загружает текстуру для декорации
func _load_decoration_texture(sprite_url: String, container: Control, width: int, height: int) -> void:
	if pending_sprite_loads.has(sprite_url):
		return
	pending_sprite_loads[sprite_url] = true

	var url = base_url + sprite_url
	_js_log("Loading decoration sprite: " + url)

	var http = HTTPRequest.new()
	http.use_threads = false
	add_child(http)
	http.request_completed.connect(_on_decoration_texture_loaded.bind(sprite_url, container, width, height, http, false))

	var headers: PackedStringArray = []
	if ApiClient.auth_token != "":
		headers.append("Authorization: Bearer " + ApiClient.auth_token)

	var err = http.request(url, headers)
	if err != OK:
		pending_sprite_loads.erase(sprite_url)
		http.queue_free()

## Загружает текстуру для препятствия
func _load_obstacle_sprite(sprite_url: String, container: Control, width: int, height: int) -> void:
	if pending_sprite_loads.has(sprite_url):
		return
	pending_sprite_loads[sprite_url] = true

	var url = base_url + sprite_url
	_js_log("Loading obstacle sprite: " + url)

	var http = HTTPRequest.new()
	http.use_threads = false
	add_child(http)
	http.request_completed.connect(_on_decoration_texture_loaded.bind(sprite_url, container, width, height, http, true))

	var headers: PackedStringArray = []
	if ApiClient.auth_token != "":
		headers.append("Authorization: Bearer " + ApiClient.auth_token)

	var err = http.request(url, headers)
	if err != OK:
		pending_sprite_loads.erase(sprite_url)
		http.queue_free()

## Обработчик загрузки текстуры декорации/препятствия
func _on_decoration_texture_loaded(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray, sprite_url: String, container: Control, width: int, height: int, http_node: HTTPRequest, is_obstacle: bool) -> void:
	http_node.queue_free()
	pending_sprite_loads.erase(sprite_url)

	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200 or body.size() == 0:
		_js_log("Decoration/obstacle sprite load failed: " + sprite_url + " code=" + str(response_code))
		return

	var image = Image.new()
	var error = ERR_FILE_UNRECOGNIZED

	# Определяем формат по сигнатуре
	if body.size() >= 4:
		var header = body.slice(0, 4)
		if header[0] == 0x89 and header[1] == 0x50 and header[2] == 0x4E and header[3] == 0x47:
			error = image.load_png_from_buffer(body)
		elif header[0] == 0xFF and header[1] == 0xD8:
			error = image.load_jpg_from_buffer(body)
		elif header[0] == 0x52 and header[1] == 0x49 and header[2] == 0x46 and header[3] == 0x46:
			error = image.load_webp_from_buffer(body)

	# Fallback
	if error != OK:
		error = image.load_png_from_buffer(body)
	if error != OK:
		error = image.load_jpg_from_buffer(body)
	if error != OK:
		error = image.load_webp_from_buffer(body)

	if error != OK:
		_js_log("Failed to decode decoration/obstacle image: " + sprite_url)
		return

	var texture = ImageTexture.create_from_image(image)
	decoration_textures[sprite_url] = texture

	# Применяем текстуру к контейнеру если он ещё валиден
	if is_instance_valid(container):
		if is_obstacle:
			_apply_obstacle_sprite(container, sprite_url, width, height)
		else:
			var texture_rect = TextureRect.new()
			texture_rect.texture = texture
			texture_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
			texture_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
			texture_rect.size = Vector2(width * TILE_WIDTH, height * TILE_HEIGHT + TILE_DEPTH)
			texture_rect.position = Vector2(0, -TILE_DEPTH)
			container.add_child(texture_rect)

	_js_log("Decoration/obstacle sprite loaded: " + sprite_url)

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

			# Обновляем счётчик юнитов и HP
			_update_unit_count(unit_id, unit.get("count", 0), unit)

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

## Обновляет счётчик юнитов и HP в существующем спрайте
func _update_unit_count(unit_id: int, count: int, unit: Dictionary = {}) -> void:
	if not unit_sprites.has(unit_id):
		return

	var unit_control = unit_sprites[unit_id]
	var count_label = unit_control.get_node_or_null("CountLabel")
	if count_label and count_label is Label:
		count_label.text = str(count)

	# Обновляем HP метку
	var hp_label = unit_control.get_node_or_null("HPLabel")
	if hp_label and hp_label is Label and not unit.is_empty():
		var unit_type = unit.get("unit_type", {})
		var hp_per_unit = unit_type.get("hp", 0)
		var remaining_hp = unit.get("remaining_hp", hp_per_unit)
		var total_hp = (count - 1) * hp_per_unit + remaining_hp if count > 0 else 0
		hp_label.text = str(total_hp)

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

	# Количество юнитов и HP - бейдж в углу (масштабируем размер)
	var badge_scale = float(TILE_WIDTH) / float(BASE_TILE_WIDTH)
	var badge_width = int(28 * badge_scale)
	var badge_height = int(20 * badge_scale)

	# Количество юнитов
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

	# Суммарный HP над количеством
	var count = unit.get("count", 0)
	var hp_per_unit = unit_type.get("hp", 0)
	var remaining_hp = unit.get("remaining_hp", hp_per_unit)
	var total_hp = (count - 1) * hp_per_unit + remaining_hp if count > 0 else 0

	var hp_label = Label.new()
	hp_label.name = "HPLabel"
	hp_label.text = str(total_hp)
	hp_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hp_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	hp_label.size = Vector2(badge_width + 10, badge_height)
	hp_label.position = Vector2(TILE_WIDTH - badge_width - 7, TILE_HEIGHT - 4 - badge_height - 2)
	hp_label.add_theme_font_size_override("font_size", int(12 * badge_scale))
	hp_label.add_theme_color_override("font_color", Color(0.5, 1.0, 0.5))  # Зеленоватый цвет для HP
	hp_label.add_theme_constant_override("outline_size", 2)
	hp_label.add_theme_color_override("font_outline_color", Color.BLACK)
	hp_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	container.add_child(hp_label)

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
		# Учитываем что контейнер смещён вверх на vertical_offset, поэтому центр выделения
		# должен быть на уровне TILE_HEIGHT + vertical_offset (возвращаем выделение на уровень тайла)
		var sel_center_y = TILE_HEIGHT + vertical_offset + int(12 * badge_scale)
		for i in range(16):
			var angle = i * PI * 2 / 16
			sel_points.append(Vector2(
				TILE_WIDTH / 2 + cos(angle) * sel_radius,
				sel_center_y + sin(angle) * sel_radius * 0.5
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

		# Если клик на своего юнита, который не атакуется и не является целью перемещения - переключаемся на него
		if unit.get("player_id") == GameManager.current_player_id:
			RemoteLogger.info("Switching to another unit", {"unit_id": unit_id})
			_clear_highlights()
			action_mode = ""
			GameManager.select_unit(unit)
			return

		# Клик не привёл к действию - игнорируем
		RemoteLogger.debug("Click on unit didn't result in action, ignoring")

## Формирует строку с информацией о юните (HP и эффекты)
func _get_unit_info_string(unit: Dictionary) -> String:
	var unit_type = unit.get("unit_type", {})
	var name = unit_type.get("name", "Юнит")
	var count = unit.get("count", 0)
	var hp_per_unit = unit_type.get("hp", 0)
	var remaining_hp = unit.get("remaining_hp", hp_per_unit)

	# Общий HP = (count - 1) * hp_per_unit + remaining_hp
	var total_hp = (count - 1) * hp_per_unit + remaining_hp if count > 0 else 0

	var info = "%s x%d | HP: %d" % [name, count, total_hp]

	# Эффекты
	var effects: Array = []

	# Регенерация (из unit_type)
	var regen = unit_type.get("regeneration_health", 0)
	if regen > 0:
		effects.append("Регенерация: +%d HP/ход" % regen)

	# Отравление (на самом юните)
	var poison_turns = unit.get("poison_remaining_turns", 0)
	var poison_damage = unit.get("poison_damage_per_turn", 0)
	if poison_turns > 0 and poison_damage > 0:
		effects.append("Яд: %d урона, %d ход(а/ов)" % [poison_damage, poison_turns])

	# Способности юнита
	var poison_ability_dmg = unit_type.get("poison_damage", 0)
	var poison_ability_turns = unit_type.get("poison_turns", 0)
	if poison_ability_dmg > 0 and poison_ability_turns > 0:
		effects.append("Отравляет: %d урона, %d ход(а/ов)" % [poison_ability_dmg, poison_ability_turns])

	var poison_immunity = unit_type.get("poison_immunity", false)
	if poison_immunity:
		effects.append("Иммунитет к яду")

	if not effects.is_empty():
		info += " | " + " | ".join(effects)

	return info

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

	# Формируем информацию о выбранном юните
	var unit_info = _get_unit_info_string(GameManager.selected_unit)

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
		hint_label.text = unit_info + "\nВыберите клетку для перемещения или атаки"
	elif can_attack:
		action_mode = "attack"
		_set_selected_unit_clickable(false)  # Отключаем клики на выбранном юните
		_highlight_attacks()
		hint_label.text = unit_info + "\nВыберите цель для атаки"
	else:
		hint_label.text = unit_info + "\nНет доступных действий. Пропустите ход."

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
		var cell_key = "%d_%d" % [x, y]
		if cells_by_coords.has(cell_key):
			var highlight = _create_iso_highlight(COLORS.move_highlight, x, y, "move")
			cells_by_coords[cell_key].add_child(highlight)

func _highlight_attacks() -> void:
	_clear_highlights()
	for target in GameManager.current_actions.get("can_attack", []):
		var x = target.get("x", 0)
		var y = target.get("y", 0)
		var cell_key = "%d_%d" % [x, y]
		if cells_by_coords.has(cell_key):
			var highlight = _create_iso_highlight(COLORS.attack_highlight, x, y, "attack")
			cells_by_coords[cell_key].add_child(highlight)

## Подсветка атаки без очистки существующей подсветки (для комбинированного отображения)
func _highlight_attacks_additional() -> void:
	for target in GameManager.current_actions.get("can_attack", []):
		var x = target.get("x", 0)
		var y = target.get("y", 0)
		var cell_key = "%d_%d" % [x, y]
		if cells_by_coords.has(cell_key):
			var highlight = _create_iso_highlight(COLORS.attack_highlight, x, y, "attack")
			cells_by_coords[cell_key].add_child(highlight)

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
			"poison":
				label.add_theme_color_override("font_color", Color(0.6, 0.2, 0.8))  # Фиолетовый
			"regeneration":
				label.add_theme_color_override("font_color", Color(0.2, 0.8, 0.4))  # Зелёный
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

func _on_game_draw() -> void:
	# Устанавливаем флаг чтобы предотвратить обновления
	is_game_over_displayed = true

	# Очищаем поле боя
	_clear_board()

	game_over_overlay.visible = true

	var title = game_over_overlay.get_node("VBox/Title")
	var message = game_over_overlay.get_node("VBox/Message")

	title.text = "НИЧЬЯ!"
	title.add_theme_color_override("font_color", Color.GRAY)
	message.text = "5 ходов без урона. Награды не начисляются."

func _on_draw_warning(turns_without_damage: int, turns_until_draw: int) -> void:
	# Показываем предупреждение о приближающейся ничьей
	hint_label.text = "⚠️ %d ходов без урона! Ещё %d и ничья!" % [turns_without_damage, turns_until_draw]
	hint_label.add_theme_color_override("font_color", Color.ORANGE)

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

# ============= Challenge (PvE) AI =============
var ai_turn_requested: bool = false  # Флаг чтобы не запрашивать AI ход повторно
var ai_turn_timer: Timer = null  # Таймер для задержки хода AI

## Запрашивает ход AI для челленджа
func _request_ai_turn() -> void:
	# Не запрашиваем если уже запрошен или это не челлендж
	if ai_turn_requested or not GameManager.is_challenge_game:
		return

	ai_turn_requested = true
	hint_label.text = "AI думает..."

	# Небольшая задержка перед ходом AI для наглядности
	if ai_turn_timer == null:
		ai_turn_timer = Timer.new()
		ai_turn_timer.one_shot = true
		ai_turn_timer.timeout.connect(_execute_ai_turn)
		add_child(ai_turn_timer)

	ai_turn_timer.start(0.8)  # 0.8 секунды задержка

## Выполняет ход AI
func _execute_ai_turn() -> void:
	_js_log("Executing AI turn for game " + str(GameManager.current_game_id))
	ApiClient.execute_ai_turn(GameManager.current_game_id)
	# Сбрасываем флаг после небольшой задержки чтобы дать время на обновление состояния
	await get_tree().create_timer(1.0).timeout
	ai_turn_requested = false
