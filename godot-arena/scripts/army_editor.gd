extends Control
## Редактор армий - создание армий, найм и роспуск юнитов
## Объединённый интерфейс: спрайт юнита справа, найм/роспуск слева

@onready var back_button: Button = %BackButton
@onready var create_army_button: Button = %CreateArmyButton
@onready var armies_list: VBoxContainer = %ArmiesList
@onready var army_name_label: Label = %ArmyNameLabel
@onready var delete_army_button: Button = %DeleteArmyButton
@onready var balance_label: Label = %BalanceLabel
@onready var units_list: VBoxContainer = %UnitsList
@onready var status_label: Label = %StatusLabel

# Размер спрайта вычисляется динамически (половина ширины экрана)
var sprite_size: int = 128

# Состояние
var armies: Array = []
var selected_army_id: int = 0
var selected_army: Dictionary = {}
var available_units: Array = []
var player_balance: float = 0.0
var player_crystals: int = 0
var army_type: String = "mercenary"  # rated или mercenary
var is_in_battle: bool = false  # Армия в бою - нельзя редактировать

# Данные для создания армии
var user_races: Array = []
var create_dialog: Window = null

# Диалог количества для найма
var hire_dialog: Window = null
var hire_race_unit_id: int = 0
var hire_max_available: int = 0
var hire_unit_cost: int = 0

# Кэш спрайтов
var sprite_sheets: Dictionary = {}  # url -> { texture, params }
var pending_sprite_loads: Dictionary = {}  # url -> true
var base_url: String = ""

# Ожидание ответов
enum RequestType { NONE, GET_ARMIES, CREATE_ARMY, DELETE_ARMY, GET_AVAILABLE_UNITS, HIRE_UNIT, DISMISS_UNIT, UNLOCK_LEVEL, GET_USER_RACES }
var pending_request: RequestType = RequestType.NONE

func _ready() -> void:
	# Вычисляем размер спрайта - половина высоты экрана
	sprite_size = int(get_viewport().get_visible_rect().size.y / 2)

	# Получаем базовый URL (origin) для загрузки спрайтов
	if OS.has_feature("web"):
		var js_code = """
			(function() {
				return window.location.origin;
			})()
		"""
		var result = JavaScriptBridge.eval(js_code)
		if result:
			base_url = result
	else:
		base_url = ""

	# Подключаем сигналы UI
	back_button.pressed.connect(_on_back_pressed)
	create_army_button.pressed.connect(_on_create_army_pressed)
	delete_army_button.pressed.connect(_on_delete_army_pressed)

	# Подключаем сигналы API
	ApiClient.request_completed.connect(_on_api_response)
	ApiClient.request_failed.connect(_on_api_error)
	ApiClient.auth_required.connect(_on_auth_required)

	# Загружаем армии
	_load_armies()

func _load_armies() -> void:
	status_label.text = "Загрузка армий..."
	pending_request = RequestType.GET_ARMIES
	ApiClient.get_armies()

func _on_api_response(data: Dictionary) -> void:
	var current_request = pending_request
	pending_request = RequestType.NONE  # Сбрасываем сразу, чтобы можно было начать новый запрос

	match current_request:
		RequestType.GET_ARMIES:
			_handle_armies_response(data)
		RequestType.CREATE_ARMY:
			_handle_create_army_response(data)
		RequestType.DELETE_ARMY:
			_handle_delete_army_response(data)
		RequestType.GET_AVAILABLE_UNITS:
			_handle_available_units_response(data)
		RequestType.HIRE_UNIT:
			_handle_hire_response(data)
		RequestType.DISMISS_UNIT:
			_handle_dismiss_response(data)
		RequestType.UNLOCK_LEVEL:
			_handle_unlock_response(data)
		RequestType.GET_USER_RACES:
			_handle_user_races_response(data)

func _handle_armies_response(data: Dictionary) -> void:
	armies = data.get("armies", [])
	status_label.text = ""
	_display_armies_list()

	# Если была выбрана армия - обновляем её данные
	if selected_army_id > 0:
		for army in armies:
			if army.get("army_id") == selected_army_id:
				selected_army = army
				_display_selected_army()
				break

func _handle_create_army_response(data: Dictionary) -> void:
	if data.get("success", false):
		status_label.text = "Армия создана!"
		selected_army_id = data.get("army_id", 0)
		_load_armies()
	else:
		status_label.text = "Ошибка создания армии"

