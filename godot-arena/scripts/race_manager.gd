extends Control
## Управление расами и лимитами найма юнитов

@onready var back_button: Button = %BackButton
@onready var balance_label: Label = %BalanceLabel
@onready var races_container: VBoxContainer = %RacesContainer
@onready var race_name_label: Label = %RaceNameLabel
@onready var levels_container: VBoxContainer = %LevelsContainer
@onready var status_label: Label = %StatusLabel
@onready var add_race_button: Button = %AddRaceButton

var user_races: Array = []
var available_races: Array = []  # Все доступные расы для добавления
var selected_race: Dictionary = {}
var user_balance: Dictionary = {}

# Состояние запроса
enum RequestState { IDLE, LOADING_RACES, UNLOCKING_LEVEL, UPGRADING_SPEED, LOADING_AVAILABLE_RACES, ADDING_RACE }
var request_state: RequestState = RequestState.IDLE
var pending_action: Dictionary = {}  # Для хранения данных об ожидающем действии

func _ready() -> void:
	# Подключаем сигналы
	back_button.pressed.connect(_on_back_pressed)
	ApiClient.request_completed.connect(_on_api_response)
	ApiClient.request_failed.connect(_on_api_error)

	# Подключаем кнопку добавления расы
	if add_race_button:
		add_race_button.pressed.connect(_on_add_race_pressed)

	# Загружаем расы
	_load_races()


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main.tscn")


func _load_races() -> void:
	status_label.text = "Загрузка рас..."
	request_state = RequestState.LOADING_RACES
	ApiClient.get_user_races_with_limits()


func _on_api_response(data: Dictionary) -> void:
	var current_state = request_state
	match current_state:
		RequestState.LOADING_RACES:
			_handle_races_loaded(data)
		RequestState.UNLOCKING_LEVEL:
			_handle_level_unlocked(data)
		RequestState.UPGRADING_SPEED:
			_handle_speed_upgraded(data)
		RequestState.LOADING_AVAILABLE_RACES:
			_handle_available_races_loaded(data)
		RequestState.ADDING_RACE:
			_handle_race_added(data)

	# Сбрасываем state только если он не изменился (не запущен новый запрос)
	if request_state == current_state:
		request_state = RequestState.IDLE


func _on_api_error(error: String) -> void:
	status_label.text = "Ошибка: " + error
	request_state = RequestState.IDLE


func _handle_races_loaded(data: Dictionary) -> void:
	if data.has("races"):
		user_races = data.races
		user_balance = data.get("user_balance", {})
		_update_balance_label()
		_populate_races_list()
		status_label.text = ""
	elif data.has("error"):
		status_label.text = "Ошибка: " + data.error


func _handle_level_unlocked(data: Dictionary) -> void:
	if data.has("success") and data.success:
		status_label.text = data.get("message", "Уровень разблокирован!")
		# Обновляем баланс если есть
		if data.has("data") and data.data.has("crystals_remaining"):
			user_balance["crystals"] = data.data.crystals_remaining
			_update_balance_label()
		# Перезагружаем данные
		_load_races()
	elif data.has("error"):
		status_label.text = "Ошибка: " + data.error


func _handle_speed_upgraded(data: Dictionary) -> void:
	if data.has("success") and data.success:
		status_label.text = data.get("message", "Скорость увеличена!")
		# Обновляем баланс
		if data.has("data") and data.data.has("currency_remaining"):
			if pending_action.get("use_gems", false):
				user_balance["crystals"] = int(data.data.currency_remaining)
			else:
				user_balance["balance"] = data.data.currency_remaining
			_update_balance_label()
		# Перезагружаем данные
		_load_races()
	elif data.has("error"):
		status_label.text = "Ошибка: " + data.error


func _handle_available_races_loaded(data: Dictionary) -> void:
	if data.has("races"):
		available_races = data.races
		_show_add_race_dialog()
	elif data.has("error"):
		status_label.text = "Ошибка: " + data.error


func _handle_race_added(data: Dictionary) -> void:
	if data.has("success") and data.success:
		status_label.text = data.get("message", "Раса добавлена!")
		# Перезагружаем данные
		_load_races()
	elif data.has("error"):
		status_label.text = "Ошибка: " + data.error


