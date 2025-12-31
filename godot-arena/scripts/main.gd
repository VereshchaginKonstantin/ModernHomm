extends Control
## Главное меню арены с JWT аутентификацией

@onready var player_name_label: Label = %PlayerNameLabel
@onready var player_stats: Label = %PlayerStats
@onready var army_select: OptionButton = %ArmySelect
@onready var army_stats: Label = %ArmyStats
@onready var opponent_select: OptionButton = %OpponentSelect
@onready var opponent_stats: Label = %OpponentStats
# Секция выбора размера поля (скрыта - размер выбирается автоматически)
@onready var field_section: Control = $VBoxContainer/FieldSection
@onready var start_button: Button = %StartButton
@onready var army_button: Button = %ArmyButton
@onready var races_button: Button = %RacesButton
@onready var challenges_button: Button = %ChallengesButton
@onready var status_label: Label = %StatusLabel
@onready var battles_panel: PanelContainer = %BattlesPanel
@onready var battles_toggle: Button = %BattlesToggle
@onready var battles_close: Button = %CloseButton
@onready var pending_list: VBoxContainer = %PendingList
@onready var version_label: Label = %VersionLabel

# Login panel elements
@onready var login_panel: PanelContainer = %LoginPanel
@onready var login_subtitle: Label = %Subtitle
@onready var username_input: LineEdit = %UsernameInput
@onready var password_input: LineEdit = %PasswordInput
@onready var login_button: Button = %LoginButton
@onready var set_password_button: Button = %SetPasswordButton
@onready var login_status: Label = %LoginStatus

# Состояние логина
enum LoginState { IDLE, CHECKING_USER, LOGGING_IN, SETTING_PASSWORD }
var login_state: LoginState = LoginState.IDLE
var login_username: String = ""

# Состояние панели боёв
var battles_panel_open: bool = false
var battles_panel_tween: Tween

var players: Array = []
var current_player: Dictionary = {}
var player_armies: Array = []  # Список армий игрока
var selected_army: Dictionary = {}  # Выбранная армия для боя
var selected_opponent: Dictionary = {}
# selected_field_size удалён - размер поля выбирается автоматически на сервере
var waiting_game_id: int = 0
var waiting_timer: Timer
var pending_games_timer: Timer  # Таймер для автообновления списка ожидающих игр
var pending_games: Array = []  # Входящие вызовы (ждут моего принятия)
var my_waiting_games: Array = []  # Мои исходящие вызовы (жду принятия противником)
var active_games: Array = []
var history_games: Array = []

const VERSION = "2025.12.15"

