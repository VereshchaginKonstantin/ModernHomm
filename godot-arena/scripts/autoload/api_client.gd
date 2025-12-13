extends Node
## API Client для связи с бэкендом арены

signal request_completed(result: Dictionary)
signal request_failed(error: String)

# API Base URL - определяется из текущего URL в браузере
# Используем публичный API без авторизации для Godot WebGL
var api_base: String = "/arena/api/public"

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
	# Используем публичный API без авторизации для Godot WebGL
	var js_code = """
		(function() {
			return window.location.origin + '/arena/api/public';
		})()
	"""
	var result = JavaScriptBridge.eval(js_code)
	if result:
		api_base = result

## Получить текущего залогиненного пользователя
func get_current_player() -> void:
	# Получаем player_id из URL параметров
	var player_id = 0
	if OS.has_feature("web"):
		var js_code = """
			(function() {
				var params = new URLSearchParams(window.location.search);
				return params.get('player_id') || '';
			})()
		"""
		var result = JavaScriptBridge.eval(js_code)
		if result:
			player_id = int(result)

	var url = api_base + "/me?player_id=" + str(player_id)
	_make_request(url, HTTPClient.METHOD_GET)

## Получить список игроков
func get_players() -> void:
	var url = api_base + "/players"
	_make_request(url, HTTPClient.METHOD_GET)

## Получить состояние игры
func get_game_state(game_id: int) -> void:
	var url = api_base + "/games/%d/state" % game_id
	_make_request(url, HTTPClient.METHOD_GET)

## Получить доступные действия юнита
func get_unit_actions(game_id: int, unit_id: int) -> void:
	var url = api_base + "/games/%d/units/%d/actions" % [game_id, unit_id]
	_make_request(url, HTTPClient.METHOD_GET)

## Создать игру
func create_game(player1_id: int, opponent_name: String, field_size: String) -> void:
	var url = api_base + "/games/create"
	var body = JSON.stringify({
		"player1_id": player1_id,
		"player2_name": opponent_name,
		"field_size": field_size
	})
	_make_request(url, HTTPClient.METHOD_POST, body)

## Принять игру
func accept_game(game_id: int, player_id: int) -> void:
	var url = api_base + "/games/%d/accept" % game_id
	var body = JSON.stringify({"player_id": player_id})
	_make_request(url, HTTPClient.METHOD_POST, body)

## Отклонить игру
func decline_game(game_id: int) -> void:
	var url = api_base + "/games/%d/decline" % game_id
	_make_request(url, HTTPClient.METHOD_POST, "{}")

## Выполнить ход (перемещение)
func move_unit(game_id: int, player_id: int, unit_id: int, x: int, y: int) -> void:
	var url = api_base + "/games/%d/move" % game_id
	var body = JSON.stringify({
		"player_id": player_id,
		"unit_id": unit_id,
		"action": "move",
		"target_x": x,
		"target_y": y
	})
	_make_request(url, HTTPClient.METHOD_POST, body)

## Выполнить атаку
func attack_unit(game_id: int, player_id: int, attacker_id: int, target_id: int) -> void:
	var url = api_base + "/games/%d/move" % game_id
	var body = JSON.stringify({
		"player_id": player_id,
		"unit_id": attacker_id,
		"action": "attack",
		"target_id": target_id
	})
	_make_request(url, HTTPClient.METHOD_POST, body)

## Пропустить ход юнита
func skip_unit(game_id: int, player_id: int, unit_id: int) -> void:
	var url = api_base + "/games/%d/move" % game_id
	var body = JSON.stringify({
		"player_id": player_id,
		"unit_id": unit_id,
		"action": "skip"
	})
	_make_request(url, HTTPClient.METHOD_POST, body)

## Отложить ход юнита
func defer_unit(game_id: int, player_id: int, unit_id: int) -> void:
	var url = api_base + "/games/%d/move" % game_id
	var body = JSON.stringify({
		"player_id": player_id,
		"unit_id": unit_id,
		"action": "defer"
	})
	_make_request(url, HTTPClient.METHOD_POST, body)

## Получить ожидающие игры
func get_pending_games(player_id: int) -> void:
	var url = api_base + "/games/pending?player_id=%d" % player_id
	_make_request(url, HTTPClient.METHOD_GET)

## Внутренний метод для выполнения запросов
func _make_request(url: String, method: int, body: String = "") -> void:
	var headers = ["Content-Type: application/json"]

	if method == HTTPClient.METHOD_GET:
		http_request.request(url, headers, method)
	else:
		http_request.request(url, headers, method, body)

## Обработка ответа
func _on_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	# Отладочная информация в консоль браузера
	if OS.has_feature("web"):
		JavaScriptBridge.eval("console.log('API Response: result=%d, code=%d');" % [result, response_code])

	if result != HTTPRequest.RESULT_SUCCESS:
		var error_msg = "Network error: " + str(result)
		if OS.has_feature("web"):
			JavaScriptBridge.eval("console.error('API Error: %s');" % error_msg)
		request_failed.emit(error_msg)
		return

	if response_code < 200 or response_code >= 300:
		var error_msg = "HTTP error: " + str(response_code)
		if OS.has_feature("web"):
			JavaScriptBridge.eval("console.error('API Error: %s');" % error_msg)
		request_failed.emit(error_msg)
		return

	var json_string = body.get_string_from_utf8()
	var json = JSON.new()
	var parse_result = json.parse(json_string)

	if parse_result != OK:
		var error_msg = "JSON parse error"
		if OS.has_feature("web"):
			JavaScriptBridge.eval("console.error('API Error: %s, body=%s');" % [error_msg, json_string.substr(0, 100)])
		request_failed.emit(error_msg)
		return

	if OS.has_feature("web"):
		JavaScriptBridge.eval("console.log('API Success: ' + JSON.stringify(%s).substr(0, 200));" % JSON.stringify(json.data))
	request_completed.emit(json.data)
