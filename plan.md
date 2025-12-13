# План портирования арены на Unity WebGL

## Предварительные требования

### Установка Unity

1. **Скачать Unity Hub**: https://unity.com/download
2. **Установить Unity Editor 2022.3 LTS** через Unity Hub:
   - Добавить модуль: WebGL Build Support
   - Добавить модуль: Visual Studio Code Editor (или VS)
3. **Создать Unity аккаунт** (бесплатный Personal план)

### Системные требования
- Windows 10/11 или macOS 10.15+
- 4GB RAM минимум (8GB рекомендуется)
- 10GB свободного места

## Обзор задачи

Портировать функционал схватки из `/arena/play` на Unity WebGL:
- Выбор противника
- Игровое поле (шахматная доска)
- Ходы юнитов (движение, атака, пропуск, откладывание)
- Синхронизация с бэкендом через API

## Архитектура решения

```
┌─────────────────────────────────────────────────────────────────┐
│                         nginx (порт 80)                         │
├─────────────────────────────────────────────────────────────────┤
│  /unityArena/* ──────► unity-arena:8081 (Unity WebGL билд)     │
│  /* ─────────────────► web:5000 (Flask)                         │
│  /arena/api/* ───────► web:5000 (API остаётся на Flask)        │
└─────────────────────────────────────────────────────────────────┘
```

## Структура папок

```
ModernHomm/
├── unity-arena/                    # Unity проект
│   ├── Assets/
│   │   ├── Scripts/
│   │   │   ├── Core/
│   │   │   │   ├── GameManager.cs         # Управление игрой
│   │   │   │   ├── ApiClient.cs           # HTTP запросы к /arena/api
│   │   │   │   └── GameState.cs           # Модели данных
│   │   │   ├── UI/
│   │   │   │   ├── PlayerSelectUI.cs      # Выбор противника
│   │   │   │   ├── GameBoardUI.cs         # Игровое поле
│   │   │   │   ├── UnitInfoPanel.cs       # Информация о юните
│   │   │   │   ├── ActionPanel.cs         # Панель действий
│   │   │   │   ├── GameLogUI.cs           # Лог боя
│   │   │   │   └── OverlayUI.cs           # Оверлеи (атака, конец игры)
│   │   │   ├── Board/
│   │   │   │   ├── BoardController.cs     # Управление доской
│   │   │   │   ├── CellController.cs      # Клетка поля
│   │   │   │   └── UnitController.cs      # Юнит на поле
│   │   │   └── Utils/
│   │   │       └── Pathfinding.cs         # BFS для движения
│   │   ├── Prefabs/
│   │   │   ├── Cell.prefab               # Префаб клетки
│   │   │   ├── Unit.prefab               # Префаб юнита
│   │   │   └── Obstacle.prefab           # Препятствие
│   │   ├── Scenes/
│   │   │   ├── MainMenu.unity            # Выбор противника
│   │   │   └── Battle.unity              # Игровое поле
│   │   ├── UI/                           # UI компоненты
│   │   └── Resources/                    # Спрайты, шрифты
│   ├── Packages/
│   ├── ProjectSettings/
│   └── Build/                            # WebGL билд
│       └── WebGL/
│           ├── index.html
│           ├── Build/
│           └── TemplateData/
├── unity-arena-server/                   # Docker контейнер для хостинга
│   ├── Dockerfile
│   └── nginx.conf                        # Простой nginx для статики
└── docker-compose.yml                    # +unity-arena сервис
```

## Этапы реализации

### Этап 1: Создание Unity проекта (базовая структура)

1. Создать папку `unity-arena/`
2. Инициализировать Unity проект (URP для WebGL)
3. Создать базовую структуру папок
4. Настроить WebGL Build Settings:
   - Compression: Gzip
   - Memory Size: 256MB
   - Template: Minimal

### Этап 2: Модели данных и API клиент

1. **GameState.cs** - модели:
   ```csharp
   [Serializable]
   public class GameStateResponse {
       public int game_id;
       public string status;
       public int player1_id, player2_id;
       public string player1_name, player2_name;
       public int current_player_id;
       public int? winner_id;
       public FieldInfo field;
       public List<UnitInfo> units;
       public List<ObstacleInfo> obstacles;
       public List<LogEntry> logs;
   }
   ```

2. **ApiClient.cs** - HTTP запросы:
   - `GetPlayers()` - список игроков
   - `CreateGame()` - создать игру
   - `GetGameState()` - состояние игры
   - `GetUnitActions()` - доступные действия
   - `MakeMove()` - выполнить ход

### Этап 3: Сцена выбора противника (MainMenu)

1. UI Canvas:
   - Информация о текущем игроке (имя, баланс, армия)
   - Dropdown выбора противника
   - Dropdown размера поля (5x5, 7x7, 10x10)
   - Кнопка "Начать бой"
   - Уведомление о входящих вызовах

2. Логика:
   - Загрузка списка игроков с API
   - Фильтрация по стоимости армии (±50%)
   - Создание игры через API
   - Переход на сцену Battle

### Этап 4: Игровое поле (Battle сцена)