func _ready() -> void:
	# Устанавливаем версию
	version_label.text = "v" + VERSION

	# Подключаем сигналы
	GameManager.players_loaded.connect(_on_players_loaded)
	GameManager.current_player_loaded.connect(_on_current_player_loaded)
	GameManager.game_state_updated.connect(_on_game_state_updated)
	GameManager.error_occurred.connect(_on_error)

	# Подключаем сигналы API
	ApiClient.request_completed.connect(_on_api_response)
	ApiClient.request_failed.connect(_on_api_error)
	ApiClient.auth_required.connect(_on_auth_required)

	# Подключаем UI
	army_select.item_selected.connect(_on_army_selected)
	opponent_select.item_selected.connect(_on_opponent_selected)
	start_button.pressed.connect(_on_start_pressed)

	# Скрываем секцию выбора размера поля (размер выбирается автоматически)
	if field_section:
		field_section.visible = false
	army_button.pressed.connect(_on_army_pressed)
	races_button.pressed.connect(_on_races_pressed)
	challenges_button.pressed.connect(_on_challenges_pressed)
	$VBoxContainer/BackButton.pressed.connect(_on_back_pressed)

	# Подключаем панель боёв
	battles_toggle.pressed.connect(_toggle_battles_panel)
	battles_close.pressed.connect(_close_battles_panel)

	# Подключаем логин UI
	login_button.pressed.connect(_on_login_pressed)
	set_password_button.pressed.connect(_on_set_password_pressed)
	username_input.text_submitted.connect(_on_username_submitted)
	password_input.text_submitted.connect(_on_password_submitted)

	# Создаём таймер для polling статуса игры
	waiting_timer = Timer.new()
	waiting_timer.wait_time = 2.0
	waiting_timer.timeout.connect(_on_waiting_timeout)
	add_child(waiting_timer)

	# Создаём таймер для автообновления списка ожидающих игр
	pending_games_timer = Timer.new()
	pending_games_timer.wait_time = 5.0
	pending_games_timer.timeout.connect(_on_pending_games_timeout)
	add_child(pending_games_timer)

	# Начальное положение панели боёв (за экраном справа)
	# Панель занимает 50% экрана (anchor_left=0.5), сдвигаем на ширину экрана
	battles_panel.position.x = get_viewport_rect().size.x * 0.5

	# Проверяем есть ли pending debug auth check
	_js_log("main._ready: pending=" + str(ApiClient._pending_debug_player_id) + ", completed=" + str(ApiClient._debug_auth_check_completed) + ", debug_mode=" + str(ApiClient.debug_mode) + ", player_id=" + str(ApiClient.player_id))

	# Если debug_mode уже включен - сразу переходим к проверке авторизации
	if ApiClient.debug_mode and ApiClient.player_id > 0:
		_js_log("Debug mode already active, skipping wait")
	# Если проверка debug auth ещё не завершена - ждём
	elif ApiClient._pending_debug_player_id > 0 and not ApiClient._debug_auth_check_completed:
		_js_log("Waiting for debug_auth_checked signal...")
		await ApiClient.debug_auth_checked
		_js_log("Got debug_auth_checked signal! debug_mode=" + str(ApiClient.debug_mode))
	elif ApiClient._debug_auth_check_completed:
		# Проверка уже завершилась - логируем результат
		_js_log("Debug auth check already completed, debug_mode=" + str(ApiClient.debug_mode))

	# Даём немного времени на завершение асинхронных операций
	await get_tree().process_frame

	_check_auth_and_show_ui()

func _js_log(msg: String) -> void:
	if OS.has_feature("web"):
		# Экранируем спецсимволы для JavaScript
		var safe_msg = msg.replace("\\", "\\\\").replace("'", "\\'").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r")
		JavaScriptBridge.eval("console.log('[Main] " + safe_msg + "')")

func _check_auth_and_show_ui() -> void:
	_js_log("_check_auth_and_show_ui: debug_mode=" + str(ApiClient.debug_mode) + ", player_id=" + str(ApiClient.player_id))
	# Проверяем режим дебага (player_id в URL)
	if ApiClient.debug_mode and ApiClient.player_id > 0:
		# В режиме дебага - загружаем данные пользователя с сервера
		_js_log("Debug mode - loading player data from server")
		login_panel.visible = false
		ApiClient.get_current_player()
	elif ApiClient.is_authenticated():
		# Пользователь уже авторизован - показываем главное меню
		login_panel.visible = false
		# Загружаем данные текущего пользователя
		ApiClient.get_current_player()
	else:
		# Показываем форму логина
		login_panel.visible = true
		set_password_button.visible = false
		username_input.grab_focus()

func _toggle_battles_panel() -> void:
	if battles_panel_open:
		_close_battles_panel()
	else:
		_open_battles_panel()

func _open_battles_panel() -> void:
	if battles_panel_tween:
		battles_panel_tween.kill()

	battles_panel.visible = true
	battles_panel_open = true
	battles_toggle.text = "<"

	# Обновляем список ожидающих игр при открытии панели
	ApiClient.get_pending_games()
	# Запускаем автообновление
	pending_games_timer.start()

	# Панель занимает 50% экрана (anchor_left=0.5), открытая позиция = 0
	battles_panel_tween = create_tween()
	battles_panel_tween.tween_property(battles_panel, "position:x", 0.0, 0.3).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)

func _close_battles_panel() -> void:
	if battles_panel_tween:
		battles_panel_tween.kill()

	battles_panel_open = false
	battles_toggle.text = ">"
	# Останавливаем автообновление
	pending_games_timer.stop()

	# Закрытая позиция = 50% ширины экрана (панель уезжает за правый край)
	battles_panel_tween = create_tween()
	battles_panel_tween.tween_property(battles_panel, "position:x", get_viewport_rect().size.x * 0.5, 0.3).set_ease(Tween.EASE_IN).set_trans(Tween.TRANS_CUBIC)
	battles_panel_tween.tween_callback(func(): battles_panel.visible = false)