func _handle_delete_army_response(data: Dictionary) -> void:
	if data.get("success", false):
		status_label.text = "Армия удалена"
		selected_army_id = 0
		selected_army = {}
		_load_armies()
		_clear_selected_army()
	else:
		status_label.text = "Ошибка удаления армии"

func _handle_available_units_response(data: Dictionary) -> void:
	available_units = data.get("units", [])
	player_balance = data.get("player_balance", 0.0)
	player_crystals = data.get("player_crystals", 0)
	army_type = data.get("army_type", "mercenary")
	is_in_battle = data.get("is_in_battle", false)

	# Обновляем метку баланса с кристаллами
	balance_label.text = "Баланс: $%.0f | Кристаллы: %d" % [player_balance, player_crystals]
	_display_units_list()

	# После обновления доступных юнитов обновляем список армий
	_load_armies()

func _handle_hire_response(data: Dictionary) -> void:
	if data.get("success", false):
		player_balance = data.get("new_balance", player_balance)
		var available_remaining = data.get("available_remaining", 0)
		status_label.text = "Юнит нанят! Стоимость: $%.0f (осталось: %d)" % [data.get("total_cost", 0), available_remaining]
		balance_label.text = "Баланс: $%.0f | Кристаллы: %d" % [player_balance, player_crystals]
		# Сначала обновляем доступных юнитов, потом армии
		if selected_army_id > 0:
			pending_request = RequestType.GET_AVAILABLE_UNITS
			ApiClient.get_available_units(selected_army_id)
		else:
			_load_armies()
	else:
		status_label.text = data.get("error", "Ошибка найма")

func _handle_dismiss_response(data: Dictionary) -> void:
	if data.get("success", false):
		player_balance = data.get("new_balance", player_balance)
		balance_label.text = "Баланс: $%.0f | Кристаллы: %d" % [player_balance, player_crystals]
		status_label.text = "Юнит распущен. Возврат: $%.0f" % data.get("refund", 0)
		# Сначала обновляем доступных юнитов, потом армии
		if selected_army_id > 0:
			pending_request = RequestType.GET_AVAILABLE_UNITS
			ApiClient.get_available_units(selected_army_id)
		else:
			_load_armies()
	else:
		status_label.text = data.get("error", "Ошибка роспуска")

func _handle_unlock_response(data: Dictionary) -> void:
	if data.get("success", false):
		player_crystals = data.get("new_crystals", player_crystals)
		var level = data.get("level", 0)
		status_label.text = "Уровень %d разблокирован!" % level
		balance_label.text = "Баланс: $%.0f | Кристаллы: %d" % [player_balance, player_crystals]
		# Перезагружаем доступных юнитов
		if selected_army_id > 0:
			pending_request = RequestType.GET_AVAILABLE_UNITS
			ApiClient.get_available_units(selected_army_id)
	else:
		status_label.text = data.get("error", "Ошибка разблокировки")

func _on_api_error(error: String) -> void:
	status_label.text = "Ошибка: " + error
	pending_request = RequestType.NONE

func _on_auth_required() -> void:
	# Возврат к логину
	get_tree().change_scene_to_file("res://scenes/main.tscn")

func _display_armies_list() -> void:
	# Очищаем список
	for child in armies_list.get_children():
		child.queue_free()

	if armies.is_empty():
		var label = Label.new()
		label.text = "Нет армий. Создайте первую!"
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		armies_list.add_child(label)
		return

	for army in armies:
		var btn = Button.new()
		var army_id = army.get("army_id", 0)
		var army_name = army.get("army_name", "Армия")
		var army_cost = army.get("army_cost", 0)
		var units_count = army.get("units", []).size()
		var current_army_type = army.get("army_type", "mercenary")
		var type_label = "[Р]" if current_army_type == "rated" else "[Н]"
		var in_battle_label = " [БОЙ]" if army.get("is_in_battle", false) else ""

		btn.text = "%s %s%s\n$%.0f | %d юн." % [type_label, army_name, in_battle_label, army_cost, units_count]
		btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		btn.custom_minimum_size = Vector2(0, 60)

		if army_id == selected_army_id:
			btn.modulate = Color(0.5, 0.8, 0.5)
		elif army.get("is_in_battle", false):
			btn.modulate = Color(0.8, 0.6, 0.6)

		btn.pressed.connect(_on_army_selected.bind(army_id))
		armies_list.add_child(btn)

