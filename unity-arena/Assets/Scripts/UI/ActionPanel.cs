using UnityEngine;
using UnityEngine.UI;
using TMPro;
using ModernHomm.Core;

namespace ModernHomm.UI
{
    /// <summary>
    /// Панель действий для выбранного юнита
    /// </summary>
    public class ActionPanel : MonoBehaviour
    {
        [Header("Buttons")]
        [SerializeField] private Button moveButton;
        [SerializeField] private Button attackButton;
        [SerializeField] private Button skipButton;
        [SerializeField] private Button deferButton;
        [SerializeField] private Button surrenderButton;

        [Header("Button Texts")]
        [SerializeField] private TextMeshProUGUI moveButtonText;
        [SerializeField] private TextMeshProUGUI attackButtonText;

        [Header("Panel")]
        [SerializeField] private CanvasGroup canvasGroup;

        private UnitActionsResponse _currentActions;

        private void Start()
        {
            // Настроить кнопки
            if (moveButton != null)
                moveButton.onClick.AddListener(OnMoveClicked);

            if (attackButton != null)
                attackButton.onClick.AddListener(OnAttackClicked);

            if (skipButton != null)
                skipButton.onClick.AddListener(OnSkipClicked);

            if (deferButton != null)
                deferButton.onClick.AddListener(OnDeferClicked);

            if (surrenderButton != null)
                surrenderButton.onClick.AddListener(OnSurrenderClicked);

            // Скрыть по умолчанию
            Hide();
        }

        public void Show(UnitActionsResponse actions)
        {
            _currentActions = actions;

            // Показать панель
            gameObject.SetActive(true);
            if (canvasGroup != null)
            {
                canvasGroup.alpha = 1f;
                canvasGroup.interactable = true;
                canvasGroup.blocksRaycasts = true;
            }

            // Обновить кнопки
            UpdateButtons();
        }

        public void Hide()
        {
            _currentActions = null;

            if (canvasGroup != null)
            {
                canvasGroup.alpha = 0f;
                canvasGroup.interactable = false;
                canvasGroup.blocksRaycasts = false;
            }
            else
            {
                gameObject.SetActive(false);
            }
        }

        private void UpdateButtons()
        {
            if (_currentActions == null) return;

            // Кнопка движения
            bool canMove = _currentActions.can_move != null && _currentActions.can_move.Count > 0;
            if (moveButton != null)
            {
                moveButton.interactable = canMove;
            }
            if (moveButtonText != null)
            {
                moveButtonText.text = canMove
                    ? $"🚶 Двигаться ({_currentActions.can_move.Count})"
                    : "🚶 Двигаться";
            }

            // Кнопка атаки
            bool canAttack = _currentActions.can_attack != null && _currentActions.can_attack.Count > 0;
            if (attackButton != null)
            {
                attackButton.interactable = canAttack;
            }
            if (attackButtonText != null)
            {
                attackButtonText.text = canAttack
                    ? $"⚔️ Атаковать ({_currentActions.can_attack.Count})"
                    : "⚔️ Атаковать";
            }

            // Пропуск и откладывание всегда доступны
            if (skipButton != null)
                skipButton.interactable = true;

            if (deferButton != null)
                deferButton.interactable = true;
        }

        #region Button Handlers

        private void OnMoveClicked()
        {
            if (_currentActions == null || _currentActions.can_move.Count == 0) return;

            // Режим выбора клетки для движения
            // BoardController уже подсвечивает доступные клетки
            Debug.Log("Move mode activated");
        }

        private void OnAttackClicked()
        {
            if (_currentActions == null || _currentActions.can_attack.Count == 0) return;

            // Режим выбора цели для атаки
            // BoardController уже подсвечивает доступные цели
            Debug.Log("Attack mode activated");
        }

        private void OnSkipClicked()
        {
            GameManager.Instance.SkipSelectedUnit();
            Hide();
        }

        private void OnDeferClicked()
        {
            GameManager.Instance.DeferSelectedUnit();
            Hide();
        }

        private void OnSurrenderClicked()
        {
            // Показать диалог подтверждения
            Debug.Log("Surrender requested");

            // TODO: Показать модальное окно подтверждения
            // Пока просто возвращаемся в меню
            GameManager.Instance.ReturnToMainMenu();
        }

        #endregion
    }
}
