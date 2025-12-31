extends Control
## Экран выбора челленджей (PvE)

@onready var back_button: Button = %BackButton
@onready var army_select: OptionButton = %ArmySelect
@onready var challenges_list: VBoxContainer = %ChallengesList
@onready var status_label: Label = %StatusLabel

var challenges: Array = []
var player_armies: Array = []
var selected_army_id: int = 0
var sprite_textures: Dictionary = {}  # challenge_id -> Texture2D
var base_url: String = ""

func _ready() -> void:
	# Кэшируем base URL
	if OS.has_feature("web"):
		base_url = JavaScriptBridge.eval("window.location.origin")
	else:
		base_url = "http://localhost"

	# Подключаем UI
	back_button.pressed.connect(_on_back_pressed)
	army_select.item_selected.connect(_on_army_selected)

	# Подключаем сигналы API
	ApiClient.request_completed.connect(_on_api_response)
	ApiClient.request_failed.connect(_on_api_error)

	# Загружаем данные
	status_label.text = "Загрузка..."
	ApiClient.get_armies()
	ApiClient.get_challenges()

func _js_log(msg: String) -> void:
	if OS.has_feature("web"):
		var safe_msg = msg.replace("\\", "\\\\").replace("'", "\\'").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r")
		JavaScriptBridge.eval("console.log('[Challenges] " + safe_msg + "')")

func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main.tscn")

func _on_army_selected(index: int) -> void:
	if index == 0:
		selected_army_id = 0
	else:
		selected_army_id = army_select.get_item_id(index)
	_update_start_buttons()

func _on_api_response(data: Dictionary) -> void:
	# Обрабатываем список армий
	if data.has("armies"):
		player_armies = data.get("armies", [])
		_populate_armies()
		return

	# Обрабатываем список челленджей
	if data.has("challenges"):
		challenges = data.get("challenges", [])
		_display_challenges()
		status_label.text = ""
		return

	# Обрабатываем создание игры (начало челленджа)
	if data.has("game_id") and data.has("success"):
		if data.get("success", false):
			GameManager.current_game_id = data.get("game_id")
			GameManager.is_challenge_game = true  # Помечаем что это челлендж
			get_tree().change_scene_to_file("res://scenes/game.tscn")
		return

func _on_api_error(error: String) -> void:
	status_label.text = "Ошибка: " + error

func _populate_armies() -> void:
	army_select.clear()
	army_select.add_item("Выберите армию", 0)

	for army in player_armies:
		var army_name = army.get("army_name", "Армия")
		var army_cost = army.get("army_cost", 0)
		var is_in_battle = army.get("is_in_battle", false)
		var units_count = army.get("units", []).size()

		var text = "%s (%.0f)" % [army_name, army_cost]
		if is_in_battle:
			text = "[БОЙ] " + text
		elif units_count == 0:
			text = "[X] " + text

		var item_idx = army_select.get_item_count()
		army_select.add_item(text, army.get("army_id", 0))

		# Делаем недоступными армии в бою или без юнитов
		if is_in_battle or units_count == 0:
			army_select.set_item_disabled(item_idx, true)

func _display_challenges() -> void:
	# Очищаем список
	for child in challenges_list.get_children():
		child.queue_free()

	if challenges.is_empty():
		var empty_label = Label.new()
		empty_label.text = "Нет доступных челленджей"
		empty_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		challenges_list.add_child(empty_label)
		return

	# Создаём карточки челленджей
	for challenge in challenges:
		var card = _create_challenge_card(challenge)
		challenges_list.add_child(card)

