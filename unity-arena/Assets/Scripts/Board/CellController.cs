using System;
using UnityEngine;

namespace ModernHomm.Board
{
    /// <summary>
    /// Контроллер отдельной клетки на поле
    /// </summary>
    public class CellController : MonoBehaviour
    {
        [Header("References")]
        [SerializeField] private SpriteRenderer backgroundRenderer;
        [SerializeField] private SpriteRenderer highlightRenderer;
        [SerializeField] private BoxCollider2D clickCollider;

        public event Action<int, int> OnCellClicked;

        public int X { get; private set; }
        public int Y { get; private set; }
        public CellHighlightType HighlightType { get; private set; } = CellHighlightType.None;

        private Color _baseColor;
        private Color _highlightColor;

        public void Initialize(int x, int y, Color baseColor)
        {
            X = x;
            Y = y;
            _baseColor = baseColor;

            if (backgroundRenderer != null)
            {
                backgroundRenderer.color = baseColor;
            }

            if (highlightRenderer != null)
            {
                highlightRenderer.enabled = false;
            }
        }

        public void SetHighlight(Color color, CellHighlightType type)
        {
            HighlightType = type;
            _highlightColor = color;

            if (highlightRenderer != null)
            {
                highlightRenderer.color = color;
                highlightRenderer.enabled = true;
            }
        }

        public void ClearHighlight()
        {
            HighlightType = CellHighlightType.None;

            if (highlightRenderer != null)
            {
                highlightRenderer.enabled = false;
            }
        }

        private void OnMouseDown()
        {
            OnCellClicked?.Invoke(X, Y);
        }

        private void OnMouseEnter()
        {
            // Подсветка при наведении
            if (HighlightType != CellHighlightType.None)
            {
                if (highlightRenderer != null)
                {
                    Color hoverColor = _highlightColor;
                    hoverColor.a = Mathf.Min(1f, hoverColor.a + 0.2f);
                    highlightRenderer.color = hoverColor;
                }
            }
        }

        private void OnMouseExit()
        {
            // Вернуть нормальную подсветку
            if (HighlightType != CellHighlightType.None && highlightRenderer != null)
            {
                highlightRenderer.color = _highlightColor;
            }
        }
    }
}
