# Unity Arena - Руководство по настройке

## Быстрый старт (автоматическая настройка)

1. Откройте проект в Unity 2022.3 LTS
2. Импортируйте TMP Essentials: **Window → TextMeshPro → Import TMP Essential Resources**
3. Запустите мастер: **ModernHomm → Setup All (Scenes + Prefabs)**
4. Откройте каждую сцену и привяжите ссылки: **ModernHomm → Link Scene References (Current Scene)**
5. Откройте сцену Bootstrap и нажмите Play!

## Меню ModernHomm

- **Setup All** - создать все сцены, префабы и материалы
- **Create Scenes Only** - создать только сцены
- **Create Prefabs Only** - создать только префабы
- **Link Prefab References** - привязать ссылки в префабах
- **Link Scene References** - привязать ссылки в текущей сцене (запускайте для каждой сцены)

## Требования

- Unity 2022.3 LTS
- TextMeshPro (устанавливается автоматически)

## Структура проекта

```
Assets/
├── Scripts/
│   ├── Core/           # Основная логика
│   │   ├── ApiClient.cs        # HTTP клиент для API
│   │   ├── GameManager.cs      # Менеджер состояния игры
│   │   ├── GameState.cs        # Модели данных
│   │   └── Bootstrap.cs        # Инициализация
│   ├── Board/          # Игровое поле
│   │   ├── BoardController.cs  # Управление доской
│   │   ├── CellController.cs   # Клетка поля
│   │   └── UnitController.cs   # Юнит на поле
│   ├── UI/             # Интерфейс
│   │   ├── PlayerSelectUI.cs   # Выбор противника
│   │   ├── GameBoardUI.cs      # UI игры
│   │   ├── UnitInfoPanel.cs    # Информация о юнитах
│   │   ├── ActionPanel.cs      # Панель действий
│   │   ├── GameLogUI.cs        # Лог событий
│   │   └── OverlayUI.cs        # Оверлеи
│   └── Utils/          # Утилиты
│       └── WebGLBridge.cs      # Связь с браузером
├── Plugins/
│   └── WebGL/
│       └── WebGLPlugin.jslib   # JavaScript для WebGL
└── Scenes/
    ├── Bootstrap.unity         # Стартовая сцена
    ├── MainMenu.unity          # Главное меню
    └── Battle.unity            # Сцена боя
```

## Создание сцен

### 1. Bootstrap (стартовая сцена)

1. Создайте сцену `Bootstrap`
2. Добавьте пустой GameObject `GameBootstrap`
3. Прикрепите скрипт `Bootstrap.cs`
4. В Build Settings установите эту сцену первой (index 0)

### 2. MainMenu (главное меню)

1. Создайте сцену `MainMenu`
2. Создайте UI Canvas:
   - **Canvas**: Screen Space - Overlay
   - **Canvas Scaler**: Scale With Screen Size, Reference: 1920x1080

3. Создайте панель игрока (левая часть):
   ```
   PlayerPanel
   ├── PlayerNameText (TMP)
   ├── BalanceText (TMP)
   ├── ArmyCostText (TMP)
   └── StatsText (TMP)
   ```

4. Создайте панель выбора противника:
   ```
   OpponentPanel
   ├── OpponentDropdown (TMP Dropdown)
   ├── OpponentInfoText (TMP)
   ├── FieldSizeDropdown (TMP Dropdown)
   └── StartBattleButton (Button)
   ```

5. Создайте панель входящего вызова:
   ```
   PendingGamePanel (по умолчанию неактивна)
   ├── PendingGameText (TMP)
   ├── AcceptButton (Button)
   └── DeclineButton (Button)
   ```

6. Добавьте пустой GameObject `MenuManager`
7. Прикрепите скрипт `PlayerSelectUI.cs`
8. Подключите все UI элементы в инспекторе

### 3. Battle (сцена боя)

1. Создайте сцену `Battle`

2. Создайте игровое поле:
   ```
   Board (пустой GameObject)
   └── BoardController.cs
   ```

