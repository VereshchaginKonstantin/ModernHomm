/**
 * Phaser.js игра для интерактивного боя (режим игры)
 * С поддержкой графического интерфейса и синхронизации с Telegram
 */

// Константы
const CELL_SIZE = 80;
const BOARD_PADDING = 40;
const COLORS = {
    lightTile: 0xF0D9B5,
    darkTile: 0xB58863,
    obstacle: 0x555555,
    player1: 0xe74c3c,
    player2: 0x2ecc71,
    moveHighlight: 0x27ae60,      // Зелёный для перемещения
    attackHighlight: 0xe74c3c,     // Красный для атаки
    selectedUnit: 0xf1c40f,        // Жёлтый для выбранного юнита
    activeUnit: 0x3498db           // Синий для активных юнитов (могут ходить)
};

// Глобальные переменные
let game = null;
let playScene = null;
let currentGameId = null;
let currentPlayerId = null;
let selectedUnitId = null;
let actionMode = null; // 'move' или 'attack'
let pollingInterval = null;
let lastGameStateHash = null;

// Инициализация после загрузки DOM
document.addEventListener('DOMContentLoaded', () => {
    // Проверяем автозагрузку игры (для PLAY_GAME_TEMPLATE)
    if (typeof autoLoadGameId !== 'undefined' && autoLoadGameId) {
        currentGameId = autoLoadGameId;
        currentPlayerId = typeof autoLoadPlayerId !== 'undefined' ? autoLoadPlayerId : null;
        loadActiveGame();
    } else {
        setupGameSetup();
        setupExistingGameLoader();
    }
});

/**
 * Настройка формы создания игры
 */
function setupGameSetup() {
    const btnStart = document.getElementById('btn-start-game');
    if (btnStart) {
        btnStart.addEventListener('click', startNewGame);
    }
}

/**
 * Настройка загрузки существующей игры
 */
function setupExistingGameLoader() {
    // Проверяем URL параметры для загрузки существующей игры
    const urlParams = new URLSearchParams(window.location.search);
    const gameId = urlParams.get('game_id');
    const playerId = urlParams.get('player_id');

    if (gameId && playerId) {
        currentGameId = parseInt(gameId);
        currentPlayerId = parseInt(playerId);
        loadExistingGame();
    }
}

/**
 * Загрузка существующей игры (из URL параметров)
 */
async function loadExistingGame() {
    try {
        const gameSetup = document.getElementById('game-setup');
        if (gameSetup) gameSetup.style.display = 'none';

        const gameContainer = document.getElementById('game-container');
        if (gameContainer) gameContainer.style.display = 'block';

        await initPlayGame();
    } catch (error) {
        console.error('Error loading existing game:', error);
        alert('Ошибка загрузки игры: ' + error.message);
    }
}

/**
 * Загрузка активной игры (для PLAY_GAME_TEMPLATE)
 */
async function loadActiveGame() {
    try {
        await initPlayGame();
    } catch (error) {
        console.error('Error loading active game:', error);
        alert('Ошибка загрузки игры: ' + error.message);
    }
}

/**
 * Начало новой игры
 */
