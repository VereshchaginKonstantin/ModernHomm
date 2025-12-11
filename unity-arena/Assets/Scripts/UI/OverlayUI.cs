using System.Collections;
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using ModernHomm.Core;

namespace ModernHomm.UI
{
    /// <summary>
    /// UI для оверлеев (результат атаки, конец игры)
    /// </summary>
    public class OverlayUI : MonoBehaviour
    {
        [Header("Battle Result Overlay")]
        [SerializeField] private GameObject battleResultPanel;
        [SerializeField] private TextMeshProUGUI battleResultText;
        [SerializeField] private float battleResultDuration = 5f;

        [Header("Game Over Overlay")]
        [SerializeField] private GameObject gameOverPanel;
        [SerializeField] private TextMeshProUGUI gameOverTitle;
        [SerializeField] private TextMeshProUGUI gameOverSubtitle;
        [SerializeField] private TextMeshProUGUI gameOverStats;
        [SerializeField] private Button returnButton;

        [Header("Animation")]
        [SerializeField] private float fadeInDuration = 0.3f;
        [SerializeField] private float fadeOutDuration = 0.3f;

        private Coroutine _battleResultCoroutine;

        private void Start()
        {
            // Скрыть все оверлеи
            HideAll();

            if (returnButton != null)
            {
                returnButton.onClick.AddListener(OnReturnClicked);
            }
        }

        public void HideAll()
        {
            if (battleResultPanel != null)
                battleResultPanel.SetActive(false);

            if (gameOverPanel != null)
                gameOverPanel.SetActive(false);
        }

        #region Battle Result

        public void ShowBattleResult(string message)
        {
            if (_battleResultCoroutine != null)
            {
                StopCoroutine(_battleResultCoroutine);
            }

            _battleResultCoroutine = StartCoroutine(BattleResultRoutine(message));
        }

        private IEnumerator BattleResultRoutine(string message)
        {
            if (battleResultPanel == null) yield break;

            // Показать панель
            battleResultPanel.SetActive(true);

            if (battleResultText != null)
            {
                battleResultText.text = FormatBattleResult(message);
            }

            // Анимация появления
            CanvasGroup canvasGroup = battleResultPanel.GetComponent<CanvasGroup>();
            if (canvasGroup != null)
            {
                canvasGroup.alpha = 0;
                float elapsed = 0;
                while (elapsed < fadeInDuration)
                {
                    elapsed += Time.deltaTime;
                    canvasGroup.alpha = elapsed / fadeInDuration;
                    yield return null;
                }
                canvasGroup.alpha = 1;
            }

            // Ждать
            yield return new WaitForSeconds(battleResultDuration);

            // Анимация исчезновения
            if (canvasGroup != null)
            {
                float elapsed = 0;
                while (elapsed < fadeOutDuration)
                {
                    elapsed += Time.deltaTime;
                    canvasGroup.alpha = 1 - (elapsed / fadeOutDuration);
                    yield return null;
                }
            }

            battleResultPanel.SetActive(false);
            _battleResultCoroutine = null;
        }

        private string FormatBattleResult(string message)
        {
            // Форматировать сообщение для красивого отображения
            // Пример: "⚔️ Атака: Мечник (x5) → Лучник\n💥 Урон: 25\n☠️ Убито: 2"

            if (string.IsNullOrEmpty(message)) return "";

            // Разбить на строки для лучшей читаемости
            string formatted = message
                .Replace(".", ".\n")
                .Replace("!", "!\n")
                .Replace("КОНТРАТАКА", "\n🛡️ КОНТРАТАКА")
                .Trim();

            return formatted;
        }

        #endregion

        #region Game Over

        public void ShowGameOver(bool isWinner, ClientGameState state)
        {
            if (gameOverPanel == null) return;

            gameOverPanel.SetActive(true);

            // Заголовок
            if (gameOverTitle != null)
            {
                gameOverTitle.text = isWinner ? "🏆 ПОБЕДА!" : "💀 ПОРАЖЕНИЕ";
                gameOverTitle.color = isWinner
                    ? new Color(1f, 0.84f, 0f) // Золотой
                    : new Color(0.8f, 0.2f, 0.2f); // Красный
            }

            // Подзаголовок
            if (gameOverSubtitle != null)
            {
                string winnerName = state.WinnerId == state.Player1Id
                    ? state.Player1Name
                    : state.Player2Name;

                gameOverSubtitle.text = isWinner
                    ? "Вы одержали победу!"
                    : $"Победитель: {winnerName}";
            }

            // Статистика
            if (gameOverStats != null)
            {
                string stats = FormatGameStats(state);
                gameOverStats.text = stats;
            }

            // Анимация появления
            StartCoroutine(FadeInPanel(gameOverPanel));
        }

        private string FormatGameStats(ClientGameState state)
        {
            // Подсчитать юнитов каждого игрока
            int player1Units = 0, player2Units = 0;
            int player1Count = 0, player2Count = 0;

            foreach (var unit in state.Units)
            {
                if (unit.player_id == state.Player1Id)
                {
                    player1Units++;
                    player1Count += unit.count;
                }
                else
                {
                    player2Units++;
                    player2Count += unit.count;
                }
            }

            return $"📊 Статистика боя:\n\n" +
                   $"{state.Player1Name}:\n" +
                   $"  Осталось юнитов: {player1Units} ({player1Count} шт)\n\n" +
                   $"{state.Player2Name}:\n" +
                   $"  Осталось юнитов: {player2Units} ({player2Count} шт)";
        }

        private IEnumerator FadeInPanel(GameObject panel)
        {
            CanvasGroup canvasGroup = panel.GetComponent<CanvasGroup>();
            if (canvasGroup == null)
            {
                canvasGroup = panel.AddComponent<CanvasGroup>();
            }

            canvasGroup.alpha = 0;
            float elapsed = 0;

            while (elapsed < fadeInDuration)
            {
                elapsed += Time.deltaTime;
                canvasGroup.alpha = elapsed / fadeInDuration;
                yield return null;
            }

            canvasGroup.alpha = 1;
        }

        #endregion

        #region Button Handlers

        private void OnReturnClicked()
        {
            GameManager.Instance.ReturnToMainMenu();
        }

        #endregion
    }
}
