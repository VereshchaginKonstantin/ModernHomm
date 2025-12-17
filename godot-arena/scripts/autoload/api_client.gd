extends Node
## API Client для связи с бэкендом арены с JWT аутентификацией

signal request_completed(result: Dictionary)
signal request_failed(error: String)
signal auth_required()  # Сигнал когда требуется авторизация

# API Base URL - определяется из текущего URL в браузере
var api_base: String = "/arena/api/public"

# Токен авторизации и данные игрока
var auth_token: String = ""
var player_id: int = 0
var player_name: String = ""

# HTTP Request node
var http_request: HTTPRequest

func _ready() -> void:
	http_request = HTTPRequest.new()
	# В WebGL отключаем threads чтобы избежать CORS проблем с SharedArrayBuffer
	http_request.use_threads = false
	add_child(http_request)
	http_request.request_completed.connect(_on_request_completed)

	# В браузере получаем базовый URL из JavaScript
	if OS.has_feature("web"):
		_init_web_api_base()

func _init_web_api_base() -> void:
	# Получаем origin из JavaScript
	var js_code = """
		(function() {
			return window.location.origin + '/arena/api/public';
		})()
	"""
	var result = JavaScriptBridge.eval(js_code)
	if result:
		api_base = result

## Проверить авторизован ли пользователь
func is_authenticated() -> bool:
	return auth_token != "" and player_id > 0

## Очистить данные авторизации
func logout() -> void:
	auth_token = ""
	player_id = 0
	player_name = ""

## Логин с паролем
func login(username: String, password: String) -> void:
	var url = api_base + "/login"
	var body = JSON.stringify({
		"username": username,
		"password": password
	})
	_make_request(url, HTTPClient.METHOD_POST, body, false)

## Проверить статус пароля пользователя
func check_password_status(username: String) -> void:
	var url = api_base + "/check_password_status"
	var body = JSON.stringify({"username": username})
	_make_request(url, HTTPClient.METHOD_POST, body, false)

## Установить пароль (для пользователей без пароля)
func set_password(username: String, password: String) -> void:
	var url = api_base + "/set_password"
	var body = JSON.stringify({
		"username": username,
		"password": password
	})
	_make_request(url, HTTPClient.METHOD_POST, body, false)