async function startNewGame() {
    const player1Input = document.getElementById('player1-id');
    const player2Select = document.getElementById('player2-select');
    const fieldSelect = document.getElementById('field-select');

    const player1Id = parseInt(player1Input.value);
    const player1Name = player1Input.dataset.name;
    const player2Id = parseInt(player2Select.value);
    const player2Name = player2Select.options[player2Select.selectedIndex].dataset.name;
    const fieldSize = fieldSelect.value;

    if (player1Id === player2Id) {
        alert('Нельзя играть против себя!');
        return;
    }

    try {
        // Создаём игру
        const createResponse = await fetch(`${apiBase}/games/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                player1_id: player1Id,
                player2_name: player2Name,
                field_size: fieldSize
            })
        });

        const createData = await createResponse.json();
        if (!createData.success) {
            alert('Ошибка создания игры: ' + createData.message);
            return;
        }

        currentGameId = createData.game_id;
        currentPlayerId = player1Id;

        // Принимаем игру от имени player2
        const acceptResponse = await fetch(`${apiBase}/games/${currentGameId}/accept`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_id: player2Id })
        });

        const acceptData = await acceptResponse.json();
        if (!acceptData.success) {
            alert('Ошибка принятия игры: ' + acceptData.message);
            return;
        }

        // Скрываем форму, показываем игру
        document.getElementById('game-setup').style.display = 'none';
        document.getElementById('game-container').style.display = 'block';

        // Устанавливаем имена игроков
        document.getElementById('p1-name').textContent = player1Name;
        document.getElementById('p2-name').textContent = player2Name;

        // Инициализируем Phaser игру
        await initPlayGame();

    } catch (error) {
        console.error('Error starting game:', error);
        alert('Ошибка: ' + error.message);
    }
}

/**
 * Инициализация Phaser игры для режима игры
 */
async function initPlayGame() {
    // Получаем состояние игры
    const response = await fetch(`${apiBase}/games/${currentGameId}/state`);
    const gameState = await response.json();

    const fieldWidth = gameState.field.width * CELL_SIZE + BOARD_PADDING * 2;
    const fieldHeight = gameState.field.height * CELL_SIZE + BOARD_PADDING * 2;

    const config = {
        type: Phaser.AUTO,
        width: fieldWidth,
        height: fieldHeight,
        parent: 'phaser-game',
        backgroundColor: '#1a1a2e',
        scene: [PlayScene]
    };

    game = new Phaser.Game(config);
    game.gameState = gameState;

    // Запускаем polling для синхронизации
    startPolling();
}

/**
 * Запуск polling для синхронизации с Telegram
 */
function startPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }

    // Обновляем каждые 2 секунды
    pollingInterval = setInterval(async () => {
        if (playScene && currentGameId) {
            await playScene.checkForUpdates();
        }
    }, 2000);
}

/**
 * Остановка polling
 */
function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

/**
 * Сцена интерактивной игры
 */
class PlayScene extends Phaser.Scene {
    constructor() {
        super({ key: 'PlayScene' });
        this.units = new Map();
        this.obstacles = [];
        this.highlightGraphics = null;
        this.selectionGraphics = null;
        this.availableMoves = [];
        this.availableAttacks = [];
    }

    create() {
        playScene = this;
        this.gameState = this.game.gameState;
        this.fieldWidth = this.gameState.field.width;
        this.fieldHeight = this.gameState.field.height;

        // Определяем, нужно ли зеркалить поле (если текущий игрок - player2)
        this.isViewerPlayer2 = currentPlayerId === this.gameState.player2_id;

        // Рисуем поле
        this.drawBoard();

        // Рисуем препятствия
        this.drawObstacles();

        // Создаём юнитов
        this.createUnits();

        // Графика для подсветки ходов
        this.highlightGraphics = this.add.graphics();
        this.highlightGraphics.setDepth(1);

        // Графика для выделения юнитов
        this.selectionGraphics = this.add.graphics();
        this.selectionGraphics.setDepth(2);

        // Настраиваем обработчик кликов на поле
        this.input.on('pointerdown', this.handleClick, this);

        // Настраиваем обработчик движения мыши для показа цели при атаке
        this.input.on('pointermove', this.handlePointerMove, this);

        // Настраиваем кнопки действий
        this.setupActionButtons();

        // Обновляем UI
        this.updateUI();

        // Подсвечиваем активных юнитов
        this.highlightActiveUnits();

        // Загружаем логи с сервера при старте
        if (this.gameState.logs && this.gameState.logs.length > 0) {
            this.loadInitialLogs(this.gameState.logs);
        }

        // Показываем начальную подсказку
        this.showHint('🎮 Игра началась! Нажмите на юнита с зеленым индикатором чтобы выбрать его.');
    }

    /**
     * Загрузка начальных логов с сервера
     */
    loadInitialLogs(serverLogs) {
        const logContainer = document.getElementById('log-entries');
        if (!logContainer || !serverLogs) return;

        // Очищаем контейнер
        logContainer.innerHTML = '';

        // Добавляем логи в обратном порядке (новые сверху)
        const reversedLogs = [...serverLogs].reverse();
        reversedLogs.forEach(log => {
            const entry = document.createElement('div');
            entry.className = `log-entry ${log.event_type}`;

            const time = new Date(log.created_at).toLocaleTimeString('ru-RU', {
                hour: '2-digit', minute: '2-digit', second: '2-digit'
            });
            entry.innerHTML = `<span style="color: #888; font-size: 11px;">[${time}]</span> ${log.message}`;

            logContainer.appendChild(entry);
        });
    }

    /**
     * Рисование доски
     */
    drawBoard() {
        const graphics = this.add.graphics();

        // Подписи колонок
        for (let x = 0; x < this.fieldWidth; x++) {
            const label = String.fromCharCode(65 + x);
            this.add.text(
                BOARD_PADDING + x * CELL_SIZE + CELL_SIZE / 2,
                15,
                label,
                { fontSize: '16px', color: '#ffffff', fontStyle: 'bold' }
            ).setOrigin(0.5);
        }

        // Подписи строк
        for (let y = 0; y < this.fieldHeight; y++) {
            this.add.text(
                15,
                BOARD_PADDING + y * CELL_SIZE + CELL_SIZE / 2,
                String(y + 1),
                { fontSize: '16px', color: '#ffffff', fontStyle: 'bold' }
            ).setOrigin(0.5);
        }

        // Клетки
        for (let x = 0; x < this.fieldWidth; x++) {
            for (let y = 0; y < this.fieldHeight; y++) {
                const isLight = (x + y) % 2 === 0;
                const color = isLight ? COLORS.lightTile : COLORS.darkTile;

                graphics.fillStyle(color, 1);
                graphics.fillRect(
                    BOARD_PADDING + x * CELL_SIZE,
                    BOARD_PADDING + y * CELL_SIZE,
                    CELL_SIZE,
                    CELL_SIZE
                );
            }
        }

        // Рамка
        graphics.lineStyle(3, 0x333333, 1);
        graphics.strokeRect(
            BOARD_PADDING,
            BOARD_PADDING,
            this.fieldWidth * CELL_SIZE,
            this.fieldHeight * CELL_SIZE
        );
    }

    /**
     * Рисование препятствий
     */
    drawObstacles() {
        const graphics = this.add.graphics();

        this.gameState.obstacles.forEach(obs => {
            const screenX = BOARD_PADDING + obs.x * CELL_SIZE;
            const screenY = BOARD_PADDING + obs.y * CELL_SIZE;

            graphics.fillStyle(COLORS.obstacle, 0.8);
            graphics.fillRect(screenX, screenY, CELL_SIZE, CELL_SIZE);

            graphics.lineStyle(2, 0x333333, 0.5);
            graphics.lineBetween(
                screenX + 10, screenY + 10,
                screenX + CELL_SIZE - 10, screenY + CELL_SIZE - 10
            );
            graphics.lineBetween(
                screenX + CELL_SIZE - 10, screenY + 10,
                screenX + 10, screenY + CELL_SIZE - 10
            );

            this.obstacles.push({ x: obs.x, y: obs.y });
        });
    }

    /**
     * Создание юнитов
     */
    createUnits() {
        this.gameState.units.forEach(unit => {
            if (unit.count > 0) {
                this.createUnitSprite(unit);
            }
        });
    }

    /**
     * Создание спрайта юнита
     */
    createUnitSprite(unitData) {
        const screenX = this.boardToScreenX(unitData.x);
        const screenY = this.boardToScreenY(unitData.y);

        const container = this.add.container(screenX, screenY);
        container.setDepth(10);

        const bgColor = this.getPlayerColor(unitData.player_id);

        // Фон
        const bg = this.add.graphics();
        bg.fillStyle(bgColor, 0.3);
        bg.fillRoundedRect(-CELL_SIZE/2 + 5, -CELL_SIZE/2 + 5, CELL_SIZE - 10, CELL_SIZE - 10, 8);
        bg.lineStyle(2, bgColor, 1);
        bg.strokeRoundedRect(-CELL_SIZE/2 + 5, -CELL_SIZE/2 + 5, CELL_SIZE - 10, CELL_SIZE - 10, 8);
        container.add(bg);

        // Иконка
        const icon = unitData.unit_type?.icon || '❓';
        const iconText = this.add.text(0, -8, icon, { fontSize: '32px' }).setOrigin(0.5);
        container.add(iconText);

        // Количество
        const countText = this.add.text(0, 22, `x${unitData.count}`, {
            fontSize: '14px',
            color: '#ffffff',
            fontStyle: 'bold',
            stroke: '#000000',
            strokeThickness: 3
        }).setOrigin(0.5);
        container.add(countText);

        // Индикатор готовности (зеленый кружок если может ходить)
        const canAct = !unitData.has_moved && unitData.player_id === this.gameState.current_player_id;
        if (canAct) {
            const readyIndicator = this.add.circle(CELL_SIZE/2 - 15, -CELL_SIZE/2 + 15, 8, 0x2ecc71);
            container.add(readyIndicator);
            container.setData('readyIndicator', readyIndicator);
        }

        container.setData('unitData', { ...unitData });
        container.setData('countText', countText);
        container.setData('bg', bg);

        this.units.set(unitData.id, container);
        return container;
    }

    /**
     * Получение цвета игрока
     */
    getPlayerColor(playerId) {
        // Используем player1_id из состояния игры для определения цвета
        return playerId === this.gameState.player1_id ? COLORS.player1 : COLORS.player2;
    }

    /**
     * Конвертация координат (с учётом зеркалирования для player2)
     */
    boardToScreenX(x) {
        // Для player2 зеркалим X координату
        const effectiveX = this.isViewerPlayer2 ? (this.fieldWidth - 1 - x) : x;
        return BOARD_PADDING + effectiveX * CELL_SIZE + CELL_SIZE / 2;
    }

    boardToScreenY(y) {
        return BOARD_PADDING + y * CELL_SIZE + CELL_SIZE / 2;
    }

    screenToBoardX(screenX) {
        const rawX = Math.floor((screenX - BOARD_PADDING) / CELL_SIZE);
        // Для player2 зеркалим X координату обратно
        return this.isViewerPlayer2 ? (this.fieldWidth - 1 - rawX) : rawX;
    }

    screenToBoardY(screenY) {
        return Math.floor((screenY - BOARD_PADDING) / CELL_SIZE);
    }

    /**
     * Подсветка активных юнитов (могут ходить)
     */
    highlightActiveUnits() {
        this.selectionGraphics.clear();

        this.units.forEach((container, unitId) => {
            const data = container.getData('unitData');

            // Юниты текущего игрока, которые еще не ходили
            if (!data.has_moved &&
                data.player_id === this.gameState.current_player_id &&
                data.count > 0) {

                // Пульсирующая обводка для активных юнитов
                this.selectionGraphics.lineStyle(3, COLORS.activeUnit, 0.8);
                this.selectionGraphics.strokeRect(
                    BOARD_PADDING + data.x * CELL_SIZE + 3,
                    BOARD_PADDING + data.y * CELL_SIZE + 3,
                    CELL_SIZE - 6,
                    CELL_SIZE - 6
                );
            }
        });
    }

    /**
     * Обработка движения мыши (для показа цели атаки при наведении)
     */
    handlePointerMove(pointer) {
        // Показываем портрет цели только в режиме атаки
        if (actionMode !== 'attack') {
            return;
        }

        const boardX = this.screenToBoardX(pointer.x);
        const boardY = this.screenToBoardY(pointer.y);

        // Проверяем границы поля
        if (boardX < 0 || boardX >= this.fieldWidth || boardY < 0 || boardY >= this.fieldHeight) {
            return;
        }

        // Проверяем, есть ли цель под курсором
        const target = this.availableAttacks.find(t => t.x === boardX && t.y === boardY);

        if (target) {
            const targetContainer = this.units.get(target.id);
            if (targetContainer) {
                const targetData = targetContainer.getData('unitData');
                this.showTargetUnitPortrait(targetData);
            }
        } else {
            // Скрываем портреты целей если не над целью
            const targetP1 = document.getElementById('p1-target-portrait');
            const targetP2 = document.getElementById('p2-target-portrait');
            if (targetP1) targetP1.style.display = 'none';
            if (targetP2) targetP2.style.display = 'none';
        }
    }

    /**
     * Обработка клика на поле
     */
    async handleClick(pointer) {
        const boardX = this.screenToBoardX(pointer.x);
        const boardY = this.screenToBoardY(pointer.y);

        // Проверяем границы поля
        if (boardX < 0 || boardX >= this.fieldWidth || boardY < 0 || boardY >= this.fieldHeight) {
            return;
        }

        // Если выбран режим перемещения
        if (actionMode === 'move') {
            await this.handleMoveClick(boardX, boardY);
            return;
        }

        // Если выбран режим атаки
        if (actionMode === 'attack') {
            await this.handleAttackClick(boardX, boardY);
            return;
        }

        // Иначе - выбор юнита
        await this.handleUnitSelect(boardX, boardY);
    }

    /**
     * Выбор юнита на поле
     */
    async handleUnitSelect(boardX, boardY) {
        // Проверяем, что сейчас ход текущего игрока (того, кто смотрит страницу)
        if (currentPlayerId !== this.gameState.current_player_id) {
            this.showHint('⏳ Ожидайте своего хода');
            return;
        }

        // Находим юнит на этой клетке
        let foundUnit = null;
        this.units.forEach((container, id) => {
            const data = container.getData('unitData');
            if (data.x === boardX && data.y === boardY && data.count > 0) {
                foundUnit = { id, container, data };
            }
        });

        // Если нашли юнит текущего игрока, который еще не ходил
        if (foundUnit &&
            foundUnit.data.player_id === currentPlayerId &&
            !foundUnit.data.has_moved) {

            await this.selectUnit(foundUnit.id);
        } else if (foundUnit) {
            // Клик по вражескому юниту или юниту, который уже походил
            this.showHint(`${foundUnit.data.unit_type?.icon || '❓'} ${foundUnit.data.unit_type?.name || 'Юнит'} - не может действовать`);
        }
    }

    /**
     * Выбор юнита для действий
     */
    async selectUnit(unitId) {
        selectedUnitId = unitId;
        actionMode = null;

        // Очищаем подсветку ходов
        this.clearHighlights();

        // Получаем доступные действия с сервера
        try {
            const response = await fetch(`${apiBase}/games/${currentGameId}/units/${unitId}/actions`);
            const actions = await response.json();

            this.availableMoves = actions.can_move || [];
            this.availableAttacks = actions.can_attack || [];

            // Подсвечиваем выбранный юнит
            this.highlightSelectedUnit(unitId);

            // Показываем панель действий
            const actionPanel = document.getElementById('action-panel');
            actionPanel.style.display = 'block';

            const unitContainer = this.units.get(unitId);
            const unitData = unitContainer.getData('unitData');
            document.getElementById('selected-unit-info').textContent =
                `${unitData.unit_type?.icon || '❓'} ${unitData.unit_type?.name || 'Unknown'} (x${unitData.count})`;

            // Показываем портрет активного юнита
            this.showActiveUnitPortrait(unitData);

            // Включаем/выключаем кнопки в зависимости от доступных действий
            const btnMove = document.getElementById('btn-move');
            const btnAttack = document.getElementById('btn-attack');

            btnMove.disabled = this.availableMoves.length === 0;
            btnMove.style.opacity = this.availableMoves.length === 0 ? '0.5' : '1';

            btnAttack.disabled = this.availableAttacks.length === 0;
            btnAttack.style.opacity = this.availableAttacks.length === 0 ? '0.5' : '1';

            this.showHint(`✅ Выбран ${unitData.unit_type?.name || 'юнит'}. Доступно ходов: ${this.availableMoves.length}, целей: ${this.availableAttacks.length}`);

        } catch (error) {
            console.error('Error getting unit actions:', error);
            this.showHint('❌ Ошибка получения действий юнита');
        }
    }

    /**
     * Нормализация пути к изображению (добавляет / в начало если отсутствует)
     */
    normalizeImagePath(path) {
        if (!path) return '/static/images/units/default.png';
        // Если путь не начинается с /, добавляем его
        if (!path.startsWith('/')) {
            return '/' + path;
        }
        return path;
    }

    /**
     * Получить префикс для портретов в зависимости от текущего игрока
     * Активный игрок показывает портрет на своей стороне
     */
    getPortraitPrefix(isAttacker) {
        const currentPlayerId = this.gameState.current_player_id;
        const player1Id = this.gameState.player1_id;

        if (isAttacker) {
            // Атакующий юнит показывается на стороне текущего игрока
            return currentPlayerId === player1Id ? 'p1' : 'p2';
        } else {
            // Цель показывается на противоположной стороне
            return currentPlayerId === player1Id ? 'p2' : 'p1';
        }
    }

    /**
     * Показать портрет активного юнита (на стороне текущего игрока)
     */
    showActiveUnitPortrait(unitData) {
        const prefix = this.getPortraitPrefix(true);
        const portrait = document.getElementById(`${prefix}-active-portrait`);
        const img = document.getElementById(`${prefix}-active-image`);
        const name = document.getElementById(`${prefix}-active-name`);
        const stats = document.getElementById(`${prefix}-active-stats`);

        if (portrait && unitData.unit_type) {
            // Устанавливаем изображение (нормализуем путь)
            const imagePath = this.normalizeImagePath(unitData.unit_type.image_path);
            img.src = imagePath;
            img.onerror = () => { img.src = '/static/images/units/default.png'; };

            // Устанавливаем имя и статистику
            name.textContent = `${unitData.unit_type.icon || '❓'} ${unitData.unit_type.name}`;
            stats.innerHTML = `
                ⚔️ ${unitData.unit_type.damage} | 🛡️ ${unitData.unit_type.defense} | ❤️ ${unitData.unit_type.health}<br>
                📍 x${unitData.count} | HP: ${unitData.hp || unitData.unit_type.health}
            `;

            // Показываем с анимацией
            portrait.style.display = 'block';
            portrait.classList.remove('show');
            void portrait.offsetWidth; // Trigger reflow
            portrait.classList.add('show');
        }
    }

    /**
     * Показать портрет цели атаки (на стороне противника)
     */
    showTargetUnitPortrait(targetData) {
        const prefix = this.getPortraitPrefix(false);
        const portrait = document.getElementById(`${prefix}-target-portrait`);
        const img = document.getElementById(`${prefix}-target-image`);
        const name = document.getElementById(`${prefix}-target-name`);
        const stats = document.getElementById(`${prefix}-target-stats`);

        if (portrait && targetData.unit_type) {
            // Устанавливаем изображение (нормализуем путь)
            const imagePath = this.normalizeImagePath(targetData.unit_type.image_path);
            img.src = imagePath;
            img.onerror = () => { img.src = '/static/images/units/default.png'; };

            // Устанавливаем имя и статистику
            name.textContent = `${targetData.unit_type.icon || '❓'} ${targetData.unit_type.name}`;
            stats.innerHTML = `
                ⚔️ ${targetData.unit_type.damage} | 🛡️ ${targetData.unit_type.defense} | ❤️ ${targetData.unit_type.health}<br>
                📍 x${targetData.count} | HP: ${targetData.hp || targetData.unit_type.health}
            `;

            // Показываем с анимацией
            portrait.style.display = 'block';
            portrait.classList.remove('show');
            void portrait.offsetWidth; // Trigger reflow
            portrait.classList.add('show');
        }
    }

    /**
     * Скрыть портреты юнитов
     */
    hideUnitPortraits() {
        // Скрываем все портреты на обеих сторонах
        const portraits = [
            'p1-active-portrait', 'p1-target-portrait',
            'p2-active-portrait', 'p2-target-portrait'
        ];

        portraits.forEach(id => {
            const portrait = document.getElementById(id);
            if (portrait) portrait.style.display = 'none';
        });
    }

    /**
     * Подсветка выбранного юнита
     */
    highlightSelectedUnit(unitId) {
        this.selectionGraphics.clear();
        this.highlightActiveUnits();

        const container = this.units.get(unitId);
        if (container) {
            const data = container.getData('unitData');

            // Яркая жёлтая обводка для выбранного юнита
            this.selectionGraphics.lineStyle(4, COLORS.selectedUnit, 1);
            this.selectionGraphics.strokeRect(
                BOARD_PADDING + data.x * CELL_SIZE + 2,
                BOARD_PADDING + data.y * CELL_SIZE + 2,
                CELL_SIZE - 4,
                CELL_SIZE - 4
            );
        }
    }

    /**
     * Показать зоны перемещения (зелёные)
     */
    showMoveHighlights() {
        if (!selectedUnitId) {
            this.showHint('⚠️ Сначала выберите юнита!');
            return;
        }

        actionMode = 'move';
        this.clearHighlights();
        this.highlightSelectedUnit(selectedUnitId);

        // Зелёная подсветка для доступных ходов
        this.availableMoves.forEach(cell => {
            this.highlightGraphics.fillStyle(COLORS.moveHighlight, 0.5);
            this.highlightGraphics.fillRect(
                BOARD_PADDING + cell.x * CELL_SIZE,
                BOARD_PADDING + cell.y * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE
            );

            // Добавляем координаты на клетках
            const label = String.fromCharCode(65 + cell.x) + (cell.y + 1);
            this.highlightGraphics.fillStyle(0xffffff, 0.8);
        });

        this.showHint(`🚶 Нажмите на зелёную клетку для перемещения (${this.availableMoves.length} вариантов)`);
    }

    /**
     * Показать зоны атаки (красные)
     */
    showAttackHighlights() {
        if (!selectedUnitId) {
            this.showHint('⚠️ Сначала выберите юнита!');
            return;
        }

        actionMode = 'attack';
        this.clearHighlights();
        this.highlightSelectedUnit(selectedUnitId);

        // Красная подсветка для целей атаки
        this.availableAttacks.forEach(target => {
            this.highlightGraphics.fillStyle(COLORS.attackHighlight, 0.5);
            this.highlightGraphics.fillRect(
                BOARD_PADDING + target.x * CELL_SIZE,
                BOARD_PADDING + target.y * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE
            );
        });

        this.showHint(`⚔️ Нажмите на красную клетку для атаки (${this.availableAttacks.length} целей)`);
    }

    /**
     * Очистка подсветки ходов
     */
    clearHighlights() {
        this.highlightGraphics.clear();
    }

    /**
     * Обработка клика для перемещения
     */
    async handleMoveClick(boardX, boardY) {
        const targetCell = this.availableMoves.find(c => c.x === boardX && c.y === boardY);

        if (targetCell) {
            await this.executeMove(selectedUnitId, boardX, boardY);
        } else {
            this.showHint('❌ Нельзя переместиться на эту клетку!');
        }

        this.resetAction();
    }

    /**
     * Обработка клика для атаки
     */
    async handleAttackClick(boardX, boardY) {
        const target = this.availableAttacks.find(t => t.x === boardX && t.y === boardY);

        if (target) {
            // Показываем портрет цели перед атакой
            const targetContainer = this.units.get(target.id);
            if (targetContainer) {
                const targetData = targetContainer.getData('unitData');
                this.showTargetUnitPortrait(targetData);
            }

            await this.executeAttack(selectedUnitId, target.id);
        } else {
            this.showHint('❌ Нельзя атаковать эту клетку!');
        }

        this.resetAction();
    }

    /**
     * Выполнение перемещения
     */
    async executeMove(unitId, targetX, targetY) {
        try {
            const response = await fetch(`${apiBase}/games/${currentGameId}/move`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    unit_id: unitId,
                    action: 'move',
                    target_x: targetX,
                    target_y: targetY
                })
            });

            const result = await response.json();

            if (result.success) {
                // Анимация перемещения
                const container = this.units.get(unitId);
                if (container) {
                    this.tweens.add({
                        targets: container,
                        x: this.boardToScreenX(targetX),
                        y: this.boardToScreenY(targetY),
                        duration: 300,
                        ease: 'Power2'
                    });

                    // Обновляем данные
                    const data = container.getData('unitData');
                    data.x = targetX;
                    data.y = targetY;
                    data.has_moved = true;
                    container.setData('unitData', data);

                    // Убираем индикатор готовности
                    const readyIndicator = container.getData('readyIndicator');
                    if (readyIndicator) readyIndicator.destroy();
                }

                // Лог перемещения показываем как подсказку (move не логируется на сервере)
                this.showHint(`✅ ${result.message}`);

                // Проверяем смену хода
                if (result.turn_switched) {
                    await this.refreshGameState();
                } else {
                    this.highlightActiveUnits();
                }
            } else {
                this.showHint('❌ Ошибка: ' + result.message);
            }

        } catch (error) {
            console.error('Error executing move:', error);
            this.showHint('❌ Ошибка выполнения хода');
        }
    }

    /**
     * Выполнение атаки
     */
    async executeAttack(unitId, targetId) {
        try {
            // Получаем данные юнитов ДО атаки для анимации
            const attackerContainer = this.units.get(unitId);
            const targetContainer = this.units.get(targetId);
            const attackerData = attackerContainer?.getData('unitData');
            const targetData = targetContainer?.getData('unitData');

            const response = await fetch(`${apiBase}/games/${currentGameId}/move`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    unit_id: unitId,
                    action: 'attack',
                    target_unit_id: targetId
                })
            });

            const result = await response.json();

            if (result.success) {
                // Анимация атаки на поле
                const attacker = this.units.get(unitId);
                const target = this.units.get(targetId);

                if (attacker && target) {
                    await this.animateAttack(attacker, target);
                }

                // Показываем оверлей схватки с результатом
                if (attackerData && targetData && result.message) {
                    await this.showBattleOverlay(attackerData, targetData, result.message, 5000);
                }

                // Атака логируется на сервере, лог подгрузится через syncLogs
                // Показываем краткую подсказку
                this.showHint('⚔️ Атака выполнена!');

                // Обновляем состояние (включая логи с сервера)
                await this.refreshGameState();

                // Проверяем завершение игры
                if (result.game_status === 'completed') {
                    stopPolling();
                    this.showGameOver(result.winner_id);
                }
            } else {
                this.showHint('❌ Ошибка: ' + result.message);
            }

        } catch (error) {
            console.error('Error executing attack:', error);
            this.showHint('❌ Ошибка выполнения атаки');
        }
    }

    /**
     * Анимация атаки
     */
    animateAttack(attacker, target) {
        return new Promise(resolve => {
            const attackerX = attacker.x;
            const attackerY = attacker.y;
            const targetX = target.x;
            const targetY = target.y;

            const graphics = this.add.graphics();
            graphics.setDepth(100);

            this.tweens.add({
                targets: { progress: 0 },
                progress: 1,
                duration: 200,
                onUpdate: (tween) => {
                    const p = tween.getValue();
                    graphics.clear();
                    graphics.lineStyle(4, 0xff0000, 0.8);
                    graphics.lineBetween(
                        attackerX, attackerY,
                        attackerX + (targetX - attackerX) * p,
                        attackerY + (targetY - attackerY) * p
                    );
                },
                onComplete: () => {
                    // Эффект удара
                    const impact = this.add.circle(targetX, targetY, 30, 0xff0000, 0.8);
                    impact.setDepth(100);

                    this.tweens.add({
                        targets: impact,
                        scale: 2,
                        alpha: 0,
                        duration: 200,
                        onComplete: () => {
                            impact.destroy();
                            graphics.destroy();
                            resolve();
                        }
                    });

                    // Тряска цели
                    this.tweens.add({
                        targets: target,
                        x: targetX + 5,
                        yoyo: true,
                        repeat: 2,
                        duration: 40
                    });
                }
            });
        });
    }

    /**
     * Показать оверлей схватки с анимацией
     * @param {Object} attackerData - данные атакующего юнита
     * @param {Object} targetData - данные цели
     * @param {string} resultMessage - результат атаки
     * @param {number} duration - длительность показа в мс (по умолчанию 5000)
     */
    showBattleOverlay(attackerData, targetData, resultMessage, duration = 5000) {
        return new Promise(resolve => {
            // Создаём оверлей
            const overlay = document.createElement('div');
            overlay.className = 'battle-overlay';
            overlay.innerHTML = `
                <div class="battle-combatants">
                    <div class="battle-unit attacker">
                        <img class="battle-unit-image"
                             src="${this.normalizeImagePath(attackerData.unit_type?.image_path)}"
                             onerror="this.src='/static/images/units/default.png'"
                             alt="${attackerData.unit_type?.name || 'Атакующий'}">
                        <div class="battle-unit-name">
                            ${attackerData.unit_type?.icon || '⚔️'} ${attackerData.unit_type?.name || 'Атакующий'}
                        </div>
                    </div>
                    <div class="battle-lightning">⚡</div>
                    <div class="battle-unit target">
                        <img class="battle-unit-image"
                             src="${this.normalizeImagePath(targetData.unit_type?.image_path)}"
                             onerror="this.src='/static/images/units/default.png'"
                             alt="${targetData.unit_type?.name || 'Цель'}">
                        <div class="battle-unit-name">
                            ${targetData.unit_type?.icon || '🎯'} ${targetData.unit_type?.name || 'Цель'}
                        </div>
                    </div>
                </div>
                <div class="battle-result">
                    <div class="battle-result-title">⚔️ Результат атаки</div>
                    <div class="battle-result-text">${resultMessage}</div>
                </div>
                <div class="battle-timer">Закроется через <span id="battle-countdown">${Math.ceil(duration / 1000)}</span> сек...</div>
            `;

            document.body.appendChild(overlay);

            // Таймер обратного отсчёта
            let remaining = Math.ceil(duration / 1000);
            const countdownEl = document.getElementById('battle-countdown');
            const countdownInterval = setInterval(() => {
                remaining--;
                if (countdownEl) countdownEl.textContent = remaining;
            }, 1000);

            // Закрытие по клику
            overlay.addEventListener('click', () => {
                clearInterval(countdownInterval);
                clearTimeout(autoCloseTimeout);
                closeBattleOverlay();
            });

            // Функция закрытия
            const closeBattleOverlay = () => {
                overlay.classList.add('fade-out');
                setTimeout(() => {
                    overlay.remove();
                    resolve();
                }, 500);
            };

            // Автоматическое закрытие
            const autoCloseTimeout = setTimeout(() => {
                clearInterval(countdownInterval);
                closeBattleOverlay();
            }, duration);
        });
    }

    /**
     * Пропуск хода юнита
     */
    async skipUnitTurn() {
        if (!selectedUnitId) {
            this.showHint('⚠️ Сначала выберите юнита!');
            return;
        }

        try {
            const response = await fetch(`${apiBase}/games/${currentGameId}/move`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    unit_id: selectedUnitId,
                    action: 'skip'
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showHint('⏭️ Юнит пропустил ход');

                // Обновляем состояние
                const container = this.units.get(selectedUnitId);
                if (container) {
                    const data = container.getData('unitData');
                    data.has_moved = true;
                    container.setData('unitData', data);

                    const readyIndicator = container.getData('readyIndicator');
                    if (readyIndicator) readyIndicator.destroy();
                }

                if (result.turn_switched) {
                    await this.refreshGameState();
                } else {
                    this.highlightActiveUnits();
                }
            }

        } catch (error) {
            console.error('Error skipping turn:', error);
        }

        this.resetAction();
    }

    /**
     * Отложить ход юнита (переместить в конец очереди)
     */
    async deferUnit() {
        if (!selectedUnitId) {
            this.showHint('⚠️ Сначала выберите юнита!');
            return;
        }

        try {
            const response = await fetch(`${apiBase}/games/${currentGameId}/move`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    unit_id: selectedUnitId,
                    action: 'defer'
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showHint('⏩ Юнит отложен в конец очереди');

                // Обновляем состояние с сервера
                await this.refreshGameState();
            } else {
                this.showHint('❌ ' + result.message);
            }

        } catch (error) {
            console.error('Error deferring unit:', error);
            this.showHint('❌ Ошибка откладывания хода');
        }

        this.resetAction();
    }

    /**
     * Сброс текущего действия
     */
    resetAction() {
        actionMode = null;
        selectedUnitId = null;
        this.clearHighlights();
        this.selectionGraphics.clear();
        this.highlightActiveUnits();
        this.hideUnitPortraits();
        this.clearHint();
        document.getElementById('action-panel').style.display = 'none';
    }

    /**
     * Проверка обновлений (polling для синхронизации с Telegram)
     */
    async checkForUpdates() {
        try {
            const response = await fetch(`${apiBase}/games/${currentGameId}/state`);
            const newState = await response.json();

            // Простой хэш для сравнения состояний
            const newHash = JSON.stringify({
                current_player_id: newState.current_player_id,
                status: newState.status,
                logs_count: newState.logs ? newState.logs.length : 0,
                units: newState.units.map(u => ({
                    id: u.id,
                    x: u.x,
                    y: u.y,
                    count: u.count,
                    has_moved: u.has_moved
                }))
            });

            if (lastGameStateHash !== newHash) {
                lastGameStateHash = newHash;

                // Проверяем новые логи на наличие атак от противника
                const oldLogsCount = this.gameState.logs ? this.gameState.logs.length : 0;
                const newLogsCount = newState.logs ? newState.logs.length : 0;

                if (newLogsCount > oldLogsCount) {
                    // Есть новые логи - проверяем на атаки
                    const newLogs = newState.logs.slice(oldLogsCount);
                    for (const log of newLogs) {
                        if (log.event_type === 'attack') {
                            // Показываем анимацию атаки от противника
                            await this.showOpponentAttackAnimation(log.message, newState.units);
                        }
                    }
                }

                // Состояние изменилось (возможно из Telegram)
                const stateChanged = this.gameState.current_player_id !== newState.current_player_id ||
                    JSON.stringify(this.gameState.units) !== JSON.stringify(newState.units);

                const logsChanged = newState.logs &&
                    (!this.gameState.logs || newState.logs.length !== this.gameState.logs.length);

                if (stateChanged || logsChanged) {
                    if (stateChanged) {
                        this.showHint('📱 Обновление состояния игры из Telegram');
                    }
                    await this.refreshGameState();
                }

                // Проверяем завершение игры
                if (newState.status === 'completed' && this.gameState.status !== 'completed') {
                    stopPolling();
                    this.showGameOver(newState.winner_id);
                }
            }
        } catch (error) {
            console.error('Error checking for updates:', error);
        }
    }

    /**
     * Показ анимации атаки от противника (из Telegram)
     */
    async showOpponentAttackAnimation(logMessage, units) {
        // Пытаемся найти юниты по именам из сообщения лога
        let attackerData = null;
        let targetData = null;

        // Ищем юниты, имена которых упоминаются в логе
        for (const unit of units) {
            if (unit.unit_type && unit.unit_type.name) {
                if (logMessage.includes(unit.unit_type.name)) {
                    if (!attackerData) {
                        attackerData = unit;
                    } else if (!targetData) {
                        targetData = unit;
                    }
                }
            }
        }

        // Если нашли хотя бы одного юнита или есть сообщение - показываем оверлей
        if (attackerData || targetData || logMessage) {
            // Используем заглушки если юнит не найден
            const defaultUnit = {
                unit_type: {
                    name: 'Юнит',
                    icon: '⚔️',
                    image_path: '/static/images/units/default.png'
                }
            };

            await this.showBattleOverlay(
                attackerData || defaultUnit,
                targetData || defaultUnit,
                logMessage,
                5000
            );
        }
    }

    /**
     * Обновление состояния игры с сервера
     */
    async refreshGameState() {
        try {
            const response = await fetch(`${apiBase}/games/${currentGameId}/state`);
            this.gameState = await response.json();

            // Обновляем юнитов
            this.gameState.units.forEach(unitData => {
                const container = this.units.get(unitData.id);
                if (container) {
                    // Анимация перемещения если позиция изменилась
                    const currentData = container.getData('unitData');
                    if (currentData.x !== unitData.x || currentData.y !== unitData.y) {
                        this.tweens.add({
                            targets: container,
                            x: this.boardToScreenX(unitData.x),
                            y: this.boardToScreenY(unitData.y),
                            duration: 300,
                            ease: 'Power2'
                        });
                    }

                    // Обновляем количество
                    const countText = container.getData('countText');
                    countText.setText(`x${unitData.count}`);

                    // Обновляем данные
                    container.setData('unitData', unitData);

                    // Видимость
                    container.setVisible(unitData.count > 0);

                    // Индикатор готовности
                    const readyIndicator = container.getData('readyIndicator');
                    if (readyIndicator) readyIndicator.destroy();

                    if (!unitData.has_moved && unitData.player_id === this.gameState.current_player_id && unitData.count > 0) {
                        const newIndicator = this.add.circle(CELL_SIZE/2 - 15, -CELL_SIZE/2 + 15, 8, 0x2ecc71);
                        container.add(newIndicator);
                        container.setData('readyIndicator', newIndicator);
                    }
                }
            });

            this.updateUI();
            this.highlightActiveUnits();

            // Обновляем логи если они есть в ответе
            if (this.gameState.logs) {
                this.syncLogs(this.gameState.logs);
            }

        } catch (error) {
            console.error('Error refreshing game state:', error);
        }
    }

    /**
     * Синхронизация логов с сервера
     */
    syncLogs(serverLogs) {
        const logContainer = document.getElementById('log-entries');
        if (!logContainer || !serverLogs) return;

        // Получаем количество текущих логов
        const currentLogsCount = logContainer.children.length;
        const serverLogsCount = serverLogs.length;

        // Если на сервере больше логов - добавляем новые
        if (serverLogsCount > currentLogsCount) {
            // Берём только новые логи (которых ещё нет в UI)
            const newLogs = serverLogs.slice(currentLogsCount);

            newLogs.forEach(log => {
                const entry = document.createElement('div');
                entry.className = `log-entry ${log.event_type}`;

                const time = new Date(log.created_at).toLocaleTimeString('ru-RU', {
                    hour: '2-digit', minute: '2-digit', second: '2-digit'
                });
                entry.innerHTML = `<span style="color: #888; font-size: 11px;">[${time}]</span> ${log.message}`;

                logContainer.insertBefore(entry, logContainer.firstChild);
            });

            // Ограничиваем количество записей
            while (logContainer.children.length > 50) {
                logContainer.removeChild(logContainer.lastChild);
            }
        }
    }

    /**
     * Обновление UI
     */
    updateUI() {
        const p1Turn = document.getElementById('p1-turn');
        const p2Turn = document.getElementById('p2-turn');
        const p1Name = document.getElementById('p1-name');
        const p2Name = document.getElementById('p2-name');

        // Используем player1_id и player2_id из состояния игры (не из юнитов!)
        const player1Id = this.gameState.player1_id;
        const player2Id = this.gameState.player2_id;

        // Обновляем имена игроков из API (если есть)
        if (p1Name && this.gameState.player1_name) {
            p1Name.textContent = this.gameState.player1_name;
        }
        if (p2Name && this.gameState.player2_name) {
            p2Name.textContent = this.gameState.player2_name;
        }

        // Обновляем индикаторы хода
        if (p1Turn && p2Turn && player1Id && player2Id) {
            if (this.gameState.current_player_id === player1Id) {
                p1Turn.style.display = 'block';
                p2Turn.style.display = 'none';
            } else {
                p1Turn.style.display = 'none';
                p2Turn.style.display = 'block';
            }
        }

        // Обновляем списки юнитов
        if (player1Id && player2Id) {
            this.updatePlayerUnits([player1Id, player2Id]);
        }
    }

    /**
     * Обновление списков юнитов игроков
     */
    updatePlayerUnits(playerIds) {
        const p1Container = document.getElementById('player1-units');
        const p2Container = document.getElementById('player2-units');

        if (p1Container && playerIds[0]) {
            p1Container.innerHTML = this.getPlayerUnitsHTML(playerIds[0]);
        }

        if (p2Container && playerIds[1]) {
            p2Container.innerHTML = this.getPlayerUnitsHTML(playerIds[1]);
        }
    }

    /**
     * HTML списка юнитов
     */
    getPlayerUnitsHTML(playerId) {
        let html = '';
        this.gameState.units
            .filter(u => u.player_id === playerId && u.count > 0)
            .forEach(unit => {
                const movedClass = unit.has_moved ? 'style="opacity: 0.5;"' : '';
                const status = unit.has_moved ? '✓' : '●';
                html += `<div class="unit-row" ${movedClass}>
                    <span>${status} ${unit.unit_type?.icon || '❓'} ${unit.unit_type?.name || 'Unknown'}</span>
                    <span>x${unit.count}</span>
                </div>`;
            });
        return html || '<div class="unit-row">Нет юнитов</div>';
    }

    /**
     * Показать UI-подсказку (НЕ записывается в лог игры)
     * Используется для информационных сообщений интерфейса
     */
    showHint(message) {
        const hintContent = document.getElementById('hint-content');
        if (!hintContent) return;

        // Добавляем анимацию смены
        hintContent.classList.remove('changing');
        void hintContent.offsetWidth; // Trigger reflow
        hintContent.classList.add('changing');

        hintContent.textContent = message;
    }

    /**
     * Очистить подсказку (покажет дефолтный текст через CSS)
     */
    clearHint() {
        const hintContent = document.getElementById('hint-content');
        if (hintContent) {
            hintContent.textContent = '';
        }
    }

    /**
     * Добавление записи в лог (только для серверных событий!)
     * НЕ использовать для UI-подсказок - для них есть showHint()
     */
    addLog(message, type = 'info') {
        const logContainer = document.getElementById('log-entries');
        if (!logContainer) return;

        const entry = document.createElement('div');
        entry.className = `log-entry ${type}`;

        const time = new Date().toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        entry.innerHTML = `<span style="color: #888; font-size: 11px;">[${time}]</span> ${message}`;

        logContainer.insertBefore(entry, logContainer.firstChild);

        // Ограничиваем количество записей
        while (logContainer.children.length > 50) {
            logContainer.removeChild(logContainer.lastChild);
        }
    }

    /**
     * Показ окончания игры
     */
    showGameOver(winnerId) {
        // Используем player1_id/player2_id из состояния игры
        const winnerName = winnerId === this.gameState.player1_id ?
            document.getElementById('p1-name').textContent :
            document.getElementById('p2-name').textContent;

        // Собираем полный лог игры
        let logsHtml = '';
        if (this.gameState.logs && this.gameState.logs.length > 0) {
            for (const log of this.gameState.logs) {
                const icon = log.event_type === 'attack' ? '⚔️' :
                            log.event_type === 'move' ? '🚶' :
                            log.event_type === 'game_start' ? '🎮' :
                            log.event_type === 'game_end' ? '🏆' : '📝';
                logsHtml += `<div class="game-over-log-entry">${icon} ${log.message}</div>`;
            }
        }

        // Создаём DOM оверлей с логом и кнопкой закрытия
        const gameOverOverlay = document.createElement('div');
        gameOverOverlay.className = 'game-over-overlay';
        gameOverOverlay.innerHTML = `
            <div class="game-over-content">
                <div class="game-over-title">🏆 ПОБЕДА!</div>
                <div class="game-over-winner">${winnerName}</div>
                <div class="game-over-log-container">
                    <div class="game-over-log-title">📋 Лог сражения</div>
                    <div class="game-over-log-scroll">
                        ${logsHtml}
                    </div>
                </div>
                <button class="game-over-close-btn" onclick="window.location.href='/arena/'">
                    ✖ Закрыть
                </button>
            </div>
        `;
        document.body.appendChild(gameOverOverlay);

        // Прокручиваем лог вниз
        const logScroll = gameOverOverlay.querySelector('.game-over-log-scroll');
        if (logScroll) {
            logScroll.scrollTop = logScroll.scrollHeight;
        }

        this.showHint(`🏆 Игра завершена! Победитель: ${winnerName}`);
    }

    /**
     * Настройка кнопок действий
     */
    setupActionButtons() {
        const btnMove = document.getElementById('btn-move');
        const btnAttack = document.getElementById('btn-attack');
        const btnSkip = document.getElementById('btn-skip');
        const btnDefer = document.getElementById('btn-defer');
        const btnCancel = document.getElementById('btn-cancel');

        if (btnMove) {
            btnMove.addEventListener('click', () => this.showMoveHighlights());
        }

        if (btnAttack) {
            btnAttack.addEventListener('click', () => this.showAttackHighlights());
        }

        if (btnSkip) {
            btnSkip.addEventListener('click', () => this.skipUnitTurn());
        }

        if (btnDefer) {
            btnDefer.addEventListener('click', () => this.deferUnit());
        }

        if (btnCancel) {
            btnCancel.addEventListener('click', () => this.resetAction());
        }
    }
}
