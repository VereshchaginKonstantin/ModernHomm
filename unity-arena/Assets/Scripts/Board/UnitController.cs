using System;
using System.Collections;
using UnityEngine;
using UnityEngine.UI;
using TMPro;
using ModernHomm.Core;

namespace ModernHomm.Board
{
    /// <summary>
    /// Контроллер юнита на поле боя
    /// </summary>
    public class UnitController : MonoBehaviour
    {
        [Header("Visual References")]
        [SerializeField] private SpriteRenderer backgroundRenderer;
        [SerializeField] private SpriteRenderer iconRenderer;
        [SerializeField] private TextMeshPro countText;
        [SerializeField] private GameObject readyIndicator;
        [SerializeField] private SpriteRenderer selectionIndicator;

        [Header("Animation Settings")]
        [SerializeField] private float moveDuration = 0.3f;
        [SerializeField] private AnimationCurve moveCurve = AnimationCurve.EaseInOut(0, 0, 1, 1);

        public event Action<int> OnUnitClicked;

        public int UnitId { get; private set; }
        public UnitInfo UnitData { get; private set; }

        private Color _playerColor;
        private Vector3 _targetPosition;
        private bool _isMoving;

        public void Initialize(UnitInfo unitInfo, Color playerColor)
        {
            UnitId = unitInfo.id;
            UnitData = unitInfo;
            _playerColor = playerColor;

            // Установить фон игрока
            if (backgroundRenderer != null)
            {
                Color bgColor = playerColor;
                bgColor.a = 0.6f;
                backgroundRenderer.color = bgColor;
            }

            // Установить иконку (используем TextMeshPro для emoji)
            if (iconRenderer != null && unitInfo.unit_type != null)
            {
                // Можно загрузить спрайт из image_path или использовать placeholder
                // Пока используем цвет для различения
            }

            UpdateVisuals();
        }

        public void UpdateInfo(UnitInfo unitInfo)
        {
            UnitData = unitInfo;
            UpdateVisuals();
        }

        private void UpdateVisuals()
        {
            if (UnitData == null) return;

            // Обновить текст количества
            if (countText != null)
            {
                countText.text = $"x{UnitData.count}";
            }

            // Обновить индикатор готовности
            if (readyIndicator != null)
            {
                bool canAct = !UnitData.has_moved &&
                              UnitData.player_id == GameManager.Instance?.CurrentPlayerId &&
                              GameManager.Instance?.CurrentState?.IsMyTurn(GameManager.Instance.CurrentPlayerId) == true;
                readyIndicator.SetActive(canAct);
            }

            // Обновить выделение
            UpdateSelection();
        }

        private void UpdateSelection()
        {
            if (selectionIndicator == null) return;

            bool isSelected = GameManager.Instance?.SelectedUnit?.id == UnitId;
            selectionIndicator.enabled = isSelected;

            if (isSelected)
            {
                selectionIndicator.color = new Color(1f, 0.9f, 0f, 0.8f); // Жёлтый
            }
        }

        public void MoveTo(Vector3 position)
        {
            if (_isMoving)
            {
                StopAllCoroutines();
            }

            if (Vector3.Distance(transform.position, position) > 0.01f)
            {
                StartCoroutine(MoveAnimation(position));
            }
        }

        private IEnumerator MoveAnimation(Vector3 targetPosition)
        {
            _isMoving = true;
            Vector3 startPosition = transform.position;
            float elapsed = 0f;

            while (elapsed < moveDuration)
            {
                elapsed += Time.deltaTime;
                float t = moveCurve.Evaluate(elapsed / moveDuration);
                transform.position = Vector3.Lerp(startPosition, targetPosition, t);
                yield return null;
            }

            transform.position = targetPosition;
            _isMoving = false;
        }

        public void PlayAttackAnimation(Vector3 targetPosition, Action onComplete = null)
        {
            StartCoroutine(AttackAnimation(targetPosition, onComplete));
        }

        private IEnumerator AttackAnimation(Vector3 targetPosition, Action onComplete)
        {
            Vector3 startPosition = transform.position;
            Vector3 direction = (targetPosition - startPosition).normalized;

            // Рывок вперёд
            float attackDuration = 0.1f;
            float elapsed = 0f;
            Vector3 attackPosition = startPosition + direction * 0.3f;

            while (elapsed < attackDuration)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / attackDuration;
                transform.position = Vector3.Lerp(startPosition, attackPosition, t);
                yield return null;
            }

            // Вернуться назад
            elapsed = 0f;
            while (elapsed < attackDuration)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / attackDuration;
                transform.position = Vector3.Lerp(attackPosition, startPosition, t);
                yield return null;
            }

            transform.position = startPosition;
            onComplete?.Invoke();
        }

        public void PlayHitAnimation()
        {
            StartCoroutine(HitAnimation());
        }

        private IEnumerator HitAnimation()
        {
            // Тряска
            Vector3 originalPosition = transform.position;
            float duration = 0.2f;
            float elapsed = 0f;
            float intensity = 0.1f;

            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                float x = originalPosition.x + UnityEngine.Random.Range(-intensity, intensity);
                float y = originalPosition.y + UnityEngine.Random.Range(-intensity, intensity);
                transform.position = new Vector3(x, y, originalPosition.z);
                yield return null;
            }

            transform.position = originalPosition;

            // Изменить цвет на красный ненадолго
            if (backgroundRenderer != null)
            {
                Color originalColor = backgroundRenderer.color;
                backgroundRenderer.color = Color.red;
                yield return new WaitForSeconds(0.1f);
                backgroundRenderer.color = originalColor;
            }
        }

        public void PlayDeathAnimation(Action onComplete = null)
        {
            StartCoroutine(DeathAnimation(onComplete));
        }

        private IEnumerator DeathAnimation(Action onComplete)
        {
            float duration = 0.3f;
            float elapsed = 0f;
            Vector3 originalScale = transform.localScale;

            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / duration;

                // Уменьшение и прозрачность
                transform.localScale = Vector3.Lerp(originalScale, Vector3.zero, t);

                if (backgroundRenderer != null)
                {
                    Color c = backgroundRenderer.color;
                    c.a = 1 - t;
                    backgroundRenderer.color = c;
                }

                yield return null;
            }

            onComplete?.Invoke();
            Destroy(gameObject);
        }

        private void OnMouseDown()
        {
            OnUnitClicked?.Invoke(UnitId);
        }

        private void OnMouseEnter()
        {
            // Можно добавить эффект при наведении
            transform.localScale = Vector3.one * 1.1f;
        }

        private void OnMouseExit()
        {
            transform.localScale = Vector3.one;
        }

        private void Update()
        {
            // Обновлять визуальное состояние (для индикатора готовности)
            UpdateSelection();
        }
    }
}