func _on_army_selected(army_id: int) -> void:
	selected_army_id = army_id

	# Находим армию в списке
	for army in armies:
		if army.get("army_id") == army_id:
			selected_army = army
			break

	_display_armies_list()  # Обновляем подсветку
	_display_selected_army()

	# Загружаем доступных юнитов
	pending_request = RequestType.GET_AVAILABLE_UNITS
	ApiClient.get_available_units(army_id)

func _display_selected_army() -> void:
	if selected_army.is_empty():
		_clear_selected_army()
		return

	# Проверяем, в бою ли армия (берём из списка armies)
	var army_in_battle = selected_army.get("is_in_battle", false)

	var army_name = selected_army.get("army_name", "Армия")
	if army_in_battle:
		army_name_label.text = army_name + " [В БОЮ]"
	else:
		army_name_label.text = army_name

	# Нельзя удалять армию в бою
	delete_army_button.visible = not army_in_battle

func _clear_selected_army() -> void:
	army_name_label.text = "Выберите армию"
	delete_army_button.visible = false

	for child in units_list.get_children():
		child.queue_free()

## Отображает объединённый список юнитов
func _display_units_list() -> void:
	for child in units_list.get_children():
		child.queue_free()

	# Если армия в бою - показываем предупреждение
	if is_in_battle:
		var warning_label = Label.new()
		warning_label.text = "АРМИЯ В БОЮ!\nНельзя нанимать или распускать юнитов"
		warning_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		warning_label.add_theme_color_override("font_color", Color(0.9, 0.3, 0.3))
		warning_label.add_theme_font_size_override("font_size", 18)
		units_list.add_child(warning_label)

	if available_units.is_empty():
		var label = Label.new()
		label.text = "Нет доступных юнитов"
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		units_list.add_child(label)
		return

	# Сортируем юнитов по уровню
	var sorted_units = available_units.duplicate()
	sorted_units.sort_custom(func(a, b): return a.get("level", 1) < b.get("level", 1))

	for unit in sorted_units:
		var current_count = unit.get("current_count", 0)
		var level_unlocked = unit.get("level_unlocked", true)
		var available_to_hire = unit.get("available_to_hire", 0)
		var is_rated = army_type == "rated"

		# Показываем юнита только если:
		# 1. Есть в армии (current_count > 0)
		# 2. Можно нанять (level_unlocked и available_to_hire > 0) или рейтинговая армия
		# НЕ показываем заблокированные уровни
		var should_show = current_count > 0 or (level_unlocked and available_to_hire > 0) or is_rated

		if should_show:
			var unit_card = _create_unit_card(unit)
			units_list.add_child(unit_card)

