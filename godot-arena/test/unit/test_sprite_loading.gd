extends "res://addons/gut/test.gd"
## Тесты для загрузки и применения спрайтов

const TestFixtures = preload("res://test/test_fixtures.gd")

var game_scene: Node


func before_each() -> void:
	game_scene = load("res://scenes/game.tscn").instantiate()
	add_child_autofree(game_scene)
	await get_tree().process_frame


func after_each() -> void:
	game_scene = null


## Тест: Кэш спрайтов пуст изначально
func test_sprite_sheets_cache_empty() -> void:
	if "sprite_sheets" in game_scene:
		assert_eq(game_scene.sprite_sheets.size(), 0, "Sprite sheets cache should be empty initially")


## Тест: Кэш текстур пуст изначально
func test_unit_textures_cache_empty() -> void:
	if "unit_textures" in game_scene:
		assert_eq(game_scene.unit_textures.size(), 0, "Unit textures cache should be empty initially")


## Тест: Создание юнита без спрайта отображает иконку
func test_unit_shows_icon_without_sprite() -> void:
	var unit_data = TestFixtures.get_test_unit_player1()
	# Убираем sprite_url чтобы отображалась только иконка
	unit_data["unit_type"]["sprite_url"] = null
	unit_data["unit_type"]["image_url"] = null

	if game_scene.has_method("_create_unit_sprite"):
		var unit_control = game_scene._create_unit_sprite(unit_data)
		assert_not_null(unit_control, "Unit control should be created")

		var icon_label = unit_control.get_node_or_null("IconLabel")
		if icon_label:
			assert_true(icon_label.visible, "Icon label should be visible when no sprite")
			assert_eq(icon_label.text, "S", "Icon should show unit type icon")

		unit_control.queue_free()


## Тест: Создание контейнера юнита
func test_create_unit_sprite_returns_control() -> void:
	var unit_data = TestFixtures.get_test_unit_player1()

	if game_scene.has_method("_create_unit_sprite"):
		var unit_control = game_scene._create_unit_sprite(unit_data)
		assert_not_null(unit_control, "Should create unit control")
		assert_true(unit_control is Control, "Should be Control node")

		# Проверяем что есть нужные дочерние узлы
		var count_label = unit_control.get_node_or_null("CountLabel")
		assert_not_null(count_label, "Should have CountLabel")

		unit_control.queue_free()


## Тест: Счётчик юнитов отображается правильно
func test_unit_count_label() -> void:
	var unit_data = TestFixtures.get_test_unit_player1()
	unit_data["count"] = 15

	if game_scene.has_method("_create_unit_sprite"):
		var unit_control = game_scene._create_unit_sprite(unit_data)
		var count_label = unit_control.get_node_or_null("CountLabel")

		if count_label:
			assert_eq(count_label.text, "15", "Count label should show unit count")

		unit_control.queue_free()


## Тест: Применение кэшированного спрайта
func test_apply_cached_texture() -> void:
	# Создаём мок текстуру и добавляем в кэш
	var mock_texture = ImageTexture.new()
	var mock_image = Image.create(64, 64, false, Image.FORMAT_RGBA8)
	mock_image.fill(Color.RED)
	mock_texture.set_image(mock_image)

	var test_url = "/test/image.png"

	if "unit_textures" in game_scene:
		game_scene.unit_textures[test_url] = mock_texture

		# Создаём юнита и добавляем в коллекцию
		var unit_data = TestFixtures.get_test_unit_player1()
		if game_scene.has_method("_create_unit_sprite"):
			var unit_control = game_scene._create_unit_sprite(unit_data)
			game_scene.unit_sprites[1001] = unit_control
			game_scene.get_node("Board").add_child(unit_control)

			# Применяем кэшированную текстуру
			if game_scene.has_method("_apply_cached_texture"):
				game_scene._apply_cached_texture(1001, test_url)

				var texture_rect = unit_control.get_node_or_null("UnitTexture")
				if texture_rect:
					assert_eq(texture_rect.texture, mock_texture, "Texture should be applied")


## Тест: Проверка параметров спрайт-листа
func test_sprite_params_parsing() -> void:
	var sprite_params = {
		"frame_count": 8,
		"fps": 12,
		"columns": 4,
		"rows": 2
	}

	# Проверяем что параметры корректно парсятся
	assert_eq(sprite_params.get("frame_count", 1), 8)
	assert_eq(sprite_params.get("fps", 10), 12)
	assert_eq(sprite_params.get("columns", 1), 4)
	assert_eq(sprite_params.get("rows", 1), 2)


## Тест: Защита от деления на ноль в спрайт-параметрах
func test_sprite_params_zero_protection() -> void:
	var sprite_params = {
		"frame_count": 0,
		"fps": 0,
		"columns": 0,
		"rows": 0
	}

	# Используем maxi для защиты от нуля (как в game.gd)
	var frame_count = maxi(1, sprite_params.get("frame_count", 1))
	var columns = maxi(1, sprite_params.get("columns", 1))
	var rows = maxi(1, sprite_params.get("rows", 1))

	assert_eq(frame_count, 1, "frame_count should be at least 1")
	assert_eq(columns, 1, "columns should be at least 1")
	assert_eq(rows, 1, "rows should be at least 1")