func _on_pending_games_timeout() -> void:
	# Периодически обновляем список ожидающих игр пока панель открыта
	if battles_panel_open and ApiClient.is_authenticated():
		ApiClient.get_pending_games()

func _on_army_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/army_editor.tscn")

func _on_races_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/race_manager.tscn")

func _on_challenges_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/challenges.tscn")

func _on_login_pressed() -> void:
	var username = username_input.text.strip_edges()
	var password = password_input.text

	if username.is_empty():
		login_status.text = "Введите имя пользователя"
		return

	if password.is_empty():
		login_status.text = "Введите пароль"
		return

	login_button.disabled = true
	set_password_button.visible = false
	login_status.text = "Вход..."
	login_state = LoginState.LOGGING_IN
	login_username = username
	ApiClient.login(username, password)

func _on_set_password_pressed() -> void:
	var username = username_input.text.strip_edges()
	var password = password_input.text

	if username.is_empty():
		login_status.text = "Введите имя пользователя"
		return

	if password.is_empty():
		login_status.text = "Введите пароль (минимум 4 символа)"
		return

	if password.length() < 4:
		login_status.text = "Пароль должен быть не менее 4 символов"
		return

	login_button.disabled = true
	set_password_button.disabled = true
	login_status.text = "Установка пароля..."
	login_state = LoginState.SETTING_PASSWORD
	login_username = username
	ApiClient.set_password(username, password)

func _on_username_submitted(_text: String) -> void:
	# При вводе username - фокус на пароль
	password_input.grab_focus()

func _on_password_submitted(_text: String) -> void:
	# При вводе пароля - логин
	_on_login_pressed()

func _on_api_response(data: Dictionary) -> void:
	# Обрабатываем ответ в зависимости от состояния логина
	match login_state:
		LoginState.LOGGING_IN:
			_handle_login_response(data)
		LoginState.SETTING_PASSWORD:
			_handle_set_password_response(data)
		_:
			_handle_game_response(data)

func _handle_login_response(data: Dictionary) -> void:
	login_state = LoginState.IDLE

	if data.has("token") and data.has("player"):
		# Успешный логин
		var player = data.get("player", {})
		if not player.is_empty():
			login_panel.visible = false
			current_player = player
			_show_main_ui()
			return

	# Ошибка или неверные данные
	login_button.disabled = false
	login_status.text = data.get("error", "Ошибка входа")

func _handle_set_password_response(data: Dictionary) -> void:
	login_state = LoginState.IDLE

	if data.has("success") and data.get("success", false):
		# Пароль установлен успешно
		login_status.text = "Пароль установлен! Входим..."
		login_button.disabled = false
		set_password_button.visible = false

		# Если вернулся токен - сразу используем его
		if data.has("token") and data.has("player_id"):
			login_panel.visible = false
			# Загружаем данные игрока
			ApiClient.get_current_player()
			return

		# Иначе предлагаем залогиниться
		login_status.text = "Пароль установлен! Теперь войдите."
	else:
		login_button.disabled = false
		set_password_button.disabled = false
		login_status.text = data.get("error", "Ошибка установки пароля")

func _handle_game_response(data: Dictionary) -> void:
	# Обрабатываем данные текущего игрока
	if data.has("current_player"):
		var player = data.get("current_player", {})
		if not player.is_empty():
			current_player = player
			_show_main_ui()
		return

	# Обрабатываем ответ на список армий
	if data.has("armies"):
		_js_log("Received armies response, count=" + str(data.get("armies", []).size()))
		player_armies = data.get("armies", [])
		_populate_armies()
		return

	# Обрабатываем ответ на ожидающие игры
	if data.has("pending_games"):
		pending_games = data.get("pending_games", [])
		my_waiting_games = data.get("my_waiting_games", [])
		active_games = data.get("active_games", [])
		history_games = data.get("history", [])
		_display_battles_list()
		return

	# Обрабатываем ответ на создание игры
	if data.has("game_id") and data.has("status"):
		if data.get("status") == "waiting":
			waiting_game_id = data.get("game_id")
			status_label.text = "Ожидание принятия игры противником..."
			waiting_timer.start()
			# Сразу обновляем список игр чтобы показать созданную игру
			ApiClient.get_pending_games()
		elif data.get("status") == "in_progress":
			GameManager.current_game_id = data.get("game_id")
			get_tree().change_scene_to_file("res://scenes/game.tscn")