## Создаёт карточку юнита с объединённым интерфейсом
func _create_unit_card(unit: Dictionary) -> Control:
	var card = PanelContainer.new()
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	card.custom_minimum_size = Vector2(0, sprite_size + 20)

	var main_hbox = HBoxContainer.new()
	main_hbox.add_theme_constant_override("separation", 10)
	card.add_child(main_hbox)

	# === Левая часть: информация и кнопки ===
	var left_vbox = VBoxContainer.new()
	left_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	left_vbox.add_theme_constant_override("separation", 3)
	main_hbox.add_child(left_vbox)

	var current_count = unit.get("current_count", 0)
	var level = unit.get("level", 1)
	var level_unlocked = unit.get("level_unlocked", true)
	var available_to_hire = unit.get("available_to_hire", 999)
	var can_hire = unit.get("can_hire", false)
	var unlock_cost = unit.get("unlock_cost_gems", 0)
	var is_rated = army_type == "rated"
	var unit_hire_cost = unit.get("hire_cost", 0)
	var race_unit_id = unit.get("race_unit_id", 0)

	# Название юнита с уровнем и количеством в армии
	var name_hbox = HBoxContainer.new()
	name_hbox.add_theme_constant_override("separation", 5)
	left_vbox.add_child(name_hbox)

	var level_label = Label.new()
	level_label.text = "[%d]" % level
	level_label.add_theme_font_size_override("font_size", 16)
	level_label.add_theme_color_override("font_color", _get_level_color(level))
	name_hbox.add_child(level_label)

	var name_label = Label.new()
	name_label.text = unit.get("name", "Юнит")
	name_label.add_theme_font_size_override("font_size", 18)
	name_hbox.add_child(name_label)

	# Количество в армии (если есть)
	if current_count > 0:
		var count_label = Label.new()
		count_label.text = "x%d" % current_count
		count_label.add_theme_font_size_override("font_size", 18)
		count_label.add_theme_color_override("font_color", Color(0.4, 0.9, 0.4))
		name_hbox.add_child(count_label)

	# Статы юнита
	var stats_label = Label.new()
	stats_label.text = "A:%d D:%d H:%d S:%d | $%d" % [
		unit.get("attack", 0),
		unit.get("defense", 0),
		unit.get("health", 0),
		unit.get("speed", 0),
		unit_hire_cost
	]
	stats_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	stats_label.add_theme_font_size_override("font_size", 13)
	left_vbox.add_child(stats_label)

	# Кнопки действий
	var buttons_hbox = HBoxContainer.new()
	buttons_hbox.add_theme_constant_override("separation", 5)
	left_vbox.add_child(buttons_hbox)

	# Логика отображения кнопок
	if not level_unlocked and not is_rated:
		# Уровень заблокирован - показываем кнопку разблокировки
		var unlock_btn = Button.new()
		unlock_btn.text = "Разблокировать (%d крист.)" % unlock_cost
		unlock_btn.disabled = player_crystals < unlock_cost or is_in_battle
		if player_crystals < unlock_cost:
			unlock_btn.tooltip_text = "Недостаточно кристаллов"
		unlock_btn.pressed.connect(_on_unlock_level.bind(level))
		buttons_hbox.add_child(unlock_btn)

		var lock_label = Label.new()
		lock_label.text = "ЗАБЛОКИРОВАНО"
		lock_label.add_theme_color_override("font_color", Color(0.8, 0.3, 0.3))
		lock_label.add_theme_font_size_override("font_size", 12)
		buttons_hbox.add_child(lock_label)
	else:
		# Уровень разблокирован
		# Кнопка найма
		var hire_btn = Button.new()
		if is_rated:
			hire_btn.text = "Нанять"
		else:
			hire_btn.text = "Нанять (%d)" % available_to_hire
		hire_btn.disabled = not can_hire or is_in_battle
		if is_in_battle:
			hire_btn.tooltip_text = "Армия в бою"
		elif not can_hire:
			if available_to_hire <= 0 and not is_rated:
				hire_btn.tooltip_text = "Нет доступных юнитов"
			else:
				hire_btn.tooltip_text = "Недостаточно средств"
		hire_btn.pressed.connect(_on_hire_unit.bind(race_unit_id, available_to_hire, unit_hire_cost))
		buttons_hbox.add_child(hire_btn)

		# Кнопка роспуска (если есть юниты в армии)
		if current_count > 0:
			var dismiss_btn = Button.new()
			dismiss_btn.text = "Распустить"
			dismiss_btn.disabled = is_in_battle
			if is_in_battle:
				dismiss_btn.tooltip_text = "Армия в бою"
			dismiss_btn.pressed.connect(_on_dismiss_unit.bind(race_unit_id))
			buttons_hbox.add_child(dismiss_btn)

	# === Правая часть: анимированный спрайт ===
	var sprite_container = Control.new()
	sprite_container.custom_minimum_size = Vector2(sprite_size, sprite_size)
	main_hbox.add_child(sprite_container)

	# Загружаем и отображаем спрайт
	var sprite_url = unit.get("sprite_url", "")
	var sprite_params = unit.get("sprite_params", null)
	var image_url = unit.get("image_url", "")

	if sprite_url != "" and sprite_params != null:
		# Анимированный спрайт
		if sprite_sheets.has(sprite_url):
			_apply_sprite_to_container(sprite_container, sprite_url)
		else:
			_load_sprite_sheet(sprite_url, sprite_params, sprite_container)
	elif image_url != "":
		# Статическое изображение
		if sprite_sheets.has(image_url):
			_apply_static_image_to_container(sprite_container, image_url)
		else:
			_load_static_image(image_url, sprite_container)
	else:
		# Иконка-заглушка
		var icon_label = Label.new()
		icon_label.text = "?"
		icon_label.add_theme_font_size_override("font_size", 32)
		icon_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		icon_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		icon_label.set_anchors_preset(Control.PRESET_FULL_RECT)
		sprite_container.add_child(icon_label)

	return card

