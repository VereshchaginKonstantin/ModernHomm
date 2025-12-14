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
@onready var pending_list: VBoxContainer = %PendingList  # Now inside ScrollContainer

var players: Array = []
var current_player: Dictionary = {}  # Текущий залогиненный игрок
var selected_opponent: Dictionary = {}
var selected_field_size: String = "5x5"
var waiting_game_id: int = 0  # ID игры в ожидании
var waiting_timer: Timer  # Таймер для polling статуса игры
var pending_games: Array = []  # Ожидающие игры
var active_games: Array = []  # Активные игры
var history_games: Array = []  # История игр

func _ready() -> void:
	# Подключаем сигналы
	GameManager.players_loaded.connect(_on_players_loaded)
	GameManager.current_player_loaded.connect(_on_current_player_loaded)
	GameManager.game_state_updated.connect(_on_game_state_updated)
	GameManager.error_occurred.connect(_on_error)

	# Подключаем сигнал API для обработки создания игры
	ApiClient.request_completed.connect(_on_api_response)

	# Подключаем UI
	opponent_select.item_selected.connect(_on_opponent_selected)
	field_5x5.pressed.connect(_on_field_5x5_pressed)
	field_7x7.pressed.connect(_on_field_7x7_pressed)
	field_10x10.pressed.connect(_on_field_10x10_pressed)
	start_button.pressed.connect(_on_start_pressed)
	$VBoxContainer/BackButton.pressed.connect(_on_back_pressed)

	# Создаём таймер для polling статуса игры
	waiting_timer = Timer.new()
	waiting_timer.wait_time = 2.0
	waiting_timer.timeout.connect(_on_waiting_timeout)
	add_child(waiting_timer)

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
	if OS.has_feature("web"):
		JavaScriptBridge.eval("console.log('[Main] _check_pending_games called');")
	if current_player.is_empty():
		if OS.has_feature("web"):
			JavaScriptBridge.eval("console.log('[Main] current_player is empty, hiding panel');")
		pending_panel.visible = false
		return

	# Загружаем ожидающие игры через API
	var player_id = current_player.get("id", 0)
	if OS.has_feature("web"):
		JavaScriptBridge.eval("console.log('[Main] Loading pending games for player_id: %d');" % player_id)
	ApiClient.get_pending_games(player_id)

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

func _on_api_response(data: Dictionary) -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("console.log('[Main] _on_api_response called, keys: ' + Object.keys(%s).join(','));" % JSON.stringify(data))
	# Обрабатываем ответ на ожидающие игры
	if data.has("pending_games"):
		pending_games = data.get("pending_games", [])
		active_games = data.get("active_games", [])
		history_games = data.get("history", [])
		if OS.has_feature("web"):
			JavaScriptBridge.eval("console.log('[Main] Got pending_games: %d, active: %d, history: %d');" % [pending_games.size(), active_games.size(), history_games.size()])
		_display_battles_list()
		return

	# Обрабатываем ответ на создание игры
	if data.has("game_id") and data.has("status"):
		if data.get("status") == "waiting":
			# Игра создана, ждём принятия
			waiting_game_id = data.get("game_id")
			status_label.text = "Ожидание принятия игры противником..."
			waiting_timer.start()
		elif data.get("status") == "in_progress":
			# Игра уже активна, переходим
			GameManager.current_game_id = data.get("game_id")
			get_tree().change_scene_to_file("res://scenes/game.tscn")

func _on_waiting_timeout() -> void:
	# Проверяем статус игры
	if waiting_game_id > 0:
		ApiClient.get_game_state(waiting_game_id)

func _on_game_state_updated(state: Dictionary) -> void:
	var status = state.get("status", "")

	# Если игра в статусе waiting - продолжаем ждать
	if status == "waiting":
		status_label.text = "Ожидание принятия игры противником..."
		return

	# Если игра стала активной - переходим
	if status == "in_progress":
		waiting_timer.stop()
		waiting_game_id = 0
		GameManager.current_game_id = state.get("game_id", 0)
		get_tree().change_scene_to_file("res://scenes/game.tscn")
		return

	# Если игра отменена или завершена
	if status == "completed" or status == "cancelled":
		waiting_timer.stop()
		waiting_game_id = 0
		status_label.text = "Игра завершена"
		start_button.disabled = false