func _on_api_error(error: String) -> void:
	match login_state:
		LoginState.LOGGING_IN:
			login_state = LoginState.IDLE
			login_button.disabled = false

			# Проверяем специальные коды ошибок
			if "PASSWORD_NOT_SET" in error or "Password not set" in error:
				# У пользователя нет пароля - предлагаем установить
				login_status.text = "У вас не установлен пароль. Установите его:"
				login_subtitle.text = "Установите пароль для входа"
				set_password_button.visible = true
			else:
				login_status.text = error

		LoginState.SETTING_PASSWORD:
			login_state = LoginState.IDLE
			login_button.disabled = false
			set_password_button.disabled = false
			login_status.text = error

		_:
			status_label.text = "Ошибка: " + error

func _on_auth_required() -> void:
	# Токен устарел - показываем логин
	login_panel.visible = true
	login_status.text = "Сессия истекла. Войдите снова."
	ApiClient.logout()

func _show_main_ui() -> void:
	# Показываем имя текущего игрока
	player_name_label.text = current_player.get("username", current_player.get("name", "???"))

	# Обновляем статистику игрока
	var win_rate = 0
	var total = current_player.get("wins", 0) + current_player.get("losses", 0)
	if total > 0:
		win_rate = int(float(current_player.get("wins", 0)) / total * 100)
	player_stats.text = "Баланс: %.0f | Побед: %d | Поражений: %d (%d%%)" % [
		current_player.get("balance", 0),
		current_player.get("wins", 0),
		current_player.get("losses", 0),
		win_rate
	]

	# Загружаем список армий игрока
	status_label.text = "Загрузка армий..."
	ApiClient.get_armies()

	# Загружаем список противников
	GameManager.load_players()

func _on_current_player_loaded(player: Dictionary) -> void:
	if player.is_empty():
		# Данные не загрузились - показываем логин
		login_panel.visible = true
		login_status.text = "Ошибка загрузки данных. Войдите снова."
		return

	current_player = player
	login_panel.visible = false
	_show_main_ui()

func _on_players_loaded(loaded_players: Array) -> void:
	players = loaded_players
	status_label.text = ""
	_populate_opponents()

func _populate_armies() -> void:
	_js_log("_populate_armies called, armies count=" + str(player_armies.size()))
	army_select.clear()
	army_select.add_item("Выберите армию", 0)

	var available_count = 0
	for army in player_armies:
		var army_name = army.get("army_name", "Армия")
		var army_cost = army.get("army_cost", 0)
		var is_in_battle = army.get("is_in_battle", false)
		var units_count = army.get("units", []).size()

		# Формируем текст пункта
		var text = "%s (%.0f)" % [army_name, army_cost]
		if is_in_battle:
			text = "[БОЙ] " + text
		elif units_count == 0:
			text = "[X] " + text + " [ПУСТАЯ]"

		var item_idx = army_select.get_item_count()
		army_select.add_item(text, army.get("army_id", 0))

		# Делаем недоступными армии в бою или без юнитов
		if is_in_battle or units_count == 0:
			army_select.set_item_disabled(item_idx, true)
		else:
			available_count += 1

	selected_army = {}
	army_stats.text = ""

	# Если нет доступных армий - показываем подсказку
	if available_count == 0:
		army_stats.text = "Нет доступных армий! Создайте армию или завершите текущие бои."

	# Очищаем статус загрузки армий
	if status_label.text == "Загрузка армий...":
		status_label.text = ""

	_update_start_button()

	# Проверяем ожидающие игры (если игроки уже загружены)
	if not players.is_empty():
		_check_pending_games()

func _on_army_selected(index: int) -> void:
	var army_id = army_select.get_item_id(index)
	if army_id == 0:
		selected_army = {}
		army_stats.text = ""
		_update_start_button()
		return

	for army in player_armies:
		if army.get("army_id") == army_id:
			selected_army = army
			break

	# Показываем состав армии
	var units = selected_army.get("units", [])
	if units.size() > 0:
		var unit_texts = []
		for unit in units:
			unit_texts.append("%s x%d" % [unit.get("name", "?"), unit.get("count", 0)])
		army_stats.text = ", ".join(unit_texts)
	else:
		army_stats.text = "Армия пустая"

	_update_start_button()