## Возвращает цвет для уровня юнита
func _get_level_color(level: int) -> Color:
	match level:
		1: return Color(0.7, 0.7, 0.7)  # Серый
		2: return Color(0.5, 0.8, 0.5)  # Зелёный
		3: return Color(0.5, 0.5, 0.9)  # Синий
		4: return Color(0.8, 0.5, 0.8)  # Фиолетовый
		5: return Color(0.9, 0.7, 0.3)  # Золотой
		_: return Color(0.9, 0.3, 0.3)  # Красный для высоких уровней

## Загружает спрайт-лист через HTTP
func _load_sprite_sheet(sprite_url: String, sprite_params: Variant, container: Control) -> void:
	if pending_sprite_loads.has(sprite_url):
		return
	pending_sprite_loads[sprite_url] = true

	var url = base_url + sprite_url
	print("Loading sprite: ", url)

	var http = HTTPRequest.new()
	http.use_threads = false
	add_child(http)
	http.request_completed.connect(_on_sprite_sheet_loaded.bind(sprite_url, sprite_params, container, http))

	var headers: PackedStringArray = []
	if ApiClient.auth_token != "":
		headers.append("Authorization: Bearer " + ApiClient.auth_token)

	var err = http.request(url, headers)
	if err != OK:
		pending_sprite_loads.erase(sprite_url)
		http.queue_free()

func _on_sprite_sheet_loaded(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray, sprite_url: String, sprite_params: Variant, container: Control, http_node: HTTPRequest) -> void:
	http_node.queue_free()
	pending_sprite_loads.erase(sprite_url)

	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200 or body.size() == 0:
		print("Sprite load failed: ", sprite_url, " result=", result, " code=", response_code, " size=", body.size())
		return

	var image = Image.new()
	var error = ERR_FILE_UNRECOGNIZED

	if body.size() >= 4:
		var header = body.slice(0, 4)
		if header[0] == 0x52 and header[1] == 0x49 and header[2] == 0x46 and header[3] == 0x46:
			error = image.load_webp_from_buffer(body)
		elif header[0] == 0x89 and header[1] == 0x50 and header[2] == 0x4E and header[3] == 0x47:
			error = image.load_png_from_buffer(body)
		elif header[0] == 0xFF and header[1] == 0xD8:
			error = image.load_jpg_from_buffer(body)

	if error != OK:
		error = image.load_png_from_buffer(body)
	if error != OK:
		error = image.load_jpg_from_buffer(body)
	if error != OK:
		error = image.load_webp_from_buffer(body)

	if error != OK:
		return

	var texture = ImageTexture.create_from_image(image)

	sprite_sheets[sprite_url] = {
		"texture": texture,
		"params": sprite_params if sprite_params else {"frame_count": 1, "fps": 10, "columns": 1, "rows": 1}
	}

	if is_instance_valid(container):
		_apply_sprite_to_container(container, sprite_url)

## Применяет анимированный спрайт к контейнеру
func _apply_sprite_to_container(container: Control, sprite_url: String) -> void:
	if not sprite_sheets.has(sprite_url):
		return

	# Очищаем контейнер
	for child in container.get_children():
		child.queue_free()

	var sprite_data = sprite_sheets[sprite_url]
	var texture: Texture2D = sprite_data["texture"]
	var params: Dictionary = sprite_data["params"]

	var animated_sprite = AnimatedSprite2D.new()
	animated_sprite.name = "AnimatedSprite"

	var sprite_frames = SpriteFrames.new()
	sprite_frames.add_animation("idle")
	sprite_frames.set_animation_loop("idle", true)
	sprite_frames.set_animation_speed("idle", params.get("fps", 10))

	var frame_count: int = maxi(1, params.get("frame_count", 1))
	var columns: int = maxi(1, params.get("columns", 1))
	var rows: int = maxi(1, params.get("rows", 1))

	var tex_width = texture.get_width()
	var tex_height = texture.get_height()
	var frame_width = tex_width / columns
	var frame_height = tex_height / rows

	for i in range(frame_count):
		var col = i % columns
		var row = i / columns

		var atlas_texture = AtlasTexture.new()
		atlas_texture.atlas = texture
		atlas_texture.region = Rect2(col * frame_width, row * frame_height, frame_width, frame_height)
		sprite_frames.add_frame("idle", atlas_texture)

	animated_sprite.sprite_frames = sprite_frames
	animated_sprite.animation = "idle"

	# Позиционирование и масштабирование
	animated_sprite.position = Vector2(sprite_size / 2, sprite_size / 2)
	var scale_factor = float(sprite_size) / maxf(frame_width, frame_height)
	animated_sprite.scale = Vector2(scale_factor, scale_factor)

	container.add_child(animated_sprite)
	animated_sprite.play("idle")

