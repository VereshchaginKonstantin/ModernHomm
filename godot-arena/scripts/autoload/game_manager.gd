extends Node
## Менеджер игры - управление состоянием и игровой логикой

signal game_state_updated(state: Dictionary)
signal unit_actions_received(actions: Dictionary)
signal move_completed(result: Dictionary)
signal game_over(winner_id: int, winner_name: String)
signal turn_changed(current_player_id: int)
signal error_occurred(message: String)
signal players_loaded(players: Array)
signal current_player_loaded(player: Dictionary)

# Текущее состояние
var current_game_id: int = 0
var current_player_id: int = 0
var game_state: Dictionary = {}
var selected_unit: Dictionary = {}
var current_actions: Dictionary = {}
var players: Array = []

# Polling
var polling_timer: Timer
var polling_interval: float = 2.0

func _ready() -> void:
	# Подключаем сигналы API клиента
	ApiClient.request_completed.connect(_on_api_response)
	ApiClient.request_failed.connect(_on_api_error)

	# Создаём таймер для polling
	polling_timer = Timer.new()
	polling_timer.wait_time = polling_interval
	polling_timer.timeout.connect(_on_polling_timeout)
	add_child(polling_timer)

	# Проверяем URL параметры в браузере
	if OS.has_feature("web"):
		_check_url_params()

func _check_url_params() -> void:
	var js_code = """
		(function() {
			var params = new URLSearchParams(window.location.search);
			return JSON.stringify({
				game_id: params.get('game_id'),
				player_id: params.get('player_id')
			});
		})()
	"""
	var result = JavaScriptBridge.eval(js_code)
	if result:
		var json = JSON.new()
		if json.parse(result) == OK:
			var data = json.data
			if data.get("game_id"):
				current_game_id = int(data.game_id)
			if data.get("player_id"):
				current_player_id = int(data.player_id)
				_save_player_id(current_player_id)
			if current_game_id > 0:
				start_game(current_game_id)

func _save_player_id(player_id: int) -> void:
	if OS.has_feature("web"):
		JavaScriptBridge.eval("localStorage.setItem('player_id', '%d');" % player_id)

func _load_player_id() -> int:
	if OS.has_feature("web"):
		var result = JavaScriptBridge.eval("localStorage.getItem('player_id');")
		if result:
			return int(result)
	return 0

## Загрузить текущего залогиненного пользователя
func load_current_player() -> void:
	ApiClient.get_current_player()

## Загрузить список игроков
func load_players() -> void:
	ApiClient.get_players()

## Начать игру
func start_game(game_id: int) -> void:
	current_game_id = game_id
	if current_player_id == 0:
		current_player_id = _load_player_id()
	refresh_game_state()
	start_polling()

## Обновить состояние игры
func refresh_game_state() -> void:
	if current_game_id > 0:
		ApiClient.get_game_state(current_game_id)

## Создать новую игру
func create_game(player1_id: int, opponent_name: String, field_size: String) -> void:
	current_player_id = player1_id
	_save_player_id(player1_id)
	ApiClient.create_game(player1_id, opponent_name, field_size)

## Принять игру
func accept_game(game_id: int, player_id: int) -> void:
	current_player_id = player_id
	_save_player_id(player_id)
	ApiClient.accept_game(game_id, player_id)

## Выбрать юнита
func select_unit(unit: Dictionary) -> void:
	# Проверяем можно ли выбрать юнита
	if unit.get("player_id") != current_player_id:
		error_occurred.emit("Это юнит противника!")
		return

	if not is_my_turn():
		error_occurred.emit("Сейчас не ваш ход!")
		return

	if unit.get("has_moved", 0) == 1:
		error_occurred.emit("Этот юнит уже ходил!")
		return

	selected_unit = unit
	current_actions = {}
	ApiClient.get_unit_actions(current_game_id, unit.id)

## Отменить выбор юнита
func deselect_unit() -> void:
	selected_unit = {}
	current_actions = {}

