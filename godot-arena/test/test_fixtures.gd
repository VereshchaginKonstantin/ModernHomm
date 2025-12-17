extends RefCounted
## Тестовые фикстуры для тестирования игры

class_name TestFixtures

## Тестовый игрок 1 (атакующий)
static func get_test_player1() -> Dictionary:
	return {
		"id": 100,
		"username": "test_player1",
		"name": "Test Player 1",
		"balance": 1000.0,
		"wins": 5,
		"losses": 3
	}

## Тестовый игрок 2 (защищающийся)
static func get_test_player2() -> Dictionary:
	return {
		"id": 101,
		"username": "test_player2",
		"name": "Test Player 2",
		"balance": 1500.0,
		"wins": 7,
		"losses": 2
	}

## Тестовый тип юнита - Мечник
static func get_test_unit_type_swordsman() -> Dictionary:
	return {
		"id": 1,
		"name": "Мечник",
		"icon": "S",
		"attack": 10,
		"defense": 8,
		"hp": 15,
		"speed": 4,
		"attack_range": 1,
		"skin_id": 1,
		"has_image": true,
		"has_sprite": true,
		"image_url": "/arena/api/public/skins/1/image",
		"sprite_url": "/arena/api/public/skins/1/sprite",
		"sprite_params": {
			"frame_count": 8,
			"fps": 10,
			"columns": 8,
			"rows": 1
		}
	}

## Тестовый тип юнита - Лучник
static func get_test_unit_type_archer() -> Dictionary:
	return {
		"id": 2,
		"name": "Лучник",
		"icon": "A",
		"attack": 12,
		"defense": 5,
		"hp": 10,
		"speed": 5,
		"attack_range": 4,
		"skin_id": 2,
		"has_image": true,
		"has_sprite": false,
		"image_url": "/arena/api/public/skins/2/image",
		"sprite_url": null,
		"sprite_params": null
	}

## Тестовый юнит игрока 1 (Мечник)
static func get_test_unit_player1() -> Dictionary:
	return {
		"id": 1001,
		"player_id": 100,
		"x": 1,
		"y": 2,
		"count": 10,
		"has_moved": 0,
		"unit_type": get_test_unit_type_swordsman()
	}

## Тестовый юнит игрока 2 (Лучник)
static func get_test_unit_player2() -> Dictionary:
	return {
		"id": 1002,
		"player_id": 101,
		"x": 3,
		"y": 2,
		"count": 8,
		"has_moved": 0,
		"unit_type": get_test_unit_type_archer()
	}

## Тестовое поле 5x5
static func get_test_field_5x5() -> Dictionary:
	return {
		"name": "5x5",
		"width": 5,
		"height": 5
	}

## Тестовое поле 7x7
static func get_test_field_7x7() -> Dictionary:
	return {
		"name": "7x7",
		"width": 7,
		"height": 7
	}

## Тестовые препятствия
static func get_test_obstacles() -> Array:
	return [
		{"x": 2, "y": 2},
		{"x": 2, "y": 3}
	]

## Полное тестовое состояние игры
static func get_test_game_state(current_player_id: int = 100) -> Dictionary:
	return {
		"game_id": 999,
		"status": "in_progress",
		"current_player_id": current_player_id,
		"player1_id": 100,
		"player2_id": 101,
		"player1_name": "test_player1",
		"player2_name": "test_player2",
		"is_game_over": false,
		"winner_id": null,
		"field": get_test_field_5x5(),
		"units": [
			get_test_unit_player1(),
			get_test_unit_player2()
		],
		"obstacles": get_test_obstacles(),
		"logs": []
	}

## Состояние игры после хода (юнит переместился)
static func get_test_game_state_after_move() -> Dictionary:
	var state = get_test_game_state(101)  # Теперь ход игрока 2
	# Юнит игрока 1 переместился
	state["units"][0]["x"] = 2
	state["units"][0]["y"] = 2
	state["units"][0]["has_moved"] = 1
	return state

## Состояние игры после атаки
static func get_test_game_state_after_attack() -> Dictionary:
	var state = get_test_game_state(101)
	# Юнит игрока 1 атаковал и походил
	state["units"][0]["x"] = 2
	state["units"][0]["y"] = 2
	state["units"][0]["has_moved"] = 1
	# Юнит игрока 2 потерял часть отряда
	state["units"][1]["count"] = 5
	return state

## Тестовые действия юнита - куда может ходить
static func get_test_unit_actions() -> Dictionary:
	return {
		"can_move": [
			{"x": 2, "y": 1},
			{"x": 2, "y": 2},
			{"x": 1, "y": 3},
			{"x": 0, "y": 2}
		],
		"can_attack": [
			{"id": 1002, "x": 3, "y": 2}
		]
	}

## Состояние игры - победа игрока 1
static func get_test_game_state_victory() -> Dictionary:
	var state = get_test_game_state()
	state["is_game_over"] = true
	state["winner_id"] = 100
	state["status"] = "completed"
	# Все юниты игрока 2 уничтожены
	state["units"] = [get_test_unit_player1()]
	return state

## Мок HTTP ответа для спрайта (PNG 8x8 пикселей)
static func get_mock_sprite_png_data() -> PackedByteArray:
	# Минимальный валидный PNG - 8x8 красный квадрат
	var png_data = PackedByteArray([
		0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
		0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
		0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x08,  # 8x8
		0x08, 0x02, 0x00, 0x00, 0x00, 0x4B, 0x6D, 0x29,
		0xDE, 0x00, 0x00, 0x00, 0x1D, 0x49, 0x44, 0x41,  # IDAT chunk
		0x54, 0x78, 0x9C, 0x62, 0xF8, 0xCF, 0xC0, 0xC0,
		0xC0, 0xC0, 0xC0, 0xC0, 0xC0, 0xC0, 0xC0, 0xC0,
		0xC0, 0xC0, 0xC0, 0xC0, 0xC0, 0x00, 0x00, 0x00,
		0x49, 0x00, 0x01, 0xE4, 0xFD, 0xEB, 0x3C, 0x00,
		0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44, 0xAE,  # IEND chunk
		0x42, 0x60, 0x82
	])
	return png_data
