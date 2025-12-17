extends Node
## Удалённый логгер - отправляет логи на сервер для отладки

signal debug_mode_changed(enabled: bool)

# Настройки
var debug_mode: bool = true
var session_id: String = ""
var api_base: String = "/arena/api/public"

# Буфер логов для отправки пачками
var log_buffer: Array = []
var max_buffer_size: int = 20
var flush_interval: float = 5.0  # Отправлять каждые 5 секунд

# HTTP Request для отправки логов
var http_request: HTTPRequest
var flush_timer: Timer

func _ready() -> void:
	# Генерируем уникальный ID сессии
	session_id = _generate_session_id()

	# Инициализируем HTTP Request
	http_request = HTTPRequest.new()
	http_request.use_threads = false
	add_child(http_request)
	http_request.request_completed.connect(_on_logs_sent)

	# Таймер для периодической отправки
	flush_timer = Timer.new()
	flush_timer.wait_time = flush_interval
	flush_timer.timeout.connect(_flush_logs)
	flush_timer.autostart = true
	add_child(flush_timer)

	# Получаем base URL в браузере
	if OS.has_feature("web"):
		var js_code = """
			(function() {
				return window.location.origin + '/arena/api/public';
			})()
		"""
		var result = JavaScriptBridge.eval(js_code)
		if result:
			api_base = result

	# Проверяем статус debug mode на сервере
	_check_debug_status()

	# Логируем старт сессии
	info("Session started", {"user_agent": _get_user_agent()})

func _generate_session_id() -> String:
	var chars = "abcdefghijklmnopqrstuvwxyz0123456789"
	var result = ""
	for i in range(16):
		result += chars[randi() % chars.length()]
	return result

func _get_user_agent() -> String:
	if OS.has_feature("web"):
		return JavaScriptBridge.eval("navigator.userAgent") or "unknown"
	return "Godot " + Engine.get_version_info().string

func _check_debug_status() -> void:
	var url = api_base + "/debug/status"
	var check_http = HTTPRequest.new()
	check_http.use_threads = false
	add_child(check_http)
	check_http.request_completed.connect(_on_debug_status_received.bind(check_http))
	check_http.request(url)

func _on_debug_status_received(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray, http_node: HTTPRequest) -> void:
	http_node.queue_free()

	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		return

	var json = JSON.new()
	if json.parse(body.get_string_from_utf8()) == OK:
		var data = json.data
		if data.has("debug_mode"):
			debug_mode = data.debug_mode
			debug_mode_changed.emit(debug_mode)

## Логирование с уровнем ERROR
func error(message: String, context: Dictionary = {}) -> void:
	_log("error", message, context)
	push_error("RemoteLog: " + message)

## Логирование с уровнем WARNING
func warning(message: String, context: Dictionary = {}) -> void:
	_log("warning", message, context)
	push_warning("RemoteLog: " + message)

## Логирование с уровнем INFO
func info(message: String, context: Dictionary = {}) -> void:
	_log("info", message, context)

## Логирование с уровнем DEBUG
func debug(message: String, context: Dictionary = {}) -> void:
	_log("debug", message, context)

## Внутренняя функция логирования
func _log(level: String, message: String, context: Dictionary) -> void:
	if not debug_mode:
		return

	log_buffer.append({
		"level": level,
		"message": message,
		"context": context,
		"timestamp": Time.get_datetime_string_from_system()
	})

	# Если буфер переполнен - отправляем немедленно
	if log_buffer.size() >= max_buffer_size:
		_flush_logs()

## Отправка логов на сервер
func _flush_logs() -> void:
	if log_buffer.is_empty() or not debug_mode:
		return

	var logs_to_send = log_buffer.duplicate()
	log_buffer.clear()

	var url = api_base + "/logs"
	var body = JSON.stringify({
		"session_id": session_id,
		"player_id": ApiClient.player_id if ApiClient.player_id > 0 else null,
		"logs": logs_to_send
	})

	var headers = ["Content-Type: application/json"]
	http_request.request(url, headers, HTTPClient.METHOD_POST, body)

func _on_logs_sent(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	# Просто игнорируем результат, логи отправлены
	pass

## Вызывается при выходе - отправляем оставшиеся логи
func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_PREDELETE:
		if not log_buffer.is_empty():
			_flush_logs()