## Переместить выбранного юнита
func move_selected_unit(x: int, y: int) -> void:
	if selected_unit.is_empty():
		return
	ApiClient.move_unit(current_game_id, current_player_id, selected_unit.id, x, y)
	deselect_unit()

## Атаковать выбранным юнитом
func attack_with_selected_unit(target_id: int) -> void:
	if selected_unit.is_empty():
		return
	ApiClient.attack_unit(current_game_id, current_player_id, selected_unit.id, target_id)
	deselect_unit()

## Пропустить ход юнита
func skip_selected_unit() -> void:
	if selected_unit.is_empty():
		return
	ApiClient.skip_unit(current_game_id, current_player_id, selected_unit.id)
	deselect_unit()

## Отложить ход юнита
func defer_selected_unit() -> void:
	if selected_unit.is_empty():
		return
	ApiClient.defer_unit(current_game_id, current_player_id, selected_unit.id)
	deselect_unit()

## Проверить мой ли ход
func is_my_turn() -> bool:
	return game_state.get("current_player_id") == current_player_id

## Получить юнита по ID
func get_unit_by_id(unit_id: int) -> Dictionary:
	for unit in game_state.get("units", []):
		if unit.get("id") == unit_id:
			return unit
	return {}

## Получить юнита по позиции
func get_unit_at_position(x: int, y: int) -> Dictionary:
	for unit in game_state.get("units", []):
		if unit.get("x") == x and unit.get("y") == y:
			return unit
	return {}

## Проверить можно ли двигаться в позицию
func can_move_to(x: int, y: int) -> bool:
	for move in current_actions.get("can_move", []):
		if move.get("x") == x and move.get("y") == y:
			return true
	return false

## Проверить можно ли атаковать юнита
func can_attack(unit_id: int) -> bool:
	for target in current_actions.get("can_attack", []):
		if target.get("id") == unit_id:
			return true
	return false

## Вернуться в главное меню
func return_to_menu() -> void:
	stop_polling()
	deselect_unit()
	current_game_id = 0
	game_state = {}
	if OS.has_feature("web"):
		JavaScriptBridge.eval("window.location.href = '/arena/';")
	else:
		get_tree().change_scene_to_file("res://scenes/main.tscn")

## Начать polling
func start_polling() -> void:
	polling_timer.start()

## Остановить polling
func stop_polling() -> void:
	polling_timer.stop()

func _on_polling_timeout() -> void:
	if current_game_id > 0 and not game_state.get("is_game_over", false):
		refresh_game_state()

## Обработка ответа API
func _on_api_response(data: Dictionary) -> void:
	# Определяем тип ответа по содержимому
	if data.has("current_player"):
		# Это ответ на запрос текущего пользователя
		var player = data.get("current_player", {})
		if not player.is_empty():
			current_player_id = player.get("id", 0)
		current_player_loaded.emit(player)

	elif data.has("players"):
		players = data.players
		players_loaded.emit(players)

	elif data.has("game_id") and data.has("units"):
		# Это состояние игры
		var old_current_player = game_state.get("current_player_id", 0)
		game_state = data

		# Проверяем смену хода
		if old_current_player != 0 and old_current_player != game_state.current_player_id:
			turn_changed.emit(game_state.current_player_id)

		# Проверяем конец игры
		if game_state.get("is_game_over", false):
			stop_polling()
			var winner_id = game_state.get("winner_id", 0)
			var winner_name = ""
			if winner_id == game_state.get("player1_id"):
				winner_name = game_state.get("player1_name", "Игрок 1")
			else:
				winner_name = game_state.get("player2_name", "Игрок 2")
			game_over.emit(winner_id, winner_name)

		game_state_updated.emit(game_state)

	elif data.has("can_move") or data.has("can_attack"):
		# Это действия юнита
		current_actions = data
		unit_actions_received.emit(data)

	elif data.has("success"):
		# Это результат действия
		move_completed.emit(data)
		if data.success:
			refresh_game_state()

func _on_api_error(error_message: String) -> void:
	error_occurred.emit(error_message)
	push_error("API Error: " + error_message)