3. Создайте префабы:

   **CellPrefab** (Sprites/Square):
   ```
   Cell
   ├── Background (SpriteRenderer, Order: 0)
   ├── Highlight (SpriteRenderer, Order: 1, изначально выключен)
   └── BoxCollider2D
   + CellController.cs
   ```

   **UnitPrefab**:
   ```
   Unit
   ├── Background (SpriteRenderer, Order: 2)
   ├── Icon (SpriteRenderer или TextMeshPro, Order: 3)
   ├── CountText (TextMeshPro, Order: 4)
   ├── ReadyIndicator (GameObject, зелёный круг)
   └── SelectionIndicator (SpriteRenderer, жёлтая рамка)
   + UnitController.cs
   + BoxCollider2D
   ```

   **ObstaclePrefab**:
   ```
   Obstacle
   └── SpriteRenderer (камень/скала)
   ```

4. Создайте UI для боя:
   ```
   BattleCanvas
   ├── TopPanel
   │   └── TurnIndicator (Background Image + Text)
   ├── LeftPanel (Player1)
   │   ├── PlayerName (TMP)
   │   ├── UnitList (Scroll View)
   │   └── PortraitPanel
   + UnitInfoPanel.cs
   ├── RightPanel (Player2)
   │   └── (то же самое)
   + UnitInfoPanel.cs
   ├── BottomPanel
   │   ├── ActionPanel
   │   │   ├── MoveButton
   │   │   ├── AttackButton
   │   │   ├── SkipButton
   │   │   ├── DeferButton
   │   │   └── SurrenderButton
   │   + ActionPanel.cs
   │   └── HintText (TMP)
   ├── GameLogPanel (справа)
   │   └── ScrollView + Content
   │   + GameLogUI.cs
   └── Overlays
       ├── BattleResultPanel (изначально неактивна)
       │   └── ResultText (TMP)
       └── GameOverPanel (изначально неактивна)
           ├── TitleText (TMP)
           ├── SubtitleText (TMP)
           ├── StatsText (TMP)
           └── ReturnButton
       + OverlayUI.cs
   ```

5. Добавьте GameObject `GameBoardUI` и прикрепите скрипт

## Настройка префабов

### Cell Prefab

В `CellController`:
- Background Renderer: спрайт фона
- Highlight Renderer: спрайт подсветки
- Click Collider: BoxCollider2D

### Unit Prefab

В `UnitController`:
- Background Renderer: фон юнита
- Icon Renderer: иконка/спрайт юнита
- Count Text: TextMeshPro для количества
- Ready Indicator: индикатор готовности (зелёный)
- Selection Indicator: рамка выделения

### Настройка BoardController

- Cell Prefab: созданный префаб клетки
- Unit Prefab: созданный префаб юнита
- Obstacle Prefab: префаб препятствия
- Cell Size: 1.0 (размер клетки в юнитах)
- Цвета: настройте по вкусу

## Настройка камеры

Для сцены Battle:
- Camera: Orthographic
- Size: ~5-7 (в зависимости от размера поля)
- Position: (0, 0, -10)

## Build Settings

1. File → Build Settings
2. Добавьте сцены в порядке:
   - Bootstrap (0)
   - MainMenu (1)
   - Battle (2)
3. Platform: WebGL
4. Player Settings:
   - Resolution: 1280x720 или 1920x1080
   - WebGL Memory Size: 256-512MB
   - Compression Format: Gzip
   - Decompression Fallback: включить

## Тестирование

### В редакторе

1. Откройте сцену Bootstrap
2. Нажмите Play
3. Или напрямую откройте MainMenu/Battle для тестирования

### WebGL билд

1. Build → WebGL
2. Скопируйте файлы в `unity-arena-server/` или примонтируйте через Docker volume
3. Откройте http://modernhomm.ru/unityArena/

## API подключение

По умолчанию:
- В редакторе: http://localhost:5000
- В WebGL: определяется из URL страницы

Для ручной настройки используйте Bootstrap → Debug Api Url

## Параметры URL

При открытии игры можно передать:
- `?player_id=123` - ID игрока (сохраняется в localStorage)
- `?game_id=456` - ID игры (для прямого входа в бой)

Пример: http://modernhomm.ru/unityArena/?player_id=1&game_id=42

## Troubleshooting

### CORS ошибки
Убедитесь, что nginx настроен на разрешение CORS для API запросов.

### Юниты не отображаются
Проверьте порядок отрисовки (Sorting Order) в SpriteRenderer.

### Клики не работают
Убедитесь, что есть Collider2D и Camera имеет Physics Raycaster.

### Шрифты не отображаются
Импортируйте TMP Essentials (Window → TextMeshPro → Import TMP Essential Resources).
