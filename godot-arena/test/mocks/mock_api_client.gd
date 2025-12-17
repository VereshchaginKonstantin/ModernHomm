extends Node
## Мок ApiClient для тестирования без реальных HTTP запросов

signal request_completed(result: Dictionary)
signal request_failed(error: String)
signal auth_required()

# Мок данные авторизации
var auth_token: String = "test_token_123"
var player_id: int = 100
var player_name: String = "test_player1"
var api_base: String = "/arena/api/public"

# Очередь ответов для тестов
var response_queue: Array = []
var should_fail: bool = false
var fail_message: String = ""

func is_authenticated() -> bool:
	return auth_token != "" and player_id > 0

func logout() -> void:
	auth_token = ""
	player_id = 0
	player_name = ""

## Добавить ответ в очередь
func queue_response(data: Dictionary) -> void:
	response_queue.append(data)

## Установить режим ошибки
func set_fail_mode(fail: bool, message: String = "Test error") -> void:
	should_fail = fail
	fail_message = message

## Очистить очередь
func clear_queue() -> void:
	response_queue.clear()
	should_fail = false

func _emit_next_response() -> void:
	if should_fail:
		request_failed.emit(fail_message)
	elif response_queue.size() > 0:
		var response = response_queue.pop_front()
		request_completed.emit(response)

## Мок методы API
func login(username: String, password: String) -> void:
	call_deferred("_emit_next_response")

func get_current_player() -> void:
	call_deferred("_emit_next_response")

func get_players() -> void:
	call_deferred("_emit_next_response")

func get_game_state(game_id: int) -> void:
	call_deferred("_emit_next_response")

func get_unit_actions(game_id: int, unit_id: int) -> void:
	call_deferred("_emit_next_response")

func create_game(opponent_name: String, field_size: String) -> void:
	call_deferred("_emit_next_response")

func accept_game(game_id: int, army_id: int = 0) -> void:
	call_deferred("_emit_next_response")

func decline_game(game_id: int) -> void:
	call_deferred("_emit_next_response")

func move_unit(game_id: int, unit_id: int, x: int, y: int) -> void:
	call_deferred("_emit_next_response")

func attack_unit(game_id: int, attacker_id: int, target_id: int) -> void:
	call_deferred("_emit_next_response")

func skip_unit(game_id: int, unit_id: int) -> void:
	call_deferred("_emit_next_response")

func defer_unit(game_id: int, unit_id: int) -> void:
	call_deferred("_emit_next_response")

func surrender_game(game_id: int) -> void:
	call_deferred("_emit_next_response")

func get_pending_games() -> void:
	call_deferred("_emit_next_response")