func _create_challenge_card(challenge: Dictionary) -> PanelContainer:
	var panel = PanelContainer.new()
	panel.custom_minimum_size = Vector2(0, 120)

	var hbox = HBoxContainer.new()
	hbox.add_theme_constant_override("separation", 20)
	panel.add_child(hbox)

	# Спрайт челленджа (если есть)
	var sprite_container = Control.new()
	sprite_container.custom_minimum_size = Vector2(100, 100)
	hbox.add_child(sprite_container)

	var sprite_url = challenge.get("sprite_url", "")
	var challenge_id = challenge.get("id", 0)

	# Создаём placeholder
	var placeholder = ColorRect.new()
	placeholder.color = Color(0.2, 0.3, 0.4)
	placeholder.custom_minimum_size = Vector2(100, 100)
	placeholder.name = "Placeholder"
	sprite_container.add_child(placeholder)

	var icon_label = Label.new()
	icon_label.text = "?"
	icon_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	icon_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	icon_label.add_theme_font_size_override("font_size", 48)
	icon_label.position = Vector2(35, 20)
	icon_label.name = "IconLabel"
	sprite_container.add_child(icon_label)

	# Загружаем спрайт если есть URL
	if sprite_url != "":
		_load_challenge_sprite(sprite_url, challenge_id, sprite_container)

	# Информация о челлендже
	var info_vbox = VBoxContainer.new()
	info_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hbox.add_child(info_vbox)

	# Название
	var name_label = Label.new()
	name_label.text = challenge.get("name", "Без названия")
	name_label.add_theme_font_size_override("font_size", 24)
	info_vbox.add_child(name_label)

	# Описание
	var desc_label = Label.new()
	desc_label.text = challenge.get("description", "")
	desc_label.add_theme_color_override("font_color", Color(0.7, 0.7, 0.7))
	desc_label.autowrap_mode = TextServer.AUTOWRAP_WORD
	info_vbox.add_child(desc_label)

	# Награды
	var rewards_hbox = HBoxContainer.new()
	rewards_hbox.add_theme_constant_override("separation", 20)
	info_vbox.add_child(rewards_hbox)

	var gold_reward = challenge.get("reward_gold", 0)
	if gold_reward > 0:
		var gold_label = Label.new()
		gold_label.text = "Gold: %d" % gold_reward
		gold_label.add_theme_color_override("font_color", Color(1, 0.85, 0.2))
		rewards_hbox.add_child(gold_label)

	var gems_reward = challenge.get("reward_gems", 0)
	if gems_reward > 0:
		var gems_label = Label.new()
		gems_label.text = "Gems: %d" % gems_reward
		gems_label.add_theme_color_override("font_color", Color(0.6, 0.3, 0.9))
		rewards_hbox.add_child(gems_label)

	# Сложность
	var difficulty = challenge.get("ai_difficulty", "normal")
	var diff_label = Label.new()
	diff_label.text = "AI: " + difficulty.capitalize()
	match difficulty:
		"easy":
			diff_label.add_theme_color_override("font_color", Color(0.3, 0.8, 0.3))
		"normal":
			diff_label.add_theme_color_override("font_color", Color(0.8, 0.8, 0.3))
		"hard":
			diff_label.add_theme_color_override("font_color", Color(0.9, 0.5, 0.2))
		"nightmare":
			diff_label.add_theme_color_override("font_color", Color(0.9, 0.2, 0.2))
	rewards_hbox.add_child(diff_label)

	# Армия челленджа
	var units = challenge.get("units", [])
	if not units.is_empty():
		var units_label = Label.new()
		var unit_texts = []
		for unit in units:
			unit_texts.append("%s x%d" % [unit.get("name", "?"), unit.get("count", 0)])
		units_label.text = "Враги: " + ", ".join(unit_texts)
		units_label.add_theme_color_override("font_color", Color(0.9, 0.4, 0.4))
		units_label.add_theme_font_size_override("font_size", 12)
		info_vbox.add_child(units_label)

	# Кнопка старта
	var start_button = Button.new()
	start_button.text = "Начать"
	start_button.custom_minimum_size = Vector2(120, 60)
	start_button.name = "StartButton_%d" % challenge.get("id", 0)
	start_button.pressed.connect(_on_start_challenge.bind(challenge.get("id", 0)))
	start_button.disabled = selected_army_id == 0
	hbox.add_child(start_button)

	return panel

func _update_start_buttons() -> void:
	# Обновляем состояние всех кнопок старта
	for i in range(challenges.size()):
		var challenge = challenges[i]
		var button_name = "StartButton_%d" % challenge.get("id", 0)
		# Ищем кнопку в дереве
		for card in challenges_list.get_children():
			var button = card.find_child(button_name, true, false)
			if button:
				button.disabled = selected_army_id == 0

func _on_start_challenge(challenge_id: int) -> void:
	if selected_army_id == 0:
		status_label.text = "Сначала выберите армию!"
		return

	status_label.text = "Начинаем челлендж..."
	ApiClient.start_challenge(challenge_id, selected_army_id)


# ============= Загрузка спрайтов челленджей =============

func _load_challenge_sprite(sprite_url: String, challenge_id: int, container: Control) -> void:
	# Если уже загружен
	if sprite_textures.has(challenge_id):
		_apply_sprite_to_container(container, sprite_textures[challenge_id])
		return

	# Формируем полный URL
	var full_url = base_url + sprite_url
	_js_log("Loading challenge sprite: " + full_url)

	var http = HTTPRequest.new()
	http.use_threads = false
	add_child(http)
	http.request_completed.connect(_on_sprite_loaded.bind(challenge_id, container, http))
	http.request(full_url)

func _on_sprite_loaded(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray, challenge_id: int, container: Control, http_node: HTTPRequest) -> void:
	http_node.queue_free()

	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		_js_log("Failed to load sprite for challenge %d: result=%d, code=%d" % [challenge_id, result, response_code])
		return

	# Создаём текстуру из данных
	var image = Image.new()
	var img_error = image.load_png_from_buffer(body)
	if img_error != OK:
		img_error = image.load_jpg_from_buffer(body)
	if img_error != OK:
		img_error = image.load_webp_from_buffer(body)
	if img_error != OK:
		_js_log("Failed to decode sprite image for challenge %d" % challenge_id)
		return

	var texture = ImageTexture.create_from_image(image)
	sprite_textures[challenge_id] = texture

	# Применяем к контейнеру если он ещё существует
	if is_instance_valid(container):
		_apply_sprite_to_container(container, texture)

func _apply_sprite_to_container(container: Control, texture: Texture2D) -> void:
	# Удаляем placeholder
	var placeholder = container.get_node_or_null("Placeholder")
	if placeholder:
		placeholder.queue_free()
	var icon_label = container.get_node_or_null("IconLabel")
	if icon_label:
		icon_label.queue_free()

	# Добавляем TextureRect со спрайтом
	var tex_rect = TextureRect.new()
	tex_rect.texture = texture
	tex_rect.expand_mode = TextureRect.EXPAND_FIT_WIDTH_PROPORTIONAL
	tex_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	tex_rect.custom_minimum_size = Vector2(100, 100)
	container.add_child(tex_rect)
