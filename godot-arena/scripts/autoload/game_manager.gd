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
var polling_interval: float = 1.0  # Уменьшен для более быстрого обновления

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
			return params.get('game_id') || '';
		})()
	"""
	var result = JavaScriptBridge.eval(js_code)
	if result and result != "":
		current_game_id = int(result)
		# Только запускаем игру если пользователь авторизован
		if current_game_id > 0 and ApiClient.is_authenticated():
			current_player_id = ApiClient.player_id
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
		current_player_id = ApiClient.player_id
	refresh_game_state()
	start_polling()

## Обновить состояние игры
func refresh_game_state() -> void:
	if current_game_id > 0:
		RemoteLogger.debug("Refreshing game state", {"game_id": current_game_id})
		ApiClient.get_game_state(current_game_id)

## Создать новую игру
func create_game(opponent_name: String, field_size: String) -> void:
	current_player_id = ApiClient.player_id
	ApiClient.create_game(opponent_name, field_size)

## Принять игру
func accept_game(game_id: int, army_id: int = 0) -> void:
	current_player_id = ApiClient.player_id
	ApiClient.accept_game(game_id, army_id)

## Выбрать юнита
func select_unit(unit: Dictionary) -> void:
	# Обновляем current_player_id из ApiClient если не установлен
	if current_player_id == 0:
		current_player_id = ApiClient.player_id

	var unit_id = int(unit.get("id", 0))

	# Получаем актуальные данные юнита из game_state (а не из переданного словаря)
	var actual_unit = get_unit_by_id(unit_id)
	if actual_unit.is_empty():
		# Если юнит не найден в game_state, используем переданные данные
		actual_unit = unit

	RemoteLogger.debug("Selecting unit", {
		"unit_id": unit_id,
		"unit_player_id": actual_unit.get("player_id"),
		"current_player_id": current_player_id,
		"game_current_player": game_state.get("current_player_id"),
		"has_moved": actual_unit.get("has_moved", 0)
	})

	# Проверяем можно ли выбрать юнита
	if actual_unit.get("player_id") != current_player_id:
		error_occurred.emit("Это юнит противника!")
		return

	if not is_my_turn():
		error_occurred.emit("Сейчас не ваш ход!")
		return

	if actual_unit.get("has_moved", 0) == 1:
		error_occurred.emit("Этот юнит уже ходил!")
		return

	selected_unit = actual_unit
	current_actions = {}
	if unit_id > 0:
		ApiClient.get_unit_actions(current_game_id, unit_id)
	else:
		error_occurred.emit("Некорректный ID юнита")

## Отменить выбор юнита
func deselect_unit() -> void:
	selected_unit = {}
	current_actions = {}

## Переместить выбранного юнита
func move_selected_unit(x: int, y: int) -> void:
	if selected_unit.is_empty():
		return
	var unit_id = selected_unit.get("id", 0)
	if unit_id > 0:
		ApiClient.move_unit(current_game_id, unit_id, x, y)
	deselect_unit()

## Атаковать выбранным юнитом
func attack_with_selected_unit(target_id: int) -> void:
	if selected_unit.is_empty():
		return
	var unit_id = selected_unit.get("id", 0)
	if unit_id > 0:
		ApiClient.attack_unit(current_game_id, unit_id, target_id)
	deselect_unit()

## Пропустить ход юнита
func skip_selected_unit() -> void:
	if selected_unit.is_empty():
		return
	var unit_id = selected_unit.get("id", 0)
	if unit_id > 0:
		ApiClient.skip_unit(current_game_id, unit_id)
	deselect_unit()

## Отложить ход юнита
func defer_selected_unit() -> void:
	if selected_unit.is_empty():
		return
	var unit_id = selected_unit.get("id", 0)
	if unit_id > 0:
		ApiClient.defer_unit(current_game_id, unit_id)
	deselect_unit()

## Сдаться в текущей игре
func surrender_game() -> void:
	if current_game_id > 0:
		ApiClient.surrender_game(current_game_id)
		stop_polling()

## Проверить мой ли ход
func is_my_turn() -> bool:
	return game_state.get("current_player_id") == current_player_id

## Получить юнита по ID
func get_unit_by_id(unit_id: int) -> Dictionary:
	for unit in game_state.get("units", []):
		if int(unit.get("id", 0)) == unit_id:
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
	# Всегда переключаем сцену внутри Godot (не редирект на веб)
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

		# Устанавливаем current_player_id если не установлен
		if current_player_id == 0:
			current_player_id = ApiClient.player_id

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

	elif data.has("moves") or data.has("attacks") or data.has("can_move") or data.has("can_attack"):
		# Это действия юнита - нормализуем названия ключей
		if data.has("moves"):
			current_actions["can_move"] = data.get("moves", [])
		else:
			current_actions["can_move"] = data.get("can_move", [])

		if data.has("attacks"):
			current_actions["can_attack"] = data.get("attacks", [])
		else:
			current_actions["can_attack"] = data.get("can_attack", [])

		unit_actions_received.emit(current_actions)

	elif data.has("success"):
		# Это результат действия
		RemoteLogger.info("Move completed", {"success": data.success, "message": data.get("message", "")})
		move_completed.emit(data)
		if data.success:
			# Немедленно обновляем состояние игры после успешного хода
			refresh_game_state()

func _on_api_error(error_message: String) -> void:
	error_occurred.emit(error_message)
	RemoteLogger.error("GameManager API error", {"message": error_message})

	# Останавливаем polling при ошибках авторизации чтобы избежать бесконечных запросов
	if "Unauthorized" in error_message or "401" in error_message or "TOKEN" in error_message:
		RemoteLogger.warning("Stopping polling due to auth error")
		stop_polling()
