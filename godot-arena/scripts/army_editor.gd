extends Control
## Редактор армий - создание армий, найм и роспуск юнитов

@onready var back_button: Button = %BackButton
@onready var create_army_button: Button = %CreateArmyButton
@onready var armies_list: VBoxContainer = %ArmiesList
@onready var army_name_label: Label = %ArmyNameLabel
@onready var delete_army_button: Button = %DeleteArmyButton
@onready var balance_label: Label = %BalanceLabel
@onready var army_units_list: VBoxContainer = %ArmyUnitsList
@onready var available_units_list: VBoxContainer = %AvailableUnitsList
@onready var status_label: Label = %StatusLabel

# Состояние
var armies: Array = []
var selected_army_id: int = 0
var selected_army: Dictionary = {}
var available_units: Array = []
var player_balance: float = 0.0

# Ожидание ответов
enum RequestType { NONE, GET_ARMIES, CREATE_ARMY, DELETE_ARMY, GET_AVAILABLE_UNITS, HIRE_UNIT, DISMISS_UNIT }
var pending_request: RequestType = RequestType.NONE

func _ready() -> void:
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
	if OS.has_feature("web"):
		JavaScriptBridge.eval("console.log('[ArmyEditor] _on_api_response, request=%d, keys: ' + Object.keys(%s).join(','));" % [pending_request, JSON.stringify(data)])

	match pending_request:
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

	pending_request = RequestType.NONE

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
	balance_label.text = "Баланс: $%.0f" % player_balance
	_display_available_units()

func _handle_hire_response(data: Dictionary) -> void:
	if data.get("success", false):
		player_balance = data.get("new_balance", player_balance)
		balance_label.text = "Баланс: $%.0f" % player_balance
		status_label.text = "Юнит нанят! Стоимость: $%.0f" % data.get("total_cost", 0)
		# Перезагружаем данные
		_load_armies()
		if selected_army_id > 0:
			pending_request = RequestType.GET_AVAILABLE_UNITS
			ApiClient.get_available_units(selected_army_id)
	else:
		status_label.text = data.get("error", "Ошибка найма")

func _handle_dismiss_response(data: Dictionary) -> void:
	if data.get("success", false):
		player_balance = data.get("new_balance", player_balance)
		balance_label.text = "Баланс: $%.0f" % player_balance
		status_label.text = "Юнит распущен. Возврат: $%.0f" % data.get("refund", 0)
		# Перезагружаем данные
		_load_armies()
		if selected_army_id > 0:
			pending_request = RequestType.GET_AVAILABLE_UNITS
			ApiClient.get_available_units(selected_army_id)
	else:
		status_label.text = data.get("error", "Ошибка роспуска")

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

		btn.text = "%s\n%.0f ⚔️ | %d юн." % [army_name, army_cost, units_count]
		btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		btn.custom_minimum_size = Vector2(0, 60)

		if army_id == selected_army_id:
			btn.modulate = Color(0.5, 0.8, 0.5)

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

	army_name_label.text = selected_army.get("army_name", "Армия")
	delete_army_button.visible = true

	# Отображаем юнитов в армии
	for child in army_units_list.get_children():
		child.queue_free()

	var units = selected_army.get("units", [])
	if units.is_empty():
		var label = Label.new()
		label.text = "В армии нет юнитов.\nНаймите юнитов во вкладке \"Нанять юнитов\""
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		army_units_list.add_child(label)
	else:
		for unit in units:
			var unit_card = _create_army_unit_card(unit)
			army_units_list.add_child(unit_card)

func _clear_selected_army() -> void:
	army_name_label.text = "Выберите армию"
	delete_army_button.visible = false

	for child in army_units_list.get_children():
		child.queue_free()
	for child in available_units_list.get_children():
		child.queue_free()