func _update_balance_label() -> void:
	var coins = int(user_balance.get("balance", 0))
	var crystals = int(user_balance.get("crystals", 0))
	var glory = int(user_balance.get("glory", 0))
	balance_label.text = "Монеты: %d | Кристаллы: %d | Слава: %d" % [coins, crystals, glory]


func _populate_races_list() -> void:
	# Очищаем список
	for child in races_container.get_children():
		child.queue_free()

	if user_races.is_empty():
		var label = Label.new()
		label.text = "У вас нет рас. Добавьте расу!"
		label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
		races_container.add_child(label)
		return

	for race in user_races:
		var btn = Button.new()
		btn.text = race.race_name
		btn.custom_minimum_size = Vector2(0, 40)
		btn.pressed.connect(_on_race_selected.bind(race))
		races_container.add_child(btn)

	# Если есть выбранная раса, обновляем её
	if not selected_race.is_empty():
		for race in user_races:
			if race.id == selected_race.id:
				selected_race = race
				_display_race_levels(race)
				return

	# Иначе выбираем первую
	if not user_races.is_empty():
		_on_race_selected(user_races[0])


func _on_race_selected(race: Dictionary) -> void:
	selected_race = race
	_display_race_levels(race)


func _display_race_levels(race: Dictionary) -> void:
	race_name_label.text = race.race_name

	# Очищаем контейнер уровней
	for child in levels_container.get_children():
		child.queue_free()

	var limits = race.get("unit_limits", [])
	if limits.is_empty():
		var label = Label.new()
		label.text = "Нет данных об уровнях"
		label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
		levels_container.add_child(label)
		return

	for limit in limits:
		var panel = _create_level_panel(race.id, limit)
		levels_container.add_child(panel)


func _create_level_panel(user_race_id: int, limit: Dictionary) -> PanelContainer:
	var panel = PanelContainer.new()
	panel.custom_minimum_size = Vector2(0, 100)

	var hbox = HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 20)
	panel.add_child(hbox)

	# Информация об уровне
	var info_vbox = VBoxContainer.new()
	info_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hbox.add_child(info_vbox)

	var level_num = limit.get("level", 0)
	var unit_name = limit.get("unit_name", "Уровень %d" % level_num)
	var is_unlocked = limit.get("level_unlocked", false)
	var available = limit.get("available_count", 0)
	var daily_speed = limit.get("daily_speed", 0)
	var unlock_cost = limit.get("unlock_cost_gems", 0)
	var speed_cost_coins = limit.get("speed_upgrade_cost", 0)
	var speed_cost_gems = limit.get("speed_upgrade_cost_gems", 0)

	# Заголовок уровня - показываем название юнита
	var title_label = Label.new()
	title_label.text = unit_name
	title_label.add_theme_font_size_override("font_size", 20)
	if is_unlocked:
		title_label.add_theme_color_override("font_color", Color(0.4, 0.9, 0.4))
	else:
		title_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	info_vbox.add_child(title_label)

	# Статус
	var status_text = ""
	if is_unlocked:
		status_text = "Доступно: %d юн. | Скорость: %d/день" % [available, daily_speed]
	else:
		status_text = "ЗАБЛОКИРОВАН - Стоимость: %d кристаллов" % unlock_cost

	var status = Label.new()
	status.text = status_text
	status.add_theme_font_size_override("font_size", 14)
	status.add_theme_color_override("font_color", Color(0.8, 0.8, 0.8))
	info_vbox.add_child(status)

	# Кнопки действий
	var buttons_vbox = VBoxContainer.new()
	buttons_vbox.add_theme_constant_override("separation", 5)
	hbox.add_child(buttons_vbox)

	if not is_unlocked:
		# Кнопка разблокировки
		var unlock_btn = Button.new()
		unlock_btn.text = "Разблокировать (%d крист.)" % unlock_cost
		unlock_btn.custom_minimum_size = Vector2(200, 35)
		unlock_btn.pressed.connect(_on_unlock_level.bind(user_race_id, limit.get("unit_level_id", 0)))
		buttons_vbox.add_child(unlock_btn)
	else:
		# Кнопка улучшения скорости (только за монеты)
		var upgrade_coins_btn = Button.new()
		upgrade_coins_btn.text = "+1 скорость найма (%.0f монет)" % speed_cost_coins
		upgrade_coins_btn.custom_minimum_size = Vector2(200, 35)
		upgrade_coins_btn.pressed.connect(_on_upgrade_speed.bind(user_race_id, limit.get("unit_level_id", 0), false))
		buttons_vbox.add_child(upgrade_coins_btn)

	return panel