## Загружает статическое изображение
func _load_static_image(image_url: String, container: Control) -> void:
	if pending_sprite_loads.has(image_url):
		return
	pending_sprite_loads[image_url] = true

	var url = base_url + image_url

	var http = HTTPRequest.new()
	http.use_threads = false
	add_child(http)
	http.request_completed.connect(_on_static_image_loaded.bind(image_url, container, http))

	var headers: PackedStringArray = []
	if ApiClient.auth_token != "":
		headers.append("Authorization: Bearer " + ApiClient.auth_token)

	var err = http.request(url, headers)
	if err != OK:
		pending_sprite_loads.erase(image_url)
		http.queue_free()

func _on_static_image_loaded(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray, image_url: String, container: Control, http_node: HTTPRequest) -> void:
	http_node.queue_free()
	pending_sprite_loads.erase(image_url)

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
	sprite_sheets[image_url] = {"texture": texture, "params": null}

	if is_instance_valid(container):
		_apply_static_image_to_container(container, image_url)

## Применяет статическое изображение к контейнеру
func _apply_static_image_to_container(container: Control, image_url: String) -> void:
	if not sprite_sheets.has(image_url):
		return

	for child in container.get_children():
		child.queue_free()

	var sprite_data = sprite_sheets[image_url]
	var texture: Texture2D = sprite_data["texture"]

	var texture_rect = TextureRect.new()
	texture_rect.texture = texture
	texture_rect.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	texture_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	texture_rect.custom_minimum_size = Vector2(sprite_size, sprite_size)
	texture_rect.size = Vector2(sprite_size, sprite_size)

	container.add_child(texture_rect)

func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main.tscn")

func _on_create_army_pressed() -> void:
	# Сначала загружаем список рас игрока
	status_label.text = "Загрузка рас..."
	pending_request = RequestType.GET_USER_RACES
	ApiClient.get_user_races()

func _handle_user_races_response(data: Dictionary) -> void:
	user_races = data.get("user_races", [])
	if user_races.is_empty():
		status_label.text = "У вас нет доступных рас"
		return

	# Показываем диалог создания армии
	_show_create_army_dialog()

