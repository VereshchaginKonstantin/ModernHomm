# План реализации веб-просмотра боёв с Phaser.js

## Обзор

Добавить в админ-панель отдельную вкладку "Арена" с возможностью:
1. Просмотра прошлых боёв с анимациями (режим воспроизведения)
2. Игры в реальном времени через браузер (режим игры)

## Архитектура

### Технологии
- **Frontend**: Phaser.js 3 (игровой движок для анимаций)
- **Backend**: Flask REST API для данных игры
- **WebSocket**: Flask-SocketIO для real-time обновлений в режиме игры
- **База данных**: Существующие модели Game, BattleUnit, GameLog

### Структура файлов

```
/home/devuser/cl_Code/ModernHomm/
├── admin_arena.py           # Blueprint для арены (новый)
├── static/
│   └── arena/
│       ├── js/
│       │   ├── phaser.min.js     # Phaser.js библиотека
│       │   ├── game.js           # Основной игровой класс
│       │   ├── scenes/
│       │   │   ├── BattleScene.js    # Сцена боя
│       │   │   ├── ReplayScene.js    # Сцена воспроизведения
│       │   │   └── UIScene.js        # UI оверлей (логи, кнопки)
│       │   └── utils/
│       │       ├── api.js        # API клиент
│       │       └── animations.js # Анимации атак/перемещений
│       ├── css/
│       │   └── arena.css
│       └── assets/
│           ├── units/           # Спрайты юнитов (PNG)
│           ├── tiles/           # Текстуры поля
│           └── effects/         # Эффекты атак
├── templates/
│   └── arena/
│       ├── index.html           # Главная страница арены
│       ├── replay.html          # Страница воспроизведения
│       └── play.html            # Страница игры
└── Dockerfile.admin            # Обновить для новых файлов
```

## API Endpoints

### REST API (admin_arena.py)

```python
# Список игроков для выбора противника
GET /arena/api/players
Response: [{"id", "name", "telegram_id", "balance", "wins", "losses", "units": [...]}]

# Список завершённых игр для просмотра
GET /arena/api/games?status=completed&limit=50
Response: [{"id", "player1", "player2", "winner", "field_size", "created_at", "duration"}]

# Данные конкретной игры для воспроизведения
GET /arena/api/games/<game_id>
Response: {
  "game": {...},
  "field": {"width", "height"},
  "players": [{"id", "name", "units": [...]}],
  "obstacles": [{"x", "y"}],
  "initial_units": [...],
  "logs": [{"event_type", "message", "data", "created_at"}]
}

# Создать новую игру
POST /arena/api/games/create
Body: {"player1_id", "player2_name", "field_size"}
Response: {"game_id", "status"}

# Принять игру (от имени player2 для тестирования)
POST /arena/api/games/<game_id>/accept
Body: {"player_id"}

# Сделать ход
POST /arena/api/games/<game_id>/move
Body: {"unit_id", "action": "move|attack|skip", "target_x", "target_y"}

# Получить доступные действия для юнита
GET /arena/api/games/<game_id>/units/<unit_id>/actions
Response: {"can_move": [...], "can_attack": [...]}
```

### WebSocket Events (для real-time режима)

```python
# Клиент → Сервер
"join_game": {"game_id"}
"make_move": {"unit_id", "action", "target"}
"leave_game": {}

# Сервер → Клиент
"game_state": {полное состояние игры}
"turn_changed": {"current_player_id"}
"unit_moved": {"unit_id", "from", "to"}
"attack_result": {"attacker", "target", "damage", "killed", "counterattack"}
"game_over": {"winner_id", "stats"}
```

## Phaser.js Структура

### BattleScene.js - Основная сцена боя

```javascript
class BattleScene extends Phaser.Scene {
    constructor() {
        super('BattleScene');
    }

    preload() {
        // Загрузка спрайтов юнитов, тайлов, эффектов
        this.load.image('tile_light', '/static/arena/assets/tiles/light.png');
        this.load.image('tile_dark', '/static/arena/assets/tiles/dark.png');
        this.load.image('obstacle', '/static/arena/assets/tiles/obstacle.png');
        // Юниты загружаются динамически по unit.image_path
    }

    create() {
        // Создание игрового поля
        this.createBoard();
        this.createUnits();
        this.createUI();
    }

    // Анимация перемещения юнита
    animateMove(unitSprite, path) {
        const timeline = this.tweens.createTimeline();
        path.forEach(({x, y}) => {
            timeline.add({
                targets: unitSprite,
                x: this.boardToScreenX(x),
                y: this.boardToScreenY(y),
                duration: 200,
                ease: 'Power2'
            });
        });
        return timeline.play();
    }

    // Анимация атаки
    animateAttack(attacker, target, damage) {
        // 1. Подсветка атакующего
        // 2. Линия/снаряд к цели
        // 3. Эффект удара
        // 4. Отображение урона
        // 5. Обновление HP/количества
    }
}
```