## Сменить пароль
func change_password(old_password: String, new_password: String) -> void:
	var url = api_base + "/change_password"
	var body = JSON.stringify({
		"old_password": old_password,
		"new_password": new_password
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true)

## Получить текущего залогиненного пользователя
func get_current_player() -> void:
	var url = api_base + "/me"
	_make_request(url, HTTPClient.METHOD_GET, "", true)

## Получить список игроков (не требует авторизации)
func get_players() -> void:
	var url = api_base + "/players"
	_make_request(url, HTTPClient.METHOD_GET, "", false)

## Получить состояние игры
func get_game_state(game_id: int) -> void:
	var url = api_base + "/games/%d/state" % game_id
	_make_request(url, HTTPClient.METHOD_GET, "", true)

## Получить доступные действия юнита
func get_unit_actions(game_id: int, unit_id: int) -> void:
	var url = api_base + "/games/%d/units/%d/actions" % [game_id, unit_id]
	_make_request(url, HTTPClient.METHOD_GET, "", true)

## Создать игру
func create_game(opponent_name: String, field_size: String) -> void:
	var url = api_base + "/games/create"
	var body = JSON.stringify({
		"player2_name": opponent_name,
		"field_size": field_size
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true)

## Принять игру с выбором армии
func accept_game(game_id: int, army_id: int = 0) -> void:
	var url = api_base + "/games/%d/accept" % game_id
	var body_data = {}
	if army_id > 0:
		body_data["army_id"] = army_id
	var body = JSON.stringify(body_data)
	_make_request(url, HTTPClient.METHOD_POST, body, true)

## Отклонить игру
func decline_game(game_id: int) -> void:
	var url = api_base + "/games/%d/decline" % game_id
	_make_request(url, HTTPClient.METHOD_POST, "{}", true)

## Выполнить ход (перемещение)
func move_unit(game_id: int, unit_id: int, x: int, y: int) -> void:
	var url = api_base + "/games/%d/move" % game_id
	var body = JSON.stringify({
		"unit_id": unit_id,
		"action": "move",
		"target_x": x,
		"target_y": y
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true)

## Выполнить атаку
func attack_unit(game_id: int, attacker_id: int, target_id: int) -> void:
	var url = api_base + "/games/%d/move" % game_id
	var body = JSON.stringify({
		"unit_id": attacker_id,
		"action": "attack",
		"target_id": target_id
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true)

## Пропустить ход юнита
func skip_unit(game_id: int, unit_id: int) -> void:
	var url = api_base + "/games/%d/move" % game_id
	var body = JSON.stringify({
		"unit_id": unit_id,
		"action": "skip"
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true)

## Отложить ход юнита
func defer_unit(game_id: int, unit_id: int) -> void:
	var url = api_base + "/games/%d/move" % game_id
	var body = JSON.stringify({
		"unit_id": unit_id,
		"action": "defer"
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true)

## Сдаться в игре
func surrender_game(game_id: int) -> void:
	var url = api_base + "/games/%d/surrender" % game_id
	_make_request(url, HTTPClient.METHOD_POST, "", true)

## Получить ожидающие игры
func get_pending_games() -> void:
	var url = api_base + "/games/pending"
	_make_request(url, HTTPClient.METHOD_GET, "", true)

## ============= Army Management =============

## Получить список армий
func get_armies() -> void:
	var url = api_base + "/armies"
	_make_request(url, HTTPClient.METHOD_GET, "", true)

## Создать новую армию
func create_army(army_name: String, user_race_id: int = 0) -> void:
	var url = api_base + "/armies/create"
	var body_data = {"name": army_name}
	if user_race_id > 0:
		body_data["user_race_id"] = user_race_id
	_make_request(url, HTTPClient.METHOD_POST, JSON.stringify(body_data), true)

## Получить детали армии
func get_army(army_id: int) -> void:
	var url = api_base + "/armies/%d" % army_id
	_make_request(url, HTTPClient.METHOD_GET, "", true)

## Удалить армию
func delete_army(army_id: int) -> void:
	var url = api_base + "/armies/%d/delete" % army_id
	_make_request(url, HTTPClient.METHOD_POST, "{}", true)

## Получить доступных юнитов для найма
func get_available_units(army_id: int) -> void:
	var url = api_base + "/armies/%d/available_units" % army_id
	_make_request(url, HTTPClient.METHOD_GET, "", true)

## Нанять юнитов в армию
func hire_unit(army_id: int, race_unit_id: int, count: int = 1) -> void:
	var url = api_base + "/armies/%d/hire" % army_id
	var body = JSON.stringify({
		"race_unit_id": race_unit_id,
		"count": count
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true)

## Распустить юнитов из армии
func dismiss_unit(army_id: int, race_unit_id: int, count: int = 1) -> void:
	var url = api_base + "/armies/%d/dismiss" % army_id
	var body = JSON.stringify({
		"race_unit_id": race_unit_id,
		"count": count
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true)

## Получить расы игрока
func get_user_races() -> void:
	var url = api_base + "/user_races"
	_make_request(url, HTTPClient.METHOD_GET, "", true)

## Сохранить токен и данные игрока после успешного логина
func _save_auth_data(data: Dictionary) -> void:
	if data.has("token"):
		auth_token = data["token"]
	if data.has("player"):
		var p = data["player"]
		player_id = p.get("id", 0)
		player_name = p.get("name", "")

## Внутренний метод для выполнения запросов
func _make_request(url: String, method: int, body: String = "", requires_auth: bool = true) -> void:
	var headers = ["Content-Type: application/json"]

	# Добавляем токен авторизации если требуется
	if requires_auth and auth_token != "":
		headers.append("Authorization: Bearer " + auth_token)

	if method == HTTPClient.METHOD_GET:
		http_request.request(url, headers, method)
	else:
		http_request.request(url, headers, method, body)

## Обработка ответа
func _on_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS:
		RemoteLogger.error("Network error", {"result": result})
		request_failed.emit("Network error: " + str(result))
		return

	var json_string = body.get_string_from_utf8()
	var json = JSON.new()
	var parse_result = json.parse(json_string)

	if parse_result != OK:
		RemoteLogger.error("JSON parse error", {"body": json_string.substr(0, 500)})
		request_failed.emit("JSON parse error")
		return

	var data = json.data

	# Проверяем на ошибки авторизации
	if response_code == 401:
		var code = data.get("code", "")
		RemoteLogger.warning("Auth error 401", {"code": code, "error": data.get("error", "")})
		if code == "TOKEN_MISSING" or code == "TOKEN_INVALID":
			auth_required.emit()
		request_failed.emit(data.get("error", "Unauthorized"))
		return

	if response_code < 200 or response_code >= 300:
		RemoteLogger.error("HTTP error", {"code": response_code, "error": data.get("error", "")})
		request_failed.emit(data.get("error", "HTTP error: " + str(response_code)))
		return

	# Сохраняем данные авторизации если есть токен
	if data.has("token"):
		_save_auth_data(data)

	request_completed.emit(data)
