using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.SceneManagement;
using ModernHomm.Utils;

namespace ModernHomm.Core
{
    /// <summary>
    /// Главный менеджер игры - управление состоянием и polling
    /// </summary>
    public class GameManager : MonoBehaviour
    {
        public static GameManager Instance { get; private set; }

        [Header("Settings")]
        [SerializeField] private float pollingInterval = 2f;

        // События
        public event Action<ClientGameState> OnGameStateUpdated;
        public event Action<UnitActionsResponse> OnUnitActionsReceived;
        public event Action<MoveResponse> OnMoveCompleted;
        public event Action<string> OnError;
        public event Action OnTurnChanged;
        public event Action OnGameOver;

        // Текущее состояние
        public ClientGameState CurrentState { get; private set; } = new ClientGameState();
        public int CurrentPlayerId { get; set; } // ID текущего игрока (из сессии/localStorage)
        public UnitInfo SelectedUnit { get; private set; }
        public UnitActionsResponse CurrentActions { get; private set; }

        private Coroutine _pollingCoroutine;
        private int _lastLogCount = 0;

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;
            DontDestroyOnLoad(gameObject);

            // Попробовать получить ID игрока из URL/localStorage
            int? playerId = WebGLBridge.GetPlayerId();
            if (playerId.HasValue)
            {
                CurrentPlayerId = playerId.Value;
            }

            // Попробовать автоматически загрузить игру из URL
            int? gameId = WebGLBridge.GetGameId();
            if (gameId.HasValue && CurrentPlayerId > 0)
            {
                StartCoroutine(AutoStartGame(gameId.Value));
            }
        }

        private IEnumerator AutoStartGame(int gameId)
        {
            // Подождать инициализации
            yield return new WaitForSeconds(0.5f);

            WebGLBridge.AddLogEntry($"Автозагрузка игры #{gameId}...", "info");
            StartGame(gameId);
        }

        #region Game Flow

        /// <summary>
        /// Начать новую игру
        /// </summary>
        public void StartGame(int gameId)
        {
            CurrentState.GameId = gameId;
            _lastLogCount = 0;

            WebGLBridge.UpdateHint("Загрузка игры...");
            WebGLBridge.DisableAllActionButtons();

            // Загрузить состояние игры
            RefreshGameState(() =>
            {
                // Обновить UI
                UpdateWebUI();

                // Начать polling
                StartPolling();

                WebGLBridge.AddLogEntry("Игра загружена!", "info");
            });
        }

        /// <summary>
        /// Загрузить состояние игры
        /// </summary>
        public void RefreshGameState(Action onComplete = null)
        {
            ApiClient.Instance.GetGameState(CurrentState.GameId,
                response =>
                {
                    int oldCurrentPlayer = CurrentState.CurrentPlayerId;
                    CurrentState.UpdateFromResponse(response);

                    // Проверить смену хода
                    if (oldCurrentPlayer != 0 && oldCurrentPlayer != CurrentState.CurrentPlayerId)
                    {
                        OnTurnChanged?.Invoke();
                        WebGLBridge.AddLogEntry("Ход сменился!", "info");
                    }

                    // Обновить Web UI
                    UpdateWebUI();

                    // Синхронизировать логи
                    SyncLogs(CurrentState.Logs);

                    // Проверить конец игры
                    if (CurrentState.IsGameOver)
                    {
                        StopPolling();
                        HandleGameOver();
                        OnGameOver?.Invoke();
                    }

                    OnGameStateUpdated?.Invoke(CurrentState);
                    onComplete?.Invoke();
                },
                error =>
                {
                    Debug.LogError($"Failed to load game state: {error}");
                    WebGLBridge.AddLogEntry($"Ошибка: {error}", "attack");
                    OnError?.Invoke(error);
                }
            );
        }

        /// <summary>
        /// Обновить Web UI через JavaScript мост
        /// </summary>
        private void UpdateWebUI()
        {
            bool isMyTurn = CurrentState.IsMyTurn(CurrentPlayerId);

            // Индикатор хода
            if (isMyTurn)
            {
                WebGLBridge.UpdateTurnIndicator("ВАШ ХОД!", true);
                WebGLBridge.UpdateHint("Выберите юнита для действия");
            }
            else
            {
                WebGLBridge.UpdateTurnIndicator("Ход противника...", false);
                WebGLBridge.UpdateHint("Ожидайте своего хода");
            }

            // Информация об игроках
            UpdatePlayerInfo();

            // Активный игрок
            if (CurrentState.CurrentPlayerId == CurrentState.Player1Id)
            {
                WebGLBridge.SetPlayerActive(1);
            }
            else
            {
                WebGLBridge.SetPlayerActive(2);
            }

            // Кнопки действий
            if (!isMyTurn || SelectedUnit == null)
            {
                WebGLBridge.DisableAllActionButtons();
            }
        }