func _show_create_army_dialog() -> void:
	# Создаём модальное окно
	create_dialog = Window.new()
	create_dialog.title = "Создание армии"
	create_dialog.size = Vector2i(400, 350)
	create_dialog.unresizable = true
	create_dialog.close_requested.connect(_on_create_dialog_close)

	var margin = MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 20)
	margin.add_theme_constant_override("margin_right", 20)
	margin.add_theme_constant_override("margin_top", 20)
	margin.add_theme_constant_override("margin_bottom", 20)
	create_dialog.add_child(margin)

	var vbox = VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 15)
	margin.add_child(vbox)

	# Название армии
	var name_label = Label.new()
	name_label.text = "Название армии:"
	vbox.add_child(name_label)

	var name_edit = LineEdit.new()
	name_edit.name = "NameEdit"
	name_edit.text = "Армия %d" % (armies.size() + 1)
	name_edit.placeholder_text = "Введите название"
	vbox.add_child(name_edit)

	# Выбор расы
	var race_label = Label.new()
	race_label.text = "Выберите расу:"
	vbox.add_child(race_label)

	var race_option = OptionButton.new()
	race_option.name = "RaceOption"
	for race in user_races:
		race_option.add_item(race.get("race_name", "Unknown"), race.get("user_race_id", 0))
	vbox.add_child(race_option)

	# Выбор типа армии
	var type_label = Label.new()
	type_label.text = "Тип армии:"
	vbox.add_child(type_label)

	var type_option = OptionButton.new()
	type_option.name = "TypeOption"
	type_option.add_item("Наёмная (покупка юнитов)", 0)
	type_option.add_item("Рейтинговая (приглашение юнитов)", 1)
	vbox.add_child(type_option)

	# Описание типа
	var type_desc = Label.new()
	type_desc.name = "TypeDesc"
	type_desc.text = "Наёмная: покупка юнитов за золото с лимитами"
	type_desc.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	type_desc.add_theme_font_size_override("font_size", 12)
	type_desc.autowrap_mode = TextServer.AUTOWRAP_WORD
	vbox.add_child(type_desc)

	type_option.item_selected.connect(func(idx):
		if idx == 0:
			type_desc.text = "Наёмная: покупка юнитов за золото с лимитами"
		else:
			type_desc.text = "Рейтинговая: приглашение юнитов без ограничений"
	)

	# Кнопки
	var btn_hbox = HBoxContainer.new()
	btn_hbox.add_theme_constant_override("separation", 10)
	btn_hbox.alignment = BoxContainer.ALIGNMENT_CENTER
	vbox.add_child(btn_hbox)

	var cancel_btn = Button.new()
	cancel_btn.text = "Отмена"
	cancel_btn.custom_minimum_size = Vector2(100, 40)
	cancel_btn.pressed.connect(_on_create_dialog_close)
	btn_hbox.add_child(cancel_btn)

	var create_btn = Button.new()
	create_btn.text = "Создать"
	create_btn.custom_minimum_size = Vector2(100, 40)
	create_btn.pressed.connect(_on_create_dialog_confirm)
	btn_hbox.add_child(create_btn)

	add_child(create_dialog)
	create_dialog.popup_centered()

func _on_create_dialog_close() -> void:
	if create_dialog:
		create_dialog.queue_free()
		create_dialog = null

func _on_create_dialog_confirm() -> void:
	if not create_dialog:
		return

	var name_edit = create_dialog.find_child("NameEdit", true, false) as LineEdit
	var race_option = create_dialog.find_child("RaceOption", true, false) as OptionButton
	var type_option = create_dialog.find_child("TypeOption", true, false) as OptionButton

	if not name_edit or not race_option or not type_option:
		status_label.text = "Ошибка диалога"
		_on_create_dialog_close()
		return

	var army_name = name_edit.text.strip_edges()
	if army_name.is_empty():
		army_name = "Армия %d" % (armies.size() + 1)

	var user_race_id = race_option.get_item_id(race_option.selected)
	var new_army_type = "mercenary" if type_option.selected == 0 else "rated"

	_on_create_dialog_close()

	status_label.text = "Создание армии..."
	pending_request = RequestType.CREATE_ARMY
	ApiClient.create_army(army_name, user_race_id, new_army_type)

func _on_delete_army_pressed() -> void:
	if selected_army_id <= 0:
		return

	status_label.text = "Удаление армии..."
	pending_request = RequestType.DELETE_ARMY
	ApiClient.delete_army(selected_army_id)

func _on_hire_unit(race_unit_id: int, available: int, cost: int) -> void:
	if selected_army_id <= 0 or race_unit_id <= 0:
		return

	# Всегда показываем диалог выбора количества
	hire_race_unit_id = race_unit_id
	# Для рейтинговых армий устанавливаем большой лимит
	hire_max_available = available if available > 0 else 999
	hire_unit_cost = cost
	_show_hire_dialog()