func _on_error(message: String) -> void:
	status_label.text = "Ошибка: " + message
	start_button.disabled = false
	waiting_timer.stop()
	waiting_game_id = 0

func _display_battles_list() -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("console.log('[Main] _display_battles_list called');")
	# Очищаем список
	for child in pending_list.get_children():
		child.queue_free()

	var has_battles = false

	# Показываем ожидающие игры (вызовы на бой)
	for game in pending_games:
		has_battles = true
		var hbox = HBoxContainer.new()
		hbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL

		var label = Label.new()
		label.text = "⚔️ %s вызывает вас!" % game.get("player1_name", "???")
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		hbox.add_child(label)

		# Выбор армии
		var army_select = OptionButton.new()
		army_select.custom_minimum_size = Vector2(150, 0)
		var player_armies = game.get("player_armies", [])
		for i in range(player_armies.size()):
			var army = player_armies[i]
			var army_name = army.get("army_name", "Армия")
			var army_cost = army.get("army_cost", 0)
			var is_matching = army.get("is_matching", false)
			var prefix = "✅ " if is_matching else "⚠️ "
			army_select.add_item(prefix + army_name + " (%.0f)" % army_cost, army.get("army_id", 0))
		hbox.add_child(army_select)

		var accept_btn = Button.new()
		accept_btn.text = "Принять"
		accept_btn.pressed.connect(_on_accept_game.bind(game.get("game_id", 0), army_select))
		hbox.add_child(accept_btn)

		var decline_btn = Button.new()
		decline_btn.text = "Отклонить"
		decline_btn.pressed.connect(_on_decline_game.bind(game.get("game_id", 0)))
		hbox.add_child(decline_btn)

		pending_list.add_child(hbox)

	# Показываем активные игры
	for game in active_games:
		has_battles = true
		var hbox = HBoxContainer.new()
		hbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL

		var opponent_name = game.get("player2_name", "???")
		if game.get("player2_id") == current_player.get("id"):
			opponent_name = game.get("player1_name", "???")

		var label = Label.new()
		var turn_text = " (ваш ход)" if game.get("is_my_turn", false) else ""
		label.text = "🎮 vs %s%s" % [opponent_name, turn_text]
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		hbox.add_child(label)

		var continue_btn = Button.new()
		continue_btn.text = "Продолжить"
		continue_btn.pressed.connect(_on_continue_game.bind(game.get("game_id", 0)))
		hbox.add_child(continue_btn)

		pending_list.add_child(hbox)

	# Показываем историю (последние 5)
	var history_shown = 0
	for game in history_games:
		if history_shown >= 5:
			break
		has_battles = true
		var hbox = HBoxContainer.new()
		hbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL

		var opponent_name = game.get("player2_name", "???")
		if game.get("player2_id") == current_player.get("id"):
			opponent_name = game.get("player1_name", "???")

		var result_icon = "🏆" if game.get("winner_id") == current_player.get("id") else "💀"
		var label = Label.new()
		label.text = "%s vs %s" % [result_icon, opponent_name]
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		label.modulate = Color(0.6, 0.6, 0.6)
		hbox.add_child(label)

		pending_list.add_child(hbox)
		history_shown += 1

	pending_panel.visible = has_battles
	if OS.has_feature("web"):
		JavaScriptBridge.eval("console.log('[Main] _display_battles_list done, has_battles=%s, panel.visible=%s');" % [str(has_battles), str(pending_panel.visible)])

func _on_accept_game(game_id: int, army_select: OptionButton) -> void:
	var selected_idx = army_select.selected
	var army_id = 0
	if selected_idx >= 0:
		army_id = army_select.get_item_id(selected_idx)
	GameManager.accept_game(game_id, current_player.get("id", 0))
	ApiClient.accept_game(game_id, current_player.get("id", 0), army_id)

func _on_decline_game(game_id: int) -> void:
	ApiClient.decline_game(game_id)
	# Обновляем список
	_check_pending_games()

func _on_continue_game(game_id: int) -> void:
	GameManager.current_game_id = game_id
	get_tree().change_scene_to_file("res://scenes/game.tscn")

func _on_back_pressed() -> void:
	waiting_timer.stop()
	waiting_game_id = 0
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.location.href = '/arena/';")