        /// <summary>
        /// Обновить информацию об игроках
        /// </summary>
        private void UpdatePlayerInfo()
        {
            // Игрок 1
            var p1Units = CurrentState.Units.Where(u => u.player_id == CurrentState.Player1Id).ToList();
            int p1Count = p1Units.Sum(u => u.count);
            string p1Stats = $"Юнитов: {p1Count}";
            WebGLBridge.UpdatePlayer1Info(CurrentState.Player1Name ?? "Игрок 1", p1Stats);

            // Игрок 2
            var p2Units = CurrentState.Units.Where(u => u.player_id == CurrentState.Player2Id).ToList();
            int p2Count = p2Units.Sum(u => u.count);
            string p2Stats = $"Юнитов: {p2Count}";
            WebGLBridge.UpdatePlayer2Info(CurrentState.Player2Name ?? "Игрок 2", p2Stats);
        }

        /// <summary>
        /// Синхронизировать логи с сервера
        /// </summary>
        private void SyncLogs(List<LogEntry> logs)
        {
            if (logs == null) return;

            // Показать только новые логи
            for (int i = _lastLogCount; i < logs.Count; i++)
            {
                var log = logs[i];
                string type = log.event_type == "attack" ? "attack" :
                             log.event_type == "move" ? "move" : "info";
                WebGLBridge.AddLogEntry(log.message, type);
            }

            _lastLogCount = logs.Count;
        }

        /// <summary>
        /// Обработка окончания игры
        /// </summary>
        private void HandleGameOver()
        {
            bool isWinner = CurrentState.WinnerId == CurrentPlayerId;
            string winnerName = CurrentState.WinnerId == CurrentState.Player1Id
                ? CurrentState.Player1Name
                : CurrentState.Player2Name;

            WebGLBridge.ShowGameOver(isWinner, winnerName ?? "Противник");
            WebGLBridge.DisableAllActionButtons();

            if (isWinner)
            {
                WebGLBridge.AddLogEntry("ПОБЕДА!", "info");
            }
            else
            {
                WebGLBridge.AddLogEntry($"Поражение. {winnerName} победил.", "attack");
            }
        }

        /// <summary>
        /// Выбрать юнита
        /// </summary>
        public void SelectUnit(UnitInfo unit)
        {
            // Можно выбирать только своих юнитов в свой ход
            if (unit.player_id != CurrentPlayerId)
            {
                Debug.Log("Cannot select enemy unit");
                WebGLBridge.UpdateHint("Это юнит противника!");
                return;
            }

            if (!CurrentState.IsMyTurn(CurrentPlayerId))
            {
                Debug.Log("Not your turn");
                WebGLBridge.UpdateHint("Сейчас не ваш ход!");
                return;
            }

            if (unit.has_moved)
            {
                Debug.Log("Unit already moved this turn");
                WebGLBridge.UpdateHint("Этот юнит уже ходил!");
                return;
            }

            SelectedUnit = unit;
            CurrentActions = null;

            string unitName = unit.unit_type?.name ?? "Юнит";
            WebGLBridge.UpdateHint($"Загрузка действий для {unitName}...");

            // Запросить доступные действия
            ApiClient.Instance.GetUnitActions(CurrentState.GameId, unit.id,
                response =>
                {
                    CurrentActions = response;

                    bool canMove = response.can_move != null && response.can_move.Count > 0;
                    bool canAttack = response.can_attack != null && response.can_attack.Count > 0;

                    WebGLBridge.EnableActionButtons(canMove, canAttack, true, true);
                    WebGLBridge.UpdateHint($"{unitName}: ходов {response.can_move?.Count ?? 0}, целей {response.can_attack?.Count ?? 0}");

                    OnUnitActionsReceived?.Invoke(response);
                },
                error =>
                {
                    Debug.LogError($"Failed to get unit actions: {error}");
                    WebGLBridge.UpdateHint($"Ошибка: {error}");
                    OnError?.Invoke(error);
                }
            );
        }

