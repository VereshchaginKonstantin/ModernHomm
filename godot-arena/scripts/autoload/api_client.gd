extends Node
## API Client для связи с бэкендом арены с JWT аутентификацией

signal request_completed(result: Dictionary)
signal request_failed(error: String)
signal auth_required()  # Сигнал когда требуется авторизация
signal debug_auth_checked(enabled: bool)  # Сигнал после проверки debug auth

# API Base URL - определяется из текущего URL в браузере
var api_base: String = "/arena/api/public"

# Токен авторизации и данные игрока
var auth_token: String = ""
var player_id: int = 0
var player_name: String = ""

# Режим дебага - аутентификация через URL параметр player_id
var debug_mode: bool = false

# HTTP Request nodes - отдельные для разных типов запросов чтобы не блокировать друг друга
var http_request: HTTPRequest  # Для polling (get_game_state)
var action_request: HTTPRequest  # Для действий (move, attack, и т.д.)
var ui_request: HTTPRequest  # Для UI запросов (players, pending_games)
var army_request: HTTPRequest  # Для запросов армий (отдельный чтобы не конфликтовать с players)

func _ready() -> void:
	# Основной запрос для polling
	http_request = HTTPRequest.new()
	http_request.use_threads = false
	add_child(http_request)
	http_request.request_completed.connect(_on_request_completed)

	# Отдельный запрос для действий игрока
	action_request = HTTPRequest.new()
	action_request.use_threads = false
	add_child(action_request)
	action_request.request_completed.connect(_on_request_completed)

	# Отдельный запрос для UI (игроки, ожидающие игры)
	ui_request = HTTPRequest.new()
	ui_request.use_threads = false
	add_child(ui_request)
	ui_request.request_completed.connect(_on_request_completed)

	# Отдельный запрос для армий
	army_request = HTTPRequest.new()
	army_request.use_threads = false
	add_child(army_request)
	army_request.request_completed.connect(_on_request_completed)

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

	# Проверяем URL параметр player_id для режима дебага
	_check_debug_mode()

## Проверяет URL параметры для режима дебага
func _check_debug_mode() -> void:
	_js_log("_check_debug_mode called, is_web=" + str(OS.has_feature("web")))
	if not OS.has_feature("web"):
		return

	# Логируем полный URL для отладки
	var full_url = JavaScriptBridge.eval("window.location.href")
	var search_part = JavaScriptBridge.eval("window.location.search")
	_js_log("Full URL: " + str(full_url))
	_js_log("Search part: " + str(search_part))

	var js_code = """
		(function() {
			var params = new URLSearchParams(window.location.search);
			return params.get('player_id') || '';
		})()
	"""
	var result = JavaScriptBridge.eval(js_code)
	_js_log("URL player_id param: " + str(result))
	if result and result != "":
		var pid = int(result)
		if pid > 0:
			# Запоминаем потенциальный player_id, но ещё не включаем debug_mode
			# Он будет включен после проверки статуса на сервере
			_pending_debug_player_id = pid
			_js_log("Starting debug auth check, pending_player_id=" + str(pid))
			# Запрашиваем статус debug_auth с сервера
			_check_debug_auth_status()
		else:
			_js_log("player_id is not positive: " + str(pid))
	else:
		_js_log("No player_id in URL")

func _js_log(msg: String) -> void:
	if OS.has_feature("web"):
		# Экранируем спецсимволы для JavaScript
		var safe_msg = msg.replace("\\", "\\\\").replace("'", "\\'").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r")
		JavaScriptBridge.eval("console.log('[ApiClient] " + safe_msg + "')")

var _pending_debug_player_id: int = 0
var _debug_auth_check_completed: bool = false  # Флаг завершения проверки

## Проверяет статус debug_auth на сервере
func _check_debug_auth_status() -> void:
	_js_log("_check_debug_auth_status called, api_base=" + api_base)
	var check_request = HTTPRequest.new()
	check_request.use_threads = false
	add_child(check_request)
	check_request.request_completed.connect(_on_debug_auth_check_completed.bind(check_request))
	var url = api_base + "/debug/auth_status"
	_js_log("Requesting debug auth status: " + url)
	check_request.request(url)