func _show_hire_dialog() -> void:
	hire_dialog = Window.new()
	hire_dialog.title = "Нанять юнитов"
	hire_dialog.size = Vector2i(350, 250)
	hire_dialog.unresizable = true
	hire_dialog.close_requested.connect(_on_hire_dialog_close)

	var margin = MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.add_theme_constant_override("margin_left", 20)
	margin.add_theme_constant_override("margin_right", 20)
	margin.add_theme_constant_override("margin_top", 20)
	margin.add_theme_constant_override("margin_bottom", 20)
	hire_dialog.add_child(margin)

	var vbox = VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 15)
	margin.add_child(vbox)

	# Информация
	var info_label = Label.new()
	info_label.text = "Доступно для найма: %d\nСтоимость за 1 юнита: $%d" % [hire_max_available, hire_unit_cost]
	info_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	vbox.add_child(info_label)

	# Количество
	var count_hbox = HBoxContainer.new()
	count_hbox.alignment = BoxContainer.ALIGNMENT_CENTER
	count_hbox.add_theme_constant_override("separation", 10)
	vbox.add_child(count_hbox)

	var count_label = Label.new()
	count_label.text = "Количество:"
	count_hbox.add_child(count_label)

	var count_spin = SpinBox.new()
	count_spin.name = "CountSpin"
	count_spin.min_value = 1
	count_spin.max_value = hire_max_available
	count_spin.value = 1
	count_spin.custom_minimum_size = Vector2(100, 0)
	count_hbox.add_child(count_spin)

	# Итоговая стоимость
	var total_label = Label.new()
	total_label.name = "TotalLabel"
	total_label.text = "Итого: $%d" % hire_unit_cost
	total_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	total_label.add_theme_font_size_override("font_size", 18)
	total_label.add_theme_color_override("font_color", Color(0.4, 0.8, 0.4))
	vbox.add_child(total_label)

	# Обновляем итого при изменении количества
	count_spin.value_changed.connect(func(value: float):
		var total = int(value) * hire_unit_cost
		total_label.text = "Итого: $%d" % total
		if total > player_balance:
			total_label.add_theme_color_override("font_color", Color(0.9, 0.3, 0.3))
		else:
			total_label.add_theme_color_override("font_color", Color(0.4, 0.8, 0.4))
	)

	# Кнопки
	var btn_hbox = HBoxContainer.new()
	btn_hbox.add_theme_constant_override("separation", 10)
	btn_hbox.alignment = BoxContainer.ALIGNMENT_CENTER
	vbox.add_child(btn_hbox)

	var cancel_btn = Button.new()
	cancel_btn.text = "Отмена"
	cancel_btn.custom_minimum_size = Vector2(90, 40)
	cancel_btn.pressed.connect(_on_hire_dialog_close)
	btn_hbox.add_child(cancel_btn)

	var hire_one_btn = Button.new()
	hire_one_btn.text = "Нанять 1"
	hire_one_btn.custom_minimum_size = Vector2(90, 40)
	hire_one_btn.pressed.connect(_on_hire_dialog_confirm.bind(1))
	btn_hbox.add_child(hire_one_btn)

	var hire_btn = Button.new()
	hire_btn.text = "Нанять"
	hire_btn.custom_minimum_size = Vector2(90, 40)
	hire_btn.pressed.connect(func(): _on_hire_dialog_confirm(int(count_spin.value)))
	btn_hbox.add_child(hire_btn)

	# Кнопка "Нанять всех"
	var hire_all_btn = Button.new()
	hire_all_btn.text = "Нанять всех (%d)" % hire_max_available
	hire_all_btn.custom_minimum_size = Vector2(0, 40)
	hire_all_btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hire_all_btn.pressed.connect(_on_hire_dialog_confirm.bind(hire_max_available))
	vbox.add_child(hire_all_btn)

	add_child(hire_dialog)
	hire_dialog.popup_centered()

func _on_hire_dialog_close() -> void:
	if hire_dialog:
		hire_dialog.queue_free()
		hire_dialog = null
	hire_race_unit_id = 0
	hire_max_available = 0
	hire_unit_cost = 0

func _on_hire_dialog_confirm(count: int) -> void:
	var race_unit_id = hire_race_unit_id
	_on_hire_dialog_close()

	if race_unit_id <= 0 or count <= 0:
		return

	_do_hire_unit(race_unit_id, count)

func _do_hire_unit(race_unit_id: int, count: int) -> void:
	status_label.text = "Найм юнитов (%d)..." % count
	pending_request = RequestType.HIRE_UNIT
	ApiClient.hire_unit(selected_army_id, race_unit_id, count)

func _on_dismiss_unit(race_unit_id: int) -> void:
	if selected_army_id <= 0 or race_unit_id <= 0:
		return

	status_label.text = "Роспуск юнита..."
	pending_request = RequestType.DISMISS_UNIT
	ApiClient.dismiss_unit(selected_army_id, race_unit_id, 1)

func _on_unlock_level(level: int) -> void:
	if level <= 0:
		return

	status_label.text = "Разблокировка уровня %d..." % level
	pending_request = RequestType.UNLOCK_LEVEL
	ApiClient.unlock_unit_level(level)
