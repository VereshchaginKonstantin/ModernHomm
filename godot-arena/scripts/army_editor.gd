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
var player_crystals: int = 0
var army_type: String = "mercenary"  # rated или mercenary
var is_in_battle: bool = false  # Армия в бою - нельзя редактировать

# Данные для создания армии
var user_races: Array = []
var create_dialog: Window = null

# Ожидание ответов
enum RequestType { NONE, GET_ARMIES, CREATE_ARMY, DELETE_ARMY, GET_AVAILABLE_UNITS, HIRE_UNIT, DISMISS_UNIT, UNLOCK_LEVEL, GET_USER_RACES }
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
	_display_available_units()

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
			var unit_card = _create_army_unit_card(unit, army_in_battle)
			army_units_list.add_child(unit_card)

func _clear_selected_army() -> void:
	army_name_label.text = "Выберите армию"
	delete_army_button.visible = false

	for child in army_units_list.get_children():
		child.queue_free()
	for child in available_units_list.get_children():
		child.queue_free()

func _create_army_unit_card(unit: Dictionary, army_in_battle: bool = false) -> Control:
	var card = PanelContainer.new()
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var hbox = HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 10)
	card.add_child(hbox)

	# Иконка и имя
	var info_vbox = VBoxContainer.new()
	info_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var name_label = Label.new()
	name_label.text = "%s x%d" % [unit.get("name", "Юнит"), unit.get("count", 0)]
	name_label.add_theme_font_size_override("font_size", 18)
	info_vbox.add_child(name_label)

	var stats_label = Label.new()
	stats_label.text = "A:%d D:%d H:%d S:%d" % [
		unit.get("attack", 0),
		unit.get("defense", 0),
		unit.get("health", 0),
		unit.get("speed", 0)
	]
	stats_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	info_vbox.add_child(stats_label)

	hbox.add_child(info_vbox)

	# Кнопка роспуска (заблокирована если армия в бою)
	var dismiss_btn = Button.new()
	dismiss_btn.text = "Распустить"
	dismiss_btn.disabled = army_in_battle
	if army_in_battle:
		dismiss_btn.tooltip_text = "Нельзя распускать юнитов - армия в бою"
	dismiss_btn.pressed.connect(_on_dismiss_unit.bind(unit.get("race_unit_id", 0)))
	hbox.add_child(dismiss_btn)

	return card

func _display_available_units() -> void:
	for child in available_units_list.get_children():
		child.queue_free()

	# Если армия в бою - показываем предупреждение
	if is_in_battle:
		var warning_label = Label.new()
		warning_label.text = "АРМИЯ В БОЮ!\nНельзя нанимать или распускать юнитов"
		warning_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		warning_label.add_theme_color_override("font_color", Color(0.9, 0.3, 0.3))
		warning_label.add_theme_font_size_override("font_size", 18)
		available_units_list.add_child(warning_label)
		return

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

	var vbox = VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 5)
	card.add_child(vbox)

	var hbox = HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 10)
	vbox.add_child(hbox)

	# Информация о юните
	var info_vbox = VBoxContainer.new()
	info_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var name_label = Label.new()
	var current_count = unit.get("current_count", 0)
	var level = unit.get("level", 1)
	var count_text = " (в армии: %d)" % current_count if current_count > 0 else ""
	name_label.text = "[Ур.%d] %s%s" % [level, unit.get("name", "Юнит"), count_text]
	name_label.add_theme_font_size_override("font_size", 18)
	info_vbox.add_child(name_label)

	var stats_label = Label.new()
	stats_label.text = "A:%d D:%d H:%d S:%d | $%d" % [
		unit.get("attack", 0),
		unit.get("defense", 0),
		unit.get("health", 0),
		unit.get("speed", 0),
		unit.get("hire_cost", 0)
	]
	stats_label.add_theme_color_override("font_color", Color(0.6, 0.6, 0.6))
	info_vbox.add_child(stats_label)

	hbox.add_child(info_vbox)

	# Проверяем тип армии и доступность
	var level_unlocked = unit.get("level_unlocked", true)
	var available_to_hire = unit.get("available_to_hire", 999)
	var can_hire = unit.get("can_hire", false)
	var unlock_cost = unit.get("unlock_cost_gems", 0)
	var is_rated = army_type == "rated"

	# Для рейтинговых армий - нет ограничений
	if is_rated:
		var hire_btn = Button.new()
		hire_btn.text = "Нанять"
		hire_btn.disabled = not can_hire
		if not can_hire:
			hire_btn.tooltip_text = "Недостаточно средств"
		hire_btn.pressed.connect(_on_hire_unit.bind(unit.get("race_unit_id", 0)))
		hbox.add_child(hire_btn)
	else:
		# Для наёмных армий - проверяем лимиты
		if not level_unlocked:
			# Уровень заблокирован - показываем кнопку разблокировки
			var unlock_btn = Button.new()
			unlock_btn.text = "Разблокировать (%d крист.)" % unlock_cost
			unlock_btn.disabled = player_crystals < unlock_cost
			if player_crystals < unlock_cost:
				unlock_btn.tooltip_text = "Недостаточно кристаллов"
			unlock_btn.pressed.connect(_on_unlock_level.bind(level))
			hbox.add_child(unlock_btn)

			# Показываем что уровень заблокирован
			var lock_label = Label.new()
			lock_label.text = "ЗАБЛОКИРОВАНО"
			lock_label.add_theme_color_override("font_color", Color(0.8, 0.3, 0.3))
			lock_label.add_theme_font_size_override("font_size", 12)
			vbox.add_child(lock_label)
		else:
			# Уровень разблокирован - показываем лимит и кнопку найма
			var limit_label = Label.new()
			limit_label.text = "Доступно для найма: %d" % available_to_hire
			if available_to_hire <= 0:
				limit_label.add_theme_color_override("font_color", Color(0.8, 0.5, 0.3))
			else:
				limit_label.add_theme_color_override("font_color", Color(0.5, 0.8, 0.5))
			limit_label.add_theme_font_size_override("font_size", 12)
			vbox.add_child(limit_label)

			var hire_btn = Button.new()
			hire_btn.text = "Нанять"
			hire_btn.disabled = not can_hire
			if not can_hire:
				if available_to_hire <= 0:
					hire_btn.tooltip_text = "Нет доступных юнитов (ожидайте регенерации)"
				else:
					hire_btn.tooltip_text = "Недостаточно средств"
			hire_btn.pressed.connect(_on_hire_unit.bind(unit.get("race_unit_id", 0)))
			hbox.add_child(hire_btn)

	return card

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

func _on_unlock_level(level: int) -> void:
	if level <= 0:
		return

	status_label.text = "Разблокировка уровня %d..." % level
	pending_request = RequestType.UNLOCK_LEVEL
	ApiClient.unlock_unit_level(level)