func _on_debug_auth_check_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray, http_req: HTTPRequest) -> void:
	http_req.queue_free()
	_js_log("_on_debug_auth_check_completed: result=" + str(result) + ", code=" + str(response_code))

	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		_js_log("Failed to check debug auth status")
		_debug_auth_check_completed = true
		debug_auth_checked.emit(false)
		return

	var body_str = body.get_string_from_utf8()
	_js_log("Response body: " + body_str)
	var json = JSON.new()
	if json.parse(body_str) != OK:
		_js_log("Failed to parse debug auth response")
		_debug_auth_check_completed = true
		debug_auth_checked.emit(false)
		return

	var data = json.data
	var server_debug_auth = data.get("debug_auth", false)
	_js_log("Server debug_auth=" + str(server_debug_auth) + ", pending_player_id=" + str(_pending_debug_player_id))
	if server_debug_auth and _pending_debug_player_id > 0:
		debug_mode = true
		player_id = _pending_debug_player_id
		player_name = "Debug Player %d" % player_id
		_js_log("Debug auth ENABLED! player_id=" + str(player_id))
		_debug_auth_check_completed = true
		debug_auth_checked.emit(true)
	else:
		_js_log("Debug auth disabled by server")
		_pending_debug_player_id = 0
		_debug_auth_check_completed = true
		debug_auth_checked.emit(false)

## Проверить авторизован ли пользователь
func is_authenticated() -> bool:
	# В режиме дебага достаточно player_id
	if debug_mode and player_id > 0:
		return true
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

## Получить список игроков (не требует авторизации) - использует ui_request
func get_players() -> void:
	var url = api_base + "/players"
	_make_request(url, HTTPClient.METHOD_GET, "", false, RequestType.UI)

## Получить состояние игры
func get_game_state(game_id: int) -> void:
	var url = api_base + "/games/%d/state" % game_id
	_make_request(url, HTTPClient.METHOD_GET, "", true)

## Получить доступные действия юнита
func get_unit_actions(game_id: int, unit_id: int) -> void:
	var url = api_base + "/games/%d/units/%d/actions" % [game_id, unit_id]
	_make_request(url, HTTPClient.METHOD_GET, "", true)

## Создать игру
func create_game(opponent_name: String, field_size: String, army_id: int = 0) -> void:
	var url = api_base + "/games/create"
	var body_data = {
		"player2_name": opponent_name,
		"field_size": field_size
	}
	if army_id > 0:
		body_data["army_id"] = army_id
	_make_request(url, HTTPClient.METHOD_POST, JSON.stringify(body_data), true)

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