func _create_army_unit_card(unit: Dictionary) -> Control:
	var card = PanelContainer.new()
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var hbox = HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 10)
	card.add_child(hbox)

	# Иконка и имя
	var info_vbox = VBoxContainer.new()
	info_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var name_label = Label.new()
	name_label.text = "%s %s x%d" % [unit.get("icon", "?"), unit.get("name", "Юнит"), unit.get("count", 0)]
	name_label.add_theme_font_size_override("font_size", 18)
	info_vbox.add_child(name_label)

	var stats_label = Label.new()
	stats_label.text = "⚔️%d 🛡️%d ❤️%d 💨%d" % [
		unit.get("attack", 0),
		unit.get("defense", 0),
		unit.get("health", 0),
		unit.get("speed", 0)
	]
	stats_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	info_vbox.add_child(stats_label)

	hbox.add_child(info_vbox)

	# Кнопка роспуска
	var dismiss_btn = Button.new()
	dismiss_btn.text = "Распустить"
	dismiss_btn.pressed.connect(_on_dismiss_unit.bind(unit.get("race_unit_id", 0)))
	hbox.add_child(dismiss_btn)

	return card

func _display_available_units() -> void:
	for child in available_units_list.get_children():
		child.queue_free()

	if available_units.is_empty():
		var label = Label.new()
		label.text = "Нет доступных юнитов для найма"
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		available_units_list.add_child(label)
		return

	for unit in available_units:
		var unit_card = _create_available_unit_card(unit)
		available_units_list.add_child(unit_card)

func _create_available_unit_card(unit: Dictionary) -> Control:
	var card = PanelContainer.new()
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var hbox = HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 10)
	card.add_child(hbox)

	# Иконка и имя
	var info_vbox = VBoxContainer.new()
	info_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var name_label = Label.new()
	var current_count = unit.get("current_count", 0)
	var count_text = " (в армии: %d)" % current_count if current_count > 0 else ""
	name_label.text = "%s %s%s" % [unit.get("icon", "?"), unit.get("name", "Юнит"), count_text]
	name_label.add_theme_font_size_override("font_size", 18)
	info_vbox.add_child(name_label)

	var stats_label = Label.new()
	stats_label.text = "⚔️%d 🛡️%d ❤️%d 💨%d | 💰%d" % [
		unit.get("attack", 0),
		unit.get("defense", 0),
		unit.get("health", 0),
		unit.get("speed", 0),
		unit.get("hire_cost", 0)
	]
	stats_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	info_vbox.add_child(stats_label)

	hbox.add_child(info_vbox)

	# Кнопка найма
	var hire_btn = Button.new()
	hire_btn.text = "Нанять"
	var can_afford = unit.get("can_afford", false)
	hire_btn.disabled = not can_afford
	if not can_afford:
		hire_btn.tooltip_text = "Недостаточно средств"
	hire_btn.pressed.connect(_on_hire_unit.bind(unit.get("race_unit_id", 0)))
	hbox.add_child(hire_btn)

	return card

func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main.tscn")

func _on_create_army_pressed() -> void:
	status_label.text = "Создание армии..."
	pending_request = RequestType.CREATE_ARMY
	ApiClient.create_army("Армия %d" % (armies.size() + 1))

func _on_delete_army_pressed() -> void:
	if selected_army_id <= 0:
		return

	status_label.text = "Удаление армии..."
	pending_request = RequestType.DELETE_ARMY
	ApiClient.delete_army(selected_army_id)

func _on_hire_unit(race_unit_id: int) -> void:
	if selected_army_id <= 0 or race_unit_id <= 0:
		return

	status_label.text = "Найм юнита..."
	pending_request = RequestType.HIRE_UNIT
	ApiClient.hire_unit(selected_army_id, race_unit_id, 1)

func _on_dismiss_unit(race_unit_id: int) -> void:
	if selected_army_id <= 0 or race_unit_id <= 0:
		return

	status_label.text = "Роспуск юнита..."
	pending_request = RequestType.DISMISS_UNIT
	ApiClient.dismiss_unit(selected_army_id, race_unit_id, 1)