func _on_unlock_level(user_race_id: int, unit_level_id: int) -> void:
	status_label.text = "Разблокировка уровня..."
	request_state = RequestState.UNLOCKING_LEVEL
	pending_action = {}
	ApiClient.unlock_race_level(user_race_id, unit_level_id)


func _on_upgrade_speed(user_race_id: int, unit_level_id: int, use_gems: bool) -> void:
	var currency = "кристаллы" if use_gems else "монеты"
	status_label.text = "Улучшение скорости за %s..." % currency
	request_state = RequestState.UPGRADING_SPEED
	pending_action = {"use_gems": use_gems}
	ApiClient.upgrade_race_speed(user_race_id, unit_level_id, use_gems)


# ============= Добавление расы =============

func _on_add_race_pressed() -> void:
	status_label.text = "Загрузка доступных рас..."
	request_state = RequestState.LOADING_AVAILABLE_RACES
	ApiClient.get_available_races()


func _show_add_race_dialog() -> void:
	# Фильтруем только расы, которых нет у пользователя
	var races_to_add = []
	for race in available_races:
		if not race.get("is_owned", false):
			races_to_add.append(race)

	if races_to_add.is_empty():
		status_label.text = "Все расы уже добавлены!"
		return

	# Показываем диалог выбора расы в панели уровней
	race_name_label.text = "Выберите расу для добавления"

	# Очищаем контейнер уровней
	for child in levels_container.get_children():
		child.queue_free()

	# Создаём карточки для каждой доступной расы
	for race in races_to_add:
		var panel = _create_race_card(race)
		levels_container.add_child(panel)

	status_label.text = ""


func _create_race_card(race: Dictionary) -> PanelContainer:
	var panel = PanelContainer.new()
	panel.custom_minimum_size = Vector2(0, 120)

	var hbox = HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 20)
	panel.add_child(hbox)

	# Информация о расе
	var info_vbox = VBoxContainer.new()
	info_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hbox.add_child(info_vbox)

	# Название расы
	var name_label = Label.new()
	var free_text = " [БЕСПЛАТНО]" if race.get("is_free", false) else ""
	name_label.text = race.get("name", "???") + free_text
	name_label.add_theme_font_size_override("font_size", 22)
	if race.get("is_free", false):
		name_label.add_theme_color_override("font_color", Color(0.4, 0.9, 0.4))
	else:
		name_label.add_theme_color_override("font_color", Color(0.9, 0.8, 0.2))
	info_vbox.add_child(name_label)

	# Описание
	var desc_label = Label.new()
	desc_label.text = race.get("description", "")
	desc_label.add_theme_font_size_override("font_size", 14)
	desc_label.add_theme_color_override("font_color", Color(0.8, 0.8, 0.8))
	desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	info_vbox.add_child(desc_label)

	# Превью юнитов
	var units_preview = race.get("units_preview", [])
	if not units_preview.is_empty():
		var units_text = "Юниты: "
		var unit_names = []
		for u in units_preview:
			unit_names.append(u.get("name", "?"))
		units_text += ", ".join(unit_names) + "..."

		var units_label = Label.new()
		units_label.text = units_text
		units_label.add_theme_font_size_override("font_size", 12)
		units_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
		info_vbox.add_child(units_label)

	# Кнопка добавления
	var add_btn = Button.new()
	add_btn.text = "Добавить"
	add_btn.custom_minimum_size = Vector2(120, 50)
	add_btn.pressed.connect(_on_add_race_confirmed.bind(race.get("id", 0)))
	hbox.add_child(add_btn)

	return panel


func _on_add_race_confirmed(race_id: int) -> void:
	status_label.text = "Добавление расы..."
	request_state = RequestState.ADDING_RACE
	ApiClient.add_user_race(race_id)