        /// <summary>
        /// Отменить выбор юнита
        /// </summary>
        public void DeselectUnit()
        {
            SelectedUnit = null;
            CurrentActions = null;
            WebGLBridge.DisableAllActionButtons();

            if (CurrentState.IsMyTurn(CurrentPlayerId))
            {
                WebGLBridge.UpdateHint("Выберите юнита для действия");
            }
        }

        /// <summary>
        /// Переместить выбранного юнита
        /// </summary>
        public void MoveSelectedUnit(int targetX, int targetY)
        {
            if (SelectedUnit == null) return;

            string unitName = SelectedUnit.unit_type?.name ?? "Юнит";
            WebGLBridge.UpdateHint($"Перемещение {unitName}...");
            WebGLBridge.DisableAllActionButtons();

            ApiClient.Instance.MoveUnit(CurrentState.GameId, SelectedUnit.id, targetX, targetY,
                response => HandleMoveResponse(response),
                error =>
                {
                    WebGLBridge.UpdateHint($"Ошибка: {error}");
                    OnError?.Invoke(error);
                }
            );
        }

        /// <summary>
        /// Атаковать выбранным юнитом
        /// </summary>
        public void AttackWithSelectedUnit(int targetUnitId)
        {
            if (SelectedUnit == null) return;

            // Получить информацию о цели для оверлея
            UnitInfo target = GetUnitById(targetUnitId);
            UnitInfo attacker = SelectedUnit;

            string attackerName = attacker.unit_type?.name ?? "Юнит";
            string targetName = target?.unit_type?.name ?? "Цель";

            WebGLBridge.UpdateHint($"{attackerName} атакует {targetName}...");
            WebGLBridge.DisableAllActionButtons();

            ApiClient.Instance.AttackUnit(CurrentState.GameId, SelectedUnit.id, targetUnitId,
                response =>
                {
                    // Показать оверлей битвы
                    if (response.success && attacker != null && target != null)
                    {
                        string attackerImg = attacker.unit_type?.image_path ?? "";
                        string targetImg = target.unit_type?.image_path ?? "";

                        WebGLBridge.ShowBattleOverlay(
                            $"{attacker.unit_type?.icon ?? ""} {attackerName}",
                            attackerImg,
                            $"{target.unit_type?.icon ?? ""} {targetName}",
                            targetImg,
                            response.message
                        );
                    }

                    HandleMoveResponse(response);
                },
                error =>
                {
                    WebGLBridge.UpdateHint($"Ошибка: {error}");
                    OnError?.Invoke(error);
                }
            );
        }

        /// <summary>
        /// Пропустить ход выбранного юнита
        /// </summary>
        public void SkipSelectedUnit()
        {
            if (SelectedUnit == null) return;

            WebGLBridge.UpdateHint("Пропуск хода...");
            WebGLBridge.DisableAllActionButtons();

            ApiClient.Instance.SkipUnit(CurrentState.GameId, SelectedUnit.id,
                response => HandleMoveResponse(response),
                error =>
                {
                    WebGLBridge.UpdateHint($"Ошибка: {error}");
                    OnError?.Invoke(error);
                }
            );
        }

        /// <summary>
        /// Отложить ход выбранного юнита
        /// </summary>
        public void DeferSelectedUnit()
        {
            if (SelectedUnit == null) return;

            WebGLBridge.UpdateHint("Откладывание хода...");
            WebGLBridge.DisableAllActionButtons();

            ApiClient.Instance.DeferUnit(CurrentState.GameId, SelectedUnit.id,
                response => HandleMoveResponse(response),
                error =>
                {
                    WebGLBridge.UpdateHint($"Ошибка: {error}");
                    OnError?.Invoke(error);
                }
            );
        }

        private void HandleMoveResponse(MoveResponse response)
        {
            DeselectUnit();
            OnMoveCompleted?.Invoke(response);

            if (response.success)
            {
                WebGLBridge.AddLogEntry(response.message, response.message.Contains("атак") ? "attack" : "move");

                // Обновить состояние игры
                RefreshGameState();
            }
            else
            {
                WebGLBridge.UpdateHint($"Ошибка: {response.message}");
            }
        }

