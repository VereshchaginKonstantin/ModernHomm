/**
 * Phaser.js игра для просмотра боёв (режим воспроизведения)
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
    highlight: 0xffff00,
    attack: 0xff0000
};

// Глобальные переменные
let game;
let battleScene;

// Инициализация после загрузки DOM
document.addEventListener('DOMContentLoaded', () => {
    if (typeof gameData !== 'undefined') {
        initReplayGame(gameData);
    }
});

/**
 * Инициализация игры для воспроизведения
 */
function initReplayGame(data) {
    const fieldWidth = data.field.width * CELL_SIZE + BOARD_PADDING * 2;
    const fieldHeight = data.field.height * CELL_SIZE + BOARD_PADDING * 2;

    const config = {
        type: Phaser.AUTO,
        width: fieldWidth,
        height: fieldHeight,
        parent: 'game-container',
        backgroundColor: '#1a1a2e',
        scene: [ReplayScene]
    };

    game = new Phaser.Game(config);
    game.gameData = data;
}

/**
 * Сцена воспроизведения боя
 */
class ReplayScene extends Phaser.Scene {
    constructor() {
        super({ key: 'ReplayScene' });
        this.units = new Map();
        this.obstacles = [];
        this.currentLogIndex = 0;
        this.isPlaying = false;
        this.playSpeed = 1;
        this.eventHistory = []; // История состояний для перемотки
    }

    create() {
        this.gameData = this.game.gameData;
        this.fieldWidth = this.gameData.field.width;
        this.fieldHeight = this.gameData.field.height;

        // Рисуем поле
        this.drawBoard();

        // Рисуем препятствия
        this.drawObstacles();

        // Инициализируем юнитов из начального состояния
        this.initUnits();

        // Сохраняем начальное состояние
        this.saveState();

        // Добавляем логи
        this.displayLogs();

        // Настраиваем контролы
        this.setupControls();

        // Обновляем информацию об игроках
        this.updatePlayerInfo();
    }

