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

        // Добавляем начальный лог
        this.addLog('Игра началась! Нажмите на юнита с зеленым индикатором чтобы выбрать его.', 'game_started');
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
        const playerIds = [...new Set(this.gameState.units.map(u => u.player_id))];
        return playerId === playerIds[0] ? COLORS.player1 : COLORS.player2;
    }

    /**
     * Конвертация координат
     */
    boardToScreenX(x) {
        return BOARD_PADDING + x * CELL_SIZE + CELL_SIZE / 2;
    }

    boardToScreenY(y) {
        return BOARD_PADDING + y * CELL_SIZE + CELL_SIZE / 2;
    }

    screenToBoardX(screenX) {
        return Math.floor((screenX - BOARD_PADDING) / CELL_SIZE);
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
            // Скрываем портрет цели если не над целью
            const targetPortrait = document.getElementById('target-unit-portrait');
            if (targetPortrait) targetPortrait.style.display = 'none';
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
            foundUnit.data.player_id === this.gameState.current_player_id &&
            !foundUnit.data.has_moved) {

            await this.selectUnit(foundUnit.id);
        } else if (foundUnit) {
            // Клик по вражескому юниту или юниту, который уже походил
            this.addLog(`${foundUnit.data.unit_type?.icon || '❓'} ${foundUnit.data.unit_type?.name || 'Юнит'} - не может действовать`, 'info');
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

            this.addLog(`Выбран ${unitData.unit_type?.name || 'юнит'}. Доступно ходов: ${this.availableMoves.length}, целей: ${this.availableAttacks.length}`, 'info');

        } catch (error) {
            console.error('Error getting unit actions:', error);
            this.addLog('Ошибка получения действий юнита', 'error');
        }
    }

    /**
     * Показать портрет активного юнита (слева)
     */
    showActiveUnitPortrait(unitData) {
        const portrait = document.getElementById('active-unit-portrait');
        const img = document.getElementById('active-unit-image');
        const name = document.getElementById('active-unit-name');
        const stats = document.getElementById('active-unit-stats');

        if (portrait && unitData.unit_type) {
            // Устанавливаем изображение
            const imagePath = unitData.unit_type.image_path || '/static/images/units/default.png';
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
     * Показать портрет цели атаки (справа)
     */
    showTargetUnitPortrait(targetData) {
        const portrait = document.getElementById('target-unit-portrait');
        const img = document.getElementById('target-unit-image');
        const name = document.getElementById('target-unit-name');
        const stats = document.getElementById('target-unit-stats');

        if (portrait && targetData.unit_type) {
            // Устанавливаем изображение
            const imagePath = targetData.unit_type.image_path || '/static/images/units/default.png';
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
        const activePortrait = document.getElementById('active-unit-portrait');
        const targetPortrait = document.getElementById('target-unit-portrait');

        if (activePortrait) activePortrait.style.display = 'none';
        if (targetPortrait) targetPortrait.style.display = 'none';
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
            this.addLog('Сначала выберите юнита!', 'error');
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

        this.addLog(`Нажмите на зелёную клетку для перемещения (${this.availableMoves.length} вариантов)`, 'move');
    }

    /**
     * Показать зоны атаки (красные)
     */
    showAttackHighlights() {
        if (!selectedUnitId) {
            this.addLog('Сначала выберите юнита!', 'error');
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

        this.addLog(`Нажмите на красную клетку для атаки (${this.availableAttacks.length} целей)`, 'attack');
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
            this.addLog('Нельзя переместиться на эту клетку!', 'error');
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
            this.addLog('Нельзя атаковать эту клетку!', 'error');
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

                this.addLog(result.message, 'move');

                // Проверяем смену хода
                if (result.turn_switched) {
                    await this.refreshGameState();
                } else {
                    this.highlightActiveUnits();
                }
            } else {
                this.addLog('Ошибка: ' + result.message, 'error');
            }

        } catch (error) {
            console.error('Error executing move:', error);
            this.addLog('Ошибка выполнения хода', 'error');
        }
    }

    /**
     * Выполнение атаки
     */
    async executeAttack(unitId, targetId) {
        try {
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
                // Анимация атаки
                const attacker = this.units.get(unitId);
                const target = this.units.get(targetId);

                if (attacker && target) {
                    await this.animateAttack(attacker, target);
                }

                this.addLog(result.message, 'attack');

                // Обновляем состояние
                await this.refreshGameState();

                // Проверяем завершение игры
                if (result.game_status === 'completed') {
                    stopPolling();
                    this.showGameOver(result.winner_id);
                }
            } else {
                this.addLog('Ошибка: ' + result.message, 'error');
            }

        } catch (error) {
            console.error('Error executing attack:', error);
            this.addLog('Ошибка выполнения атаки', 'error');
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
     * Пропуск хода юнита
     */
    async skipUnitTurn() {
        if (!selectedUnitId) {
            this.addLog('Сначала выберите юнита!', 'error');
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
                this.addLog('Юнит пропустил ход', 'move');

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
     * Сброс текущего действия
     */
    resetAction() {
        actionMode = null;
        selectedUnitId = null;
        this.clearHighlights();
        this.selectionGraphics.clear();
        this.highlightActiveUnits();
        this.hideUnitPortraits();
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

                // Состояние изменилось (возможно из Telegram)
                if (this.gameState.current_player_id !== newState.current_player_id ||
                    JSON.stringify(this.gameState.units) !== JSON.stringify(newState.units)) {

                    this.addLog('📱 Обновление состояния игры из Telegram', 'info');
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

        } catch (error) {
            console.error('Error refreshing game state:', error);
        }
    }

    /**
     * Обновление UI
     */
    updateUI() {
        const p1Turn = document.getElementById('p1-turn');
        const p2Turn = document.getElementById('p2-turn');

        const playerIds = [...new Set(this.gameState.units.map(u => u.player_id))];

        if (p1Turn && p2Turn) {
            if (this.gameState.current_player_id === playerIds[0]) {
                p1Turn.style.display = 'block';
                p2Turn.style.display = 'none';
            } else {
                p1Turn.style.display = 'none';
                p2Turn.style.display = 'block';
            }
        }

        this.updatePlayerUnits(playerIds);
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
     * Добавление записи в лог
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
        const playerIds = [...new Set(this.gameState.units.map(u => u.player_id))];
        const winnerIndex = playerIds.indexOf(winnerId);
        const winnerName = winnerIndex === 0 ?
            document.getElementById('p1-name').textContent :
            document.getElementById('p2-name').textContent;

        // Затемнение
        const overlay = this.add.rectangle(
            this.cameras.main.centerX,
            this.cameras.main.centerY,
            this.cameras.main.width,
            this.cameras.main.height,
            0x000000,
            0.7
        );
        overlay.setDepth(200);

        // Текст победы
        const victoryText = this.add.text(
            this.cameras.main.centerX,
            this.cameras.main.centerY - 30,
            '🏆 ПОБЕДА!',
            { fontSize: '48px', color: '#f1c40f', fontStyle: 'bold' }
        ).setOrigin(0.5);
        victoryText.setDepth(201);

        const winnerText = this.add.text(
            this.cameras.main.centerX,
            this.cameras.main.centerY + 30,
            winnerName,
            { fontSize: '32px', color: '#ffffff' }
        ).setOrigin(0.5);
        winnerText.setDepth(201);

        this.addLog(`🏆 Игра завершена! Победитель: ${winnerName}`, 'game_ended');
    }

    /**
     * Настройка кнопок действий
     */
    setupActionButtons() {
        const btnMove = document.getElementById('btn-move');
        const btnAttack = document.getElementById('btn-attack');
        const btnSkip = document.getElementById('btn-skip');
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

        if (btnCancel) {
            btnCancel.addEventListener('click', () => this.resetAction());
        }
    }
}