1. **BoardController** - генерация доски:
   - Создание сетки клеток (5x5 до 10x10)
   - Шахматная раскраска
   - Координаты (A-J, 1-10)
   - Размещение препятствий

2. **UnitController** - юниты:
   - Спрайт/иконка юнита
   - Текст количества (x5)
   - Индикатор готовности (зелёный/серый)
   - Цвет игрока (синий/красный)

3. **Подсветка клеток**:
   - Зелёные - возможные ходы
   - Красные - цели атаки
   - Жёлтый контур - выбранный юнит

### Этап 5: UI панели

1. **Левая панель** (Player 1):
   - Портрет выбранного юнита
   - Статистика (урон, защита, HP, количество)
   - Список юнитов игрока

2. **Правая панель** (Player 2):
   - Аналогично левой
   - Показывает инфо при наведении на врага

3. **Панель действий** (при выборе юнита):
   - Кнопка "Двигаться" 🚶
   - Кнопка "Атаковать" ⚔️
   - Кнопка "Пропустить" ⏭️
   - Кнопка "Сбежать" 🏃

4. **Лог игры** (внизу):
   - ScrollView со списком событий
   - Иконки по типу (атака, движение, старт)
   - Максимум 50 записей

### Этап 6: Игровая логика

1. **Выбор юнита**:
   - Клик на своём юните → выделение
   - Запрос `/api/games/{id}/units/{unit_id}/actions`
   - Отображение возможных ходов/атак

2. **Движение**:
   - Клик на зелёной клетке
   - POST `/api/games/{id}/move` с action="move"
   - Анимация перемещения (Tween)
   - Обновление состояния

3. **Атака**:
   - Клик на красной клетке
   - POST `/api/games/{id}/move` с action="attack"
   - Оверлей результата атаки
   - Анимация удара

4. **Polling** (каждые 2 сек):
   - GET `/api/games/{id}/state`
   - Сравнение с текущим состоянием
   - Обновление UI при изменениях

### Этап 7: Оверлеи

1. **Battle Overlay** (при атаке):
   - Иконки атакующего и цели
   - Результат атаки (урон, убито)
   - Автоскрытие через 5 сек

2. **Game Over Overlay**:
   - "ПОБЕДА!" или "ПОРАЖЕНИЕ"
   - Статистика боя
   - Кнопка возврата

### Этап 8: Docker контейнер

1. **Dockerfile** для unity-arena-server:
   ```dockerfile
   FROM nginx:alpine
   COPY Build/WebGL/ /usr/share/nginx/html/
   COPY nginx.conf /etc/nginx/nginx.conf
   EXPOSE 8081
   ```

2. **docker-compose.yml** - добавить сервис:
   ```yaml
   unity-arena:
     build: ./unity-arena-server
     container_name: modernhomm_unity_arena
     restart: unless-stopped
     networks:
       - modernhomm_network
   ```

### Этап 9: Nginx конфигурация

Добавить в nginx.conf:
```nginx
upstream unity_backend {
    server unity-arena:8081;
}

location /unityArena/ {
    proxy_pass http://unity_backend/;
    proxy_set_header Host $host;
}
```

### Этап 10: Интеграция в веб-меню

1. Добавить пункт меню в `/arena/play`:
   - "🎮 Unity схватка" → `/unityArena/`

2. Модифицировать `web/arena.py`:
   - Добавить ссылку в шаблон страницы play

## API Endpoints (используемые Unity)

| Метод | Endpoint | Описание |
|-------|----------|----------|
| GET | `/arena/api/players` | Список игроков |
| POST | `/arena/api/games/create` | Создать игру |
| POST | `/arena/api/games/{id}/accept` | Принять вызов |
| GET | `/arena/api/games/{id}/state` | Состояние игры |
| GET | `/arena/api/games/{id}/units/{uid}/actions` | Действия юнита |
| POST | `/arena/api/games/{id}/move` | Сделать ход |

## Технические требования

- **Unity версия**: 2022.3 LTS (для стабильного WebGL)
- **Render Pipeline**: URP (лучшая производительность WebGL)
- **Разрешение**: 1280x720 (адаптивное)
- **Браузеры**: Chrome, Firefox, Safari, Edge

## Оценка времени

| Этап | Часы |
|------|------|
| 1. Создание проекта | 2-3 |
| 2. Модели и API | 4-5 |
| 3. Выбор противника | 6-8 |
| 4. Игровое поле | 10-12 |
| 5. UI панели | 8-10 |
| 6. Игровая логика | 12-15 |
| 7. Оверлеи | 4-5 |
| 8. Docker | 2-3 |
| 9. Nginx | 1-2 |
| 10. Интеграция | 2-3 |
| **Итого** | **51-66 часов** |

## Риски и ограничения

1. **WebGL производительность** - может тормозить на слабых устройствах
2. **CORS** - нужно настроить на Flask для запросов из Unity
3. **Память WebGL** - ограничена, нужно оптимизировать ассеты
4. **Мобильные устройства** - WebGL работает плохо на iOS Safari

## Начало работы

1. Установить Unity Hub и Unity 2022.3 LTS
2. Создать проект с URP template
3. Настроить WebGL в Build Settings
4. Начать с ApiClient и моделей данных