    /**
     * Рисование шахматной доски
     */
    drawBoard() {
        const graphics = this.add.graphics();

        // Подписи колонок (A, B, C...)
        for (let x = 0; x < this.fieldWidth; x++) {
            const label = String.fromCharCode(65 + x);
            this.add.text(
                BOARD_PADDING + x * CELL_SIZE + CELL_SIZE / 2,
                15,
                label,
                { fontSize: '16px', color: '#ffffff', fontStyle: 'bold' }
            ).setOrigin(0.5);
        }

        // Подписи строк (1, 2, 3...)
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

        // Рамка поля
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

        this.gameData.obstacles.forEach(obs => {
            const screenX = BOARD_PADDING + obs.x * CELL_SIZE;
            const screenY = BOARD_PADDING + obs.y * CELL_SIZE;

            // Заливка
            graphics.fillStyle(COLORS.obstacle, 0.8);
            graphics.fillRect(screenX, screenY, CELL_SIZE, CELL_SIZE);

            // X-паттерн
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
     * Инициализация юнитов
     */
    initUnits() {
        this.gameData.units.forEach(unit => {
            this.createUnitSprite(unit);
        });
    }

    /**
     * Создание спрайта юнита
     */
    createUnitSprite(unitData) {
        const screenX = this.boardToScreenX(unitData.x);
        const screenY = this.boardToScreenY(unitData.y);

        // Контейнер для юнита
        const container = this.add.container(screenX, screenY);

        // Фон (цвет игрока)
        const isPlayer1 = unitData.player_id === this.gameData.player1.id;
        const bgColor = isPlayer1 ? COLORS.player1 : COLORS.player2;

        const bg = this.add.graphics();
        bg.fillStyle(bgColor, 0.3);
        bg.fillRoundedRect(-CELL_SIZE/2 + 5, -CELL_SIZE/2 + 5, CELL_SIZE - 10, CELL_SIZE - 10, 8);
        bg.lineStyle(2, bgColor, 1);
        bg.strokeRoundedRect(-CELL_SIZE/2 + 5, -CELL_SIZE/2 + 5, CELL_SIZE - 10, CELL_SIZE - 10, 8);
        container.add(bg);

        // Иконка юнита
        const icon = unitData.unit_type?.icon || '❓';
        const iconText = this.add.text(0, -8, icon, {
            fontSize: '32px'
        }).setOrigin(0.5);
        container.add(iconText);

        // Количество юнитов
        const countText = this.add.text(0, 22, `x${unitData.count}`, {
            fontSize: '14px',
            color: '#ffffff',
            fontStyle: 'bold',
            stroke: '#000000',
            strokeThickness: 3
        }).setOrigin(0.5);
        container.add(countText);

        // Сохраняем данные
        container.setData('unitData', { ...unitData });
        container.setData('countText', countText);
        container.setData('bg', bg);

        this.units.set(unitData.id, container);

        // Скрываем если 0 юнитов
        if (unitData.count <= 0) {
            container.setVisible(false);
        }

        return container;
    }

    /**
     * Конвертация координат доски в экранные
     */
    boardToScreenX(x) {
        return BOARD_PADDING + x * CELL_SIZE + CELL_SIZE / 2;
    }

    boardToScreenY(y) {
        return BOARD_PADDING + y * CELL_SIZE + CELL_SIZE / 2;
    }

    /**
     * Отображение логов
     */
    displayLogs() {
        const logContainer = document.getElementById('log-entries');
        if (!logContainer) return;

        logContainer.innerHTML = '';

        this.gameData.logs.forEach((log, index) => {
            const entry = document.createElement('div');
            entry.className = `log-entry ${log.event_type}`;
            entry.dataset.index = index;

            // Форматируем сообщение
            let message = log.message;
            if (message.length > 500) {
                message = message.substring(0, 500) + '...';
            }
            entry.textContent = message;

            // Клик для перехода к событию
            entry.addEventListener('click', () => {
                this.goToEvent(index);
            });

            logContainer.appendChild(entry);
        });

        // Обновляем счётчик
        this.updateEventCounter();
    }

    /**
     * Настройка контролов воспроизведения
     */
    setupControls() {
        const btnPlay = document.getElementById('btn-play');
        const btnPrev = document.getElementById('btn-prev');
        const btnNext = document.getElementById('btn-next');
        const speedSelect = document.getElementById('speed-select');

        if (btnPlay) {
            btnPlay.addEventListener('click', () => this.togglePlay());
        }

        if (btnPrev) {
            btnPrev.addEventListener('click', () => this.prevEvent());
        }

        if (btnNext) {
            btnNext.addEventListener('click', () => this.nextEvent());
        }

        if (speedSelect) {
            speedSelect.addEventListener('change', (e) => {
                this.playSpeed = parseFloat(e.target.value);
            });
        }
    }

    /**
     * Переключение воспроизведения
     */
    togglePlay() {
        this.isPlaying = !this.isPlaying;
        const btn = document.getElementById('btn-play');
        if (btn) {
            btn.textContent = this.isPlaying ? '⏸️ Пауза' : '▶️ Играть';
        }

        if (this.isPlaying) {
            this.playNextEvent();
        }
    }

    /**
     * Воспроизведение следующего события
     */
    async playNextEvent() {
        if (!this.isPlaying || this.currentLogIndex >= this.gameData.logs.length) {
            this.isPlaying = false;
            const btn = document.getElementById('btn-play');
            if (btn) btn.textContent = '▶️ Играть';
            return;
        }

        await this.processEvent(this.currentLogIndex);
        this.currentLogIndex++;
        this.updateEventCounter();
        this.highlightCurrentLog();

        // Следующее событие с задержкой
        const delay = 1500 / this.playSpeed;
        this.time.delayedCall(delay, () => this.playNextEvent());
    }

    /**
     * Переход к предыдущему событию
     */
    prevEvent() {
        if (this.currentLogIndex > 0) {
            this.currentLogIndex--;
            this.restoreState(this.currentLogIndex);
            this.updateEventCounter();
            this.highlightCurrentLog();
        }
    }

    /**
     * Переход к следующему событию
     */
    async nextEvent() {
        if (this.currentLogIndex < this.gameData.logs.length) {
            await this.processEvent(this.currentLogIndex);
            this.currentLogIndex++;
            this.updateEventCounter();
            this.highlightCurrentLog();
        }
    }

    /**
     * Переход к конкретному событию
     */
    async goToEvent(index) {
        this.isPlaying = false;
        const btn = document.getElementById('btn-play');
        if (btn) btn.textContent = '▶️ Играть';

        // Восстанавливаем ближайшее сохранённое состояние
        this.restoreState(index);
        this.currentLogIndex = index;
        this.updateEventCounter();
        this.highlightCurrentLog();
    }

    /**
     * Обработка события
     */
    async processEvent(index) {
        const log = this.gameData.logs[index];
        if (!log) return;

        // Сохраняем состояние перед изменением
        this.saveState();

        // Парсим событие из сообщения
        if (log.event_type === 'attack') {
            await this.processAttackEvent(log);
        } else if (log.event_type === 'move') {
            await this.processMoveEvent(log);
        }
    }

    /**
     * Обработка события атаки
     */
    async processAttackEvent(log) {
        // Парсим сообщение для извлечения данных
        const message = log.message;

        // Ищем паттерн атаки: "⚔️ Unit (xN) атакует Target"
        const attackMatch = message.match(/⚔️\s+(.+?)\s+\(x?(\d+)\)\s+атакует\s+(.+)/);
        if (!attackMatch) return;

        const attackerName = attackMatch[1];
        const targetName = attackMatch[3].split('\n')[0].trim();

        // Находим юнитов по имени
        let attackerUnit = null;
        let targetUnit = null;

        this.units.forEach((container, id) => {
            const data = container.getData('unitData');
            if (data.unit_type?.name === attackerName) {
                attackerUnit = container;
            }
            if (data.unit_type?.name === targetName) {
                targetUnit = container;
            }
        });

        if (attackerUnit && targetUnit) {
            await this.animateAttack(attackerUnit, targetUnit, log);
        }

        // Обновляем количество юнитов на основе лога
        this.updateUnitsFromLog(log);
    }

    /**
     * Анимация атаки
     */
    async animateAttack(attacker, target, log) {
        return new Promise(resolve => {
            const attackerX = attacker.x;
            const attackerY = attacker.y;
            const targetX = target.x;
            const targetY = target.y;

            // Создаём линию атаки
            const graphics = this.add.graphics();
            graphics.lineStyle(4, 0xff0000, 0.8);

            // Анимация линии
            this.tweens.add({
                targets: { progress: 0 },
                progress: 1,
                duration: 300,
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
                    this.tweens.add({
                        targets: impact,
                        scale: 2,
                        alpha: 0,
                        duration: 300,
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
                        repeat: 3,
                        duration: 50
                    });
                }
            });
        });
    }

    /**
     * Обновление юнитов на основе лога атаки
     */
    updateUnitsFromLog(log) {
        // Ищем информацию об убитых юнитах
        const killedMatch = log.message.match(/Убито юнитов:\s*(\d+)/);
        if (killedMatch) {
            // Для простоты просто обновляем визуально
            // В реальной реализации нужно парсить все данные
        }
    }

    /**
     * Сохранение текущего состояния
     */
    saveState() {
        const state = {};
        this.units.forEach((container, id) => {
            const data = container.getData('unitData');
            state[id] = { ...data, visible: container.visible };
        });
        this.eventHistory[this.currentLogIndex] = state;
    }

    /**
     * Восстановление состояния
     */
    restoreState(index) {
        // Находим ближайшее сохранённое состояние
        let stateIndex = index;
        while (stateIndex >= 0 && !this.eventHistory[stateIndex]) {
            stateIndex--;
        }

        if (stateIndex < 0) {
            // Восстанавливаем начальное состояние
            this.gameData.units.forEach(unit => {
                const container = this.units.get(unit.id);
                if (container) {
                    const countText = container.getData('countText');
                    countText.setText(`x${unit.count}`);
                    container.setVisible(unit.count > 0);
                    container.x = this.boardToScreenX(unit.x);
                    container.y = this.boardToScreenY(unit.y);
                }
            });
            return;
        }

        const state = this.eventHistory[stateIndex];
        if (state) {
            Object.entries(state).forEach(([id, data]) => {
                const container = this.units.get(parseInt(id));
                if (container) {
                    const countText = container.getData('countText');
                    countText.setText(`x${data.count}`);
                    container.setVisible(data.visible);
                    container.x = this.boardToScreenX(data.x);
                    container.y = this.boardToScreenY(data.y);
                }
            });
        }
    }

    /**
     * Обновление счётчика событий
     */
    updateEventCounter() {
        const counter = document.getElementById('event-counter');
        if (counter) {
            counter.textContent = `Событие: ${this.currentLogIndex} / ${this.gameData.logs.length}`;
        }
    }

    /**
     * Подсветка текущего лога
     */
    highlightCurrentLog() {
        const entries = document.querySelectorAll('.log-entry');
        entries.forEach((entry, idx) => {
            entry.classList.remove('current');
            if (idx === this.currentLogIndex - 1) {
                entry.classList.add('current');
                entry.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });
    }

    /**
     * Обновление информации об игроках
     */
    updatePlayerInfo() {
        const p1Container = document.getElementById('player1-units');
        const p2Container = document.getElementById('player2-units');

        if (p1Container) {
            p1Container.innerHTML = this.getPlayerUnitsHTML(this.gameData.player1.id);
        }

        if (p2Container) {
            p2Container.innerHTML = this.getPlayerUnitsHTML(this.gameData.player2.id);
        }
    }

    /**
     * Получение HTML списка юнитов игрока
     */
    getPlayerUnitsHTML(playerId) {
        let html = '';
        this.gameData.units
            .filter(u => u.player_id === playerId)
            .forEach(unit => {
                html += `<div class="unit-row">
                    <span>${unit.unit_type?.icon || '❓'} ${unit.unit_type?.name || 'Unknown'}</span>
                    <span>x${unit.count}</span>
                </div>`;
            });
        return html || '<div class="unit-row">Нет юнитов</div>';
    }
}