## Выполнить ход (перемещение) - использует action_request чтобы не блокироваться polling
func move_unit(game_id: int, unit_id: int, x: int, y: int) -> void:
	var url = api_base + "/games/%d/move" % game_id
	var body = JSON.stringify({
		"unit_id": unit_id,
		"action": "move",
		"target_x": x,
		"target_y": y
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true, RequestType.ACTION)

## Выполнить атаку - использует action_request
func attack_unit(game_id: int, attacker_id: int, target_id: int) -> void:
	var url = api_base + "/games/%d/move" % game_id
	var body = JSON.stringify({
		"unit_id": attacker_id,
		"action": "attack",
		"target_id": target_id
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true, RequestType.ACTION)

## Пропустить ход юнита - использует action_request
func skip_unit(game_id: int, unit_id: int) -> void:
	var url = api_base + "/games/%d/move" % game_id
	var body = JSON.stringify({
		"unit_id": unit_id,
		"action": "skip"
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true, RequestType.ACTION)

## Отложить ход юнита - использует action_request
func defer_unit(game_id: int, unit_id: int) -> void:
	var url = api_base + "/games/%d/move" % game_id
	var body = JSON.stringify({
		"unit_id": unit_id,
		"action": "defer"
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true, RequestType.ACTION)

## Сдаться в игре - использует action_request
func surrender_game(game_id: int) -> void:
	var url = api_base + "/games/%d/surrender" % game_id
	_make_request(url, HTTPClient.METHOD_POST, "", true, RequestType.ACTION)

## Получить ожидающие игры - использует ui_request
func get_pending_games() -> void:
	var url = api_base + "/games/pending"
	_make_request(url, HTTPClient.METHOD_GET, "", true, RequestType.UI)

## ============= Army Management =============

## Получить список армий - использует army_request
func get_armies() -> void:
	var url = api_base + "/armies"
	_make_request(url, HTTPClient.METHOD_GET, "", true, RequestType.ARMY)

## Создать новую армию - использует army_request
func create_army(army_name: String, user_race_id: int, army_type: String = "mercenary") -> void:
	var url = api_base + "/armies/create"
	var body_data = {
		"name": army_name,
		"user_race_id": user_race_id,
		"army_type": army_type
	}
	_make_request(url, HTTPClient.METHOD_POST, JSON.stringify(body_data), true, RequestType.ARMY)

## Получить детали армии - использует army_request
func get_army(army_id: int) -> void:
	var url = api_base + "/armies/%d" % army_id
	_make_request(url, HTTPClient.METHOD_GET, "", true, RequestType.ARMY)

## Удалить армию - использует army_request
func delete_army(army_id: int) -> void:
	var url = api_base + "/armies/%d/delete" % army_id
	_make_request(url, HTTPClient.METHOD_POST, "{}", true, RequestType.ARMY)

## Получить доступных юнитов для найма - использует army_request
func get_available_units(army_id: int) -> void:
	var url = api_base + "/armies/%d/available_units" % army_id
	_make_request(url, HTTPClient.METHOD_GET, "", true, RequestType.ARMY)

## Нанять юнитов в армию - использует army_request
func hire_unit(army_id: int, race_unit_id: int, count: int = 1) -> void:
	var url = api_base + "/armies/%d/hire" % army_id
	var body = JSON.stringify({
		"race_unit_id": race_unit_id,
		"count": count
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true, RequestType.ARMY)

## Распустить юнитов из армии - использует army_request
func dismiss_unit(army_id: int, race_unit_id: int, count: int = 1) -> void:
	var url = api_base + "/armies/%d/dismiss" % army_id
	var body = JSON.stringify({
		"race_unit_id": race_unit_id,
		"count": count
	})
	_make_request(url, HTTPClient.METHOD_POST, body, true, RequestType.ARMY)

## Получить расы игрока - использует army_request
func get_user_races() -> void:
	var url = api_base + "/user_races"
	_make_request(url, HTTPClient.METHOD_GET, "", true, RequestType.ARMY)

## ============= Unit Limits Management =============

## Получить лимиты найма юнитов - использует army_request
func get_unit_limits() -> void:
	var url = api_base + "/unit_limits"
	_make_request(url, HTTPClient.METHOD_GET, "", true, RequestType.ARMY)

## Разблокировать уровень юнитов за кристаллы - использует army_request
func unlock_unit_level(level: int) -> void:
	var url = api_base + "/unit_levels/%d/unlock" % level
	_make_request(url, HTTPClient.METHOD_POST, "{}", true, RequestType.ARMY)

## Увеличить скорость регенерации юнитов за кристаллы - использует army_request
func upgrade_recruit_speed(level: int) -> void:
	var url = api_base + "/unit_levels/%d/upgrade_speed" % level
	_make_request(url, HTTPClient.METHOD_POST, "{}", true, RequestType.ARMY)

## Сохранить токен и данные игрока после успешного логина
func _save_auth_data(data: Dictionary) -> void:
	if data.has("token"):
		auth_token = data["token"]
	if data.has("player"):
		var p = data["player"]
		player_id = p.get("id", 0)
		player_name = p.get("name", "")

## Типы запросов для выбора нужного HTTPRequest
enum RequestType { POLLING, ACTION, UI, ARMY, GENERAL }

## Внутренний метод для выполнения запросов
## request_type - какой HTTPRequest использовать (POLLING, ACTION, UI, ARMY)
func _make_request(url: String, method: int, body: String = "", requires_auth: bool = true, request_type: int = RequestType.POLLING) -> void:
	var headers = ["Content-Type: application/json"]

	# В режиме дебага добавляем player_id в заголовок
	if debug_mode and player_id > 0:
		headers.append("X-Debug-Player-Id: " + str(player_id))
	# Добавляем токен авторизации если требуется (только если не в режиме дебага)
	elif requires_auth and auth_token != "":
		headers.append("Authorization: Bearer " + auth_token)

	# Выбираем какой HTTPRequest использовать
	var req: HTTPRequest
	match request_type:
		RequestType.ACTION:
			req = action_request
		RequestType.UI:
			req = ui_request
		RequestType.ARMY:
			req = army_request
		_:
			req = http_request

	if method == HTTPClient.METHOD_GET:
		req.request(url, headers, method)
	else:
		req.request(url, headers, method, body)

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


# =============================================================================
# API для управления лимитами найма рас
# =============================================================================

## Получить все расы пользователя с лимитами найма
func get_user_races_with_limits() -> void:
	var url = api_base + "/user/races-with-limits"
	_make_request(url, HTTPClient.METHOD_GET, "", true, RequestType.GENERAL)


## Получить лимиты найма для конкретной расы
func get_race_unit_limits(user_race_id: int) -> void:
	var url = api_base + "/races/" + str(user_race_id) + "/unit-limits"
	_make_request(url, HTTPClient.METHOD_GET, "", true, RequestType.GENERAL)


## Разблокировать уровень найма для расы
func unlock_race_level(user_race_id: int, unit_level_id: int) -> void:
	var url = api_base + "/races/" + str(user_race_id) + "/unlock-level"
	var body = JSON.stringify({"unit_level_id": unit_level_id})
	_make_request(url, HTTPClient.METHOD_POST, body, true, RequestType.GENERAL)


## Увеличить скорость найма для расы
func upgrade_race_speed(user_race_id: int, unit_level_id: int, use_gems: bool = false) -> void:
	var url = api_base + "/races/" + str(user_race_id) + "/upgrade-speed"
	var body = JSON.stringify({"unit_level_id": unit_level_id, "use_gems": use_gems})
	_make_request(url, HTTPClient.METHOD_POST, body, true, RequestType.GENERAL)
