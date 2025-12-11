using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

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
        }

        #region Game Flow

        /// <summary>
        /// Начать новую игру
        /// </summary>
        public void StartGame(int gameId)
        {
            CurrentState.GameId = gameId;
            _lastLogCount = 0;

            // Загрузить состояние игры
            RefreshGameState(() =>
            {
                // Начать polling
                StartPolling();
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
                    }

                    // Проверить конец игры
                    if (CurrentState.IsGameOver)
                    {
                        StopPolling();
                        OnGameOver?.Invoke();
                    }

                    OnGameStateUpdated?.Invoke(CurrentState);
                    onComplete?.Invoke();
                },
                error =>
                {
                    Debug.LogError($"Failed to load game state: {error}");
                    OnError?.Invoke(error);
                }
            );
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
                return;
            }

            if (!CurrentState.IsMyTurn(CurrentPlayerId))
            {
                Debug.Log("Not your turn");
                return;
            }

            if (unit.has_moved)
            {
                Debug.Log("Unit already moved this turn");
                return;
            }

            SelectedUnit = unit;
            CurrentActions = null;

            // Запросить доступные действия
            ApiClient.Instance.GetUnitActions(CurrentState.GameId, unit.id,
                response =>
                {
                    CurrentActions = response;
                    OnUnitActionsReceived?.Invoke(response);
                },
                error =>
                {
                    Debug.LogError($"Failed to get unit actions: {error}");
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
        }

        /// <summary>
        /// Переместить выбранного юнита
        /// </summary>
        public void MoveSelectedUnit(int targetX, int targetY)
        {
            if (SelectedUnit == null) return;

            ApiClient.Instance.MoveUnit(CurrentState.GameId, SelectedUnit.id, targetX, targetY,
                response => HandleMoveResponse(response),
                error => OnError?.Invoke(error)
            );
        }

        /// <summary>
        /// Атаковать выбранным юнитом
        /// </summary>
        public void AttackWithSelectedUnit(int targetUnitId)
        {
            if (SelectedUnit == null) return;

            ApiClient.Instance.AttackUnit(CurrentState.GameId, SelectedUnit.id, targetUnitId,
                response => HandleMoveResponse(response),
                error => OnError?.Invoke(error)
            );
        }

        /// <summary>
        /// Пропустить ход выбранного юнита
        /// </summary>
        public void SkipSelectedUnit()
        {
            if (SelectedUnit == null) return;

            ApiClient.Instance.SkipUnit(CurrentState.GameId, SelectedUnit.id,
                response => HandleMoveResponse(response),
                error => OnError?.Invoke(error)
            );
        }

        /// <summary>
        /// Отложить ход выбранного юнита
        /// </summary>
        public void DeferSelectedUnit()
        {
            if (SelectedUnit == null) return;

            ApiClient.Instance.DeferUnit(CurrentState.GameId, SelectedUnit.id,
                response => HandleMoveResponse(response),
                error => OnError?.Invoke(error)
            );
        }

        private void HandleMoveResponse(MoveResponse response)
        {
            DeselectUnit();
            OnMoveCompleted?.Invoke(response);

            if (response.success)
            {
                // Обновить состояние игры
                RefreshGameState();
            }
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
            SceneManager.LoadScene("MainMenu");
        }

        #endregion
    }
}