func _populate_opponents() -> void:
	if current_player.is_empty():
		return

	var my_id = current_player.get("id", 0)

	opponent_select.clear()
	opponent_select.add_item("Выберите противника", 0)

	for p in players:
		if p.get("id") == my_id:
			continue
		if p.get("units", []).size() == 0:
			continue

		var wr = 0
		var t = p.get("wins", 0) + p.get("losses", 0)
		if t > 0:
			wr = int(float(p.get("wins", 0)) / t * 100)
		var text = "%s - %d%%" % [p.get("username", p.get("name", "???")), wr]
		opponent_select.add_item(text, p.get("id", 0))

	selected_opponent = {}
	opponent_stats.text = ""
	_update_start_button()
	_check_pending_games()

func _check_pending_games() -> void:
	_js_log("_check_pending_games: current_player.is_empty=" + str(current_player.is_empty()) + ", is_authenticated=" + str(ApiClient.is_authenticated()))
	if current_player.is_empty() or not ApiClient.is_authenticated():
		_js_log("_check_pending_games: hiding battles_toggle")
		battles_toggle.visible = false
		return

	_js_log("_check_pending_games: showing battles_toggle")
	battles_toggle.visible = true
	ApiClient.get_pending_games()

func _on_opponent_selected(index: int) -> void:
	var opponent_id = opponent_select.get_item_id(index)
	if opponent_id == 0:
		selected_opponent = {}
		opponent_stats.text = ""
		_update_start_button()
		return

	for p in players:
		if p.get("id") == opponent_id:
			selected_opponent = p
			break

	var win_rate = 0
	var total = selected_opponent.get("wins", 0) + selected_opponent.get("losses", 0)
	if total > 0:
		win_rate = int(float(selected_opponent.get("wins", 0)) / total * 100)
	opponent_stats.text = "Побед: %d | Поражений: %d (%d%%)" % [
		selected_opponent.get("wins", 0),
		selected_opponent.get("losses", 0),
		win_rate
	]
	_update_start_button()

func _update_start_button() -> void:
	start_button.disabled = current_player.is_empty() or selected_army.is_empty() or selected_opponent.is_empty()

func _on_start_pressed() -> void:
	if current_player.is_empty() or selected_army.is_empty() or selected_opponent.is_empty():
		return

	start_button.disabled = true
	status_label.text = "Создание игры..."

	# Используем новый API с army_id (размер поля определяется автоматически)
	ApiClient.create_game(
		selected_opponent.get("username", selected_opponent.get("name", "")),
		"",  # Размер поля выбирается автоматически на сервере
		selected_army.get("army_id", 0)
	)

func _on_waiting_timeout() -> void:
	if waiting_game_id > 0:
		ApiClient.get_game_state(waiting_game_id)

func _on_game_state_updated(state: Dictionary) -> void:
	var status = state.get("status", "")

	if status == "waiting":
		status_label.text = "Ожидание принятия игры противником..."
		return

	if status == "in_progress":
		waiting_timer.stop()
		waiting_game_id = 0
		GameManager.current_game_id = state.get("game_id", 0)
		get_tree().change_scene_to_file("res://scenes/game.tscn")
		return

	if status == "completed" or status == "cancelled":
		waiting_timer.stop()
		waiting_game_id = 0
		status_label.text = "Игра завершена"
		start_button.disabled = false

func _on_error(message: String) -> void:
	status_label.text = "Ошибка: " + message
	start_button.disabled = false
	waiting_timer.stop()
	waiting_game_id = 0

