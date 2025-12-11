using UnityEngine;
using UnityEngine.UI;
using TMPro;
using ModernHomm.Core;
using ModernHomm.Board;

namespace ModernHomm.UI
{
    /// <summary>
    /// Главный UI контроллер для сцены боя
    /// </summary>
    public class GameBoardUI : MonoBehaviour
    {
        [Header("Player Panels")]
        [SerializeField] private UnitInfoPanel player1Panel;
        [SerializeField] private UnitInfoPanel player2Panel;

        [Header("Turn Indicator")]
        [SerializeField] private TextMeshProUGUI turnIndicatorText;
        [SerializeField] private Image turnIndicatorBackground;
        [SerializeField] private Color myTurnColor = new Color(0.2f, 0.8f, 0.2f);
        [SerializeField] private Color enemyTurnColor = new Color(0.8f, 0.2f, 0.2f);

        [Header("Action Panel")]
        [SerializeField] private ActionPanel actionPanel;

        [Header("Game Log")]
        [SerializeField] private GameLogUI gameLogUI;

        [Header("Overlays")]
        [SerializeField] private OverlayUI overlayUI;

        [Header("Hint")]
        [SerializeField] private TextMeshProUGUI hintText;

        [Header("Board")]
        [SerializeField] private BoardController boardController;

        private void Start()
        {
            // Подписаться на события
            if (GameManager.Instance != null)
            {
                GameManager.Instance.OnGameStateUpdated += OnGameStateUpdated;
                GameManager.Instance.OnUnitActionsReceived += OnUnitActionsReceived;
                GameManager.Instance.OnMoveCompleted += OnMoveCompleted;
                GameManager.Instance.OnTurnChanged += OnTurnChanged;
                GameManager.Instance.OnGameOver += OnGameOver;
                GameManager.Instance.OnError += OnError;

                // Начать игру
                GameManager.Instance.StartGame(GameManager.Instance.CurrentState.GameId);
            }
        }

        private void OnDestroy()
        {
            if (GameManager.Instance != null)
            {
                GameManager.Instance.OnGameStateUpdated -= OnGameStateUpdated;
                GameManager.Instance.OnUnitActionsReceived -= OnUnitActionsReceived;
                GameManager.Instance.OnMoveCompleted -= OnMoveCompleted;
                GameManager.Instance.OnTurnChanged -= OnTurnChanged;
                GameManager.Instance.OnGameOver -= OnGameOver;
                GameManager.Instance.OnError -= OnError;
            }
        }

        #region Event Handlers

        private void OnGameStateUpdated(ClientGameState state)
        {
            // Обновить панели игроков
            UpdatePlayerPanels(state);

            // Обновить индикатор хода
            UpdateTurnIndicator(state);

            // Обновить лог
            if (gameLogUI != null)
            {
                gameLogUI.UpdateLogs(state.Logs);
            }

            // Обновить подсказку
            UpdateHint(state);
        }

        private void OnUnitActionsReceived(UnitActionsResponse actions)
        {
            // Показать панель действий
            if (actionPanel != null)
            {
                actionPanel.Show(actions);
            }

            // Обновить подсказку
            SetHint($"✅ Выбран юнит. Ходов: {actions.can_move.Count}, целей: {actions.can_attack.Count}");
        }

        private void OnMoveCompleted(MoveResponse response)
        {
            // Скрыть панель действий
            if (actionPanel != null)
            {
                actionPanel.Hide();
            }

            // Показать результат атаки
            if (response.success && response.message.Contains("атак"))
            {
                if (overlayUI != null)
                {
                    overlayUI.ShowBattleResult(response.message);
                }
            }
        }

        private void OnTurnChanged()
        {
            SetHint("🔔 Ход сменился!");

            // Воспроизвести звук (если есть)
        }

        private void OnGameOver()
        {
            var state = GameManager.Instance.CurrentState;
            bool isWinner = state.WinnerId == GameManager.Instance.CurrentPlayerId;

            if (overlayUI != null)
            {
                overlayUI.ShowGameOver(isWinner, state);
            }
        }

        private void OnError(string error)
        {
            Debug.LogError($"Game Error: {error}");
            SetHint($"❌ Ошибка: {error}");
        }

        #endregion

        #region UI Updates

        private void UpdatePlayerPanels(ClientGameState state)
        {
            bool amPlayer1 = GameManager.Instance.CurrentPlayerId == state.Player1Id;

            // Левая панель - текущий игрок
            // Правая панель - противник
            if (amPlayer1)
            {
                if (player1Panel != null)
                    player1Panel.SetPlayer(state.Player1Name, state.Player1Id, state.Units, true);
                if (player2Panel != null)
                    player2Panel.SetPlayer(state.Player2Name, state.Player2Id, state.Units, false);
            }
            else
            {
                if (player1Panel != null)
                    player1Panel.SetPlayer(state.Player2Name, state.Player2Id, state.Units, true);
                if (player2Panel != null)
                    player2Panel.SetPlayer(state.Player1Name, state.Player1Id, state.Units, false);
            }

            // Обновить портрет выбранного юнита
            var selectedUnit = GameManager.Instance.SelectedUnit;
            if (selectedUnit != null)
            {
                if (selectedUnit.player_id == GameManager.Instance.CurrentPlayerId)
                {
                    player1Panel?.ShowUnitPortrait(selectedUnit);
                }
                else
                {
                    player2Panel?.ShowUnitPortrait(selectedUnit);
                }
            }
        }

        private void UpdateTurnIndicator(ClientGameState state)
        {
            if (turnIndicatorText == null) return;

            bool isMyTurn = state.IsMyTurn(GameManager.Instance.CurrentPlayerId);

            turnIndicatorText.text = isMyTurn ? "⚔️ ВАШ ХОД!" : "⏳ Ход противника...";

            if (turnIndicatorBackground != null)
            {
                turnIndicatorBackground.color = isMyTurn ? myTurnColor : enemyTurnColor;
            }
        }

        private void UpdateHint(ClientGameState state)
        {
            if (state.IsGameOver)
            {
                SetHint("🏁 Игра окончена!");
                return;
            }

            bool isMyTurn = state.IsMyTurn(GameManager.Instance.CurrentPlayerId);

            if (!isMyTurn)
            {
                SetHint("⏳ Ожидайте своего хода...");
            }
            else if (GameManager.Instance.SelectedUnit == null)
            {
                SetHint("🎮 Нажмите на юнита для выбора действия");
            }
        }

        private void SetHint(string message)
        {
            if (hintText != null)
            {
                hintText.text = message;
            }
        }

        #endregion

        #region Button Handlers

        public void OnMoveButtonClicked()
        {
            SetHint("🚶 Нажмите на зелёную клетку для перемещения");
        }

        public void OnAttackButtonClicked()
        {
            SetHint("⚔️ Нажмите на красную клетку для атаки");
        }

        public void OnSkipButtonClicked()
        {
            GameManager.Instance.SkipSelectedUnit();
        }

        public void OnDeferButtonClicked()
        {
            GameManager.Instance.DeferSelectedUnit();
        }

        public void OnSurrenderButtonClicked()
        {
            // Показать диалог подтверждения
            // Пока просто вернуться в меню
            GameManager.Instance.ReturnToMainMenu();
        }

        public void OnReturnToMenuClicked()
        {
            GameManager.Instance.ReturnToMainMenu();
        }

        #endregion
    }
}