### ReplayScene.js - Воспроизведение записанного боя

```javascript
class ReplayScene extends BattleScene {
    constructor() {
        super('ReplayScene');
        this.logs = [];
        this.currentLogIndex = 0;
        this.isPlaying = false;
    }

    // Загрузка логов и начального состояния
    loadReplay(gameData) {
        this.logs = gameData.logs;
        this.setupInitialState(gameData.initial_units);
    }

    // Воспроизведение следующего события
    playNextEvent() {
        if (this.currentLogIndex >= this.logs.length) return;

        const event = this.logs[this.currentLogIndex++];

        switch (event.event_type) {
            case 'attack':
                await this.replayAttack(event.data);
                break;
            case 'move':
                await this.replayMove(event.data);
                break;
            case 'game_ended':
                this.showVictory(event.data);
                break;
        }
    }

    // Контроль воспроизведения
    play() { this.isPlaying = true; }
    pause() { this.isPlaying = false; }
    setSpeed(multiplier) { }
    seekTo(logIndex) { }
}
```

### UIScene.js - Оверлей интерфейса

```javascript
class UIScene extends Phaser.Scene {
    constructor() {
        super('UIScene');
    }

    create() {
        // Панель информации об игроках
        // Логи боя (прокручиваемый список)
        // Кнопки управления (для replay: play/pause/speed)
        // Индикатор текущего хода
    }

    addLog(message, type) {
        // Добавить сообщение в список логов
        // Подсветка в зависимости от типа (атака, крит, контратака)
    }

    updatePlayerInfo(player1, player2) {
        // Обновить HP, количество юнитов, мораль
    }
}
```

## Этапы реализации

### Этап 1: Базовая инфраструктура
- [ ] Создать admin_arena.py Blueprint
- [ ] Добавить вкладку "Арена" в навигацию
- [ ] Создать базовые HTML шаблоны
- [ ] Подключить Phaser.js
- [ ] Создать API endpoints для получения данных игр

### Этап 2: Воспроизведение боёв (Replay)
- [ ] Реализовать BattleScene с отрисовкой поля
- [ ] Загрузка начального состояния игры
- [ ] Парсинг логов для воспроизведения
- [ ] Анимации перемещения юнитов
- [ ] Анимации атак с визуализацией урона
- [ ] UIScene с логами и контролами воспроизведения
- [ ] Контроль скорости и перемотка

### Этап 3: Игра в реальном времени
- [ ] Интеграция Flask-SocketIO
- [ ] WebSocket события для real-time обновлений
- [ ] Выбор противника и создание игры
- [ ] Интерактивный выбор юнита для хода
- [ ] Подсветка доступных клеток для хода/атаки
- [ ] Выполнение хода через API
- [ ] Синхронизация состояния между игроками

### Этап 4: Улучшения и полировка
- [ ] Звуковые эффекты (опционально)
- [ ] Улучшенные анимации эффектов (крит, удача, контратака)
- [ ] Адаптивный дизайн для разных экранов
- [ ] Сохранение настроек скорости воспроизведения
- [ ] Мини-карта для больших полей

## Зависимости

### Python
- flask-socketio (для WebSocket)
- eventlet или gevent (для async WebSocket)

### JavaScript (CDN)
- Phaser.js 3.x

## Требования к обновлению

### requirements.txt
```
flask-socketio>=5.3.0
eventlet>=0.33.0
```

### Dockerfile.admin
```dockerfile
COPY admin_arena.py .
COPY static/arena/ ./static/arena/
COPY templates/arena/ ./templates/arena/
```

## Изменения в существующем коде

### GameLog - расширить для воспроизведения
Добавить JSON поле `data` для структурированных данных события:
```python
# Для атаки:
{
    "attacker_id": 1,
    "target_id": 2,
    "damage": 150,
    "killed": 2,
    "crit": true,
    "counterattack": {"damage": 30, "killed": 0}
}
```

### game_engine.py
- Добавить сохранение структурированных данных в GameLog
- Добавить метод get_game_state() для получения полного состояния

## Оценка сложности

- **Этап 1**: 2-3 часа - базовая настройка
- **Этап 2**: 4-6 часов - воспроизведение с анимациями
- **Этап 3**: 4-6 часов - real-time игра
- **Этап 4**: 2-3 часа - улучшения

**Итого**: ~14-18 часов работы

## Риски и ограничения

1. **Спрайты юнитов**: Нужны PNG изображения для всех типов юнитов
   - Решение: Использовать текстовые иконки как fallback

2. **WebSocket в Docker**: Требует правильной настройки nginx
   - Решение: Добавить proxy_pass для WebSocket

3. **Производительность**: Большие поля с множеством юнитов
   - Решение: Оптимизация рендеринга, object pooling
