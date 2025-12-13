extends Control
## Главное меню арены

@onready var player_name_label: Label = %PlayerNameLabel
@onready var player_stats: Label = %PlayerStats
@onready var opponent_select: OptionButton = %OpponentSelect
@onready var opponent_stats: Label = %OpponentStats
@onready var field_5x5: Button = %Field5x5
@onready var field_7x7: Button = %Field7x7
@onready var field_10x10: Button = %Field10x10
@onready var start_button: Button = %StartButton
@onready var status_label: Label = %StatusLabel
@onready var pending_panel: PanelContainer = %PendingGamesPanel
@onready var pending_list: VBoxContainer = %PendingList

var players: Array = []
var current_player: Dictionary = {}  # Текущий залогиненный игрок
var selected_opponent: Dictionary = {}
var selected_field_size: String = "5x5"

func _ready() -> void:
	# Подключаем сигналы
	GameManager.players_loaded.connect(_on_players_loaded)
	GameManager.current_player_loaded.connect(_on_current_player_loaded)
	GameManager.game_state_updated.connect(_on_game_started)
	GameManager.error_occurred.connect(_on_error)

	# Подключаем UI
	opponent_select.item_selected.connect(_on_opponent_selected)
	field_5x5.pressed.connect(_on_field_5x5_pressed)
	field_7x7.pressed.connect(_on_field_7x7_pressed)
	field_10x10.pressed.connect(_on_field_10x10_pressed)
	start_button.pressed.connect(_on_start_pressed)
	$VBoxContainer/BackButton.pressed.connect(_on_back_pressed)

	# Сначала загружаем текущего пользователя
	status_label.text = "Загрузка..."
	GameManager.load_current_player()

func _on_current_player_loaded(player: Dictionary) -> void:
	if player.is_empty():
		# Пользователь не залогинен - показываем сообщение
		# Кнопка "Назад" переведёт на веб-арену где можно залогиниться
		status_label.text = "Необходимо войти через веб-арену"
		player_name_label.text = "Не авторизован"
		start_button.disabled = true
		return

	current_player = player

	# Показываем имя текущего игрока
	player_name_label.text = current_player.get("name", "???")

	# Обновляем статистику игрока
	var win_rate = 0
	var total = current_player.get("wins", 0) + current_player.get("losses", 0)
	if total > 0:
		win_rate = int(float(current_player.get("wins", 0)) / total * 100)
	player_stats.text = "Армия: %.0f | Побед: %d | Поражений: %d (%d%%)" % [
		current_player.get("army_cost", 0),
		current_player.get("wins", 0),
		current_player.get("losses", 0),
		win_rate
	]

	# Теперь загружаем список противников
	status_label.text = "Загрузка противников..."
	GameManager.load_players()

func _on_players_loaded(loaded_players: Array) -> void:
	players = loaded_players
	status_label.text = ""

	# Заполняем список противников
	_populate_opponents()

func _populate_opponents() -> void:
	if current_player.is_empty():
		return

	var my_id = current_player.get("id", 0)
	var my_cost = current_player.get("army_cost", 0)
	var min_cost = my_cost * 0.5
	var max_cost = my_cost * 1.5

	opponent_select.clear()
	opponent_select.add_item("Выберите противника", 0)

	for p in players:
		if p.get("id") == my_id:
			continue  # Себя пропускаем
		if p.get("units", []).size() == 0:
			continue  # Без юнитов пропускаем

		var cost = p.get("army_cost", 0)
		if cost >= min_cost and cost <= max_cost:
			var wr = 0
			var t = p.get("wins", 0) + p.get("losses", 0)
			if t > 0:
				wr = int(float(p.get("wins", 0)) / t * 100)
			var text = "%s (%.0f) - %d%%" % [p.get("name", "???"), cost, wr]
			opponent_select.add_item(text, p.get("id", 0))

	selected_opponent = {}
	opponent_stats.text = ""
	_update_start_button()

	# Проверяем ожидающие игры
	_check_pending_games()

func _check_pending_games() -> void:
	if current_player.is_empty():
		pending_panel.visible = false
		return

	# TODO: Реализовать проверку ожидающих игр через API
	pending_panel.visible = false

func _on_opponent_selected(index: int) -> void:
	var opponent_id = opponent_select.get_item_id(index)
	if opponent_id == 0:
		selected_opponent = {}
		opponent_stats.text = ""
		_update_start_button()
		return

	# Находим противника
	for p in players:
		if p.get("id") == opponent_id:
			selected_opponent = p
			break

	# Обновляем статистику противника
	var win_rate = 0
	var total = selected_opponent.get("wins", 0) + selected_opponent.get("losses", 0)
	if total > 0:
		win_rate = int(float(selected_opponent.get("wins", 0)) / total * 100)
	opponent_stats.text = "Побед: %d | Поражений: %d (%d%%)" % [
		selected_opponent.get("wins", 0),
		selected_opponent.get("losses", 0),
		win_rate
	]

	_update_start_button()

func _on_field_5x5_pressed() -> void:
	selected_field_size = "5x5"
	field_5x5.button_pressed = true
	field_7x7.button_pressed = false
	field_10x10.button_pressed = false

func _on_field_7x7_pressed() -> void:
	selected_field_size = "7x7"
	field_5x5.button_pressed = false
	field_7x7.button_pressed = true
	field_10x10.button_pressed = false

func _on_field_10x10_pressed() -> void:
	selected_field_size = "10x10"
	field_5x5.button_pressed = false
	field_7x7.button_pressed = false
	field_10x10.button_pressed = true

func _update_start_button() -> void:
	start_button.disabled = current_player.is_empty() or selected_opponent.is_empty()

func _on_start_pressed() -> void:
	if current_player.is_empty() or selected_opponent.is_empty():
		return

	start_button.disabled = true
	status_label.text = "Создание игры..."

	GameManager.create_game(
		current_player.get("id"),
		selected_opponent.get("name", ""),
		selected_field_size
	)

func _on_game_started(state: Dictionary) -> void:
	# Переходим на сцену игры
	get_tree().change_scene_to_file("res://scenes/game.tscn")

func _on_error(message: String) -> void:
	status_label.text = "Ошибка: " + message
	start_button.disabled = false

func _on_back_pressed() -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.location.href = '/arena/';")