func _display_battles_list() -> void:
	for child in pending_list.get_children():
		child.queue_free()

	var has_battles = false

	# Ожидающие игры
	for game in pending_games:
		has_battles = true
		var hbox = HBoxContainer.new()
		hbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL

		var label = Label.new()
		label.text = "%s вызывает вас!" % game.get("player1_name", "???")
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		hbox.add_child(label)

		var army_select = OptionButton.new()
		army_select.custom_minimum_size = Vector2(120, 0)
		var player_armies = game.get("player_armies", [])
		for i in range(player_armies.size()):
			var army = player_armies[i]
			var army_name = army.get("army_name", "Армия")
			var army_cost = army.get("army_cost", 0)
			var is_matching = army.get("is_matching", false)
			var prefix = "[+] " if is_matching else "[!] "
			army_select.add_item(prefix + army_name + " (%.0f)" % army_cost, army.get("army_id", 0))
		hbox.add_child(army_select)

		var accept_btn = Button.new()
		accept_btn.text = "OK"
		accept_btn.custom_minimum_size = Vector2(40, 0)
		accept_btn.pressed.connect(_on_accept_game.bind(game.get("game_id", 0), army_select))
		hbox.add_child(accept_btn)

		var decline_btn = Button.new()
		decline_btn.text = "X"
		decline_btn.custom_minimum_size = Vector2(40, 0)
		decline_btn.pressed.connect(_on_decline_game.bind(game.get("game_id", 0)))
		hbox.add_child(decline_btn)

		pending_list.add_child(hbox)

	# Мои исходящие вызовы (ожидаем принятия)
	for game in my_waiting_games:
		has_battles = true
		var hbox = HBoxContainer.new()
		hbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL

		var label = Label.new()
		label.text = "vs %s - Ожидаем..." % game.get("player2_name", "???")
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		label.modulate = Color(1, 1, 0.7)  # Жёлтый оттенок для ожидания
		hbox.add_child(label)

		var cancel_btn = Button.new()
		cancel_btn.text = "Отмена"
		cancel_btn.custom_minimum_size = Vector2(70, 0)
		cancel_btn.pressed.connect(_on_decline_game.bind(game.get("game_id", 0)))
		hbox.add_child(cancel_btn)

		pending_list.add_child(hbox)

	# Активные игры
	for game in active_games:
		has_battles = true
		var hbox = HBoxContainer.new()
		hbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL

		var opponent_name = game.get("player2_name", "???")
		if game.get("player2_id") == current_player.get("id"):
			opponent_name = game.get("player1_name", "???")

		var label = Label.new()
		var turn_text = " (ваш ход)" if game.get("is_my_turn", false) else ""
		label.text = "vs %s%s" % [opponent_name, turn_text]
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		hbox.add_child(label)

		var continue_btn = Button.new()
		continue_btn.text = "Играть"
		var is_challenge = game.get("is_challenge", false)
		continue_btn.pressed.connect(_on_continue_game.bind(game.get("game_id", 0), is_challenge))
		hbox.add_child(continue_btn)

		pending_list.add_child(hbox)

	# История (последние 5)
	var history_shown = 0
	for game in history_games:
		if history_shown >= 5:
			break
		has_battles = true
		var hbox = HBoxContainer.new()
		hbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL

		var opponent_name = game.get("player2_name", "???")
		if game.get("player2_id") == current_player.get("id"):
			opponent_name = game.get("player1_name", "???")

		var result_icon = "W" if game.get("winner_id") == current_player.get("id") else "L"
		var label = Label.new()
		label.text = "%s vs %s" % [result_icon, opponent_name]
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		label.modulate = Color(0.6, 0.6, 0.6)
		hbox.add_child(label)

		pending_list.add_child(hbox)
		history_shown += 1

	# Показываем/скрываем кнопку toggle в зависимости от наличия боёв
	battles_toggle.visible = has_battles or not current_player.is_empty()

	# Автоматически открываем панель если есть активные бои или вызовы
	if pending_games.size() > 0 or my_waiting_games.size() > 0 or active_games.size() > 0:
		if not battles_panel_open:
			_open_battles_panel()

func _on_accept_game(game_id: int, army_select: OptionButton) -> void:
	var selected_idx = army_select.selected
	var army_id = 0
	if selected_idx >= 0:
		army_id = army_select.get_item_id(selected_idx)
	ApiClient.accept_game(game_id, army_id)

func _on_decline_game(game_id: int) -> void:
	ApiClient.decline_game(game_id)
	_check_pending_games()

func _on_continue_game(game_id: int, is_challenge: bool = false) -> void:
	GameManager.current_game_id = game_id
	GameManager.is_challenge_game = is_challenge
	get_tree().change_scene_to_file("res://scenes/game.tscn")

func _on_back_pressed() -> void:
	waiting_timer.stop()
	waiting_game_id = 0
	# Выход из аккаунта
	ApiClient.logout()
	login_panel.visible = true
	login_status.text = ""
	username_input.text = ""
	password_input.text = ""
	username_input.grab_focus()