        #endregion

        #region JavaScript Button Callbacks

        /// <summary>
        /// Вызывается из JavaScript при нажатии кнопки "Двигаться"
        /// </summary>
        public void OnMoveButtonClicked()
        {
            if (SelectedUnit == null || CurrentActions == null) return;

            WebGLBridge.UpdateHint("Нажмите на зелёную клетку для перемещения");
            // Подсветка ходов обрабатывается в BoardController через OnUnitActionsReceived
        }

        /// <summary>
        /// Вызывается из JavaScript при нажатии кнопки "Атаковать"
        /// </summary>
        public void OnAttackButtonClicked()
        {
            if (SelectedUnit == null || CurrentActions == null) return;

            WebGLBridge.UpdateHint("Нажмите на красную клетку для атаки");
            // Подсветка атак обрабатывается в BoardController через OnUnitActionsReceived
        }

        /// <summary>
        /// Вызывается из JavaScript при нажатии кнопки "Пропустить"
        /// </summary>
        public void OnSkipButtonClicked()
        {
            SkipSelectedUnit();
        }

        /// <summary>
        /// Вызывается из JavaScript при нажатии кнопки "Отложить"
        /// </summary>
        public void OnDeferButtonClicked()
        {
            DeferSelectedUnit();
        }

        /// <summary>
        /// Вызывается из JavaScript при нажатии кнопки "Сдаться"
        /// </summary>
        public void OnSurrenderClicked()
        {
            ReturnToMainMenu();
        }

        #endregion

        #region Polling

        public void StartPolling()
        {
            if (_pollingCoroutine != null)
            {
                StopCoroutine(_pollingCoroutine);
            }
            _pollingCoroutine = StartCoroutine(PollingRoutine());
        }

        public void StopPolling()
        {
            if (_pollingCoroutine != null)
            {
                StopCoroutine(_pollingCoroutine);
                _pollingCoroutine = null;
            }
        }

        private IEnumerator PollingRoutine()
        {
            while (true)
            {
                yield return new WaitForSeconds(pollingInterval);

                if (CurrentState.GameId > 0 && !CurrentState.IsGameOver)
                {
                    RefreshGameState();
                }
            }
        }

        #endregion

        #region Helpers

        /// <summary>
        /// Получить юнита по ID
        /// </summary>
        public UnitInfo GetUnitById(int unitId)
        {
            return CurrentState.Units.Find(u => u.id == unitId);
        }

        /// <summary>
        /// Получить юнита по позиции
        /// </summary>
        public UnitInfo GetUnitAtPosition(int x, int y)
        {
            return CurrentState.Units.Find(u => u.x == x && u.y == y);
        }

        /// <summary>
        /// Проверить, есть ли препятствие в позиции
        /// </summary>
        public bool HasObstacleAt(int x, int y)
        {
            return CurrentState.Obstacles.Exists(o => o.x == x && o.y == y);
        }

        /// <summary>
        /// Получить юнитов игрока
        /// </summary>
        public List<UnitInfo> GetPlayerUnits(int playerId)
        {
            return CurrentState.Units.FindAll(u => u.player_id == playerId);
        }

        /// <summary>
        /// Проверить, можно ли двигаться в позицию
        /// </summary>
        public bool CanMoveTo(int x, int y)
        {
            if (CurrentActions == null) return false;
            return CurrentActions.can_move.Exists(m => m.x == x && m.y == y);
        }

        /// <summary>
        /// Проверить, можно ли атаковать юнита
        /// </summary>
        public bool CanAttack(int unitId)
        {
            if (CurrentActions == null) return false;
            return CurrentActions.can_attack.Exists(a => a.id == unitId);
        }

        /// <summary>
        /// Загрузить сцену боя
        /// </summary>
        public void LoadBattleScene(int gameId)
        {
            CurrentState.GameId = gameId;
            SceneManager.LoadScene("Battle");
        }

        /// <summary>
        /// Вернуться в главное меню
        /// </summary>
        public void ReturnToMainMenu()
        {
            StopPolling();
            DeselectUnit();

            // В WebGL редирект на арену
            #if UNITY_WEBGL && !UNITY_EDITOR
            WebGLBridge.Redirect("/arena/");
            #else
            SceneManager.LoadScene("MainMenu");
            #endif
        }

        #endregion
    }
}
